"""
Tests for Monitoring Module

Tests for error monitoring, health checks, metrics, and alerts.
"""

import pytest
import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from src.monitoring.sentry import (
    SentryConfig,
    SentryClient,
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
    create_error_reporter,
    create_error_report,
)

from src.monitoring.health import (
    HealthStatus,
    ComponentHealth,
    HealthCheck,
    ExternalServiceHealthCheck,
    CallableHealthCheck,
    HealthCheckResult,
    HealthCheckRegistry,
)

from src.monitoring.metrics import (
    MetricsCollector,
    Counter,
    Gauge,
    Histogram,
    Timer,
    get_metrics,
)

from src.monitoring.alerts import (
    AlertSeverity,
    AlertChannel,
    Alert,
    SlackAlerter,
    EmailAlerter,
    PagerDutyAlerter,
    AlertManager,
    create_alert_manager,
)


# ============================================================================
# Sentry Tests
# ============================================================================

class TestSentryConfig:
    """Test SentryConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = SentryConfig()
        
        assert config.dsn is None
        assert config.environment == "development"
        assert config.sample_rate == 1.0
        assert config.enable_tracing is True
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = SentryConfig(
            dsn="https://key@sentry.io/123",
            environment="production",
            sample_rate=0.5,
        )
        
        assert config.dsn == "https://key@sentry.io/123"
        assert config.environment == "production"
        assert config.sample_rate == 0.5
    
    def test_from_env(self):
        """Test loading from environment."""
        with patch.dict('os.environ', {
            'SENTRY_DSN': 'https://test@sentry.io/456',
            'SENTRY_ENVIRONMENT': 'staging',
        }):
            config = SentryConfig.from_env()
            
            assert config.dsn == 'https://test@sentry.io/456'
            assert config.environment == 'staging'


class TestSentryClient:
    """Test SentryClient."""
    
    def test_client_without_dsn(self):
        """Test client without DSN configured."""
        config = SentryConfig(dsn=None)
        client = SentryClient(config)
        
        # Should not raise, just return None
        result = client.capture_message("test")
        assert result is None
    
    def test_client_methods_without_sdk(self):
        """Test client methods when SDK not installed."""
        client = SentryClient()
        
        # All methods should gracefully handle missing SDK
        client.set_user(user_id="123")
        client.set_context("test", {"key": "value"})
        client.set_tag("test", "value")
        client.add_breadcrumb("test message")


# ============================================================================
# Error Tests
# ============================================================================

class TestErrorModels:
    """Test error models."""
    
    def test_error_severity_enum(self):
        """Test ErrorSeverity values."""
        assert ErrorSeverity.DEBUG.value == "debug"
        assert ErrorSeverity.CRITICAL.value == "critical"
    
    def test_error_category_enum(self):
        """Test ErrorCategory values."""
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.PAYMENT.value == "payment"
    
    def test_error_context(self):
        """Test ErrorContext model."""
        context = ErrorContext(
            user_id="user-123",
            project_id="project-456",
            method="POST",
            path="/api/generate",
        )
        
        data = context.to_dict()
        
        assert data["user_id"] == "user-123"
        assert data["project_id"] == "project-456"
        assert data["request"]["method"] == "POST"
    
    def test_error_context_sanitizes_headers(self):
        """Test that sensitive headers are redacted."""
        context = ErrorContext(
            method="GET",
            path="/api/test",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer secret-token",
                "X-Api-Key": "secret-key",
            },
        )
        
        data = context.to_dict()
        headers = data["request"]["headers"]
        
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "[REDACTED]"
        assert headers["X-Api-Key"] == "[REDACTED]"
    
    def test_error_report(self):
        """Test ErrorReport model."""
        report = ErrorReport(
            error_id="err-123",
            timestamp=datetime.now(timezone.utc),
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.DATABASE,
            message="Connection failed",
            error_type="ConnectionError",
        )
        
        assert report.severity == ErrorSeverity.ERROR
        assert report.category == ErrorCategory.DATABASE
        
        data = report.to_dict()
        assert data["error_id"] == "err-123"
        assert data["severity"] == "error"
    
    def test_error_report_to_json(self):
        """Test ErrorReport JSON conversion."""
        report = ErrorReport(
            error_id="err-456",
            timestamp=datetime.now(timezone.utc),
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION,
            message="Invalid input",
            error_type="ValueError",
        )
        
        json_str = report.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["error_id"] == "err-456"
        assert parsed["severity"] == "warning"


class TestConsoleReporter:
    """Test ConsoleReporter."""
    
    def test_report_logs_message(self, caplog):
        """Test that reporter logs messages."""
        reporter = ConsoleReporter()
        
        report = ErrorReport(
            error_id="test-123",
            timestamp=datetime.now(timezone.utc),
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.UNKNOWN,
            message="Test error message",
            error_type="TestError",
        )
        
        result = reporter.report(report)
        
        assert result is True


class TestFileReporter:
    """Test FileReporter."""
    
    def test_report_writes_to_file(self):
        """Test that reporter writes to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = FileReporter(log_dir=tmpdir)
            
            report = ErrorReport(
                error_id="file-test-123",
                timestamp=datetime.now(timezone.utc),
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.UNKNOWN,
                message="File test error",
                error_type="TestError",
            )
            
            result = reporter.report(report)
            assert result is True
            
            # Check file was created
            files = list(Path(tmpdir).glob("*.jsonl"))
            assert len(files) == 1
            
            # Check content
            with open(files[0]) as f:
                line = f.readline()
                data = json.loads(line)
                assert data["error_id"] == "file-test-123"


