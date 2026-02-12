"""Services module for external integrations.

DEPRECATED: Use src.config.settings for Settings and src.emails.client for EmailClient.
These re-exports remain for backward compatibility.
"""
import warnings

try:
    from src.config.settings import Settings, settings
    def get_settings() -> Settings:
        warnings.warn("Use src.config.settings directly", DeprecationWarning, stacklevel=2)
        return settings
except Exception:
    from .config import Settings, get_settings

try:
    from src.emails.client import EmailClient as EmailService
except Exception:
    from .email_service import EmailService

__all__ = ['EmailService', 'Settings', 'get_settings']
