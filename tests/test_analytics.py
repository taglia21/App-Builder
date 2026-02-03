"""Tests for analytics module."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


class TestAnalyticsMetrics:
    """Test analytics metrics collection."""

    def test_metrics_class_exists(self):
        """Test that Metrics class can be imported."""
        from src.analytics.metrics import Metrics
        assert Metrics is not None

    def test_track_app_generation(self):
        """Test tracking app generation events."""
        from src.analytics.metrics import Metrics
        
        metrics = Metrics()
        result = metrics.track_app_generation(
            user_id=1,
            app_name="TestApp",
            tech_stack="FastAPI",
            success=True
        )
        assert result is not None
        assert result["event"] == "app_generation"
        assert result["user_id"] == 1

    def test_track_user_signup(self):
        """Test tracking user signup events."""
        from src.analytics.metrics import Metrics
        
        metrics = Metrics()
        result = metrics.track_user_signup(
            user_id=1,
            email="test@example.com",
            signup_method="email"
        )
        assert result is not None
        assert result["event"] == "user_signup"

    def test_track_subscription_change(self):
        """Test tracking subscription changes."""
        from src.analytics.metrics import Metrics
        
        metrics = Metrics()
        result = metrics.track_subscription_change(
            user_id=1,
            from_tier="free",
            to_tier="professional"
        )
        assert result is not None
        assert result["event"] == "subscription_change"
        assert result["from_tier"] == "free"
        assert result["to_tier"] == "professional"

    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        from src.analytics.metrics import Metrics
        
        metrics = Metrics()
        # Track some events
        metrics.track_app_generation(1, "App1", "FastAPI", True)
        metrics.track_app_generation(2, "App2", "Django", True)
        
        summary = metrics.get_summary()
        assert isinstance(summary, dict)
        assert "total_events" in summary


class TestAnalyticsRoutes:
    """Test analytics API routes."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.analytics.routes import router
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(router, prefix="/api/v1/analytics")
        
        return TestClient(app)

    def test_dashboard_endpoint_exists(self, client):
        """Test dashboard endpoint returns 200."""
        response = client.get("/api/v1/analytics/dashboard")
        assert response.status_code == 200

    def test_dashboard_returns_json(self, client):
        """Test dashboard returns JSON data."""
        response = client.get("/api/v1/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "overview" in data or "metrics" in data or "summary" in data

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/api/v1/analytics/metrics")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_events_endpoint(self, client):
        """Test events endpoint."""
        response = client.get("/api/v1/analytics/events")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)

    def test_dashboard_with_date_range(self, client):
        """Test dashboard with date range parameters."""
        response = client.get(
            "/api/v1/analytics/dashboard",
            params={"start_date": "2026-01-01", "end_date": "2026-02-01"}
        )
        assert response.status_code in [200, 422]  # 422 if validation fails

    def test_user_metrics_endpoint(self, client):
        """Test user-specific metrics endpoint."""
        response = client.get("/api/v1/analytics/users/1")
        assert response.status_code in [200, 404]  # 404 if user not found


class TestAnalyticsIntegration:
    """Integration tests for analytics."""

    @pytest.mark.asyncio
    async def test_track_and_retrieve(self):
        """Test tracking an event and retrieving it."""
        from src.analytics.metrics import Metrics
        
        metrics = Metrics()
        
        # Track event
        metrics.track_app_generation(
            user_id=1,
            app_name="TestApp",
            tech_stack="FastAPI",
            success=True
        )
        
        # Retrieve summary
        summary = metrics.get_summary()
        assert summary["total_events"] > 0

    @pytest.mark.asyncio
    async def test_multiple_event_types(self):
        """Test tracking multiple event types."""
        from src.analytics.metrics import Metrics
        
        metrics = Metrics()
        
        # Track different events
        metrics.track_user_signup(1, "test@example.com", "email")
        metrics.track_app_generation(1, "App1", "FastAPI", True)
        metrics.track_subscription_change(1, "free", "pro")
        
        summary = metrics.get_summary()
        assert summary["total_events"] >= 3


class TestAnalyticsFiltering:
    """Test analytics filtering and querying."""

    def test_filter_by_date_range(self):
        """Test filtering events by date range."""
        from src.analytics.metrics import Metrics
        
        metrics = Metrics()
        
        # This should not raise an error
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        result = metrics.get_events(start_date=start_date, end_date=end_date)
        assert isinstance(result, list)

    def test_filter_by_user(self):
        """Test filtering events by user."""
        from src.analytics.metrics import Metrics
        
        metrics = Metrics()
        metrics.track_app_generation(1, "App1", "FastAPI", True)
        
        result = metrics.get_events(user_id=1)
        assert isinstance(result, list)

    def test_filter_by_event_type(self):
        """Test filtering events by type."""
        from src.analytics.metrics import Metrics
        
        metrics = Metrics()
        metrics.track_app_generation(1, "App1", "FastAPI", True)
        
        result = metrics.get_events(event_type="app_generation")
        assert isinstance(result, list)