class TestCompositeReporter:
    """Test CompositeReporter."""
    
    def test_reports_to_all(self):
        """Test composite reports to all reporters."""
        mock1 = MagicMock(spec=ErrorReporter)
        mock1.report.return_value = True
        
        mock2 = MagicMock(spec=ErrorReporter)
        mock2.report.return_value = True
        
        composite = CompositeReporter([mock1, mock2])
        
        report = ErrorReport(
            error_id="composite-123",
            timestamp=datetime.now(timezone.utc),
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.UNKNOWN,
            message="Test",
            error_type="Error",
        )
        
        result = composite.report(report)
        
        assert result is True
        mock1.report.assert_called_once()
        mock2.report.assert_called_once()
    
    def test_handles_reporter_failure(self):
        """Test composite handles individual reporter failures."""
        mock1 = MagicMock(spec=ErrorReporter)
        mock1.report.return_value = True
        
        mock2 = MagicMock(spec=ErrorReporter)
        mock2.report.side_effect = Exception("Reporter failed")
        
        composite = CompositeReporter([mock1, mock2])
        
        report = ErrorReport(
            error_id="fail-123",
            timestamp=datetime.now(timezone.utc),
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.UNKNOWN,
            message="Test",
            error_type="Error",
        )
        
        # Should not raise, but return False
        result = composite.report(report)
        assert result is False


class TestCreateErrorReport:
    """Test create_error_report factory."""
    
    def test_creates_from_exception(self):
        """Test creating report from exception."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            report = create_error_report(
                exception=e,
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.VALIDATION,
            )
        
        assert report.message == "Test error"
        assert report.error_type == "ValueError"
        assert report.severity == ErrorSeverity.ERROR
        assert report.stacktrace is not None


# ============================================================================
# Health Check Tests
# ============================================================================

class TestHealthModels:
    """Test health check models."""
    
    def test_health_status_enum(self):
        """Test HealthStatus values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
    
    def test_component_health(self):
        """Test ComponentHealth model."""
        health = ComponentHealth(
            name="database",
            status=HealthStatus.HEALTHY,
            message="Connection OK",
            response_time_ms=5.2,
        )
        
        data = health.to_dict()
        
        assert data["name"] == "database"
        assert data["status"] == "healthy"
        assert data["response_time_ms"] == 5.2
    
    def test_health_check_result(self):
        """Test HealthCheckResult model."""
        result = HealthCheckResult(
            status=HealthStatus.HEALTHY,
            components=[
                ComponentHealth(name="db", status=HealthStatus.HEALTHY),
                ComponentHealth(name="redis", status=HealthStatus.HEALTHY),
            ],
        )
        
        data = result.to_dict()
        
        assert data["status"] == "healthy"
        assert len(data["components"]) == 2


class TestExternalServiceHealthCheck:
    """Test ExternalServiceHealthCheck."""
    
    @pytest.mark.asyncio
    async def test_check_healthy_service(self):
        """Test checking a healthy service."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )
            
            check = ExternalServiceHealthCheck(
                name="test-service",
                url="https://api.example.com/health",
            )
            
            result = await check.check()
            
            assert result.status == HealthStatus.HEALTHY
            assert result.name == "test-service"
    
    @pytest.mark.asyncio
    async def test_check_unhealthy_service(self):
        """Test checking an unhealthy service."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                side_effect=Exception("Connection failed")
            )
            
            check = ExternalServiceHealthCheck(
                name="failing-service",
                url="https://api.example.com/health",
            )
            
            result = await check.check()
            
            assert result.status == HealthStatus.UNHEALTHY


