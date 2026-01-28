"""
LaunchForge Token Utilities

Generation and verification of various tokens:
- Email verification tokens
- Password reset tokens
- API tokens
"""

import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import uuid4


# Token configuration
VERIFICATION_TOKEN_LENGTH = 32
RESET_TOKEN_LENGTH = 32
API_TOKEN_LENGTH = 48

RESET_TOKEN_EXPIRE_HOURS = 1
VERIFICATION_TOKEN_EXPIRE_HOURS = 24


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Length of token in bytes (will be hex encoded to 2x length)
        
    Returns:
        str: Hex-encoded secure token
    """
    return secrets.token_hex(length)


def generate_verification_token() -> str:
    """
    Generate a token for email verification.
    
    Returns:
        str: Verification token
    """
    return generate_secure_token(VERIFICATION_TOKEN_LENGTH)


def generate_reset_token() -> Tuple[str, datetime]:
    """
    Generate a password reset token with expiration.
    
    Returns:
        Tuple[str, datetime]: (reset_token, expiration_datetime)
    """
    token = generate_secure_token(RESET_TOKEN_LENGTH)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
    return token, expires_at


def verify_reset_token(
    token: str,
    stored_token: str,
    expires_at: Optional[datetime]
) -> Tuple[bool, Optional[str]]:
    """
    Verify a password reset token.
    
    Args:
        token: Token provided by user
        stored_token: Token stored in database
        expires_at: Expiration time from database
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Check if token matches
    if not secrets.compare_digest(token, stored_token):
        return False, "Invalid reset token"
    
    # Check expiration
    if expires_at is None:
        return False, "Reset token has no expiration"
    
    # Handle timezone-aware comparison
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if now > expires_at:
        return False, "Reset token has expired"
    
    return True, None


def generate_api_token() -> Tuple[str, str]:
    """
    Generate an API token for programmatic access.
    
    Returns:
        Tuple[str, str]: (full_token, token_hash)
        - full_token: Give to user (shown only once)
        - token_hash: Store in database
    """
    # Generate token with prefix for easy identification
    token_id = str(uuid4()).replace("-", "")[:8]
    token_secret = generate_secure_token(API_TOKEN_LENGTH)
    full_token = f"lf_{token_id}_{token_secret}"
    
    # Hash for storage
    token_hash = hash_api_token(full_token)
    
    return full_token, token_hash


def hash_api_token(token: str) -> str:
    """
    Hash an API token for secure storage.
    
    Args:
        token: Full API token
        
    Returns:
        str: SHA-256 hash of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def verify_api_token(token: str, stored_hash: str) -> bool:
    """
    Verify an API token against its stored hash.
    
    Args:
        token: API token to verify
        stored_hash: Hash from database
        
    Returns:
        bool: True if valid
    """
    token_hash = hash_api_token(token)
    return secrets.compare_digest(token_hash, stored_hash)


def generate_session_id() -> str:
    """
    Generate a unique session identifier.
    
    Returns:
        str: Session ID
    """
    return str(uuid4())


def mask_token(token: str, visible_chars: int = 8) -> str:
    """
    Mask a token for safe display.
    
    Args:
        token: Token to mask
        visible_chars: Number of characters to show at start and end
        
    Returns:
        str: Masked token
    """
    if len(token) <= visible_chars * 2:
        return "*" * len(token)
    
    start = token[:visible_chars]
    end = token[-visible_chars:]
    middle_len = len(token) - (visible_chars * 2)
    
    return f"{start}{'*' * min(middle_len, 8)}{end}"
