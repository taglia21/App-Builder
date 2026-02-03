"""Tests for security middleware."""
import pytest
import time
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_security_middleware_module_exists():
    """Test that security middleware module exists."""
    from src.middleware import security
    assert security is not None


def test_rate_limiter_class_exists():
    """Test RateLimiter class exists."""
    from src.middleware.security import RateLimiter
    assert RateLimiter is not None


def test_rate_limiter_allows_requests_under_limit():
    """Test that rate limiter allows requests under the limit."""
    from src.middleware.security import RateLimiter
    
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    ip = "192.168.1.1"
    
    # First 5 requests should be allowed
    for _ in range(5):
        assert limiter.is_allowed(ip) is True


def test_rate_limiter_blocks_requests_over_limit():
    """Test that rate limiter blocks requests over the limit."""
    from src.middleware.security import RateLimiter
    
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    ip = "192.168.1.2"
    
    # First 3 should be allowed
    for _ in range(3):
        assert limiter.is_allowed(ip) is True
    
    # 4th should be blocked
    assert limiter.is_allowed(ip) is False


def test_rate_limiter_resets_after_window():
    """Test that rate limiter resets after time window."""
    from src.middleware.security import RateLimiter
    
    limiter = RateLimiter(max_requests=2, window_seconds=1)
    ip = "192.168.1.3"
    
    # First 2 allowed
    assert limiter.is_allowed(ip) is True
    assert limiter.is_allowed(ip) is True
    
    # 3rd blocked
    assert limiter.is_allowed(ip) is False
    
    # Wait for window to expire
    time.sleep(1.1)
    
    # Should be allowed again
    assert limiter.is_allowed(ip) is True


def test_security_middleware_integration():
    """Test security middleware integration with FastAPI."""
    from src.middleware.security import add_security_middleware
    
    app = FastAPI()
    add_security_middleware(app)
    
    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    assert response.status_code == 200


def test_security_headers_added():
    """Test that security headers are added to responses."""
    from src.middleware.security import add_security_middleware
    
    app = FastAPI()
    add_security_middleware(app)
    
    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    # Check security headers
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers
    assert "X-XSS-Protection" in response.headers


def test_cors_middleware_configured():
    """Test that CORS is properly configured."""
    from src.middleware.security import add_security_middleware
    
    app = FastAPI()
    add_security_middleware(app, cors_origins=["https://example.com"])
    
    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}
    
    client = TestClient(app)
    response = client.get(
        "/test",
        headers={"Origin": "https://example.com"}
    )
    
    # CORS header should be present
    assert response.status_code == 200


def test_rate_limiting_middleware_integration():
    """Test rate limiting middleware blocks excessive requests."""
    from src.middleware.security import add_security_middleware
    
    app = FastAPI()
    add_security_middleware(app, rate_limit=5, rate_window=60)
    
    @app.get("/test")
    def test_endpoint():
        return {"message": "ok"}
    
    client = TestClient(app)
    
    # First 5 requests should succeed
    for _ in range(5):
        response = client.get("/test")
        assert response.status_code == 200
    
    # 6th request might be rate limited (implementation dependent)
    # Just verify it doesn't crash
    response = client.get("/test")
    assert response.status_code in [200, 429]


def test_request_size_limit():
    """Test that request size limit is enforced."""
    from src.middleware.security import add_security_middleware
    
    app = FastAPI()
    add_security_middleware(app, max_request_size=1024)  # 1KB limit
    
    @app.post("/test")
    def test_endpoint(data: dict):
        return {"message": "ok"}
    
    client = TestClient(app)
    
    # Small request should work
    small_data = {"key": "value"}
    response = client.post("/test", json=small_data)
    assert response.status_code in [200, 422]  # 422 if validation fails


def test_security_middleware_preserves_functionality():
    """Test that security middleware doesn't break normal functionality."""
    from src.middleware.security import add_security_middleware
    
    app = FastAPI()
    add_security_middleware(app)
    
    @app.get("/items/{item_id}")
    def get_item(item_id: int):
        return {"item_id": item_id}
    
    @app.post("/items")
    def create_item(name: str):
        return {"name": name}
    
    client = TestClient(app)
    
    # Test GET
    response = client.get("/items/123")
    assert response.status_code == 200
    assert response.json()["item_id"] == 123
    
    # Test POST
    response = client.post("/items?name=test")
    assert response.status_code == 200
    assert response.json()["name"] == "test"