class TestCallableHealthCheck:
    """Test CallableHealthCheck."""
    
    @pytest.mark.asyncio
    async def test_sync_callable(self):
        """Test with sync callable."""
        def check_func():
            return ComponentHealth(
                name="custom",
                status=HealthStatus.HEALTHY,
                message="All good",
            )
        
        check = CallableHealthCheck("custom", check_func)
        result = await check.check()
        
        assert result.status == HealthStatus.HEALTHY
    
    @pytest.mark.asyncio
    async def test_async_callable(self):
        """Test with async callable."""
        async def check_func():
            return ComponentHealth(
                name="async-custom",
                status=HealthStatus.DEGRADED,
                message="Slow",
            )
        
        check = CallableHealthCheck("async-custom", check_func)
        result = await check.check()
        
        assert result.status == HealthStatus.DEGRADED


class TestHealthCheckRegistry:
    """Test HealthCheckRegistry."""
    
    @pytest.fixture
    def registry(self):
        """Create health check registry."""
        return HealthCheckRegistry()
    
    @pytest.mark.asyncio
    async def test_register_and_check(self, registry):
        """Test registering and running checks."""
        check = CallableHealthCheck(
            "test-component",
            lambda: ComponentHealth(
                name="test-component",
                status=HealthStatus.HEALTHY,
            ),
        )
        
        registry.register(check)
        result = await registry.check()
        
        assert result.status == HealthStatus.HEALTHY
        assert len(result.components) == 1
    
    @pytest.mark.asyncio
    async def test_overall_status_unhealthy(self, registry):
        """Test that one unhealthy component makes overall unhealthy."""
        registry.register(CallableHealthCheck(
            "healthy",
            lambda: ComponentHealth(name="healthy", status=HealthStatus.HEALTHY),
        ))
        registry.register(CallableHealthCheck(
            "unhealthy",
            lambda: ComponentHealth(name="unhealthy", status=HealthStatus.UNHEALTHY),
        ))
        
        result = await registry.check()
        
        assert result.status == HealthStatus.UNHEALTHY


# ============================================================================
# Metrics Tests
# ============================================================================

class TestCounter:
    """Test Counter metric."""
    
    def test_increment(self):
        """Test counter increment."""
        counter = Counter("test_counter")
        
        counter.inc()
        counter.inc(5)
        
        assert counter.get() == 6
    
    def test_increment_negative_raises(self):
        """Test that negative increment raises."""
        counter = Counter("test_counter")
        
        with pytest.raises(ValueError):
            counter.inc(-1)
    
    def test_labels(self):
        """Test counter with labels."""
        counter = Counter("requests", labels=["method", "path"])
        
        counter.inc(labels={"method": "GET", "path": "/api"})
        counter.inc(labels={"method": "POST", "path": "/api"})
        counter.inc(labels={"method": "GET", "path": "/api"})
        
        assert counter.get({"method": "GET", "path": "/api"}) == 2
        assert counter.get({"method": "POST", "path": "/api"}) == 1


class TestGauge:
    """Test Gauge metric."""
    
    def test_set(self):
        """Test gauge set."""
        gauge = Gauge("temperature")
        
        gauge.set(25.5)
        assert gauge.get() == 25.5
        
        gauge.set(30.0)
        assert gauge.get() == 30.0
    
    def test_inc_dec(self):
        """Test gauge increment and decrement."""
        gauge = Gauge("queue_size")
        
        gauge.inc(5)
        assert gauge.get() == 5
        
        gauge.dec(2)
        assert gauge.get() == 3


class TestHistogram:
    """Test Histogram metric."""
    
    def test_observe(self):
        """Test histogram observe."""
        histogram = Histogram("latency")
        
        histogram.observe(0.1)
        histogram.observe(0.5)
        histogram.observe(1.0)
        
        stats = histogram.get_stats()
        
        assert stats["count"] == 3
        assert stats["sum"] == 1.6
        assert stats["mean"] == pytest.approx(0.533, rel=0.01)
    
    def test_time_context_manager(self):
        """Test histogram time context manager."""
        histogram = Histogram("operation_time")
        
        with histogram.time():
            pass  # Simulate operation
        
        stats = histogram.get_stats()
        assert stats["count"] == 1
        assert stats["sum"] >= 0


class TestTimer:
    """Test Timer metric."""
    
    def test_record(self):
        """Test timer record."""
        timer = Timer("request_time")
        
        timer.record(0.5)
        timer.record(1.0)
        
        stats = timer.get_stats()
        assert stats["count"] == 2
    
    def test_time_context(self):
        """Test timer context manager."""
        timer = Timer("operation")
        
        with timer.time():
            pass
        
        stats = timer.get_stats()
        assert stats["count"] == 1


class TestMetricsCollector:
    """Test MetricsCollector."""
    
    def test_counter_creation(self):
        """Test counter creation and retrieval."""
        collector = MetricsCollector()
        
        counter1 = collector.counter("test_requests")
        counter2 = collector.counter("test_requests")
        
        # Should return same instance
        assert counter1 is counter2
    
    def test_export(self):
        """Test metrics export."""
        collector = MetricsCollector()
        
        collector.counter("requests").inc(10)
        collector.gauge("active").set(5)
        
        export = collector.export()
        
        assert "counters" in export
        assert "gauges" in export
        assert "timestamp" in export


