"""Services module for external integrations."""
from .config import Settings, get_settings
from .email_service import EmailService

__all__ = ['EmailService', 'Settings', 'get_settings']
