from fastapi import Header

"""
LaunchForge Authentication Middleware

JWT verification middleware for protecting API routes.
"""

import logging
from functools import wraps
from typing import Any, Callable, Optional

from src.auth.jwt import (
    InvalidTokenError,
    TokenError,
    TokenExpiredError,
    TokenType,
    verify_token,
)
from src.database.db import get_db
from src.database.repositories import UserRepository

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


class AuthorizationError(Exception):
    """Raised when authorization fails."""

    def __init__(self, message: str, status_code: int = 403):
        super().__init__(message)
        self.status_code = status_code


def extract_token_from_header(auth_header: Optional[str]) -> Optional[str]:
    """
    Extract JWT token from Authorization header.

    Args:
        auth_header: Authorization header value

    Returns:
        str: JWT token or None
    """
    if not auth_header:
        return None

    parts = auth_header.split()

    if len(parts) != 2:
        return None

    scheme, token = parts

    if scheme.lower() != "bearer":
        return None

    return token


def get_current_user_id(auth_header: Optional[str]) -> str:
    """
    Get current user ID from Authorization header.

    Args:
        auth_header: Authorization header value

    Returns:
        str: User ID

    Raises:
        AuthenticationError: If authentication fails
    """
    token = extract_token_from_header(auth_header)

    if not token:
        raise AuthenticationError("Missing authentication token")

    try:
        payload = verify_token(token, TokenType.ACCESS)
        user_id = payload.get("sub")

        if not user_id:
            raise AuthenticationError("Invalid token: missing user ID")

        return user_id

    except TokenExpiredError:
        raise AuthenticationError("Token has expired", status_code=401)
    except InvalidTokenError as e:
        raise AuthenticationError(f"Invalid token: {e}", status_code=401)
    except TokenError as e:
        raise AuthenticationError(f"Token error: {e}", status_code=401)


def get_current_user(auth_header: Optional[str]):
    """
    Get current user from Authorization header.

    Args:
        auth_header: Authorization header value

    Returns:
        User: Current user object

    Raises:
        AuthenticationError: If authentication fails
    """
    user_id = get_current_user_id(auth_header)

    db = get_db()
    with db.session() as session:
        user_repo = UserRepository(session)
        user = user_repo.get(user_id)

        if not user:
            raise AuthenticationError("User not found")

        if user.is_deleted:
            raise AuthenticationError("User account is deactivated")

        return user


def verify_email_required(auth_header: Optional[str]) -> None:
    """
    Verify that the current user has verified their email.

    Args:
        auth_header: Authorization header value

    Raises:
        AuthorizationError: If email is not verified
    """
    token = extract_token_from_header(auth_header)

    if not token:
        raise AuthenticationError("Missing authentication token")

    try:
        payload = verify_token(token, TokenType.ACCESS)

        if not payload.get("verified", False):
            raise AuthorizationError(
                "Email verification required",
                status_code=403
            )

    except TokenError as e:
        raise AuthenticationError(f"Token error: {e}")


def _user_bypasses_billing(payload: dict) -> bool:
    """Check if a JWT payload indicates a demo/admin user who bypasses billing."""
    role = payload.get("role", "user")
    return role in ("admin", "demo")


def require_subscription_tier(required_tier: str):
    """
    Decorator to require a minimum subscription tier.
    Demo and admin users bypass this check.

    Args:
        required_tier: Minimum required tier (free, starter, pro, enterprise)
    """
    tier_hierarchy = ["free", "starter", "pro", "enterprise"]

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, auth_header: Optional[str] = None, **kwargs) -> Any:
            token = extract_token_from_header(auth_header)

            if not token:
                raise AuthenticationError("Missing authentication token")

            try:
                payload = verify_token(token, TokenType.ACCESS)

                # Demo/admin users bypass tier checks
                if _user_bypasses_billing(payload):
                    return func(*args, **kwargs)

                user_tier = payload.get("tier", "free")

                user_tier_level = tier_hierarchy.index(user_tier) if user_tier in tier_hierarchy else 0
                required_tier_level = tier_hierarchy.index(required_tier) if required_tier in tier_hierarchy else 0

                if user_tier_level < required_tier_level:
                    raise AuthorizationError(
                        f"This feature requires {required_tier} tier or higher",
                        status_code=403
                    )

                return func(*args, **kwargs)

            except TokenError as e:
                raise AuthenticationError(f"Token error: {e}")

        return wrapper
    return decorator


def require_credits(amount: int = 1):
    """
    Decorator to require user has enough credits.
    Demo and admin users bypass this check.

    Args:
        amount: Required credit amount
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, auth_header: Optional[str] = None, **kwargs) -> Any:
            user = get_current_user(auth_header)

            # Demo/admin users bypass credit checks
            if hasattr(user, 'bypasses_billing') and user.bypasses_billing:
                return func(*args, **kwargs)

            if user.credits_remaining < amount:
                raise AuthorizationError(
                    f"Insufficient credits. Required: {amount}, Available: {user.credits_remaining}",
                    status_code=402  # Payment Required
                )

            return func(*args, **kwargs)

        return wrapper
    return decorator


class JWTMiddleware:
    """
    JWT authentication middleware class.

    Can be used as a class-based middleware for frameworks
    that support it (e.g., Starlette, FastAPI).
    """

    def __init__(
        self,
        exclude_paths: Optional[list] = None,
        require_verified: bool = False,
    ):
        """
        Initialize JWT middleware.

        Args:
            exclude_paths: Paths to exclude from authentication
            require_verified: Require email verification
        """
        self.exclude_paths = exclude_paths or [
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/refresh",
            "/api/auth/forgot-password",
            "/api/auth/reset-password",
            "/api/auth/verify-email",
            "/api/auth/oauth/google",
            "/api/auth/oauth/google/callback",
            "/health",
            "/docs",
            "/openapi.json",
        ]
        self.require_verified = require_verified

    def is_excluded(self, path: str) -> bool:
        """Check if path is excluded from authentication."""
        for excluded in self.exclude_paths:
            if path.startswith(excluded):
                return True
        return False

    def authenticate(self, auth_header: Optional[str]) -> dict:
        """
        Authenticate request and return user info.

        Args:
            auth_header: Authorization header value

        Returns:
            dict: User info from token

        Raises:
            AuthenticationError: If authentication fails
        """
        token = extract_token_from_header(auth_header)

        if not token:
            raise AuthenticationError("Missing authentication token")

        try:
            payload = verify_token(token, TokenType.ACCESS)

            if self.require_verified and not payload.get("verified", False):
                raise AuthorizationError("Email verification required")

            return {
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "tier": payload.get("tier"),
                "verified": payload.get("verified"),
            }

        except TokenExpiredError:
            raise AuthenticationError("Token has expired")
        except InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {e}")


# Create default middleware instance
jwt_middleware = JWTMiddleware()

async def get_optional_current_user(auth_header: Optional[str] = Header(None, alias="Authorization")) -> Optional[dict]:
    """Get current user if authenticated, otherwise return None."""
    if not auth_header:
        return None
    try:
        return await get_current_user(auth_header)
    except (ValueError, KeyError, Exception):
        return None
