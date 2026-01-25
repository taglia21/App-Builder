"""
Email verification routes and service.

Handles:
- Sending verification emails
- Processing verification tokens
- Resending verification emails
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from src.database.engine import get_db
from src.database.models import User
from src.emails import send_verification_email, send_welcome_email

router = APIRouter(prefix="/verify", tags=["verification"])


class ResendVerificationRequest(BaseModel):
    """Request to resend verification email."""
    email: EmailStr


def generate_verification_token() -> str:
    """Generate a secure verification token."""
    return secrets.token_urlsafe(48)


async def create_verification_token(
    user: User,
    db: Session,
    base_url: str
) -> str:
    """
    Create a verification token for a user.
    
    Args:
        user: User to create token for
        db: Database session
        base_url: Base URL for verification link
        
    Returns:
        Full verification URL
    """
    token = generate_verification_token()
    user.verification_token = token
    db.commit()
    
    return f"{base_url}/verify/email/{token}"


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
    """
    verification_url = await create_verification_token(user, db, base_url)
    
    result = await send_verification_email(
        email=user.email,
        name=user.name or user.email.split('@')[0],
        verification_url=verification_url
    )
    
    return result.success


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
    # Find user with this token
    user = db.query(User).filter(
        User.verification_token == token,
        User.is_deleted == False
    ).first()
    
    if not user:
        # Invalid or expired token
        return RedirectResponse(
            url="/login?error=invalid_token",
            status_code=status.HTTP_302_FOUND
        )
    
    if user.email_verified:
        # Already verified
        return RedirectResponse(
            url="/dashboard?message=already_verified",
            status_code=status.HTTP_302_FOUND
        )
    
    # Mark as verified
    user.email_verified = True
    user.verification_token = None  # Invalidate token
    db.commit()
    
    # Send welcome email
    await send_welcome_email(
        email=user.email,
        name=user.name or user.email.split('@')[0]
    )
    
    # Redirect to dashboard with success
    return RedirectResponse(
        url="/dashboard?message=email_verified",
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
        Success response (always, for security)
    """
    user = db.query(User).filter(
        User.email == data.email,
        User.is_deleted == False
    ).first()
    
    # Always return success to prevent email enumeration
    if user and not user.email_verified:
        base_url = str(request.base_url).rstrip('/')
        await send_verification_for_user(user, db, base_url)
    
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
        <title>Email Verification - LaunchForge</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="min-h-screen bg-gray-100 flex items-center justify-center">
        <div class="max-w-md w-full bg-white rounded-xl shadow-lg p-8">
            {content}
        </div>
    </body>
    </html>
    """
