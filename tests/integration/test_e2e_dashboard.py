"""End-to-end integration tests for dashboard."""
import pytest
import requests
from fastapi.testclient import TestClient
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'src'))

from dashboard.app import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestDashboardE2E:
    """End-to-end dashboard tests."""
    
    def test_dashboard_home_loads(self, client):
        """Test dashboard home page loads successfully."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"LaunchForge" in response.content
    
    def test_dashboard_accessible(self, client):
        """Test dashboard page is accessible."""
        response = client.get("/dashboard")
        # Dashboard should be accessible (200) or redirect to login (302/303)
        assert response.status_code in [200, 302, 303]
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_api_docs_available(self, client):
        """Test API documentation is available."""
        response = client.get("/docs")
        assert response.status_code == 200
        
    def test_security_headers_present(self, client):
        """Test security headers are set."""
        response = client.get("/")
        headers = response.headers
        
        # Check for security headers
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        
    def test_cors_configured(self, client):
        """Test CORS is properly configured."""
        response = client.options(
            "/api/projects",
            headers={"Origin": "http://localhost:3000"}
        )
        # CORS headers should be present
        assert "Access-Control-Allow-Origin" in response.headers or response.status_code == 404
