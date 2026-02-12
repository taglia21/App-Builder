"""CSRF Protection Middleware.

Implements the Double-Submit Cookie pattern:
- On every response, set a `csrftoken` cookie with a random token.
- On POST/PUT/PATCH/DELETE requests, verify the token matches either:
  1. A form field `csrf_token`, or
  2. An `X-CSRFToken` header (for HTMX/AJAX)

The Jinja2 `csrf_token()` global reads the cookie value set by this middleware
and renders it as a hidden field in forms.
"""
import hashlib
import hmac
import logging
import os
import secrets
from typing import Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
COOKIE_NAME = "csrftoken"
HEADER_NAME = "x-csrftoken"
FORM_FIELD = "csrf_token"

# Exempt paths that legitimately receive external POST requests (e.g. webhooks)
DEFAULT_EXEMPT_PATHS = {
    "/billing/webhook",
    "/api/v1/webhooks",
    "/health",
    "/api/health",
}


def _get_csrf_secret() -> str:
    """Get the CSRF signing secret (shares the cookie secret)."""
    return os.getenv("COOKIE_SECRET", os.getenv("SECRET_KEY", "dev-csrf-secret"))


def _sign_token(token: str) -> str:
    """Create an HMAC signature for a CSRF token."""
    secret = _get_csrf_secret()
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def generate_csrf_token() -> str:
    """Generate a new CSRF token."""
    return secrets.token_hex(32)


class CSRFProtectMiddleware(BaseHTTPMiddleware):
    """CSRF protection using double-submit cookie pattern."""

    def __init__(
        self,
        app,
        exempt_paths: Optional[Set[str]] = None,
        cookie_secure: bool = False,
        cookie_samesite: str = "lax",
    ):
        super().__init__(app)
        self.exempt_paths = exempt_paths or DEFAULT_EXEMPT_PATHS
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip safe methods
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            # Ensure CSRF cookie is set on GET responses
            self._ensure_csrf_cookie(request, response)
            return response

        # Skip exempt paths (webhooks, health checks)
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        # Validate CSRF for unsafe methods
        cookie_token = request.cookies.get(COOKIE_NAME)
        if not cookie_token:
            logger.warning("CSRF: No csrftoken cookie on %s %s", request.method, request.url.path)
            return self._reject(request)

        # Check header first (HTMX / AJAX)
        submitted_token = request.headers.get(HEADER_NAME)

        # Check form field if header not present
        if not submitted_token:
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                try:
                    form = await request.form()
                    submitted_token = form.get(FORM_FIELD)
                except Exception:
                    pass

        if not submitted_token:
            logger.warning("CSRF: No token submitted on %s %s", request.method, request.url.path)
            return self._reject(request)

        # Constant-time comparison
        if not hmac.compare_digest(cookie_token, submitted_token):
            logger.warning("CSRF: Token mismatch on %s %s", request.method, request.url.path)
            return self._reject(request)

        response = await call_next(request)
        # Rotate the CSRF token after each successful POST
        self._set_csrf_cookie(response, generate_csrf_token())
        return response

    def _ensure_csrf_cookie(self, request: Request, response: Response):
        """Set CSRF cookie if not already present."""
        if COOKIE_NAME not in request.cookies:
            token = generate_csrf_token()
            self._set_csrf_cookie(response, token)

    def _set_csrf_cookie(self, response: Response, token: str):
        """Set the CSRF cookie on the response."""
        response.set_cookie(
            key=COOKIE_NAME,
            value=token,
            httponly=False,  # Must be readable by JavaScript for HTMX
            samesite=self.cookie_samesite,
            secure=self.cookie_secure,
            path="/",
            max_age=3600,  # 1 hour
        )

    def _reject(self, request: Request) -> Response:
        """Return a 403 CSRF validation failure."""
        # For API/HTMX requests, return JSON
        accept = request.headers.get("accept", "")
        if "application/json" in accept or "hx-request" in request.headers:
            return JSONResponse(
                {"detail": "CSRF validation failed"},
                status_code=403,
            )
        # For browser form submissions, return a simple error page
        from starlette.responses import HTMLResponse
        return HTMLResponse(
            "<h1>403 Forbidden</h1><p>CSRF validation failed. "
            "Please go back and try again.</p>",
            status_code=403,
        )
