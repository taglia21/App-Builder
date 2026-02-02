"""Application configuration using environment variables."""
import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = Field(default="App-Builder", env="APP_NAME")
    APP_ENV: str = Field(default="development", env="APP_ENV")
    DEBUG: bool = Field(default=False, env="DEBUG")
    SECRET_KEY: str = Field(default="change-me-in-production", env="SECRET_KEY")
    BASE_URL: str = Field(default="http://localhost:8000", env="BASE_URL")
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./app.db",
        env="DATABASE_URL"
    )
    DATABASE_POOL_SIZE: int = Field(default=5, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, env="DATABASE_MAX_OVERFLOW")
    
    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = Field(default=None, env="STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY: Optional[str] = Field(default=None, env="STRIPE_PUBLISHABLE_KEY")
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRET")
    STRIPE_PRICE_ID_PRO: Optional[str] = Field(default=None, env="STRIPE_PRICE_ID_PRO")
    STRIPE_PRICE_ID_ENTERPRISE: Optional[str] = Field(default=None, env="STRIPE_PRICE_ID_ENTERPRISE")
    
    # Email (SendGrid)
    SENDGRID_API_KEY: Optional[str] = Field(default=None, env="SENDGRID_API_KEY")
    EMAIL_FROM_ADDRESS: str = Field(default="noreply@example.com", env="EMAIL_FROM_ADDRESS")
    EMAIL_FROM_NAME: str = Field(default="App-Builder", env="EMAIL_FROM_NAME")
    
    # Email (SMTP fallback)
    SMTP_HOST: Optional[str] = Field(default=None, env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USER: Optional[str] = Field(default=None, env="SMTP_USER")
    SMTP_PASSWORD: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    SMTP_USE_TLS: bool = Field(default=True, env="SMTP_USE_TLS")
    
    # Redis (for caching/queues)
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    
    # OpenAI / LLM
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"
    
    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"
    
    @property
    def stripe_configured(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY)
    
    @property
    def email_configured(self) -> bool:
        return bool(self.SENDGRID_API_KEY) or bool(self.SMTP_HOST)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
