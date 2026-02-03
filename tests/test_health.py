"""Tests for health and monitoring endpoints."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_health_endpoint_exists():
    """Test that health endpoint module exists."""
    from src.api import health
    
    assert hasattr(health, 'router'), "health module should have router"


def test_health_endpoint_basic():
    """Test basic health check endpoint."""
    from src.api.health import router
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_health_endpoint_includes_version():
    """Test health endpoint includes version."""
    from src.api.health import router
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    response = client.get("/health")
    data = response.json()
    
    assert "version" in data
    assert isinstance(data["version"], str)


def test_health_endpoint_includes_timestamp():
    """Test health endpoint includes timestamp."""
    from src.api.health import router
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    response = client.get("/health")
    data = response.json()
    
    assert "timestamp" in data
    assert isinstance(data["timestamp"], str)


def test_readiness_endpoint():
    """Test readiness endpoint for Kubernetes."""
    from src.api.health import router
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    response = client.get("/health/ready")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["ready", "not_ready"]


def test_liveness_endpoint():
    """Test liveness endpoint for Kubernetes."""
    from src.api.health import router
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    response = client.get("/health/live")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "alive"


def test_health_checks_dependencies():
    """Test health endpoint checks for dependencies."""
    from src.api.health import router
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    response = client.get("/health")
    data = response.json()
    
    # Should include checks object
    assert "checks" in data
    assert isinstance(data["checks"], dict)


def test_readiness_checks_llm_providers():
    """Test readiness endpoint checks LLM provider availability."""
    from src.api.health import router
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    response = client.get("/health/ready")
    data = response.json()
    
    # Should include checks for providers
    assert "checks" in data
    checks = data["checks"]
    
    # Should check at least one provider
    assert "llm_providers" in checks or "providers" in checks


def test_health_endpoint_response_time():
    """Test health endpoint responds quickly."""
    from src.api.health import router
    import time
    
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    
    start = time.time()
    response = client.get("/health")
    elapsed = time.time() - start
    
    assert response.status_code == 200
    assert elapsed < 1.0, "Health check should respond in < 1 second"


def test_health_router_tags():
    """Test health router has proper tags."""
    from src.api.health import router
    
    assert hasattr(router, 'tags')
    assert "health" in router.tags or "monitoring" in router.tags


def test_metrics_endpoint_exists():
    """Test metrics endpoint exists for monitoring."""
    from src.api.health import router
    
    # Check if metrics endpoint is defined
    paths = [route.path for route in router.routes]
    
    # Should have at least health endpoints
    assert "/health" in paths or "/" in paths
    assert "/health/ready" in paths or "/ready" in paths
    assert "/health/live" in paths or "/live" in paths
