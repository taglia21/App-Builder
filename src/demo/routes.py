"""
Demo access routes for LaunchForge.

Provides a /demo URL that auto-authenticates users with the demo account,
and a /demo/info endpoint that returns demo credentials as JSON.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.database.models import User
from src.demo.seed_demo_account import get_demo_credentials

logger = logging.getLogger(__name__)

# Setup templates
templates_path = Path(__file__).parent.parent / "dashboard" / "templates"
templates = Jinja2Templates(directory=str(templates_path))

router = APIRouter(tags=["demo"])

# Cache demo mode check
_demo_mode: Optional[bool] = None


def is_demo_enabled() -> bool:
    """Check if demo mode is enabled."""
    global _demo_mode
    if _demo_mode is None:
        _demo_mode = os.environ.get("DEMO_MODE", "").lower() in ("true", "1", "yes")
    return _demo_mode


@router.get("/demo")
async def demo_login(
    request: Request,
    token: Optional[str] = Query(None),
):
    """
    Auto-login with demo account and redirect to dashboard.

    Accessible via:
      - GET /demo (when DEMO_MODE=true)
      - GET /demo?token=<DEMO_TOKEN> (token-based access)

    The demo account is created on first access if it doesn't exist.
    """
    # Check if demo mode is enabled or valid token provided
    demo_token = os.environ.get("DEMO_TOKEN")
    token_valid = demo_token and token == demo_token

    if not is_demo_enabled() and not token_valid:
        return JSONResponse(
            status_code=403,
            content={
                "error": "Demo mode is not enabled",
                "message": "Set DEMO_MODE=true to enable demo access, "
                           "or provide a valid ?token= parameter.",
            },
        )

    email, password = get_demo_credentials()

    # Use get_session context manager for DB access
    from src.database.db import get_db

    try:
        db = get_db()
        # Ensure tables exist (needed for fresh databases)
        db.create_tables()
        with db.session() as session:
            demo_user = session.query(User).filter(User.email == email).first()

            if not demo_user:
                logger.info("Demo user not found, creating demo account...")
                from src.auth.password import hash_password
                from src.database.models import SubscriptionTier

                demo_user = User(
                    email=email,
                    password_hash=hash_password(password),
                    name="Demo User",
                    role="admin",
                    is_demo_account=True,
                    subscription_tier=SubscriptionTier.ENTERPRISE,
                    credits_remaining=999999,
                    email_verified=True,
                )
                session.add(demo_user)
                session.flush()  # Get the user ID without committing yet

            if not demo_user:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Demo account could not be created"},
                )

            user_id = str(demo_user.id)

    except Exception as e:
        logger.error(f"Demo login error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to access demo account", "detail": str(e)},
        )

    # Set session cookie (same as regular login)
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="user_id",
        value=user_id,
        httponly=True,
        max_age=86400,  # 24 hours for demo sessions
    )

    logger.info(f"Demo login: {email} -> /dashboard")
    return response


@router.get("/demo/info")
async def demo_info(request: Request):
    """
    Return demo credentials as JSON (for API consumers / sharing).

    Only available when DEMO_MODE=true.
    """
    if not is_demo_enabled():
        return JSONResponse(
            status_code=403,
            content={"error": "Demo mode is not enabled"},
        )

    email, password = get_demo_credentials()
    base_url = os.environ.get("BASE_URL", str(request.base_url).rstrip("/"))

    return JSONResponse(
        content={
            "demo_url": f"{base_url}/demo",
            "login_url": f"{base_url}/login",
            "dashboard_url": f"{base_url}/dashboard",
            "email": email,
            "password": password,
            "features": [
                "Full app generation workflow",
                "Enterprise tier access",
                "Unlimited credits",
                "All AI providers available",
                "Admin dashboard access",
            ],
            "note": "This is a demo account. Generated apps may use mock data.",
        },
    )


@router.get("/demo/status")
async def demo_status(request: Request):
    """Check if demo mode is active and what's available."""
    return JSONResponse(
        content={
            "demo_mode": is_demo_enabled(),
            "demo_url": "/demo" if is_demo_enabled() else None,
            "info_url": "/demo/info" if is_demo_enabled() else None,
        },
    )
