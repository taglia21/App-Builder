"""
LaunchForge Database Utilities

Connection management, session handling, and database operations.
Provides a production-ready database layer with connection pooling,
retry logic, and error handling.
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator, Optional, Any
from functools import wraps
import time

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import (
    SQLAlchemyError,
    OperationalError,
    IntegrityError,
    DisconnectionError,
)

from src.database.models import Base

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_POOL_SIZE = 5
DEFAULT_MAX_OVERFLOW = 10
DEFAULT_POOL_TIMEOUT = 30
DEFAULT_POOL_RECYCLE = 1800  # 30 minutes
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1


def get_database_url() -> str:
    """
    Get database URL from environment variables.
    
    Supports both DATABASE_URL (standard) and individual components.
    Falls back to SQLite for development/testing if not configured.
    
    Returns:
        str: Database connection URL
    """
    # Check for full DATABASE_URL first
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        # Handle Heroku-style postgres:// URLs (need postgresql://)
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return database_url
    
    # Build from components
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "nexusai")
    db_user = os.getenv("DB_USER", "nexusai")
    db_password = os.getenv("DB_PASSWORD", "")
    
    if db_password:
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # Fallback to SQLite for development
    logger.warning("No PostgreSQL configuration found. Using SQLite for development.")
    return "sqlite:///./nexusai_dev.db"


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class ConnectionError(DatabaseError):
    """Database connection error."""
    pass


class TransactionError(DatabaseError):
    """Database transaction error."""
    pass


def retry_on_connection_error(max_attempts: int = MAX_RETRY_ATTEMPTS):
    """
    Decorator to retry database operations on connection errors.
    
    Args:
        max_attempts: Maximum number of retry attempts
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, DisconnectionError) as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        wait_time = RETRY_DELAY_SECONDS * (2 ** attempt)
                        logger.warning(
                            f"Database connection error (attempt {attempt + 1}/{max_attempts}). "
                            f"Retrying in {wait_time}s: {e}"
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Database connection failed after {max_attempts} attempts: {e}")
            raise ConnectionError(f"Failed to connect to database: {last_error}")
        return wrapper
    return decorator


class DatabaseManager:
    """
    Database connection and session manager.
    
    Provides connection pooling, session management, and 
    error handling for production PostgreSQL usage.
    
    Usage:
        db_manager = DatabaseManager()
        with db_manager.session() as session:
            user = session.query(User).first()
    """
    
    _instance: Optional["DatabaseManager"] = None
    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker] = None
    _scoped_session: Optional[scoped_session] = None
    
    def __new__(cls, *args, **kwargs) -> "DatabaseManager":
        """Singleton pattern for database manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        database_url: Optional[str] = None,
        pool_size: int = DEFAULT_POOL_SIZE,
        max_overflow: int = DEFAULT_MAX_OVERFLOW,
        pool_timeout: int = DEFAULT_POOL_TIMEOUT,
        pool_recycle: int = DEFAULT_POOL_RECYCLE,
        echo: bool = False
    ):
        """
        Initialize database manager.
        
        Args:
            database_url: Database connection URL
            pool_size: Connection pool size
            max_overflow: Max connections beyond pool_size
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Recycle connections after this many seconds
            echo: Echo SQL statements to stdout
        """
        # Skip re-initialization if already configured
        if self._engine is not None:
            return
            
        self._database_url = database_url or get_database_url()
        self._is_sqlite = self._database_url.startswith("sqlite")
        
        # Configure engine options
        engine_options: dict[str, Any] = {
            "echo": echo,
            "future": True,  # Use SQLAlchemy 2.0 style
        }
        
        # PostgreSQL-specific pooling (SQLite doesn't support it)
        if not self._is_sqlite:
            engine_options.update({
                "poolclass": QueuePool,
                "pool_size": pool_size,
                "max_overflow": max_overflow,
                "pool_timeout": pool_timeout,
                "pool_recycle": pool_recycle,
                "pool_pre_ping": True,  # Enable connection health checks
            })
        
        # Create engine
        self._engine = create_engine(self._database_url, **engine_options)
        
        # Set up connection event listeners for PostgreSQL
        if not self._is_sqlite:
            self._setup_event_listeners()
        
        # Create session factory
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        
        # Create scoped session for thread-safety
        self._scoped_session = scoped_session(self._session_factory)
        
        logger.info(f"Database manager initialized: {self._get_safe_url()}")
    
    def _get_safe_url(self) -> str:
        """Get database URL with password masked."""
        url = self._database_url
        if "@" in url and "://" in url:
            # Mask password in URL
            prefix = url.split("://")[0]
            rest = url.split("://")[1]
            if "@" in rest:
                user_pass = rest.split("@")[0]
                host_rest = rest.split("@")[1]
                if ":" in user_pass:
                    user = user_pass.split(":")[0]
                    return f"{prefix}://{user}:****@{host_rest}"
        return url
    
    def _setup_event_listeners(self) -> None:
        """Set up SQLAlchemy event listeners."""
        
        @event.listens_for(self._engine, "connect")
        def set_search_path(dbapi_connection, connection_record):
            """Set PostgreSQL search path on connect."""
            cursor = dbapi_connection.cursor()
            cursor.execute("SET TIME ZONE 'UTC'")
            cursor.close()
        
        @event.listens_for(self._engine, "checkout")
        def ping_connection(dbapi_connection, connection_record, connection_proxy):
            """Ping connection on checkout to verify it's alive."""
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("SELECT 1")
            except Exception:
                # Raise DisconnectionError to invalidate and get a fresh connection
                raise DisconnectionError()
            finally:
                cursor.close()
    
    @property
    def engine(self) -> Engine:
        """Get SQLAlchemy engine."""
        if self._engine is None:
            raise ConnectionError("Database not initialized")
        return self._engine
    
    @retry_on_connection_error()
    def create_tables(self) -> None:
        """Create all tables defined in models."""
        Base.metadata.create_all(bind=self._engine)
        logger.info("Database tables created successfully")
    
    def drop_tables(self) -> None:
        """Drop all tables. USE WITH CAUTION!"""
        Base.metadata.drop_all(bind=self._engine)
        logger.warning("All database tables dropped")
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        
        Handles session lifecycle, commits, and rollbacks automatically.
        
        Usage:
            with db_manager.session() as session:
                user = session.query(User).first()
        
        Yields:
            Session: SQLAlchemy session instance
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except IntegrityError as e:
            session.rollback()
            logger.error(f"Integrity error: {e}")
            raise TransactionError(f"Database integrity error: {e}")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error in database session: {e}")
            raise
        finally:
            session.close()
    
    def get_session(self) -> Session:
        """
        Get a new session instance.
        
        Note: Caller is responsible for closing the session.
        Prefer using the session() context manager instead.
        
        Returns:
            Session: New SQLAlchemy session
        """
        return self._session_factory()
    
    @retry_on_connection_error()
    def health_check(self) -> bool:
        """
        Check database connectivity.
        
        Returns:
            bool: True if database is reachable
        """
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def get_pool_status(self) -> dict:
        """
        Get connection pool status.
        
        Returns:
            dict: Pool statistics
        """
        if self._is_sqlite:
            return {"type": "sqlite", "pooling": False}
        
        pool = self._engine.pool
        return {
            "type": "postgresql",
            "pooling": True,
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalidatedcount(),
        }
    
    def close(self) -> None:
        """Close all connections and dispose of the engine."""
        if self._scoped_session:
            self._scoped_session.remove()
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections closed")
    
    def reset(self) -> None:
        """Reset the singleton instance. Used for testing."""
        self.close()
        DatabaseManager._instance = None
        DatabaseManager._engine = None
        DatabaseManager._session_factory = None
        DatabaseManager._scoped_session = None


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def init_db(
    database_url: Optional[str] = None,
    create_tables: bool = False,
    **kwargs
) -> DatabaseManager:
    """
    Initialize the global database manager.
    
    Args:
        database_url: Database connection URL
        create_tables: Whether to create tables on init
        **kwargs: Additional options for DatabaseManager
    
    Returns:
        DatabaseManager: Initialized database manager
    """
    global _db_manager
    _db_manager = DatabaseManager(database_url=database_url, **kwargs)
    
    if create_tables:
        _db_manager.create_tables()
    
    return _db_manager


def get_db() -> DatabaseManager:
    """
    Get the global database manager instance.
    
    Returns:
        DatabaseManager: Database manager instance
    
    Raises:
        ConnectionError: If database is not initialized
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Convenience function for getting a database session.
    
    Usage:
        with get_session() as session:
            user = session.query(User).first()
    
    Yields:
        Session: SQLAlchemy session instance
    """
    db = get_db()
    with db.session() as session:
        yield session
