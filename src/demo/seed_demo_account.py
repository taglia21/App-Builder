"""
Demo Account Seeder for Valeric.

Creates or updates a demo user account with admin/demo privileges
that bypasses billing and subscription checks.

Usage:
    # As a script
    python -m src.demo.seed_demo_account

    # Programmatically
    from src.demo.seed_demo_account import seed_demo_user
    seed_demo_user()

Environment variables:
    DEMO_EMAIL    - Demo account email (default: demo@valeric.dev)
    DEMO_PASSWORD - Demo account password (default: Valeric-Demo-2026!)
"""

import logging
import os
import sys
from uuid import uuid4

logger = logging.getLogger(__name__)

# Demo account defaults
DEFAULT_DEMO_EMAIL = "demo@valeric.dev"
DEMO_USER_ID = "demo-00000000-0000-0000-0000-000000000001"


def get_demo_credentials() -> tuple[str, str]:
    """Get demo credentials from environment.
    
    DEMO_PASSWORD must be set in the environment. No hardcoded fallback.
    """
    email = os.environ.get("DEMO_EMAIL", DEFAULT_DEMO_EMAIL)
    password = os.environ.get("DEMO_PASSWORD", "")
    if not password:
        raise RuntimeError(
            "DEMO_PASSWORD environment variable is required when DEMO_MODE is enabled. "
            "Set it in your .env file or deployment config."
        )
    return email, password


def seed_demo_user(database_url: str | None = None) -> dict:
    """
    Create or update the demo user account.

    Args:
        database_url: Optional database URL. If None, uses DATABASE_URL env var.

    Returns:
        dict with demo account info (email, password, user_id)
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from src.auth.password import hash_password
    from src.database.models import Base, SubscriptionTier, User

    # Get database URL
    if database_url is None:
        database_url = os.environ.get(
            "DATABASE_URL",
            "sqlite:///./app.db"
        )
        # Handle Railway/Heroku postgres:// -> postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

    logger.info(f"Seeding demo account in database: {database_url[:30]}...")

    engine = create_engine(database_url, echo=False)

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)

    email, password = get_demo_credentials()

    with Session(engine) as session:
        # Check if demo user already exists
        existing = session.query(User).filter(User.email == email).first()

        if existing:
            # Update existing demo user
            existing.password_hash = hash_password(password)
            existing.role = "admin"
            existing.is_demo_account = True
            existing.subscription_tier = SubscriptionTier.ENTERPRISE
            existing.credits_remaining = 999999
            existing.email_verified = True
            existing.is_deleted = False
            existing.name = "Demo User"
            session.commit()
            logger.info(f"Updated existing demo user: {email}")
            user_id = existing.id
        else:
            # Create new demo user
            demo_user = User(
                id=DEMO_USER_ID,
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
            session.commit()
            logger.info(f"Created demo user: {email}")
            user_id = demo_user.id

    result = {
        "email": email,
        "password": password,
        "user_id": user_id,
        "role": "admin",
        "tier": "enterprise",
        "credits": 999999,
    }

    logger.info(f"Demo account ready: {email} (role=admin, tier=enterprise)")
    return result


def print_demo_info():
    """Print demo account credentials for sharing."""
    email, password = get_demo_credentials()
    base_url = os.environ.get("BASE_URL", "http://localhost:8000")

    print("\n" + "=" * 60)
    print("  Valeric Demo Account")
    print("=" * 60)
    print(f"  Email:    {email}")
    print(f"  Password: {password}")
    print(f"  URL:      {base_url}/demo")
    print(f"  Login:    {base_url}/login")
    print(f"  Dashboard:{base_url}/dashboard")
    print("=" * 60)
    print("  Share the /demo URL for instant access (auto-login)")
    print("  Or share email/password for manual login")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = seed_demo_user()
    print_demo_info()
