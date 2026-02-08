"""Tests for database connection pooling."""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock


def test_database_pool_module_exists():
    """Test that database pool module exists."""
    from src.database import pool
    assert pool is not None


def test_async_engine_factory_exists():
    """Test async_engine_factory function exists."""
    from src.database.pool import get_async_engine
    assert get_async_engine is not None


def test_async_engine_creation_functions():
    """Test that all required functions exist."""
    from src.database.pool import (
        get_async_engine,
        get_async_session_factory,
        check_connection,
        close_connections,
        get_engine,
        shutdown
    )
    
    assert get_async_engine is not None
    assert get_async_session_factory is not None
    assert check_connection is not None
    assert close_connections is not None
    assert get_engine is not None
    assert shutdown is not None


def test_connection_health_check_function():
    """Test connection health check function exists."""
    from src.database.pool import check_connection
    assert check_connection is not None


def test_graceful_shutdown_function():
    """Test graceful shutdown function exists."""
    from src.database.pool import close_connections
    assert close_connections is not None


def test_get_session_factory_exists():
    """Test async session factory creation function exists."""
    from src.database.pool import get_async_session_factory
    assert get_async_session_factory is not None


def test_global_engine_functions():
    """Test global engine getter and shutdown."""
    from src.database.pool import get_engine, shutdown
    
    assert get_engine is not None
    assert shutdown is not None


@pytest.mark.asyncio
async def test_check_connection_with_mock():
    """Test check_connection handles exceptions."""
    from src.database.pool import check_connection
    
    # Create a mock engine whose async context manager raises
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__aenter__ = AsyncMock(side_effect=Exception("Connection failed"))
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    mock_engine.connect.return_value = mock_conn
    
    result = await check_connection(mock_engine)
    assert result is False


@pytest.mark.asyncio
async def test_close_connections_with_mock():
    """Test close_connections handles engine disposal."""
    from src.database.pool import close_connections
    
    # Create a mock engine
    mock_engine = AsyncMock()
    
    # Should not raise
    await close_connections(mock_engine)
    mock_engine.dispose.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown_clears_global_engine():
    """Test shutdown disposes global engine."""
    from src.database import pool
    
    # Set a mock global engine
    pool._global_engine = AsyncMock()
    
    await pool.shutdown()
    
    # Should be cleared
    assert pool._global_engine is None


def test_engine_configuration_options():
    """Test that engine accepts configuration parameters."""
    from src.database.pool import get_async_engine
    from unittest.mock import patch
    
    with patch('src.database.pool.create_async_engine') as mock_create:
        get_async_engine(
            "sqlite+aiosqlite:///:memory:",
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False
        )
        
        # Verify create_async_engine was called
        mock_create.assert_called_once()
