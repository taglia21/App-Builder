"""Database connection pooling for LaunchForge.

Provides async SQLAlchemy engine with connection pooling,
health checks, and graceful shutdown.
"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
    AsyncSession,
)
from sqlalchemy.pool import NullPool, QueuePool

from src.config.settings import settings

logger = logging.getLogger(__name__)


def get_async_engine(
    database_url: Optional[str] = None,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_pre_ping: bool = True,
    echo: bool = False,
) -> AsyncEngine:
    """Create async SQLAlchemy engine with connection pooling.
    
    Args:
        database_url: Database URL (uses settings.DATABASE_URL if not provided)
        pool_size: Number of connections to maintain in pool
        max_overflow: Maximum number of connections to create beyond pool_size
        pool_pre_ping: Test connections before use
        echo: Enable SQL query logging
        
    Returns:
        Configured async engine
    """
    if database_url is None:
        database_url = settings.DATABASE_URL
    
    # Determine pooling strategy based on database
    if database_url.startswith("sqlite"):
        # SQLite doesn't support connection pooling well
        poolclass = NullPool
        pool_kwargs = {}
    else:
        poolclass = QueuePool
        pool_kwargs = {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_pre_ping": pool_pre_ping,
        }
    
    engine = create_async_engine(
        database_url,
        echo=echo,
        poolclass=poolclass,
        **pool_kwargs,
    )
    
    logger.info(f"Created async engine for {database_url.split('@')[-1] if '@' in database_url else database_url}")
    
    return engine


def get_async_session_factory(
    database_url: Optional[str] = None,
    **engine_kwargs
) -> async_sessionmaker:
    """Create async session factory.
    
    Args:
        database_url: Database URL
        **engine_kwargs: Additional arguments for engine creation
        
    Returns:
        Async session factory
    """
    engine = get_async_engine(database_url, **engine_kwargs)
    
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    return session_factory


async def check_connection(engine: AsyncEngine) -> bool:
    """Check if database connection is healthy.
    
    Args:
        engine: Async SQLAlchemy engine
        
    Returns:
        True if connection is healthy, False otherwise
    """
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def close_connections(engine: AsyncEngine):
    """Gracefully close all database connections.
    
    Args:
        engine: Async SQLAlchemy engine to dispose
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


# Global engine instance (optional, for application-wide use)
_global_engine: Optional[AsyncEngine] = None


def get_engine() -> AsyncEngine:
    """Get or create global async engine.
    
    Returns:
        Global async engine instance
    """
    global _global_engine
    
    if _global_engine is None:
        _global_engine = get_async_engine()
    
    return _global_engine


async def shutdown():
    """Shutdown global engine connections."""
    global _global_engine
    
    if _global_engine is not None:
        await close_connections(_global_engine)
        _global_engine = None
