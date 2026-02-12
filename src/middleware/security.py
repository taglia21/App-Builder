"""Security middleware for Valeric.

Provides:
- Rate limiting per IP (Redis-backed when available, in-memory fallback)
- CORS configuration
- Security headers
- Request size limits
"""
import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter with Redis backend and in-memory fallback."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # In-memory fallback
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()
        # Try Redis
        self._redis = None
        try:
            import os
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                import redis
                self._redis = redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
                logger.info("Rate limiter using Redis backend")
        except Exception:
            self._redis = None
            logger.info("Rate limiter using in-memory backend")
    
    def is_allowed(self, ip: str) -> bool:
        """Check if request from IP is allowed."""
        if self._redis:
            return self._is_allowed_redis(ip)
        return self._is_allowed_memory(ip)
    
    def _is_allowed_redis(self, ip: str) -> bool:
        """Redis-backed rate limiting using sliding window."""
        key = f"ratelimit:{ip}"
        try:
            pipe = self._redis.pipeline()
            now = time.time()
            pipe.zremrangebyscore(key, 0, now - self.window_seconds)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, self.window_seconds)
            results = pipe.execute()
            count = results[2]
            return count <= self.max_requests
        except Exception:
            # Fall back to memory on Redis error
            return self._is_allowed_memory(ip)

    def _is_allowed_memory(self, ip: str) -> bool:
        """In-memory rate limiting."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        self.requests[ip] = [t for t in self.requests[ip] if t > cutoff]
        
        if len(self.requests[ip]) < self.max_requests:
            self.requests[ip].append(now)
            return True
        
        return False
    
    def cleanup(self):
        """Clean up old entries to prevent memory leak."""
        now = time.time()
        cutoff = now - self.window_seconds
        to_remove = [
            ip for ip, times in self.requests.items()
            if not times or max(times) < cutoff
        ]
        for ip in to_remove:
            del self.requests[ip]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting."""
    
    def __init__(self, app, limiter: RateLimiter):
        """Initialize middleware.
        
        Args:
            app: FastAPI application
            limiter: RateLimiter instance
        """
        super().__init__(app)
        self.limiter = limiter
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limit
        if not self.limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate Limit Exceeded",
                    "message": "Too many requests. Please try again later."
                }
            )
        
        # Continue processing
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response with security headers
        """
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size."""
    
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        """Initialize middleware.
        
        Args:
            app: FastAPI application
            max_size: Maximum request body size in bytes
        """
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        """Check request size.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
            
        Returns:
            Response
        """
        # Check content length if provided
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": "Request Too Large",
                    "message": f"Request body must be less than {self.max_size} bytes"
                }
            )
        
        response = await call_next(request)
        return response


def add_security_middleware(
    app: FastAPI,
    cors_origins: Optional[List[str]] = None,
    rate_limit: int = 100,
    rate_window: int = 60,
    max_request_size: int = 10 * 1024 * 1024
):
    """Add all security middleware to FastAPI app.
    
    Args:
        app: FastAPI application
        cors_origins: Allowed CORS origins (None = allow all)
        rate_limit: Maximum requests per IP in window
        rate_window: Rate limit window in seconds
        max_request_size: Maximum request body size in bytes
    """
    # CORS middleware
    if cors_origins is None:
        cors_origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8080",
        ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request size limit
    app.add_middleware(RequestSizeLimitMiddleware, max_size=max_request_size)
    
    # Rate limiting
    limiter = RateLimiter(max_requests=rate_limit, window_seconds=rate_window)
    app.add_middleware(RateLimitMiddleware, limiter=limiter)
