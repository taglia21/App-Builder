"""
LaunchForge Authentication Module

Production-ready authentication system with:
- Password hashing (bcrypt)
- JWT tokens (access + refresh)
- Email verification
- Password reset
- OAuth2 (Google)
"""

from src.auth.jwt import (
    InvalidTokenError,
    TokenError,
    TokenExpiredError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)
from src.auth.password import (
    PasswordStrengthError,
    hash_password,
    validate_password_strength,
    verify_password,
)
from src.auth.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from src.auth.tokens import (
    generate_reset_token,
    generate_verification_token,
    verify_reset_token,
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
