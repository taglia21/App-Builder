"""
Production Logging System

JSON-formatted structured logging with error tracking,
request tracing, and performance monitoring.
"""

import json
import logging
import os
import sys
import time
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
from typing import Optional

# Context variables for request tracing
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for production logging.

    Outputs structured JSON logs compatible with log aggregators
    like Datadog, ELK, CloudWatch, etc.
    """

    def __init__(self, service_name: str = "nexusai"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
        }

        # Add location info
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName,
            "module": record.module,
        }

        # Add request context if available
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            log_data["user_id"] = user_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data, default=str)


class TextFormatter(logging.Formatter):
    """Human-readable formatter for development."""

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, '')
        reset = self.RESET

        # Format timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Format message
        message = f"{color}{timestamp} | {record.levelname:8} | {record.name} | {record.getMessage()}{reset}"

        # Add request context if available
        request_id = request_id_var.get()
        if request_id:
            message = f"{message} | req:{request_id[:8]}"

        # Add exception info
        if record.exc_info:
            message += f"\n{traceback.format_exception(*record.exc_info)}"

        return message


class StructuredLogger:
    """
    Structured logger with context support.

    Usage:
        logger = get_logger(__name__)
        logger.info("User logged in", user_id="123", ip="1.2.3.4")
        logger.error("Payment failed", error=str(e), amount=100)
    """

    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _log(self, log_level: int, message: str, **kwargs):
        """Log with extra structured data."""
        extra = {'extra_data': kwargs} if kwargs else {}
        self._logger.log(log_level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs):
        self._logger.error(message, exc_info=exc_info, extra={'extra_data': kwargs})

    def critical(self, message: str, exc_info: bool = True, **kwargs):
        self._logger.critical(message, exc_info=exc_info, extra={'extra_data': kwargs})

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._logger.exception(message, extra={'extra_data': kwargs})


def setup_logging(
    level: str = None,
    format_type: str = None,
    service_name: str = "nexusai",
) -> None:
    """
    Configure application-wide logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Output format (json, text)
        service_name: Service name for logs
    """
    # Get config from environment
    level = level or os.getenv("LOG_LEVEL", "INFO")
    format_type = format_type or os.getenv("LOG_FORMAT", "json")
    environment = os.getenv("ENVIRONMENT", "development")

    # Force text format in development
    if environment == "development":
        format_type = "text"

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Set formatter
    if format_type == "json":
        handler.setFormatter(JSONFormatter(service_name))
    else:
        handler.setFormatter(TextFormatter())

    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("stripe").setLevel(logging.INFO)

    # Log startup
    logger = get_logger(__name__)
    logger.info(
        "Logging initialized",
        level=level,
        format=format_type,
        environment=environment,
    )


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(logging.getLogger(name))


def set_request_context(request_id: str = None, user_id: str = None):
    """Set request context for logging."""
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context():
    """Clear request context after request completes."""
    request_id_var.set(None)
    user_id_var.set(None)


def log_execution_time(logger: StructuredLogger = None):
    """
    Decorator to log function execution time.

    Usage:
        @log_execution_time()
        def my_function():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    f"{func.__name__} completed",
                    function=func.__name__,
                    execution_time_ms=round(execution_time * 1000, 2),
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"{func.__name__} failed",
                    function=func.__name__,
                    execution_time_ms=round(execution_time * 1000, 2),
                    error=str(e),
                    exc_info=True,
                )
                raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger(func.__module__)

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(
                    f"{func.__name__} completed",
                    function=func.__name__,
                    execution_time_ms=round(execution_time * 1000, 2),
                )
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(
                    f"{func.__name__} failed",
                    function=func.__name__,
                    execution_time_ms=round(execution_time * 1000, 2),
                    error=str(e),
                    exc_info=True,
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator


# FastAPI middleware for request logging
class RequestLoggingMiddleware:
    """
    FastAPI middleware for structured request logging.

    Logs all requests with timing, status codes, and error details.
    """

    def __init__(self, app):
        self.app = app
        self.logger = get_logger("request")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import uuid

        # Generate request ID
        request_id = str(uuid.uuid4())
        set_request_context(request_id=request_id)

        start_time = time.time()
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            self.logger.exception(
                "Request failed",
                path=scope.get("path"),
                method=scope.get("method"),
                error=str(e),
            )
            raise
        finally:
            execution_time = time.time() - start_time

            # Get client IP
            client = scope.get("client", ("unknown", 0))
            client_ip = client[0] if client else "unknown"

            # Log request
            log_level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
            getattr(self.logger, log_level)(
                f"{scope.get('method', 'UNKNOWN')} {scope.get('path', '/')} {status_code}",
                request_id=request_id,
                method=scope.get("method"),
                path=scope.get("path"),
                status_code=status_code,
                duration_ms=round(execution_time * 1000, 2),
                client_ip=client_ip,
            )

            clear_request_context()


def setup_sentry():
    """Initialize Sentry for error tracking."""
    sentry_dsn = os.getenv("SENTRY_DSN")
    if not sentry_dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")),
            traces_sample_rate=0.1,  # 10% of transactions
            profiles_sample_rate=0.1,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
        )

        logger = get_logger(__name__)
        logger.info("Sentry error tracking initialized")
    except ImportError:
        pass  # Sentry not installed


# Initialize logging on import if in production
if os.getenv("ENVIRONMENT") == "production":
    setup_logging()
    setup_sentry()
