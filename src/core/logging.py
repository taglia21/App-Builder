"""Logging configuration for LaunchForge."""
import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", format_json: bool = False) -> logging.Logger:
    """Setup structured logging for the application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_json: Whether to use JSON format (for production)
        
    Returns:
        Configured logger
    """
    # Get root logger
    logger = logging.getLogger()
    
    # Set level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    
    # Create formatter
    if format_json:
        # JSON format for production
        formatter = logging.Formatter(
            '{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Context manager for request ID tracking
class RequestIDFilter(logging.Filter):
    """Add request ID to log records."""
    
    def __init__(self, request_id: Optional[str] = None):
        """Initialize filter with request ID.
        
        Args:
            request_id: Request ID to add to logs
        """
        super().__init__()
        self.request_id = request_id or "no-request-id"
    
    def filter(self, record):
        """Add request_id to the record."""
        record.request_id = self.request_id
        return True


def add_request_id_to_logs(request_id: str):
    """Add request ID filter to all handlers.
    
    Args:
        request_id: Request ID to track
    """
    filter_obj = RequestIDFilter(request_id)
    
    for handler in logging.root.handlers:
        handler.addFilter(filter_obj)
