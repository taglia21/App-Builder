"""
Rate Limiting Module

Redis-backed rate limiting for API endpoints using slowapi.
"""

from fastapi import Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import redis
import os
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """
    Get client IP address, handling proxies.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Client IP address
    """
    # Check for X-Forwarded-For header (behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()
    
    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fall back to direct client IP
    return get_remote_address(request)


def get_user_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    Uses user ID if authenticated, otherwise IP address.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Unique identifier for rate limiting
    """
    # Check for authenticated user
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"
    
    # Fall back to IP address
    return f"ip:{get_client_ip(request)}"


class RateLimitConfig:
    """Rate limit configuration for different tiers."""
    
    # Anonymous users (by IP)
    ANONYMOUS_LIMITS = {
        "default": "30/minute",
        "auth": "10/minute",
        "generation": "5/minute",
        "deployment": "3/minute",
    }
    
    # Free tier users
    FREE_TIER_LIMITS = {
        "default": "100/minute",
        "auth": "20/minute",
        "generation": "10/minute",
        "deployment": "5/minute",
    }
    
    # Pro tier users
    PRO_TIER_LIMITS = {
        "default": "500/minute",
        "auth": "50/minute",
        "generation": "50/minute",
        "deployment": "20/minute",
    }
    
    # Enterprise tier users
    ENTERPRISE_TIER_LIMITS = {
        "default": "2000/minute",
        "auth": "200/minute",
        "generation": "200/minute",
        "deployment": "100/minute",
    }


def get_redis_url() -> Optional[str]:
    """Get Redis URL from environment."""
    return os.getenv("REDIS_URL", "redis://localhost:6379")


def create_limiter() -> Limiter:
    """
    Create and configure rate limiter.
    
    Returns:
        Configured Limiter instance
    """
    redis_url = get_redis_url()
    
    # Use Redis storage if available, otherwise in-memory
    storage_uri = None
    if redis_url:
        try:
            # Test Redis connection
            r = redis.from_url(redis_url)
            r.ping()
            storage_uri = redis_url
            logger.info("Rate limiter using Redis storage")
        except redis.ConnectionError:
            logger.warning("Redis not available, using in-memory rate limiting")
    
    return Limiter(
        key_func=get_user_identifier,
        default_limits=["100/minute"],
        storage_uri=storage_uri,
        strategy="fixed-window",
        headers_enabled=True,  # Add X-RateLimit headers to responses
    )


# Global limiter instance
limiter = create_limiter()


def setup_rate_limiting(app):
    """
    Setup rate limiting middleware on FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    
    logger.info("Rate limiting middleware configured")


# Rate limit decorators for common use cases
def rate_limit_default(func: Callable) -> Callable:
    """Default rate limit decorator - 100/minute."""
    return limiter.limit("100/minute")(func)


def rate_limit_strict(func: Callable) -> Callable:
    """Strict rate limit for sensitive endpoints - 10/minute."""
    return limiter.limit("10/minute")(func)


def rate_limit_generation(func: Callable) -> Callable:
    """Rate limit for AI generation endpoints - 20/minute."""
    return limiter.limit("20/minute")(func)


def rate_limit_auth(func: Callable) -> Callable:
    """Rate limit for auth endpoints - 5/minute (brute force protection)."""
    return limiter.limit("5/minute")(func)


def rate_limit_deployment(func: Callable) -> Callable:
    """Rate limit for deployment endpoints - 10/minute."""
    return limiter.limit("10/minute")(func)


class DynamicRateLimiter:
    """
    Dynamic rate limiter that adjusts limits based on user tier.
    """
    
    def __init__(self, endpoint_type: str = "default"):
        self.endpoint_type = endpoint_type
    
    def get_limit_for_user(self, request: Request) -> str:
        """
        Get appropriate rate limit based on user tier.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Rate limit string (e.g., "100/minute")
        """
        user = getattr(request.state, "user", None)
        
        if not user:
            return RateLimitConfig.ANONYMOUS_LIMITS.get(
                self.endpoint_type,
                RateLimitConfig.ANONYMOUS_LIMITS["default"]
            )
        
        tier = getattr(user, "subscription_tier", "free")
        
        tier_configs = {
            "free": RateLimitConfig.FREE_TIER_LIMITS,
            "pro": RateLimitConfig.PRO_TIER_LIMITS,
            "enterprise": RateLimitConfig.ENTERPRISE_TIER_LIMITS,
        }
        
        config = tier_configs.get(tier, RateLimitConfig.FREE_TIER_LIMITS)
        return config.get(self.endpoint_type, config["default"])


# Shared exempt check for internal/health endpoints
def is_exempt_endpoint(request: Request) -> bool:
    """
    Check if endpoint should be exempt from rate limiting.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if exempt, False otherwise
    """
    exempt_paths = [
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/_internal/",
    ]
    
    path = request.url.path
    return any(path.startswith(exempt) for exempt in exempt_paths)
