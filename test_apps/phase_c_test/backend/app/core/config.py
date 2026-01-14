"""Application configuration with validation."""

import logging
import os
import warnings
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Weak/default SECRET_KEY patterns to warn about
WEAK_SECRET_PATTERNS = [
    "changeme",
    "your-secret-key",
    "change-in-production",
    "CHANGE_ME",
    "secret",
]


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI-PoweredCrmAutomation"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@db:5432/ai_poweredcrmautomation"
    )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Password requirements
    MIN_PASSWORD_LENGTH: int = 8

    # OAuth
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")

    # CORS - configurable via environment
    # Set CORS_ORIGINS as comma-separated URLs, e.g., "http://localhost:3000,https://myapp.com"
    CORS_ORIGINS: List[str] = _parse_cors_origins()

    class Config:
        env_file = ".env"

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Warn if SECRET_KEY appears to be a weak default."""
        is_weak = any(pattern.lower() in v.lower() for pattern in WEAK_SECRET_PATTERNS)
        is_short = len(v) < 32

        if is_weak or is_short:
            warnings.warn(
                "\n" + "=" * 60 + "\n"
                "⚠️  SECURITY WARNING: SECRET_KEY appears to be weak!\n"
                "   For production, generate a secure key with:\n"
                '   python -c "import secrets; print(secrets.token_urlsafe(32))"\n'
                "=" * 60,
                UserWarning,
                stacklevel=2,
            )
        return v


def _parse_cors_origins() -> List[str]:
    """Parse CORS_ORIGINS from environment or use defaults."""
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        # Split by comma and strip whitespace
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]
    # Default origins for local development
    return ["http://localhost:3000", "http://localhost:8000"]


settings = Settings()

# Log startup configuration (non-sensitive)
logger.info(f"Starting {settings.APP_NAME}")
logger.info(f"Debug mode: {settings.DEBUG}")
logger.info(f"CORS origins: {settings.CORS_ORIGINS}")
