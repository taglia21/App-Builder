"""Tests for src/api/versioning - API Versioning functionality."""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import JSONResponse

from src.api.versioning import (
    CURRENT_VERSION,
    SUPPORTED_VERSIONS,
    APIVersionMiddleware,
    VersionNotSupportedError,
    add_versioning_to_app,
    check_api_version,
    create_versioned_router,
    get_api_version,
)


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    return FastAPI()


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


def test_create_versioned_router_default():
    """Test creating versioned router with defaults."""
    router = create_versioned_router()
    
    assert router.prefix == "/api/v1"
    assert "API V1" in router.tags


def test_create_versioned_router_custom():
    """Test creating versioned router with custom values."""
    router = create_versioned_router(prefix="/custom", version="v2")
    
    assert router.prefix == "/custom/v2"
    assert "API V2" in router.tags


def test_add_versioning_to_app(app):
    """Test adding versioning middleware to app."""
    add_versioning_to_app(app, default_version="v1")
    
    # Verify middleware was added
    assert len(app.user_middleware) > 0


def test_api_version_middleware_with_header(app, client):
    """Test middleware extracts version from header."""
    add_versioning_to_app(app)
    
    @app.get("/test")
    async def test_endpoint(request: Request):
        version = get_api_version(request)
        return {"version": version}
    
    response = client.get("/test", headers={"X-API-Version": "v2"})
    
    assert response.status_code == 200
    assert response.json()["version"] == "v2"
    assert response.headers["X-API-Version"] == "v2"


def test_api_version_middleware_from_path(app, client):
    """Test middleware extracts version from URL path."""
    add_versioning_to_app(app)
    
    @app.get("/api/v2/test")
    async def test_endpoint(request: Request):
        version = get_api_version(request)
        return {"version": version}
    
    response = client.get("/api/v2/test")
    
    assert response.status_code == 200
    assert response.json()["version"] == "v2"


def test_api_version_middleware_default(app, client):
    """Test middleware uses default version."""
    add_versioning_to_app(app, default_version="v1")
    
    @app.get("/test")
    async def test_endpoint(request: Request):
        version = get_api_version(request)
        return {"version": version}
    
    response = client.get("/test")
    
    assert response.status_code == 200
    assert response.json()["version"] == "v1"
    assert response.headers["X-API-Version"] == "v1"


def test_get_api_version_with_state():
    """Test get_api_version with request state."""
    request = Request({"type": "http", "method": "GET", "path": "/"})
    request.state.api_version = "v3"
    
    version = get_api_version(request)
    
    assert version == "v3"


def test_get_api_version_default():
    """Test get_api_version returns default when no state."""
    request = Request({"type": "http", "method": "GET", "path": "/"})
    
    version = get_api_version(request)
    
    assert version == "v1"


def test_check_api_version_dependency(app, client):
    """Test API version check dependency."""
    from fastapi import Depends
    add_versioning_to_app(app, default_version="v1")
    
    @app.get("/guarded", dependencies=[Depends(check_api_version(["v1", "v2"]))])
    async def guarded_endpoint():
        return {"status": "ok"}
    
    # Should allow v1
    response = client.get("/guarded", headers={"X-API-Version": "v1"})
    assert response.status_code == 200
    
    # Should block v3
    response = client.get("/guarded", headers={"X-API-Version": "v3"})
    assert response.status_code == 400


def test_current_version_constant():
    """Test CURRENT_VERSION is defined."""
    assert CURRENT_VERSION is not None
    assert isinstance(CURRENT_VERSION, str)
    assert CURRENT_VERSION.startswith("v")


def test_supported_versions_constant():
    """Test SUPPORTED_VERSIONS is defined."""
    assert SUPPORTED_VERSIONS is not None
    assert isinstance(SUPPORTED_VERSIONS, list)
    assert CURRENT_VERSION in SUPPORTED_VERSIONS


def test_versioned_router_in_app(app, client):
    """Test using versioned router in app."""
    router = create_versioned_router(version="v1")
    
    @router.get("/items")
    async def get_items():
        return {"items": [1, 2, 3]}
    
    app.include_router(router)
    
    response = client.get("/api/v1/items")
    
    assert response.status_code == 200
    assert response.json()["items"] == [1, 2, 3]


def test_multiple_versions_in_app():
    """Test app with multiple API versions."""
    app = FastAPI()
    client = TestClient(app)
    
    v1_router = create_versioned_router(version="v1")
    v2_router = create_versioned_router(version="v2")
    
    @v1_router.get("/status")
    async def v1_status():
        return {"version": "v1", "deprecated": False}
    
    @v2_router.get("/status")
    async def v2_status():
        return {"version": "v2", "features": ["new_feature"]}
    
    app.include_router(v1_router)
    app.include_router(v2_router)
    
    v1_response = client.get("/api/v1/status")
    v2_response = client.get("/api/v2/status")
    
    assert v1_response.json()["version"] == "v1"
    assert v2_response.json()["version"] == "v2"
    assert "features" in v2_response.json()


def test_version_not_supported_error():
    """Test VersionNotSupportedError exception."""
    error = VersionNotSupportedError("v99 not supported")
    assert isinstance(error, Exception)
    assert "v99" in str(error)
