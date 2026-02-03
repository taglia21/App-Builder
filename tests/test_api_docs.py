"""Tests for API documentation."""
import pytest
from fastapi.testclient import TestClient
from src.dashboard.app import create_app


def test_openapi_docs_accessible():
    """Test that OpenAPI docs are accessible at /docs."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_redoc_docs_accessible():
    """Test that ReDoc is accessible at /redoc."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_json_schema():
    """Test that OpenAPI JSON schema is available."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema


def test_openapi_metadata():
    """Test OpenAPI metadata is properly configured."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/openapi.json")
    schema = response.json()
    info = schema["info"]
    
    assert "title" in info
    assert "description" in info
    assert "version" in info
    assert len(info["description"]) > 0


def test_health_endpoints_documented():
    """Test that health endpoints are documented in OpenAPI."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/openapi.json")
    schema = response.json()
    paths = schema["paths"]
    
    # Health endpoints should be documented
    assert "/health" in paths or "/api/health" in paths


def test_openapi_has_tags():
    """Test OpenAPI schema includes endpoint tags."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/openapi.json")
    schema = response.json()
    
    # Should have tags defined
    if "tags" in schema:
        assert isinstance(schema["tags"], list)
        assert len(schema["tags"]) > 0


def test_openapi_security_schemes():
    """Test OpenAPI includes security schemes if auth is enabled."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/openapi.json")
    schema = response.json()
    
    # Check components section
    assert "components" in schema


def test_api_endpoints_have_descriptions():
    """Test that API endpoints have descriptions."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/openapi.json")
    schema = response.json()
    paths = schema["paths"]
    
    # At least health endpoint should have description
    for path, methods in paths.items():
        for method, spec in methods.items():
            if method in ["get", "post", "put", "delete", "patch"]:
                # Should have summary or description
                assert "summary" in spec or "description" in spec


def test_openapi_version():
    """Test OpenAPI version is 3.x."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/openapi.json")
    schema = response.json()
    
    assert "openapi" in schema
    assert schema["openapi"].startswith("3.")


def test_health_router_integrated():
    """Test that health router is integrated in the app."""
    from src.api.health import router
    app = create_app()
    
    # Check that health router routes are available
    paths = [route.path for route in app.routes]
    
    # Should have health endpoints (either directly or via API prefix)
    health_paths = [p for p in paths if "health" in p]
    assert len(health_paths) > 0, "Health endpoints should be mounted"
