"""
Sentry Integration

Provides Sentry error tracking and performance monitoring.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)

# Track if Sentry is available and initialized
_sentry_available = False
_sentry_initialized = False
_sentry_sdk = None

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    _sentry_available = True
    _sentry_sdk = sentry_sdk
except ImportError:
    logger.debug("Sentry SDK not installed. Error tracking disabled.")


@dataclass
class SentryConfig:
    """Sentry configuration."""
    dsn: Optional[str] = None
    environment: str = "development"
    release: Optional[str] = None
    sample_rate: float = 1.0
    traces_sample_rate: float = 0.1
    profiles_sample_rate: float = 0.1
    
    # Feature flags
    enable_tracing: bool = True
    enable_profiling: bool = False
    attach_stacktrace: bool = True
    send_default_pii: bool = False
    
    # Filtering
    ignore_errors: List[str] = field(default_factory=list)
    deny_urls: List[str] = field(default_factory=list)
    
    # Debug
    debug: bool = False
    
    @classmethod
    def from_env(cls) -> "SentryConfig":
        """Create config from environment variables."""
        return cls(
            dsn=os.getenv("SENTRY_DSN"),
            environment=os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")),
            release=os.getenv("SENTRY_RELEASE", os.getenv("APP_VERSION")),
            sample_rate=float(os.getenv("SENTRY_SAMPLE_RATE", "1.0")),
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
            enable_tracing=os.getenv("SENTRY_ENABLE_TRACING", "true").lower() == "true",
            enable_profiling=os.getenv("SENTRY_ENABLE_PROFILING", "false").lower() == "true",
            debug=os.getenv("SENTRY_DEBUG", "false").lower() == "true",
        )


class SentryClient:
    """
    Sentry client wrapper.
    
    Provides a clean interface for Sentry operations with
    graceful fallbacks when Sentry is not available.
    """
    
    def __init__(self, config: Optional[SentryConfig] = None):
        """
        Initialize Sentry client.
        
        Args:
            config: Sentry configuration. If None, loads from environment.
        """
        self.config = config or SentryConfig.from_env()
        self._initialized = False
        self._hub = None
    
    def init(self) -> bool:
        """
        Initialize Sentry SDK.
        
        Returns:
            True if Sentry was initialized, False otherwise.
        """
        global _sentry_initialized
        
        if not _sentry_available:
            logger.warning("Sentry SDK not available. Install with: pip install sentry-sdk")
            return False
        
        if not self.config.dsn:
            logger.debug("Sentry DSN not configured. Error tracking disabled.")
            return False
        
        if _sentry_initialized:
            logger.debug("Sentry already initialized.")
            return True
        
        try:
            integrations = [
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR,
                ),
                AsyncioIntegration(),
            ]
            
            _sentry_sdk.init(
                dsn=self.config.dsn,
                environment=self.config.environment,
                release=self.config.release,
                sample_rate=self.config.sample_rate,
                traces_sample_rate=self.config.traces_sample_rate if self.config.enable_tracing else 0.0,
                profiles_sample_rate=self.config.profiles_sample_rate if self.config.enable_profiling else 0.0,
                attach_stacktrace=self.config.attach_stacktrace,
                send_default_pii=self.config.send_default_pii,
                debug=self.config.debug,
                integrations=integrations,
                before_send=self._before_send,
            )
            
            self._initialized = True
            _sentry_initialized = True
            logger.info(f"Sentry initialized for environment: {self.config.environment}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
            return False
    
    def _before_send(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Filter events before sending to Sentry.
        
        Args:
            event: The event to be sent.
            hint: Additional information about the event.
        
        Returns:
            The event to send, or None to drop it.
        """
        # Filter out ignored errors
        if "exception" in event:
            for exc_info in event.get("exception", {}).get("values", []):
                exc_type = exc_info.get("type", "")
                if exc_type in self.config.ignore_errors:
                    return None
        
        return event
    
    def capture_exception(
        self,
        error: Optional[Exception] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Capture an exception.
        
        Args:
            error: The exception to capture. If None, captures current exception.
            **kwargs: Additional data to attach.
        
        Returns:
            Event ID if captured, None otherwise.
        """
        if not _sentry_available or not _sentry_initialized:
            if error:
                logger.exception(f"Error (not sent to Sentry): {error}")
            return None
        
        return _sentry_sdk.capture_exception(error, **kwargs)
    
    def capture_message(
        self,
        message: str,
        level: str = "info",
        **kwargs
    ) -> Optional[str]:
        """
        Capture a message.
        
        Args:
            message: The message to capture.
            level: Log level (debug, info, warning, error, fatal).
            **kwargs: Additional data to attach.
        
        Returns:
            Event ID if captured, None otherwise.
        """
        if not _sentry_available or not _sentry_initialized:
            logger.log(getattr(logging, level.upper(), logging.INFO), message)
            return None
        
        return _sentry_sdk.capture_message(message, level=level, **kwargs)
    
    def set_user(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        username: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Set user context.
        
        Args:
            user_id: User ID.
            email: User email.
            username: Username.
            **kwargs: Additional user data.
        """
        if not _sentry_available or not _sentry_initialized:
            return
        
        user_data = {
            k: v for k, v in {
                "id": user_id,
                "email": email,
                "username": username,
                **kwargs,
            }.items() if v is not None
        }
        
        _sentry_sdk.set_user(user_data)
    
    def set_context(self, key: str, value: Dict[str, Any]) -> None:
        """
        Set additional context.
        
        Args:
            key: Context key.
            value: Context data.
        """
        if not _sentry_available or not _sentry_initialized:
            return
        
        _sentry_sdk.set_context(key, value)
    
    def set_tag(self, key: str, value: str) -> None:
        """
        Set a tag.
        
        Args:
            key: Tag key.
            value: Tag value.
        """
        if not _sentry_available or not _sentry_initialized:
            return
        
        _sentry_sdk.set_tag(key, value)
    
    def add_breadcrumb(
        self,
        message: str,
        category: str = "default",
        level: str = "info",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a breadcrumb.
        
        Args:
            message: Breadcrumb message.
            category: Category for grouping.
            level: Log level.
            data: Additional data.
        """
        if not _sentry_available or not _sentry_initialized:
            return
        
        _sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data,
        )
    
    @contextmanager
    def start_transaction(
        self,
        name: str,
        op: str = "task",
        **kwargs
    ):
        """
        Start a transaction for performance monitoring.
        
        Args:
            name: Transaction name.
            op: Operation type.
            **kwargs: Additional transaction data.
        
        Yields:
            Transaction object or None.
        """
        if not _sentry_available or not _sentry_initialized or not self.config.enable_tracing:
            yield None
            return
        
        with _sentry_sdk.start_transaction(name=name, op=op, **kwargs) as transaction:
            yield transaction
    
    @contextmanager
    def start_span(
        self,
        description: str,
        op: str = "task",
    ):
        """
        Start a span within a transaction.
        
        Args:
            description: Span description.
            op: Operation type.
        
        Yields:
            Span object or None.
        """
        if not _sentry_available or not _sentry_initialized:
            yield None
            return
        
        with _sentry_sdk.start_span(description=description, op=op) as span:
            yield span
    
    def get_current_transaction(self):
        """Get the current transaction."""
        if not _sentry_available or not _sentry_initialized:
            return None
        
        return _sentry_sdk.Hub.current.scope.transaction
    
    def flush(self, timeout: float = 2.0) -> None:
        """
        Flush pending events.
        
        Args:
            timeout: Maximum time to wait.
        """
        if not _sentry_available or not _sentry_initialized:
            return
        
        _sentry_sdk.flush(timeout=timeout)


# Global client instance
_client: Optional[SentryClient] = None


def init_sentry(config: Optional[SentryConfig] = None) -> bool:
    """
    Initialize Sentry globally.
    
    Args:
        config: Sentry configuration.
    
    Returns:
        True if initialized successfully.
    """
    global _client
    _client = SentryClient(config)
    return _client.init()


def get_client() -> SentryClient:
    """Get the global Sentry client."""
    global _client
    if _client is None:
        _client = SentryClient()
    return _client


def capture_exception(error: Optional[Exception] = None, **kwargs) -> Optional[str]:
    """Capture an exception."""
    return get_client().capture_exception(error, **kwargs)


def capture_message(message: str, level: str = "info", **kwargs) -> Optional[str]:
    """Capture a message."""
    return get_client().capture_message(message, level, **kwargs)


def set_user(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    **kwargs
) -> None:
    """Set user context."""
    get_client().set_user(user_id, email, username, **kwargs)


def set_context(key: str, value: Dict[str, Any]) -> None:
    """Set additional context."""
    get_client().set_context(key, value)


def set_tag(key: str, value: str) -> None:
    """Set a tag."""
    get_client().set_tag(key, value)


@contextmanager
def start_transaction(name: str, op: str = "task", **kwargs):
    """Start a transaction."""
    with get_client().start_transaction(name, op, **kwargs) as transaction:
        yield transaction


def get_transaction():
    """Get current transaction."""
    return get_client().get_current_transaction()


def traced(name: Optional[str] = None, op: str = "function"):
    """
    Decorator to trace a function.
    
    Args:
        name: Transaction name. Defaults to function name.
        op: Operation type.
    """
    def decorator(func: Callable):
        transaction_name = name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with get_client().start_span(description=transaction_name, op=op):
                return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with get_client().start_span(description=transaction_name, op=op):
                return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
