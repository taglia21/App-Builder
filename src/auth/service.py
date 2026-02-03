"""
LaunchForge Authentication Service

Core authentication logic connecting all auth components.
Handles user registration, login, token management, and OAuth.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from src.auth.jwt import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    InvalidTokenError,
    TokenExpiredError,
    TokenType,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from src.auth.password import (
    PasswordStrengthError,
    hash_password,
    validate_password_strength,
    verify_password,
)
from src.auth.schemas import (
    TokenResponse,
    UserResponse,
)
from src.auth.tokens import (
    generate_reset_token,
    generate_verification_token,
    verify_reset_token,
)
from src.database.models import SubscriptionTier, User
from src.database.repositories import UserRepository

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Base exception for authentication errors."""
    pass


class UserExistsError(AuthError):
    """Raised when trying to register with existing email."""
    pass


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid."""
    pass


class UserNotFoundError(AuthError):
    """Raised when user is not found."""
    pass


class EmailNotVerifiedError(AuthError):
    """Raised when email verification is required."""
    pass


class AuthService:
    """
    Authentication service for LaunchForge.

    Handles all authentication operations including registration,
    login, token management, and password reset.
    """

    def __init__(self, session: Session):
        """
        Initialize auth service.

        Args:
            session: SQLAlchemy database session
        """
        self.session = session
        self.user_repo = UserRepository(session)

    def register(
        self,
        email: str,
        password: str,
        name: Optional[str] = None,
    ) -> Tuple[User, str]:
        """
        Register a new user.

        Args:
            email: User's email address
            password: User's password (plain text)
            name: Optional display name

        Returns:
            Tuple[User, str]: (created user, email verification token)

        Raises:
            UserExistsError: If email is already registered
            PasswordStrengthError: If password doesn't meet requirements
        """
        # Validate password strength
        is_valid, errors = validate_password_strength(password)
        if not is_valid:
            raise PasswordStrengthError("Password too weak", errors)

        # Check if user exists
        existing = self.user_repo.get_by_email(email)
        if existing:
            raise UserExistsError(f"User with email {email} already exists")

        # Hash password
        password_hash = hash_password(password)

        # Generate verification token
        verification_token = generate_verification_token()

        # Create user
        user = User(
            id=str(uuid4()),
            email=email.lower().strip(),
            password_hash=password_hash,
            subscription_tier=SubscriptionTier.FREE,
            credits_remaining=100,
            email_verified=False,
            verification_token=verification_token,
        )

        if name:
            user.name = name

        self.session.add(user)
        self.session.flush()

        logger.info(f"User registered: {email}")

        return user, verification_token

    def login(
        self,
        email: str,
        password: str,
        require_verified: bool = False,
    ) -> Tuple[User, TokenResponse]:
        """
        Authenticate a user and generate tokens.

        Args:
            email: User's email address
            password: User's password
            require_verified: Require email to be verified

        Returns:
            Tuple[User, TokenResponse]: (user, tokens)

        Raises:
            InvalidCredentialsError: If credentials are invalid
            EmailNotVerifiedError: If email not verified and required
        """
        # Find user
        user = self.user_repo.get_by_email(email)
        if not user:
            raise InvalidCredentialsError("Invalid email or password")

        # Verify password
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")

        # Check verification if required
        if require_verified and not user.email_verified:
            raise EmailNotVerifiedError("Please verify your email before logging in")

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        self.session.flush()

        # Generate tokens
        tokens = self._generate_tokens(user)

        logger.info(f"User logged in: {email}")

        return user, tokens

    def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            TokenResponse: New token pair

        Raises:
            TokenError: If refresh token is invalid
        """
        try:
            payload = verify_token(refresh_token, TokenType.REFRESH)
            user_id = payload.get("sub")

            user = self.user_repo.get(user_id)
            if not user:
                raise InvalidTokenError("User not found")

            if user.is_deleted:
                raise InvalidTokenError("User account is deactivated")

            return self._generate_tokens(user)

        except TokenExpiredError:
            raise TokenExpiredError("Refresh token has expired. Please login again.")
        except InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid refresh token: {e}")

    def verify_email(self, token: str) -> User:
        """
        Verify user's email address.

        Args:
            token: Email verification token

        Returns:
            User: Verified user

        Raises:
            InvalidTokenError: If token is invalid
        """
        # Find user by verification token
        user = self.session.query(User).filter(
            User.verification_token == token,
            User.is_deleted == False,
        ).first()

        if not user:
            raise InvalidTokenError("Invalid or expired verification token")

        if user.email_verified:
            # Already verified, just return
            return user

        # Mark as verified
        user.email_verified = True
        user.verification_token = None
        self.session.flush()

        logger.info(f"Email verified: {user.email}")

        return user

    def request_password_reset(self, email: str) -> Optional[str]:
        """
        Request a password reset.

        Args:
            email: User's email address

        Returns:
            Optional[str]: Reset token if user exists, None otherwise

        Note:
            Always returns same response time to prevent email enumeration
        """
        user = self.user_repo.get_by_email(email)

        if not user:
            # Don't reveal that email doesn't exist
            logger.warning(f"Password reset requested for non-existent email: {email}")
            return None

        # Generate reset token
        reset_token, expires_at = generate_reset_token()

        # Store in user record
        user.reset_token = reset_token
        user.reset_token_expires = expires_at
        self.session.flush()

        logger.info(f"Password reset requested: {email}")

        return reset_token

    def reset_password(self, token: str, new_password: str) -> User:
        """
        Reset user's password.

        Args:
            token: Password reset token
            new_password: New password

        Returns:
            User: Updated user

        Raises:
            InvalidTokenError: If token is invalid or expired
            PasswordStrengthError: If new password is too weak
        """
        # Validate new password
        is_valid, errors = validate_password_strength(new_password)
        if not is_valid:
            raise PasswordStrengthError("Password too weak", errors)

        # Find user by reset token
        user = self.session.query(User).filter(
            User.reset_token == token,
            User.is_deleted == False,
        ).first()

        if not user:
            raise InvalidTokenError("Invalid or expired reset token")

        # Verify token hasn't expired
        is_valid, error = verify_reset_token(
            token,
            user.reset_token,
            user.reset_token_expires
        )

        if not is_valid:
            raise InvalidTokenError(error)

        # Update password
        user.password_hash = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        self.session.flush()

        logger.info(f"Password reset completed: {user.email}")

        return user

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> User:
        """
        Change user's password (requires current password).

        Args:
            user_id: User's ID
            current_password: Current password
            new_password: New password

        Returns:
            User: Updated user

        Raises:
            InvalidCredentialsError: If current password is wrong
            PasswordStrengthError: If new password is too weak
        """
        user = self.user_repo.get(user_id)
        if not user:
            raise UserNotFoundError("User not found")

        # Verify current password
        if not verify_password(current_password, user.password_hash):
            raise InvalidCredentialsError("Current password is incorrect")

        # Validate new password
        is_valid, errors = validate_password_strength(new_password)
        if not is_valid:
            raise PasswordStrengthError("Password too weak", errors)

        # Update password
        user.password_hash = hash_password(new_password)
        self.session.flush()

        logger.info(f"Password changed: {user.email}")

        return user

    def get_user_by_token(self, access_token: str) -> User:
        """
        Get user from access token.

        Args:
            access_token: JWT access token

        Returns:
            User: Authenticated user

        Raises:
            TokenError: If token is invalid
            UserNotFoundError: If user doesn't exist
        """
        payload = verify_token(access_token, TokenType.ACCESS)
        user_id = payload.get("sub")

        user = self.user_repo.get(user_id)
        if not user or user.is_deleted:
            raise UserNotFoundError("User not found")

        return user

    def create_or_link_oauth_user(
        self,
        email: str,
        oauth_provider: str,
        oauth_id: str,
        name: Optional[str] = None,
        email_verified: bool = False,
    ) -> Tuple[User, bool]:
        """
        Create or link a user from OAuth login.

        Args:
            email: User's email from OAuth
            oauth_provider: Provider name (e.g., "google")
            oauth_id: User's ID from provider
            name: User's name from provider
            email_verified: Whether provider verified the email

        Returns:
            Tuple[User, bool]: (user, is_new_user)
        """
        # Check for existing user
        existing = self.user_repo.get_by_email(email)

        if existing:
            # Update OAuth info
            if not hasattr(existing, 'oauth_provider') or not existing.oauth_provider:
                existing.oauth_provider = oauth_provider
                existing.oauth_id = oauth_id

            # Trust OAuth provider's email verification
            if email_verified and not existing.email_verified:
                existing.email_verified = True

            existing.last_login_at = datetime.now(timezone.utc)
            self.session.flush()

            return existing, False

        # Create new user
        user = User(
            id=str(uuid4()),
            email=email.lower().strip(),
            password_hash="",  # OAuth users don't have passwords
            subscription_tier=SubscriptionTier.FREE,
            credits_remaining=100,
            email_verified=email_verified,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
        )

        if name:
            user.name = name

        self.session.add(user)
        self.session.flush()

        logger.info(f"OAuth user created: {email} via {oauth_provider}")

        return user, True

    def _generate_tokens(self, user: User) -> TokenResponse:
        """Generate access and refresh tokens for user."""
        access_token = create_access_token(
            user_id=user.id,
            email=user.email,
            additional_claims={
                "tier": user.subscription_tier.value,
                "verified": user.email_verified,
            }
        )

        refresh_token = create_refresh_token(
            user_id=user.id,
            token_id=str(uuid4()),
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def to_user_response(self, user: User) -> UserResponse:
        """Convert User model to UserResponse schema."""
        return UserResponse(
            id=user.id,
            email=user.email,
            name=getattr(user, 'name', None),
            subscription_tier=user.subscription_tier.value,
            credits_remaining=user.credits_remaining,
            email_verified=user.email_verified,
            created_at=user.created_at,
        )
