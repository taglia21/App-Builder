"""Web authentication routes for Valeric dashboard."""

import hashlib
import hmac
import logging
import os
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.auth.password import hash_password, validate_password_strength, verify_password
from src.database.db import get_session
from src.database.models import User

logger = logging.getLogger(__name__)

# --- Signed cookie helpers ---------------------------------------------------
_COOKIE_SECRET: str | None = None


def _get_cookie_secret() -> str:
    """Get the cookie signing secret from environment, fail loudly if missing in prod."""
    global _COOKIE_SECRET
    if _COOKIE_SECRET is None:
        _COOKIE_SECRET = os.getenv(
            "COOKIE_SECRET",
            os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "")),
        )
        env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development"))
        if env.lower() in ("production", "prod") and len(_COOKIE_SECRET) < 32:
            raise ValueError(
                "COOKIE_SECRET (or SECRET_KEY) must be at least 32 characters in production."
            )
        if not _COOKIE_SECRET:
            _COOKIE_SECRET = "valeric-dev-cookie-secret-change-in-production"
    return _COOKIE_SECRET


def sign_session_cookie(user_id: str) -> str:
    """Create a signed session value: ``user_id.timestamp.signature``."""
    ts = str(int(time.time()))
    payload = f"{user_id}.{ts}"
    sig = hmac.new(
        _get_cookie_secret().encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}.{sig}"


def verify_session_cookie(cookie_value: str, max_age: int = 2592000) -> str | None:
    """Verify a signed session cookie and return the user_id, or None."""
    if not cookie_value:
        return None
    parts = cookie_value.split(".")
    if len(parts) != 3:
        return None
    user_id, ts_str, sig = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return None
    # Check expiry
    if time.time() - ts > max_age:
        return None
    # Verify signature
    expected_sig = hmac.new(
        _get_cookie_secret().encode(), f"{user_id}.{ts_str}".encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return None
    return user_id

# Setup templates
templates_path = Path(__file__).parent.parent / "dashboard" / "templates"
templates = Jinja2Templates(directory=str(templates_path))

router = APIRouter()

# --- Brute-force protection ---------------------------------------------------
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_DURATION = 900  # 15 minutes
_failed_attempts: dict[str, list[float]] = {}  # email -> [timestamps]

def _check_lockout(email: str) -> bool:
    """Return True if account is locked out due to too many failed attempts."""
    attempts = _failed_attempts.get(email, [])
    cutoff = time.time() - _LOCKOUT_DURATION
    recent = [t for t in attempts if t > cutoff]
    _failed_attempts[email] = recent
    return len(recent) >= _MAX_FAILED_ATTEMPTS

def _record_failed_attempt(email: str) -> None:
    """Record a failed login attempt."""
    if email not in _failed_attempts:
        _failed_attempts[email] = []
    _failed_attempts[email].append(time.time())

def _clear_failed_attempts(email: str) -> None:
    """Clear failed attempts on successful login."""
    _failed_attempts.pop(email, None)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page."""
    return templates.TemplateResponse(
        "pages/login.html",
        {"request": request}
    )


@router.post("/auth/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember: bool = Form(False),
    db: Session = Depends(get_session)
):
    """Process login form."""
    try:
        normalized_email = email.lower().strip()

        # Check lockout
        if _check_lockout(normalized_email):
            return templates.TemplateResponse(
                "pages/login.html",
                {"request": request, "error": "Too many failed attempts. Please try again in 15 minutes."}
            )

        # Find user
        user = db.query(User).filter(User.email == normalized_email).first()

        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            _record_failed_attempt(normalized_email)
            # Check if user exists but uses OAuth
            if user and not user.password_hash:
                return templates.TemplateResponse(
                    "pages/login.html",
                    {"request": request, "error": "This account uses social sign-in. Please log in with Google."}
                )
            return templates.TemplateResponse(
                "pages/login.html",
                {"request": request, "error": "Invalid email or password"}
            )

        _clear_failed_attempts(normalized_email)

        # Set signed session cookie
        max_age = 2592000 if remember else 86400  # 30 days or 1 day
        response = RedirectResponse(url="/projects", status_code=303)
        response.set_cookie(
            key="session",
            value=sign_session_cookie(str(user.id)),
            httponly=True,
            secure=os.getenv("ENVIRONMENT", "development") == "production",
            samesite="lax",
            max_age=max_age,
        )

        logger.info(f"User {email} logged in successfully")
        return response

    except Exception as e:
        logger.error(f"Login error: {e}")
        return templates.TemplateResponse(
            "pages/login.html",
            {"request": request, "error": "An error occurred. Please try again."}
        )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Display registration page."""
    return templates.TemplateResponse(
        "pages/register.html",
        {"request": request}
    )


@router.post("/auth/register")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    terms: bool = Form(False),
    db: Session = Depends(get_session)
):
    """Process registration form."""
    try:
        # Validate
        if not terms:
            return templates.TemplateResponse(
                "pages/register.html",
                {"request": request, "error": "You must agree to the terms"}
            )

        is_valid, pw_errors = validate_password_strength(password)
        if not is_valid:
            return templates.TemplateResponse(
                "pages/register.html",
                {"request": request, "error": pw_errors[0] if pw_errors else "Password too weak"}
            )

        # Check if user exists
        existing_user = db.query(User).filter(User.email == email.lower()).first()
        if existing_user:
            return templates.TemplateResponse(
                "pages/register.html",
                {"request": request, "error": "Email already registered"}
            )

        # Create user
        new_user = User(
            name=name,
            email=email.lower(),
            password_hash=hash_password(password),
            subscription_tier="FREE",
            credits_remaining=100,  # Free tier credits (consistent with API)
            email_verified=False
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"New user registered: {email}")

        # Auto-login after registration — signed session cookie
        response = RedirectResponse(url="/projects", status_code=303)
        response.set_cookie(
            key="session",
            value=sign_session_cookie(str(new_user.id)),
            httponly=True,
            secure=os.getenv("ENVIRONMENT", "development") == "production",
            samesite="lax",
            max_age=2592000,  # 30 days
        )
        return response

    except Exception as e:
        logger.error(f"Registration error: {e}")
        db.rollback()
        return templates.TemplateResponse(
            "pages/register.html",
            {"request": request, "error": "An error occurred. Please try again."}
        )


@router.get("/logout")
async def logout(request: Request):
    """Logout user."""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(key="session")
    # Also delete legacy cookie if present
    response.delete_cookie(key="user_id")
    return response
