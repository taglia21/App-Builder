"""
Monitoring Module

Provides comprehensive error monitoring, logging, and observability:
- Sentry integration for error tracking
- Custom error reporting with context
- Performance monitoring
- Health checks
- Alerting integrations
"""

from src.monitoring.alerts import (
    Alert,
    AlertChannel,
    AlertManager,
    AlertSeverity,
    EmailAlerter,
    PagerDutyAlerter,
    SlackAlerter,
)
from src.monitoring.errors import (
    CompositeReporter,
    ConsoleReporter,
    ErrorCategory,
    ErrorContext,
    ErrorReport,
    ErrorReporter,
    ErrorSeverity,
    FileReporter,
    WebhookReporter,
)
from src.monitoring.health import (
    ComponentHealth,
    DatabaseHealthCheck,
    ExternalServiceHealthCheck,
    HealthCheck,
    HealthCheckRegistry,
    HealthStatus,
    RedisHealthCheck,
)
from src.monitoring.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsCollector,
    Timer,
)
from src.monitoring.sentry import (
    SentryClient,
    SentryConfig,
    capture_exception,
    capture_message,
    get_transaction,
    init_sentry,
    set_context,
    set_tag,
    set_user,
    start_transaction,
)

__all__ = [
    # Sentry
    "SentryConfig",
    "SentryClient",
    "init_sentry",
    "capture_exception",
    "capture_message",
    "set_user",
    "set_context",
    "set_tag",
    "start_transaction",
    "get_transaction",
    # Errors
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorContext",
    "ErrorReport",
    "ErrorReporter",
    "ConsoleReporter",
    "FileReporter",
    "WebhookReporter",
    "CompositeReporter",
    # Health
    "HealthStatus",
    "ComponentHealth",
    "HealthCheck",
    "DatabaseHealthCheck",
    "RedisHealthCheck",
    "ExternalServiceHealthCheck",
    "HealthCheckRegistry",
    # Metrics
    "MetricsCollector",
    "Counter",
    "Gauge",
    "Histogram",
    "Timer",
    # Alerts
    "AlertSeverity",
    "AlertChannel",
    "Alert",
    "SlackAlerter",
    "EmailAlerter",
    "PagerDutyAlerter",
    "AlertManager",
]
