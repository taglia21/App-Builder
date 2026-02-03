"""Redis client for caching."""
import logging
from typing import Optional, Any
import json

from src.config.settings import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client with graceful fallback."""
    
    def __init__(
        self,
        url: Optional[str] = None,
        enabled: Optional[bool] = None
    ):
        """Initialize Redis client.
        
        Args:
            url: Redis connection URL
            enabled: Whether caching is enabled (defaults to checking REDIS_URL)
        """
        self.url = url or settings.REDIS_URL
        
        if enabled is None:
            self.enabled = bool(self.url)
        else:
            self.enabled = enabled
        
        self._client = None
        
        if self.enabled:
            try:
                # Try to import redis
                import redis.asyncio as aioredis
                self._redis = aioredis
            except ImportError:
                logger.warning("redis package not installed, caching disabled")
                self.enabled = False
    
    async def _get_client(self):
        """Get or create Redis client."""
        if not self.enabled:
            return None
        
        if self._client is None:
            try:
                self._client = self._redis.from_url(self.url, decode_responses=True)
                # Test connection
                await self._client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.enabled = False
                self._client = None
        
        return self._client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self.enabled:
            return None
        
        try:
            client = await self._get_client()
            if client is None:
                return None
            
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            client = await self._get_client()
            if client is None:
                return False
            
            serialized = json.dumps(value)
            if ttl:
                await client.setex(key, ttl, serialized)
            else:
                await client.set(key, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            client = await self._get_client()
            if client is None:
                return False
            
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self._client:
            try:
                await self._client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")


# Global cache instance
_cache_client: Optional[RedisClient] = None


def get_cache() -> RedisClient:
    """Get or create global cache client.
    
    Returns:
        Global RedisClient instance
    """
    global _cache_client
    
    if _cache_client is None:
        _cache_client = RedisClient()
    
    return _cache_client
