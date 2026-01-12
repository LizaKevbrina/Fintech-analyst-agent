import sys
import logging
from pathlib import Path
from loguru import logger
from typing import Optional

from ..core.config import settings


class InterceptHandler(logging.Handler):
    """Intercept standard logging и направить в loguru"""
    
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Setup structured logging с loguru
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
    """
    # Remove default handler
    logger.remove()
    
    # Уровень логирования
    level = log_level or settings.LOG_LEVEL
    
    # Console handler
    if settings.LOG_FORMAT == "json":
        # JSON format для production
        logger.add(
            sys.stderr,
            format="{message}",
            level=level,
            serialize=True,  # JSON output
            backtrace=True,
            diagnose=settings.DEBUG
        )
    else:
        # Human-readable для development
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=level,
            colorize=True,
            backtrace=True,
            diagnose=settings.DEBUG
        )
    
    # File handler для errors
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / "errors.log",
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Intercept uvicorn, fastapi logs
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
        logging.getLogger(logger_name).handlers = [InterceptHandler()]
    
    logger.info(f"Logging initialized (level={level}, format={settings.LOG_FORMAT})")


def get_logger(name: str):
    """Получение logger для модуля"""
    return logger.bind(module=name)
