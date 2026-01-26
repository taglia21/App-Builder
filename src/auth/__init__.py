"""
NexusAI Authentication Module

Production-ready authentication system with:
- Password hashing (bcrypt)
- JWT tokens (access + refresh)
- Email verification
- Password reset
- OAuth2 (Google)
"""

from src.auth.password import (
    hash_password,
    verify_password,
    validate_password_strength,
    PasswordStrengthError,
)
from src.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token,
    TokenType,
    TokenError,
    TokenExpiredError,
    InvalidTokenError,
)
from src.auth.tokens import (
    generate_verification_token,
    generate_reset_token,
    verify_reset_token,
)
from src.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    TokenResponse,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserResponse,
)

__all__ = [
    # Password
    "hash_password",
    "verify_password",
    "validate_password_strength",
    "PasswordStrengthError",
    # JWT
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token",
    "TokenType",
    "TokenError",
    "TokenExpiredError",
    "InvalidTokenError",
    # Tokens
    "generate_verification_token",
    "generate_reset_token",
    "verify_reset_token",
    # Schemas
    "RegisterRequest",
    "LoginRequest",
    "LoginResponse",
    "RefreshRequest",
    "TokenResponse",
    "VerifyEmailRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "UserResponse",
]
