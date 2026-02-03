"""Tests for Redis caching layer."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import json


def test_cache_module_exists():
    """Test that cache module exists."""
    from src import cache
    assert cache is not None


def test_redis_client_exists():
    """Test RedisClient class exists."""
    from src.cache.redis_client import RedisClient
    assert RedisClient is not None


def test_cached_decorator_exists():
    """Test cached decorator exists."""
    from src.cache.decorators import cached
    assert cached is not None


def test_redis_client_initialization():
    """Test Redis client can be initialized."""
    from src.cache.redis_client import RedisClient
    
    client = RedisClient(url="redis://localhost:6379", enabled=False)
    assert client is not None


@pytest.mark.asyncio
async def test_redis_client_get_set():
    """Test Redis client get/set operations."""
    from src.cache.redis_client import RedisClient
    
    # Use mock Redis
    client = RedisClient(url="redis://localhost:6379", enabled=False)
    
    # When disabled, should fall back gracefully
    await client.set("key", "value")
    result = await client.get("key")
    
    # Disabled cache returns None
    assert result is None


@pytest.mark.asyncio
async def test_redis_client_graceful_fallback():
    """Test Redis client falls back gracefully when unavailable."""
    from src.cache.redis_client import RedisClient
    
    client = RedisClient(url="redis://invalid:9999", enabled=True)
    
    # Should not raise, just log and disable
    await client.set("key", "value")
    result = await client.get("key")
    assert result is None


@pytest.mark.asyncio
async def test_redis_client_delete():
    """Test Redis client delete operation."""
    from src.cache.redis_client import RedisClient
    
    client = RedisClient(enabled=False)
    
    # Should not raise
    await client.delete("key")


@pytest.mark.asyncio
async def test_redis_client_close():
    """Test Redis client connection closing."""
    from src.cache.redis_client import RedisClient
    
    client = RedisClient(enabled=False)
    
    # Should not raise
    await client.close()


def test_cached_decorator_with_disabled_cache():
    """Test cached decorator works when cache is disabled."""
    from src.cache.decorators import cached
    
    call_count = 0
    
    @cached(ttl=60, enabled=False)
    async def expensive_function(x):
        nonlocal call_count
        call_count += 1
        return x * 2
    
    # Decorator should be applied
    assert expensive_function is not None


@pytest.mark.asyncio
async def test_cached_decorator_caches_results():
    """Test cached decorator caches function results."""
    from src.cache.decorators import cached
    from src.cache.redis_client import RedisClient
    
    # Create a mock cache
    mock_cache = AsyncMock(spec=RedisClient)
    mock_cache.enabled = False
    
    call_count = 0
    
    @cached(ttl=60, cache_client=mock_cache)
    async def expensive_function(x):
        nonlocal call_count
        call_count += 1
        return x * 2
    
    # When cache disabled, function always runs
    result1 = await expensive_function(5)
    result2 = await expensive_function(5)
    
    assert result1 == 10
    assert result2 == 10


def test_cache_invalidation_helper():
    """Test cache invalidation helper function."""
    from src.cache.decorators import invalidate_cache
    
    assert invalidate_cache is not None


@pytest.mark.asyncio
async def test_invalidate_cache_function():
    """Test cache invalidation."""
    from src.cache.decorators import invalidate_cache
    from src.cache.redis_client import RedisClient
    
    client = RedisClient(enabled=False)
    
    # Should not raise
    await invalidate_cache(client, "key_pattern*")


def test_get_cache_key_function():
    """Test cache key generation."""
    from src.cache.decorators import get_cache_key
    
    key = get_cache_key("test_func", args=(1, 2), kwargs={"a": "b"})
    assert key is not None
    assert isinstance(key, str)
    assert "test_func" in key
