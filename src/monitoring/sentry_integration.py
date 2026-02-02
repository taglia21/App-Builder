"""Sentry error monitoring integration."""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def init_sentry(app=None) -> bool:
    """Initialize Sentry error tracking.
    
    Args:
        app: Flask application instance (optional)
        
    Returns:
        bool: True if Sentry was initialized, False otherwise
    """
    sentry_dsn = os.getenv('SENTRY_DSN')
    
    if not sentry_dsn:
        logger.info("SENTRY_DSN not configured, skipping Sentry initialization")
        return False
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                FlaskIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            profiles_sample_rate=float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', '0.1')),
            environment=os.getenv('ENVIRONMENT', 'development'),
            release=os.getenv('APP_VERSION', '1.0.0'),
        )
        
        logger.info("Sentry initialized successfully")
        return True
        
    except ImportError:
        logger.warning("sentry-sdk not installed, skipping Sentry initialization")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def capture_exception(exception: Exception, **kwargs) -> Optional[str]:
    """Capture an exception to Sentry.
    
    Args:
        exception: The exception to capture
        **kwargs: Additional context to attach
        
    Returns:
        Event ID if captured, None otherwise
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in kwargs.items():
                scope.set_extra(key, value)
            return sentry_sdk.capture_exception(exception)
    except ImportError:
        logger.error(f"Exception (Sentry not available): {exception}")
        return None


def capture_message(message: str, level: str = 'info', **kwargs) -> Optional[str]:
    """Capture a message to Sentry.
    
    Args:
        message: The message to capture
        level: Log level (debug, info, warning, error, fatal)
        **kwargs: Additional context
        
    Returns:
        Event ID if captured, None otherwise
    """
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for key, value in kwargs.items():
                scope.set_extra(key, value)
            return sentry_sdk.capture_message(message, level=level)
    except ImportError:
        logger.log(
            getattr(logging, level.upper(), logging.INFO),
            f"Message (Sentry not available): {message}"
        )
        return None
