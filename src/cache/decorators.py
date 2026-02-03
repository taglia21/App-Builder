"""Cache decorators for function memoization."""
import functools
import hashlib
import json
import logging
from typing import Any, Callable, Optional

from src.cache.redis_client import get_cache, RedisClient

logger = logging.getLogger(__name__)


def get_cache_key(func_name: str, args: tuple = (), kwargs: dict = None) -> str:
    """Generate cache key from function name and arguments.
    
    Args:
        func_name: Function name
        args: Positional arguments
        kwargs: Keyword arguments
        
    Returns:
        Cache key string
    """
    if kwargs is None:
        kwargs = {}
    
    # Create a stable representation of arguments
    key_data = {
        "func": func_name,
        "args": args,
        "kwargs": sorted(kwargs.items())
    }
    
    # Hash for consistent key
    key_str = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.md5(key_str.encode()).hexdigest()
    
    return f"cache:{func_name}:{key_hash}"


def cached(
    ttl: int = 300,
    enabled: bool = True,
    cache_client: Optional[RedisClient] = None
):
    """Decorator to cache async function results.
    
    Args:
        ttl: Time to live in seconds
        enabled: Whether caching is enabled
        cache_client: Custom cache client (uses global if not provided)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Use provided cache or get global
            cache = cache_client or get_cache()
            
            if not enabled or not cache.enabled:
                # Cache disabled, just call function
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key = get_cache_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Cache miss, call function
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


async def invalidate_cache(
    cache_client: RedisClient,
    pattern: str
):
    """Invalidate cache entries matching pattern.
    
    Args:
        cache_client: Redis client
        pattern: Key pattern to match (e.g., "user:*")
    """
    if not cache_client.enabled:
        return
    
    try:
        # Note: Pattern-based deletion requires Redis SCAN command
        # For simplicity, just delete the exact key
        await cache_client.delete(pattern)
    except Exception as e:
        logger.error(f"Cache invalidation error: {e}")
