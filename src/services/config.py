"""Application configuration using environment variables."""
import logging
from functools import lru_cache
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_INSECURE_SECRET_KEYS = {
    "change-me-in-production",
    "nexusai-dev-secret-key-change-in-production",
    "secret",
    "password",
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "App-Builder"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    BASE_URL: str = "http://localhost:8000"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID_PRO: Optional[str] = None
    STRIPE_PRICE_ID_ENTERPRISE: Optional[str] = None

    # Email (SendGrid)
    SENDGRID_API_KEY: Optional[str] = None
    EMAIL_FROM_ADDRESS: str = "noreply@example.com"
    EMAIL_FROM_NAME: str = "App-Builder"

    # Email (SMTP fallback)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True

    # Redis (for caching/queues)
    REDIS_URL: Optional[str] = None

    # OpenAI / LLM
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @model_validator(mode='after')
    def _validate_secret_key_in_production(self) -> 'Settings':
        """Raise an error if SECRET_KEY is an insecure default in production."""
        if self.is_production and self.SECRET_KEY in _INSECURE_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY must be changed from its default value in production. "
                "Generate a strong random key: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        if self.is_production and len(self.SECRET_KEY) < 32:
            raise ValueError(
                f"SECRET_KEY is only {len(self.SECRET_KEY)} characters. "
                "Production requires at least 32 random characters."
            )
        return self

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
