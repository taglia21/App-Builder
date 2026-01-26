"""
Error Reporting

Custom error reporting with context, severity, and multiple destinations.
"""

import os
import json
import logging
import traceback
from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pathlib import Path
import httpx

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for grouping."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    DATABASE = "database"
    EXTERNAL_SERVICE = "external_service"
    PAYMENT = "payment"
    DEPLOYMENT = "deployment"
    GENERATION = "generation"
    RATE_LIMIT = "rate_limit"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context for an error."""
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Request info
    method: Optional[str] = None
    path: Optional[str] = None
    query_params: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, Any]] = None
    
    # Environment
    environment: str = "development"
    service: str = "nexusai"
    version: Optional[str] = None
    hostname: Optional[str] = None
    
    # Additional data
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "project_id": self.project_id,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "request": {
                "method": self.method,
                "path": self.path,
                "query_params": self.query_params,
                "headers": self._sanitize_headers(self.headers),
            } if self.method else None,
            "environment": self.environment,
            "service": self.service,
            "version": self.version,
            "hostname": self.hostname,
            "extra": self.extra,
        }
    
    def _sanitize_headers(self, headers: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """Remove sensitive headers."""
        if not headers:
            return None
        
        sensitive = {"authorization", "cookie", "x-api-key", "api-key"}
        return {
            k: "[REDACTED]" if k.lower() in sensitive else v
            for k, v in headers.items()
        }


@dataclass
class ErrorReport:
    """Complete error report."""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: ErrorCategory
    
    # Error details
    message: str
    error_type: str
    stacktrace: Optional[str] = None
    
    # Context
    context: Optional[ErrorContext] = None
    
    # Grouping
    fingerprint: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_id": self.error_id,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "error_type": self.error_type,
            "stacktrace": self.stacktrace,
            "context": self.context.to_dict() if self.context else None,
            "fingerprint": self.fingerprint,
            "tags": self.tags,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)


class ErrorReporter(ABC):
    """Abstract base class for error reporters."""
    
    @abstractmethod
    def report(self, error: ErrorReport) -> bool:
        """
        Report an error.
        
        Args:
            error: The error report to send.
        
        Returns:
            True if successfully reported.
        """
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Flush any pending reports."""
        pass


class ConsoleReporter(ErrorReporter):
    """Reports errors to console/logs."""
    
    def __init__(self, log_level: int = logging.ERROR):
        self.logger = logging.getLogger("error_reporter")
        self.log_level = log_level
    
    def report(self, error: ErrorReport) -> bool:
        """Report error to console."""
        level_map = {
            ErrorSeverity.DEBUG: logging.DEBUG,
            ErrorSeverity.INFO: logging.INFO,
            ErrorSeverity.WARNING: logging.WARNING,
            ErrorSeverity.ERROR: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }
        
        level = level_map.get(error.severity, logging.ERROR)
        
        message = (
            f"[{error.category.value}] {error.message}\n"
            f"Error ID: {error.error_id}\n"
            f"Type: {error.error_type}"
        )
        
        if error.context and error.context.user_id:
            message += f"\nUser: {error.context.user_id}"
        
        if error.stacktrace:
            message += f"\n\nStacktrace:\n{error.stacktrace}"
        
        self.logger.log(level, message)
        return True
    
    def flush(self) -> None:
        """No-op for console reporter."""
        pass


