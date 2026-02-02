"""Services module for external integrations."""
from .email_service import EmailService
from .config import Settings, get_settings

__all__ = ['EmailService', 'Settings', 'get_settings']
