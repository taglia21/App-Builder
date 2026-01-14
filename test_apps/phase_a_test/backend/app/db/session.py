"""Database session management with connection retry logic."""

import logging
import time
from typing import Generator

from app.core.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

# Create engine with connection pooling
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def wait_for_db(max_retries: int = 30, initial_interval: float = 1.0) -> bool:
    """
    Wait for database to be ready with exponential backoff.

    Args:
        max_retries: Maximum number of connection attempts
        initial_interval: Initial wait time between retries (doubles each attempt, max 30s)

    Returns:
        True if connection successful

    Raises:
        RuntimeError if database is not available after max_retries
    """
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                conn.commit()
            logger.info("✓ Database connection established.")
            return True
        except OperationalError as e:
            wait_time = min(initial_interval * (2 ** (attempt - 1)), 30.0)
            logger.warning(
                f"Database not ready (attempt {attempt}/{max_retries}). "
                f"Retrying in {wait_time:.1f}s... Error: {str(e)[:100]}"
            )
            time.sleep(wait_time)
        except Exception as e:
            logger.error(f"Unexpected database error: {e}")
            raise

    raise RuntimeError(
        f"Could not connect to database after {max_retries} attempts. "
        f"Check DATABASE_URL and ensure PostgreSQL is running."
    )


def check_db_connection() -> dict:
    """
    Check database connectivity for health endpoints.

    Returns:
        Dict with status and optional error message
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        return {"status": "connected", "error": None}
    except Exception as e:
        return {"status": "disconnected", "error": str(e)}


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI endpoints to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
