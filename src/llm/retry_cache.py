"""
Retry Logic and Caching for LLM API Calls

Provides robust retry mechanisms with exponential backoff and
response caching to handle rate limits, transient errors, and reduce costs.
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, ParamSpec, TypeVar

from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Type variables for generic functions
P = ParamSpec('P')
T = TypeVar('T')


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 5
    min_wait_seconds: float = 1.0
    max_wait_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

    # Error types to retry on
    retry_on_rate_limit: bool = True
    retry_on_timeout: bool = True
    retry_on_server_error: bool = True
    retry_on_connection_error: bool = True


@dataclass
class CacheConfig:
    """Configuration for response caching."""
    enabled: bool = True
    cache_dir: str = ".llm_cache"
    ttl_seconds: int = 86400 * 7  # 7 days default
    max_size_gb: float = 1.0

    # What to include in cache key
    include_model: bool = True
    include_temperature: bool = True
    include_max_tokens: bool = False  # Usually doesn't affect output significantly


class RateLimitError(Exception):
    """Raised when hitting API rate limits."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class TransientError(Exception):
    """Raised for transient/recoverable errors."""
    pass


class LLMCache:
    """Disk-based cache for LLM responses using diskcache."""

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._cache = None

        if self.config.enabled:
            self._initialize_cache()

    def _initialize_cache(self):
        """Initialize the disk cache."""
        try:
            import diskcache
            cache_path = Path(self.config.cache_dir)
            cache_path.mkdir(parents=True, exist_ok=True)

            # Size limit in bytes (GB to bytes)
            size_limit = int(self.config.max_size_gb * 1024 * 1024 * 1024)

            self._cache = diskcache.Cache(
                directory=str(cache_path),
                size_limit=size_limit,
                eviction_policy='least-recently-used',
            )
            logger.info(f"Initialized LLM cache at {cache_path} (max {self.config.max_size_gb}GB)")
        except ImportError:
            logger.warning("diskcache not installed. Caching disabled. Run: pip install diskcache")
            self.config.enabled = False
        except Exception as e:
            logger.warning(f"Failed to initialize cache: {e}. Caching disabled.")
            self.config.enabled = False

    def _generate_key(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        provider: str,
    ) -> str:
        """Generate a unique cache key for the request."""
        key_parts = [prompt]

        if system_prompt:
            key_parts.append(system_prompt)

        if self.config.include_model:
            key_parts.extend([model, provider])

        if self.config.include_temperature:
            key_parts.append(str(temperature))

        if self.config.include_max_tokens:
            key_parts.append(str(max_tokens))

        key_parts.append(str(json_mode))

        # Create hash of all parts
        key_string = "|||".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        provider: str,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached response if available."""
        if not self.config.enabled or self._cache is None:
            return None

        key = self._generate_key(
            prompt, system_prompt, model, temperature, max_tokens, json_mode, provider
        )

        try:
            cached = self._cache.get(key)
            if cached:
                logger.debug(f"Cache HIT for key {key[:16]}...")
                return cached
            logger.debug(f"Cache MISS for key {key[:16]}...")
        except Exception as e:
            logger.warning(f"Cache read error: {e}")

        return None

    def set(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool,
        provider: str,
        response: Dict[str, Any],
    ) -> None:
        """Store response in cache."""
        if not self.config.enabled or self._cache is None:
            return

        key = self._generate_key(
            prompt, system_prompt, model, temperature, max_tokens, json_mode, provider
        )

        try:
            self._cache.set(key, response, expire=self.config.ttl_seconds)
            logger.debug(f"Cached response for key {key[:16]}...")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    def clear(self) -> None:
        """Clear all cached responses."""
        if self._cache is not None:
            try:
                self._cache.clear()
                logger.info("LLM cache cleared")
            except Exception as e:
                logger.warning(f"Cache clear error: {e}")

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self.config.enabled or self._cache is None:
            return {"enabled": False}

        try:
            return {
                "enabled": True,
                "size_bytes": self._cache.volume(),
                "item_count": len(self._cache),
                "hits": self._cache.stats().get('hits', 0),
                "misses": self._cache.stats().get('misses', 0),
            }
        except (RuntimeError, ConnectionError, Exception):
            return {"enabled": True, "error": "Could not retrieve stats"}

    def close(self):
        """Close the cache properly."""
        if self._cache is not None:
            try:
                self._cache.close()
            except (RuntimeError, ConnectionError, Exception):
                pass


def is_rate_limit_error(exception: Exception) -> bool:
    """Check if exception is a rate limit error."""
    error_str = str(exception).lower()

    # Common rate limit indicators
    rate_limit_patterns = [
        'rate limit',
        'rate_limit',
        'ratelimit',
        '429',
        'too many requests',
        'quota exceeded',
        'tokens per',
        'requests per',
        'exceeded your',
    ]

    return any(pattern in error_str for pattern in rate_limit_patterns)


def is_transient_error(exception: Exception) -> bool:
    """Check if exception is transient (recoverable)."""
    error_str = str(exception).lower()

    transient_patterns = [
        'timeout',
        'connection',
        'temporarily',
        'unavailable',
        '500',
        '502',
        '503',
        '504',
        'internal server',
        'gateway',
        'overloaded',
    ]

    return any(pattern in error_str for pattern in transient_patterns)


def extract_retry_after(exception: Exception) -> Optional[float]:
    """Extract retry-after hint from rate limit error if available."""
    error_str = str(exception)

    # Try to find patterns like "try again in 4m46.848s"
    import re

    # Pattern: Xm Ys or X.Ys
    match = re.search(r'try again in (\d+)m([\d.]+)s', error_str)
    if match:
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        return minutes * 60 + seconds

    # Pattern: just seconds
    match = re.search(r'try again in ([\d.]+)s', error_str)
    if match:
        return float(match.group(1))

    # Pattern: Retry-After header style
    match = re.search(r'retry.?after[:\s]+(\d+)', error_str, re.IGNORECASE)
    if match:
        return float(match.group(1))

    return None


def create_retry_decorator(config: Optional[RetryConfig] = None):
    """Create a tenacity retry decorator with the given configuration."""
    config = config or RetryConfig()

    # Define which exceptions to retry on
    def should_retry(exception: Exception) -> bool:
        if config.retry_on_rate_limit and is_rate_limit_error(exception):
            return True
        if config.retry_on_timeout and 'timeout' in str(exception).lower():
            return True
        if config.retry_on_server_error and is_transient_error(exception):
            return True
        if config.retry_on_connection_error and 'connection' in str(exception).lower():
            return True
        return False

    return retry(
        stop=stop_after_attempt(config.max_retries),
        wait=wait_exponential(
            multiplier=config.exponential_base,
            min=config.min_wait_seconds,
            max=config.max_wait_seconds,
        ),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


class SmartRetry:
    """
    Smart retry handler that respects rate limit hints and uses exponential backoff.

    Usage:
        retrier = SmartRetry(RetryConfig(max_retries=5))

        @retrier
        def call_api():
            ...
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.total_retries = 0
        self.successful_calls = 0
        self.failed_calls = 0

    def __call__(self, func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None

            for attempt in range(self.config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    self.successful_calls += 1
                    return result

                except Exception as e:
                    last_exception = e

                    # Check if we should retry
                    should_retry = False
                    wait_time = self._calculate_wait_time(attempt, e)

                    if is_rate_limit_error(e) and self.config.retry_on_rate_limit:
                        should_retry = True
                        # Try to get retry-after hint
                        hint = extract_retry_after(e)
                        if hint and hint < self.config.max_wait_seconds * 2:
                            wait_time = hint + 1  # Add 1 second buffer

                    elif is_transient_error(e) and self.config.retry_on_server_error:
                        should_retry = True

                    elif 'timeout' in str(e).lower() and self.config.retry_on_timeout:
                        should_retry = True

                    elif 'connection' in str(e).lower() and self.config.retry_on_connection_error:
                        should_retry = True

                    if not should_retry or attempt >= self.config.max_retries:
                        self.failed_calls += 1
                        raise

                    self.total_retries += 1
                    logger.warning(
                        f"Retry {attempt + 1}/{self.config.max_retries} after {wait_time:.1f}s: {e}"
                    )
                    time.sleep(wait_time)

            # Should not reach here, but just in case
            self.failed_calls += 1
            raise last_exception

        return wrapper

    def _calculate_wait_time(self, attempt: int, exception: Exception) -> float:
        """Calculate wait time with exponential backoff and optional jitter."""
        base_wait = self.config.min_wait_seconds * (self.config.exponential_base ** attempt)
        wait_time = min(base_wait, self.config.max_wait_seconds)

        if self.config.jitter:
            import random
            jitter = random.uniform(0, wait_time * 0.1)  # 10% jitter
            wait_time += jitter

        return wait_time

    def get_stats(self) -> Dict[str, int]:
        """Get retry statistics."""
        return {
            "total_retries": self.total_retries,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
        }


# Global instances for convenience
_default_cache: Optional[LLMCache] = None
_default_retry: Optional[SmartRetry] = None


def get_default_cache() -> LLMCache:
    """Get or create the default cache instance."""
    global _default_cache
    if _default_cache is None:
        _default_cache = LLMCache()
    return _default_cache


def get_default_retry() -> SmartRetry:
    """Get or create the default retry handler."""
    global _default_retry
    if _default_retry is None:
        _default_retry = SmartRetry()
    return _default_retry


def configure_llm_resilience(
    cache_config: Optional[CacheConfig] = None,
    retry_config: Optional[RetryConfig] = None,
) -> tuple[LLMCache, SmartRetry]:
    """Configure global cache and retry instances."""
    global _default_cache, _default_retry

    _default_cache = LLMCache(cache_config)
    _default_retry = SmartRetry(retry_config)

    return _default_cache, _default_retry
