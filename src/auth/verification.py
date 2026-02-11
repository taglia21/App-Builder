"""
Email verification routes and service.

Handles:
- Sending verification emails
- Processing verification tokens
- Resending verification emails

Error Handling:
- Token validation errors
- Database errors
- Email sending failures
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database.models import User
from src.emails import send_verification_email, send_welcome_email

router = APIRouter(prefix="/verify", tags=["verification"])
logger = logging.getLogger(__name__)


class VerificationError(Exception):
    """Base exception for verification errors."""
    pass


class TokenExpiredError(VerificationError):
    """Raised when verification token has expired."""
    pass


class TokenInvalidError(VerificationError):
    """Raised when verification token is invalid."""
    pass


class AlreadyVerifiedError(VerificationError):
    """Raised when email is already verified."""
    pass


class ResendVerificationRequest(BaseModel):
    """Request to resend verification email."""
    email: EmailStr


def generate_verification_token() -> str:
    """Generate a secure verification token."""
    return secrets.token_urlsafe(48)


def validate_verification_token(token: str) -> bool:
    """
    Validate token format.

    Args:
        token: Token to validate

    Returns:
        True if token format is valid
    """
    if not token:
        return False
    # Token should be base64 URL-safe encoded, minimum 48 bytes
    if len(token) < 32:
        return False
    # Check for valid characters
    import re
    return bool(re.match(r'^[A-Za-z0-9_-]+$', token))


async def create_verification_token(
    user: User,
    db: Session,
    base_url: str,
    expiry_hours: int = 24
) -> str:
    """
    Create a verification token for a user.

    Args:
        user: User to create token for
        db: Database session
        base_url: Base URL for verification link
        expiry_hours: Token expiry time in hours

    Returns:
        Full verification URL

    Raises:
        SQLAlchemyError: If database operation fails
    """
    try:
        token = generate_verification_token()
        user.verification_token = token
        user.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
        db.commit()

        return f"{base_url}/verify/email/{token}"
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to create verification token: {e}")
        raise


async def send_verification_for_user(
    user: User,
    db: Session,
    base_url: str
) -> bool:
    """
    Send verification email to a user.

    Args:
        user: User to send verification to
        db: Database session
        base_url: Base URL for verification link

    Returns:
        True if email sent successfully

    Note:
        Logs errors but doesn't raise - returns False on failure
    """
    try:
        verification_url = await create_verification_token(user, db, base_url)

        result = await send_verification_email(
            email=user.email,
            name=user.name or user.email.split('@')[0],
            verification_url=verification_url
        )

        if not result.success:
            logger.error(f"Failed to send verification email to {user.email}: {result.error}")

        return result.success

    except SQLAlchemyError as e:
        logger.error(f"Database error sending verification to {user.email}: {e}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected error sending verification to {user.email}: {e}")
        return False


def verify_token_and_get_user(
    token: str,
    db: Session
) -> User:
    """
    Verify token and return associated user.

    Args:
        token: Verification token
        db: Database session

    Returns:
        User associated with token

    Raises:
        TokenInvalidError: If token is invalid or not found
        TokenExpiredError: If token has expired
        AlreadyVerifiedError: If email already verified
    """
    # Validate token format
    if not validate_verification_token(token):
        raise TokenInvalidError("Invalid token format")

    # Find user with token
    user = db.query(User).filter(
        User.verification_token == token,
        not User.is_deleted
    ).first()

    if not user:
        raise TokenInvalidError("Verification token not found")

    # Check if already verified
    if user.email_verified:
        raise AlreadyVerifiedError("Email already verified")

    # Check expiry (if field exists)
    if hasattr(user, 'verification_token_expires') and user.verification_token_expires:
        if datetime.now(timezone.utc) > user.verification_token_expires:
            raise TokenExpiredError("Verification token has expired")

    return user


@router.get("/email/{token}", response_class=HTMLResponse)
async def verify_email(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Verify email address using token.

    Args:
        token: Verification token from email
        request: FastAPI request
        db: Database session

    Returns:
        Redirect to dashboard with success/error message
    """
    try:
        # Validate and get user
        user = verify_token_and_get_user(token, db)

        # Mark as verified
        user.email_verified = True
        user.verification_token = None
        user.email_verified_at = datetime.now(timezone.utc)

        # Update onboarding status if exists
        try:
            from src.database.models import OnboardingStatus
            onboarding = db.query(OnboardingStatus).filter(
                OnboardingStatus.user_id == user.id
            ).first()
            if onboarding:
                onboarding.email_verified = True
                onboarding.email_verified_at = datetime.now(timezone.utc)
        except (ValueError, TypeError, Exception):
            pass  # Onboarding table may not exist yet

        db.commit()

        # Track metric
        try:
            from src.monitoring.metrics import track_onboarding_step
            track_onboarding_step("email_verified")
        except (ValueError, TypeError, Exception):
            pass

        # Send welcome email (don't fail verification if this fails)
        try:
            await send_welcome_email(
                email=user.email,
                name=user.name or user.email.split('@')[0]
            )
        except Exception as e:
            logger.warning(f"Failed to send welcome email to {user.email}: {e}")

        # Redirect to dashboard with success
        return RedirectResponse(
            url="/dashboard?message=email_verified",
            status_code=status.HTTP_302_FOUND
        )

    except AlreadyVerifiedError:
        logger.info(f"Token {token[:8]}... - email already verified")
        return RedirectResponse(
            url="/dashboard?message=already_verified",
            status_code=status.HTTP_302_FOUND
        )

    except TokenExpiredError:
        logger.warning(f"Token {token[:8]}... has expired")
        return RedirectResponse(
            url="/login?error=token_expired",
            status_code=status.HTTP_302_FOUND
        )

    except TokenInvalidError as e:
        logger.warning(f"Invalid verification token: {e}")
        return RedirectResponse(
            url="/login?error=invalid_token",
            status_code=status.HTTP_302_FOUND
        )

    except SQLAlchemyError as e:
        logger.error(f"Database error during email verification: {e}")
        db.rollback()
        return RedirectResponse(
            url="/login?error=verification_failed",
            status_code=status.HTTP_302_FOUND
        )

    except Exception as e:
        logger.exception(f"Unexpected error during email verification: {e}")
        return RedirectResponse(
            url="/login?error=verification_failed",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/resend")
async def resend_verification(
    request: Request,
    data: ResendVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Resend verification email.

    Args:
        request: FastAPI request
        data: Request with email
        db: Database session

    Returns:
        Success response (always, for security - prevents email enumeration)
    """
    try:
        user = db.query(User).filter(
            User.email == data.email,
            not User.is_deleted
        ).first()

        # Always return success to prevent email enumeration
        if user and not user.email_verified:
            base_url = str(request.base_url).rstrip('/')
            success = await send_verification_for_user(user, db, base_url)

            if not success:
                # Log but don't expose to user
                logger.warning(f"Failed to resend verification to {data.email}")

        return {"message": "If an account exists, a verification email has been sent"}

    except SQLAlchemyError as e:
        logger.error(f"Database error in resend_verification: {e}")
        # Still return success to prevent enumeration
        return {"message": "If an account exists, a verification email has been sent"}

    except Exception as e:
        logger.exception(f"Unexpected error in resend_verification: {e}")
        return {"message": "If an account exists, a verification email has been sent"}


@router.get("/status")
async def verification_status(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Check verification status for current user.

    Returns:
        Verification status
    """
    # This would normally check the authenticated user
    # For now, return a placeholder
    return {
        "verified": False,
        "email": None
    }


def get_verification_page_html(
    success: bool = True,
    message: str = ""
) -> str:
    """Generate verification result HTML page."""

    if success:
        content = f"""
        <div class="text-center">
            <div class="w-16 h-16 mx-auto mb-6 rounded-full bg-green-100 flex items-center justify-center">
                <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
            </div>
            <h1 class="text-2xl font-bold text-gray-900 mb-2">Email Verified!</h1>
            <p class="text-gray-600 mb-6">{message or "Your email has been verified successfully."}</p>
            <a href="/dashboard" class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-forge-600 hover:bg-forge-700">
                Go to Dashboard
            </a>
        </div>
        """
    else:
        content = f"""
        <div class="text-center">
            <div class="w-16 h-16 mx-auto mb-6 rounded-full bg-red-100 flex items-center justify-center">
                <svg class="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </div>
            <h1 class="text-2xl font-bold text-gray-900 mb-2">Verification Failed</h1>
            <p class="text-gray-600 mb-6">{message or "This verification link is invalid or has expired."}</p>
            <a href="/login" class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-forge-600 hover:bg-forge-700">
                Back to Login
            </a>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Email Verification - Valeric</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="min-h-screen bg-gray-100 flex items-center justify-center">
        <div class="max-w-md w-full bg-white rounded-xl shadow-lg p-8">
            {content}
        </div>
    </body>
    </html>
    """
