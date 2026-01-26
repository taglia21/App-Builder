"""
NexusAI JWT Token Module

JWT token generation and verification for authentication.
Supports access tokens (short-lived) and refresh tokens (long-lived).
"""

import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional

import jwt


class TokenType(str, Enum):
    """Types of JWT tokens."""
    ACCESS = "access"
    REFRESH = "refresh"
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


class TokenError(Exception):
    """Base exception for token errors."""
    pass


class TokenExpiredError(TokenError):
    """Raised when a token has expired."""
    pass


class InvalidTokenError(TokenError):
    """Raised when a token is invalid."""
    pass


# Token configuration
DEFAULT_SECRET_KEY = "nexusai-dev-secret-key-change-in-production"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
EMAIL_VERIFICATION_EXPIRE_HOURS = 24
PASSWORD_RESET_EXPIRE_HOURS = 1

ALGORITHM = "HS256"


def get_secret_key() -> str:
    """Get the JWT secret key from environment or default."""
    return os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY))


def create_access_token(
    user_id: str,
    email: str,
    additional_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        additional_claims: Extra claims to include in the token
        expires_delta: Custom expiration time
        
    Returns:
        str: Encoded JWT access token
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    payload = {
        "sub": user_id,
        "email": email,
        "type": TokenType.ACCESS.value,
        "iat": now,
        "exp": expire,
    }
    
    if additional_claims:
        payload.update(additional_claims)
    
    return jwt.encode(payload, get_secret_key(), algorithm=ALGORITHM)


def create_refresh_token(
    user_id: str,
    token_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User's unique identifier
        token_id: Unique identifier for this refresh token (for revocation)
        expires_delta: Custom expiration time
        
    Returns:
        str: Encoded JWT refresh token
    """
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    payload = {
        "sub": user_id,
        "type": TokenType.REFRESH.value,
        "iat": now,
        "exp": expire,
    }
    
    if token_id:
        payload["jti"] = token_id  # JWT ID for token revocation
    
    return jwt.encode(payload, get_secret_key(), algorithm=ALGORITHM)


def create_email_verification_token(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a token for email verification.
    
    Args:
        user_id: User's unique identifier
        email: Email address to verify
        expires_delta: Custom expiration time
        
    Returns:
        str: Encoded JWT token for email verification
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=EMAIL_VERIFICATION_EXPIRE_HOURS)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    payload = {
        "sub": user_id,
        "email": email,
        "type": TokenType.EMAIL_VERIFICATION.value,
        "iat": now,
        "exp": expire,
    }
    
    return jwt.encode(payload, get_secret_key(), algorithm=ALGORITHM)


def create_password_reset_token(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a token for password reset.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        expires_delta: Custom expiration time
        
    Returns:
        str: Encoded JWT token for password reset
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=PASSWORD_RESET_EXPIRE_HOURS)
    
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    payload = {
        "sub": user_id,
        "email": email,
        "type": TokenType.PASSWORD_RESET.value,
        "iat": now,
        "exp": expire,
    }
    
    return jwt.encode(payload, get_secret_key(), algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode a JWT token without verification.
    
    Args:
        token: Encoded JWT token
        
    Returns:
        Dict: Token payload
        
    Raises:
        InvalidTokenError: If token is malformed
    """
    try:
        return jwt.decode(
            token,
            get_secret_key(),
            algorithms=[ALGORITHM],
            options={"verify_exp": False}
        )
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {str(e)}")


def verify_token(
    token: str,
    expected_type: Optional[TokenType] = None,
) -> Dict[str, Any]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: Encoded JWT token
        expected_type: Expected token type (access, refresh, etc.)
        
    Returns:
        Dict: Verified token payload
        
    Raises:
        TokenExpiredError: If token has expired
        InvalidTokenError: If token is invalid or type mismatch
    """
    try:
        payload = jwt.decode(
            token,
            get_secret_key(),
            algorithms=[ALGORITHM],
        )
        
        # Verify token type if specified
        if expected_type:
            token_type = payload.get("type")
            if token_type != expected_type.value:
                raise InvalidTokenError(
                    f"Expected {expected_type.value} token, got {token_type}"
                )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {str(e)}")


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get the expiration time of a token.
    
    Args:
        token: Encoded JWT token
        
    Returns:
        datetime: Expiration time or None if not set
    """
    try:
        payload = decode_token(token)
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=timezone.utc)
        return None
    except InvalidTokenError:
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if a token has expired.
    
    Args:
        token: Encoded JWT token
        
    Returns:
        bool: True if expired, False otherwise
    """
    expiry = get_token_expiry(token)
    if expiry is None:
        return True
    return datetime.now(timezone.utc) > expiry


def get_user_id_from_token(token: str) -> Optional[str]:
    """
    Extract user ID from a token without full verification.
    
    Args:
        token: Encoded JWT token
        
    Returns:
        str: User ID or None if extraction fails
    """
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except InvalidTokenError:
        return None
