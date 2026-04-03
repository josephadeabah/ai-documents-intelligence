from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI Document Intelligence API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="development")
    
    # Database
    DATABASE_URL: str = Field(default="postgresql://postgres:postgres@localhost:5432/ragdb")
    DATABASE_POOL_SIZE: int = Field(default=20)
    DATABASE_MAX_OVERFLOW: int = Field(default=40)
    
    # OpenAI
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-ada-002")
    
    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None)
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None)
    AWS_REGION: str = Field(default="us-east-1")
    S3_BUCKET: Optional[str] = Field(default=None)
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379")
    
    # Security
    SECRET_KEY: str = Field(default="change-this-in-production")
    API_RATE_LIMIT: int = Field(default=100)
    API_RATE_LIMIT_PERIOD: int = Field(default=60)
    
    # Document Processing
    CHUNK_SIZE: int = Field(default=500)
    CHUNK_OVERLAP: int = Field(default=50)
    MAX_FILE_SIZE_MB: int = Field(default=10)
    ALLOWED_EXTENSIONS: List[str] = Field(default=[".pdf", ".txt", ".md"])
    
    # Embedding
    EMBEDDING_DIM: int = Field(default=1536)
    USE_CLOUD_EMBEDDINGS: bool = Field(default=True)
    LOCAL_EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2")
    BATCH_SIZE: int = Field(default=100)
    
    # RAG
    RAG_TOP_K: int = Field(default=5)
    RAG_TEMPERATURE: float = Field(default=0.7)
    RAG_MAX_TOKENS: int = Field(default=500)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v):
        if "postgresql" not in v and "sqlite" not in v:
            raise ValueError("DATABASE_URL must be postgresql or sqlite")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()