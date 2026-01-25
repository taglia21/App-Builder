"""
Monitoring Module

Provides comprehensive error monitoring, logging, and observability:
- Sentry integration for error tracking
- Custom error reporting with context
- Performance monitoring
- Health checks
- Alerting integrations
"""

from src.monitoring.sentry import (
    SentryConfig,
    SentryClient,
    init_sentry,
    capture_exception,
    capture_message,
    set_user,
    set_context,
    set_tag,
    start_transaction,
    get_transaction,
)

from src.monitoring.errors import (
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    ErrorReport,
    ErrorReporter,
    ConsoleReporter,
    FileReporter,
    WebhookReporter,
    CompositeReporter,
)

from src.monitoring.health import (
    HealthStatus,
    ComponentHealth,
    HealthCheck,
    DatabaseHealthCheck,
    RedisHealthCheck,
    ExternalServiceHealthCheck,
    HealthCheckRegistry,
)

from src.monitoring.metrics import (
    MetricsCollector,
    Counter,
    Gauge,
    Histogram,
    Timer,
)

from src.monitoring.alerts import (
    AlertSeverity,
    AlertChannel,
    Alert,
    SlackAlerter,
    EmailAlerter,
    PagerDutyAlerter,
    AlertManager,
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