# ============================================================================
# Alert Tests
# ============================================================================

class TestAlertModels:
    """Test alert models."""
    
    def test_alert_severity_enum(self):
        """Test AlertSeverity values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.CRITICAL.value == "critical"
    
    def test_alert_channel_enum(self):
        """Test AlertChannel values."""
        assert AlertChannel.SLACK.value == "slack"
        assert AlertChannel.PAGERDUTY.value == "pagerduty"
    
    def test_alert_model(self):
        """Test Alert model."""
        alert = Alert(
            title="Test Alert",
            message="Something happened",
            severity=AlertSeverity.ERROR,
            component="api",
        )
        
        data = alert.to_dict()
        
        assert data["title"] == "Test Alert"
        assert data["severity"] == "error"
        assert data["component"] == "api"


class TestSlackAlerter:
    """Test SlackAlerter."""
    
    @pytest.mark.asyncio
    async def test_send_without_webhook(self):
        """Test send without webhook configured."""
        alerter = SlackAlerter(webhook_url=None)
        
        alert = Alert(
            title="Test",
            message="Test message",
            severity=AlertSeverity.ERROR,
        )
        
        result = await alerter.send(alert)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_with_webhook(self):
        """Test send with webhook configured."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            alerter = SlackAlerter(
                webhook_url="https://hooks.slack.com/services/xxx",
                min_severity=AlertSeverity.ERROR,
            )
            
            alert = Alert(
                title="Test Alert",
                message="Test message",
                severity=AlertSeverity.ERROR,
            )
            
            result = await alerter.send(alert)
            assert result is True
    
    @pytest.mark.asyncio
    async def test_severity_filtering(self):
        """Test that low severity alerts are skipped."""
        alerter = SlackAlerter(
            webhook_url="https://hooks.slack.com/services/xxx",
            min_severity=AlertSeverity.ERROR,
        )
        
        # Info alert should be skipped
        alert = Alert(
            title="Info",
            message="Info message",
            severity=AlertSeverity.INFO,
        )
        
        # Should return True (skipped, not failed)
        result = await alerter.send(alert)
        assert result is True


class TestPagerDutyAlerter:
    """Test PagerDutyAlerter."""
    
    @pytest.mark.asyncio
    async def test_send_without_key(self):
        """Test send without routing key."""
        alerter = PagerDutyAlerter(routing_key=None)
        
        alert = Alert(
            title="Test",
            message="Test",
            severity=AlertSeverity.CRITICAL,
        )
        
        result = await alerter.send(alert)
        assert result is False


class TestAlertManager:
    """Test AlertManager."""
    
    @pytest.fixture
    def manager(self):
        """Create alert manager."""
        return AlertManager()
    
    @pytest.mark.asyncio
    async def test_send_to_multiple_channels(self, manager):
        """Test sending to multiple channels."""
        mock_slack = MagicMock(spec=SlackAlerter)
        mock_slack.channel = AlertChannel.SLACK
        mock_slack.send = AsyncMock(return_value=True)
        
        mock_email = MagicMock(spec=EmailAlerter)
        mock_email.channel = AlertChannel.EMAIL
        mock_email.send = AsyncMock(return_value=True)
        
        manager.add_alerter(mock_slack)
        manager.add_alerter(mock_email)
        
        alert = Alert(
            title="Multi-channel test",
            message="Test",
            severity=AlertSeverity.ERROR,
        )
        
        results = await manager.send_alert(alert)
        
        assert results["slack"] is True
        assert results["email"] is True
    
    @pytest.mark.asyncio
    async def test_history_tracking(self, manager):
        """Test that alerts are tracked in history."""
        mock_alerter = MagicMock()
        mock_alerter.channel = AlertChannel.SLACK
        mock_alerter.send = AsyncMock(return_value=True)
        
        manager.add_alerter(mock_alerter)
        
        for i in range(5):
            await manager.send_alert(Alert(
                title=f"Alert {i}",
                message="Test",
                severity=AlertSeverity.ERROR,
            ))
        
        history = manager.get_history()
        assert len(history) == 5


# ============================================================================
# Factory Function Tests
# ============================================================================

class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_error_reporter(self):
        """Test creating error reporter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reporter = create_error_reporter(
                console=True,
                file=True,
                log_dir=tmpdir,
            )
            
            assert isinstance(reporter, CompositeReporter)
            assert len(reporter.reporters) == 2
    
    def test_get_metrics_singleton(self):
        """Test that get_metrics returns singleton."""
        metrics1 = get_metrics()
        metrics2 = get_metrics()
        
        assert metrics1 is metrics2
