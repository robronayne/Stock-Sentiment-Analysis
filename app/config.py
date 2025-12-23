"""Application configuration"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Database
    database_url: str = "mysql+pymysql://sentimentbot:changeme123@localhost:3306/sentiment_analysis"
    
    # Ollama
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    
    # API Keys
    finnhub_api_key: str = ""
    
    # Application
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Rate Limiting
    max_requests_per_hour: int = 60
    
    # Data Collection
    news_lookback_days: int = 7
    article_retention_days: int = 30
    
    # Validation
    run_validation_hour: int = 2  # Hour to run daily validation (0-23)
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
