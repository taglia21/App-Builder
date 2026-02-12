"""Centralized configuration using Pydantic Settings."""
import os
from typing import Optional, Dict, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with type-safe configuration from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )
    
    # Application Settings
    APP_NAME: str = "Valeric"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "production", "testing"] = "development"
    DEBUG: bool = Field(default=False)
    
    # LLM Provider API Keys (all optional for demo mode)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    PERPLEXITY_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    
    # Deployment Tokens
    VERCEL_TOKEN: Optional[str] = None
    VERCEL_ORG_ID: Optional[str] = None
    VERCEL_PROJECT_ID: Optional[str] = None
    
    # Database (optional)
    DATABASE_URL: Optional[str] = None
    
    # Redis (optional)
    REDIS_URL: Optional[str] = None
    
    # Demo Mode
    DEMO_MODE: bool = False
    DEMO_EMAIL: str = "demo@valeric.dev"
    DEMO_PASSWORD: str = ""  # MUST be set via DEMO_PASSWORD env variable
    DEMO_TOKEN: Optional[str] = None  # Optional magic token for /demo?token=xxx URL
    
    # Admin
    ADMIN_EMAILS: str = ""  # Comma-separated admin emails
    
    # Default LLM Provider
    DEFAULT_LLM_PROVIDER: str = "auto"
    
    @field_validator('DEBUG', mode='before')
    @classmethod
    def parse_debug(cls, v):
        """Parse DEBUG from string to bool."""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes')
        return bool(v)
    
    @field_validator('DEMO_MODE', mode='before')
    @classmethod
    def parse_demo_mode(cls, v):
        """Parse DEMO_MODE from string to bool."""
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes')
        return bool(v)
    
    def get_llm_provider_config(self) -> Dict[str, Optional[str]]:
        """Get all LLM provider API keys as a dictionary.
        
        Returns:
            Dictionary mapping provider names to API keys
        """
        return {
            'openai': self.OPENAI_API_KEY,
            'anthropic': self.ANTHROPIC_API_KEY,
            'google': self.GOOGLE_API_KEY,
            'perplexity': self.PERPLEXITY_API_KEY,
            'groq': self.GROQ_API_KEY,
        }
    
    def get_provider_keys(self) -> Dict[str, Optional[str]]:
        """Alias for get_llm_provider_config."""
        return self.get_llm_provider_config()
    
    def has_llm_provider(self) -> bool:
        """Check if at least one LLM provider is configured.
        
        Returns:
            True if any LLM provider API key is set
        """
        providers = self.get_llm_provider_config()
        return any(key is not None for key in providers.values())
    
    @property
    def llm_providers(self) -> Dict[str, Optional[str]]:
        """Property to access LLM provider config."""
        return self.get_llm_provider_config()
    
    def __repr__(self) -> str:
        """Safe repr that doesn't expose secrets."""
        return (
            f"Settings("
            f"APP_NAME='{self.APP_NAME}', "
            f"ENVIRONMENT='{self.ENVIRONMENT}', "
            f"DEBUG={self.DEBUG}, "
            f"DEMO_MODE={self.DEMO_MODE}, "
            f"has_llm_provider={self.has_llm_provider()}"
            ")"
        )


# Singleton instance
settings = Settings()
