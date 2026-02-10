"""Web authentication routes for LaunchForge dashboard."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.auth.password import hash_password, verify_password
from src.database.db import  get_session
from src.database.models import User

logger = logging.getLogger(__name__)

# Setup templates
templates_path = Path(__file__).parent.parent / "dashboard" / "templates"
templates = Jinja2Templates(directory=str(templates_path))

router = APIRouter()


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
        # Find user
        user = db.query(User).filter(User.email == email.lower()).first()

        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse(
                "pages/login.html",
                {"request": request, "error": "Invalid email or password"}
            )

        # Create session (we'll implement proper session management later)
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key="user_id",
            value=str(user.id),
            httponly=True,
            max_age=2592000 if remember else 3600  # 30 days or 1 hour
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

        if len(password) < 8:
            return templates.TemplateResponse(
                "pages/register.html",
                {"request": request, "error": "Password must be at least 8 characters"}
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
            credits_remaining=5,  # Free tier gets 5 apps
            email_verified=False
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info(f"New user registered: {email}")

        # Auto-login after registration
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(
            key="user_id",
            value=str(new_user.id),
            httponly=True,
            max_age=3600
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
    response.delete_cookie(key="user_id")
    return response