class FileReporter(ErrorReporter):
    """Reports errors to files."""
    
    def __init__(
        self,
        log_dir: str = "./logs/errors",
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        max_files: int = 10,
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self.max_files = max_files
        self._current_file = None
        self._current_size = 0
    
    def _get_log_file(self) -> Path:
        """Get current log file, rotating if needed."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        base_path = self.log_dir / f"errors-{today}.jsonl"
        
        if base_path.exists() and base_path.stat().st_size >= self.max_file_size:
            # Rotate
            for i in range(self.max_files - 1, 0, -1):
                old = self.log_dir / f"errors-{today}.{i}.jsonl"
                new = self.log_dir / f"errors-{today}.{i + 1}.jsonl"
                if old.exists():
                    old.rename(new)
            base_path.rename(self.log_dir / f"errors-{today}.1.jsonl")
        
        return base_path
    
    def report(self, error: ErrorReport) -> bool:
        """Report error to file."""
        try:
            log_file = self._get_log_file()
            with open(log_file, "a") as f:
                f.write(json.dumps(error.to_dict(), default=str) + "\n")
            return True
        except Exception as e:
            logger.error(f"Failed to write error to file: {e}")
            return False
    
    def flush(self) -> None:
        """No-op for file reporter."""
        pass


class WebhookReporter(ErrorReporter):
    """Reports errors to webhooks (Slack, Discord, etc.)."""
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        min_severity: ErrorSeverity = ErrorSeverity.ERROR,
        format_type: str = "slack",
    ):
        self.webhook_url = webhook_url or os.getenv("ERROR_WEBHOOK_URL")
        self.min_severity = min_severity
        self.format_type = format_type
        self._pending: List[ErrorReport] = []
    
    def _should_report(self, error: ErrorReport) -> bool:
        """Check if error meets minimum severity."""
        severity_order = [
            ErrorSeverity.DEBUG,
            ErrorSeverity.INFO,
            ErrorSeverity.WARNING,
            ErrorSeverity.ERROR,
            ErrorSeverity.CRITICAL,
        ]
        return severity_order.index(error.severity) >= severity_order.index(self.min_severity)
    
    def _format_slack(self, error: ErrorReport) -> Dict[str, Any]:
        """Format error for Slack."""
        color_map = {
            ErrorSeverity.DEBUG: "#808080",
            ErrorSeverity.INFO: "#36a64f",
            ErrorSeverity.WARNING: "#ff9800",
            ErrorSeverity.ERROR: "#f44336",
            ErrorSeverity.CRITICAL: "#9c27b0",
        }
        
        fields = [
            {"title": "Error ID", "value": error.error_id, "short": True},
            {"title": "Category", "value": error.category.value, "short": True},
            {"title": "Type", "value": error.error_type, "short": True},
            {"title": "Severity", "value": error.severity.value, "short": True},
        ]
        
        if error.context:
            if error.context.user_id:
                fields.append({"title": "User", "value": error.context.user_id, "short": True})
            if error.context.environment:
                fields.append({"title": "Environment", "value": error.context.environment, "short": True})
        
        return {
            "attachments": [{
                "color": color_map.get(error.severity, "#f44336"),
                "title": f"🚨 {error.severity.value.upper()}: {error.message[:100]}",
                "text": error.message,
                "fields": fields,
                "footer": "NexusAI Error Monitor",
                "ts": int(error.timestamp.timestamp()),
            }]
        }
    
    def _format_discord(self, error: ErrorReport) -> Dict[str, Any]:
        """Format error for Discord."""
        color_map = {
            ErrorSeverity.DEBUG: 0x808080,
            ErrorSeverity.INFO: 0x36a64f,
            ErrorSeverity.WARNING: 0xff9800,
            ErrorSeverity.ERROR: 0xf44336,
            ErrorSeverity.CRITICAL: 0x9c27b0,
        }
        
        return {
            "embeds": [{
                "title": f"🚨 {error.severity.value.upper()}",
                "description": error.message[:2000],
                "color": color_map.get(error.severity, 0xf44336),
                "fields": [
                    {"name": "Error ID", "value": error.error_id, "inline": True},
                    {"name": "Category", "value": error.category.value, "inline": True},
                    {"name": "Type", "value": error.error_type, "inline": True},
                ],
                "timestamp": error.timestamp.isoformat(),
            }]
        }
    
    def report(self, error: ErrorReport) -> bool:
        """Report error to webhook."""
        if not self.webhook_url or not self._should_report(error):
            return False
        
        try:
            if self.format_type == "slack":
                payload = self._format_slack(error)
            elif self.format_type == "discord":
                payload = self._format_discord(error)
            else:
                payload = error.to_dict()
            
            response = httpx.post(
                self.webhook_url,
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"Failed to send error to webhook: {e}")
            self._pending.append(error)
            return False
    
    def flush(self) -> None:
        """Retry pending reports."""
        pending = self._pending.copy()
        self._pending.clear()
        
        for error in pending:
            self.report(error)


class CompositeReporter(ErrorReporter):
    """Combines multiple reporters."""
    
    def __init__(self, reporters: Optional[List[ErrorReporter]] = None):
        self.reporters = reporters or []
    
    def add_reporter(self, reporter: ErrorReporter) -> None:
        """Add a reporter."""
        self.reporters.append(reporter)
    
    def report(self, error: ErrorReport) -> bool:
        """Report to all reporters."""
        success = True
        for reporter in self.reporters:
            try:
                if not reporter.report(error):
                    success = False
            except Exception as e:
                logger.error(f"Reporter {reporter.__class__.__name__} failed: {e}")
                success = False
        return success
    
    def flush(self) -> None:
        """Flush all reporters."""
        for reporter in self.reporters:
            try:
                reporter.flush()
            except Exception as e:
                logger.error(f"Failed to flush {reporter.__class__.__name__}: {e}")


# Factory functions
def create_error_reporter(
    console: bool = True,
    file: bool = True,
    webhook_url: Optional[str] = None,
    log_dir: str = "./logs/errors",
) -> CompositeReporter:
    """
    Create a composite error reporter.
    
    Args:
        console: Enable console reporting.
        file: Enable file reporting.
        webhook_url: Webhook URL for alerts.
        log_dir: Directory for error logs.
    
    Returns:
        Configured CompositeReporter.
    """
    reporters = []
    
    if console:
        reporters.append(ConsoleReporter())
    
    if file:
        reporters.append(FileReporter(log_dir=log_dir))
    
    if webhook_url:
        reporters.append(WebhookReporter(webhook_url=webhook_url))
    
    return CompositeReporter(reporters)


def create_error_report(
    exception: Exception,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    context: Optional[ErrorContext] = None,
    tags: Optional[Dict[str, str]] = None,
) -> ErrorReport:
    """
    Create an error report from an exception.
    
    Args:
        exception: The exception to report.
        severity: Error severity.
        category: Error category.
        context: Additional context.
        tags: Additional tags.
    
    Returns:
        ErrorReport instance.
    """
    import uuid
    
    return ErrorReport(
        error_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        severity=severity,
        category=category,
        message=str(exception),
        error_type=type(exception).__name__,
        stacktrace=traceback.format_exc(),
        context=context,
        fingerprint=f"{type(exception).__name__}:{str(exception)[:50]}",
        tags=tags or {},
    )
