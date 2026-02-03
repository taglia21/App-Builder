"""
LaunchForge Authentication Schemas

Pydantic models for request/response validation in auth endpoints.
"""

import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, max_length=128, description="User's password")
    name: Optional[str] = Field(None, max_length=255, description="User's display name")

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        errors = []

        if len(v) < 8:
            errors.append("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', v):
            errors.append("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            errors.append("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            errors.append("Password must contain at least one digit")

        if errors:
            raise ValueError("; ".join(errors))

        return v


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")
    remember_me: bool = Field(False, description="Extend token expiration")


class TokenResponse(BaseModel):
    """Response schema for token operations."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class LoginResponse(BaseModel):
    """Response schema for successful login."""

    user: "UserResponse"
    tokens: TokenResponse
    message: str = "Login successful"


class RefreshRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str = Field(..., description="JWT refresh token")


class VerifyEmailRequest(BaseModel):
    """Request schema for email verification."""

    token: str = Field(..., description="Email verification token")


class ForgotPasswordRequest(BaseModel):
    """Request schema for password reset request."""

    email: EmailStr = Field(..., description="User's email address")


class ResetPasswordRequest(BaseModel):
    """Request schema for password reset."""

    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        errors = []

        if len(v) < 8:
            errors.append("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', v):
            errors.append("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            errors.append("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            errors.append("Password must contain at least one digit")

        if errors:
            raise ValueError("; ".join(errors))

        return v


class ChangePasswordRequest(BaseModel):
    """Request schema for password change (logged in user)."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength."""
        errors = []

        if len(v) < 8:
            errors.append("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', v):
            errors.append("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            errors.append("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            errors.append("Password must contain at least one digit")

        if errors:
            raise ValueError("; ".join(errors))

        return v


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User's email address")
    name: Optional[str] = Field(None, description="User's display name")
    subscription_tier: str = Field(..., description="Subscription tier")
    credits_remaining: int = Field(..., description="API credits remaining")
    email_verified: bool = Field(..., description="Email verification status")
    created_at: datetime = Field(..., description="Account creation date")

    model_config = {"from_attributes": True}


class AuthError(BaseModel):
    """Error response for authentication failures."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[List[str]] = Field(None, description="Detailed error messages")


class OAuthState(BaseModel):
    """State for OAuth flow."""

    state: str = Field(..., description="CSRF state token")
    redirect_uri: Optional[str] = Field(None, description="Post-auth redirect URI")
    nonce: Optional[str] = Field(None, description="Nonce for OIDC")


class OAuthCallbackRequest(BaseModel):
    """Request from OAuth callback."""

    code: str = Field(..., description="Authorization code")
    state: str = Field(..., description="State parameter for CSRF protection")


class GoogleUserInfo(BaseModel):
    """User info from Google OAuth."""

    id: str = Field(..., description="Google user ID")
    email: str = Field(..., description="User's email")
    verified_email: bool = Field(False, description="Email verification status")
    name: Optional[str] = Field(None, description="User's full name")
    given_name: Optional[str] = Field(None, description="User's first name")
    family_name: Optional[str] = Field(None, description="User's last name")
    picture: Optional[str] = Field(None, description="Profile picture URL")


# Forward reference resolution
LoginResponse.model_rebuild()
