from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
from pathlib import Path
from typing import Optional

from ..models.kpi_models import AnalysisResult, ReportType
from ..agents.analyst_agent import FinancialAnalystAgent
from ..utils.logging_config import get_logger, setup_logging
from ..utils.validators import InputValidator
from ..core.config import settings
from ..core.exceptions import ValidationError, ProcessingError

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hooks"""
    # Startup
    logger.info("🚀 Starting FinTech Analyst Agent API")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Initialize agent
    app.state.agent = FinancialAnalystAgent()
    
    # Health check
    logger.info("✅ API ready")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down API")


app = FastAPI(
    title="FinTech Analyst Agent API",
    description="AI-powered финансовый аналитик для анализа отчетов",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiting middleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }


# Main analysis endpoint
@app.post("/api/v1/analyze", response_model=AnalysisResult)
@limiter.limit("10/minute")  # Rate limit
async def analyze_report(
    file: UploadFile = File(...),
    report_type: ReportType = ReportType.BALANCE_SHEET,
    company_name: Optional[str] = None
):
    """
    Анализ финансового отчета
    
    Args:
        file: PDF/Excel файл отчета
        report_type: Тип отчета
        company_name: Название компании (опционально)
    
    Returns:
        AnalysisResult с извлеченными KPI
    
    Raises:
        HTTPException: При ошибках валидации или обработки
    """
    start_time = time.time()
    
    try:
        # Валидация файла
        temp_path = Path(f"/tmp/{file.filename}")
        
        with open(temp_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        InputValidator.validate_file_upload(temp_path)
        
        # Валидация company name
        if company_name:
            company_name = InputValidator.validate_company_name(company_name)
        
        # Анализ через агента
        agent: FinancialAnalystAgent = app.state.agent
        result = await agent.analyze_document(
            file_path=temp_path,
            report_type=report_type,
            company_name=company_name
        )
        
        # Добавление processing time
        result.processing_time = time.time() - start_time
        
        logger.info(
            f"Analysis completed in {result.processing_time:.2f}s",
            extra={
                "report_id": result.report_id,
                "report_type": report_type,
                "file_size": len(content)
            }
        )
        
        return result
        
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except ProcessingError as e:
        logger.error(f"Processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal processing error")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
        
    finally:
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()


# Error handlers
@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )


@app.exception_handler(ProcessingError)
async def processing_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Processing failed"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
