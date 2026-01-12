from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    """Application settings с автозагрузкой из .env"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # API Keys
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: str = ""  # Optional fallback
    
    # LLM Configuration
    LLM_MODEL: str = "claude-3-5-sonnet-20241022"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096
    
    # Vision API
    VISION_FALLBACK_ENABLED: bool = True
    VISION_MAX_RETRIES: int = 3
    
    # FAISS
    FAISS_INDEX_PATH: Path = Path("data/embeddings")
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".xlsx", ".xls"]
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 10
    
    # Database (если понадобится)
    DATABASE_URL: str = "sqlite:///./data/fintech_agent.db"


settings = Settings()
