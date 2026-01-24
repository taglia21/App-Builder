"""
Unit tests for LLM retry and caching functionality.

Tests cover:
- SmartRetry decorator behavior
- LLMCache operations
- Rate limit detection
- Retry-after extraction
"""

import pytest
import time
import hashlib
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

# Import modules to test
from src.llm.retry_cache import (
    RetryConfig,
    CacheConfig,
    LLMCache,
    SmartRetry,
    RateLimitError,
    TransientError,
    is_rate_limit_error,
    extract_retry_after,
    configure_llm_resilience,
)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = RetryConfig()
        
        assert config.max_retries == 5
        assert config.min_wait_seconds == 1.0
        assert config.max_wait_seconds == 60.0
        assert config.exponential_base == 2.0
    
    def test_custom_values(self):
        """Test custom configuration values."""
        config = RetryConfig(
            max_retries=3,
            min_wait_seconds=0.5,
            max_wait_seconds=30.0,
            exponential_base=3.0
        )
        
        assert config.max_retries == 3
        assert config.min_wait_seconds == 0.5
        assert config.max_wait_seconds == 30.0
        assert config.exponential_base == 3.0


class TestCacheConfig:
    """Tests for CacheConfig dataclass."""
    
    def test_default_values(self):
        """Test default cache configuration."""
        config = CacheConfig()
        
        assert config.enabled is True
        assert config.ttl_seconds == 604800  # 7 days
        assert config.max_size_gb == 1.0
        assert config.cache_dir == ".llm_cache"
    
    def test_custom_values(self):
        """Test custom cache configuration."""
        config = CacheConfig(
            enabled=False,
            ttl_seconds=3600,
            max_size_gb=0.5,
            cache_dir="/tmp/custom_cache"
        )
        
        assert config.enabled is False
        assert config.ttl_seconds == 3600
        assert config.max_size_gb == 0.5
        assert config.cache_dir == "/tmp/custom_cache"


class TestLLMCache:
    """Tests for LLMCache class."""
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create a cache instance with temp directory."""
        config = CacheConfig(cache_dir=temp_cache_dir, ttl_seconds=3600)
        return LLMCache(config)
    
    def test_cache_key_generation(self, cache):
        """Test cache key generation is deterministic."""
        key1 = cache._generate_key("test prompt", None, "test-model", 0.7, 1000, False, "openai")
        key2 = cache._generate_key("test prompt", None, "test-model", 0.7, 1000, False, "openai")
        
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex length
    
    def test_cache_key_varies_with_model(self, cache):
        """Test different models produce different keys."""
        key1 = cache._generate_key("test prompt", None, "model-a", 0.7, 1000, False, "openai")
        key2 = cache._generate_key("test prompt", None, "model-b", 0.7, 1000, False, "openai")
        
        assert key1 != key2
    
    def test_cache_key_varies_with_prompt(self, cache):
        """Test different prompts produce different keys."""
        key1 = cache._generate_key("prompt a", None, "test-model", 0.7, 1000, False, "openai")
        key2 = cache._generate_key("prompt b", None, "test-model", 0.7, 1000, False, "openai")
        
        assert key1 != key2
    
    def test_cache_key_varies_with_temperature(self, cache):
        """Test different temperatures produce different keys."""
        key1 = cache._generate_key("test prompt", None, "test-model", 0.5, 1000, False, "openai")
        key2 = cache._generate_key("test prompt", None, "test-model", 0.9, 1000, False, "openai")
        
        assert key1 != key2
    
    def test_cache_miss(self, cache):
        """Test cache returns None on miss."""
        result = cache.get("nonexistent prompt", None, "model", 0.7, 1000, False, "openai")
        assert result is None
    
    def test_cache_set_and_get(self, cache):
        """Test storing and retrieving from cache."""
        prompt = "test prompt"
        value = {"content": "test response", "tokens": 100}
        
        cache.set(prompt, None, "model", 0.7, 1000, False, "openai", value)
        result = cache.get(prompt, None, "model", 0.7, 1000, False, "openai")
        
        assert result == value
    
    def test_cache_clear(self, cache):
        """Test clearing the cache."""
        cache.set("prompt1", None, "model", 0.7, 1000, False, "openai", {"data": "value1"})
        cache.set("prompt2", None, "model", 0.7, 1000, False, "openai", {"data": "value2"})
        
        cache.clear()
        
        assert cache.get("prompt1", None, "model", 0.7, 1000, False, "openai") is None
        assert cache.get("prompt2", None, "model", 0.7, 1000, False, "openai") is None
    
    def test_cache_stats(self, cache):
        """Test cache statistics."""
        cache.set("prompt1", None, "model", 0.7, 1000, False, "openai", {"data": "value1"})
        cache.get("prompt1", None, "model", 0.7, 1000, False, "openai")  # Hit
        cache.get("nonexistent", None, "model", 0.7, 1000, False, "openai")  # Miss
        
        stats = cache.stats()
        
        assert isinstance(stats, dict)
    
    def test_disabled_cache(self, temp_cache_dir):
        """Test disabled cache behavior."""
        config = CacheConfig(enabled=False, cache_dir=temp_cache_dir)
        cache = LLMCache(config)
        
        cache.set("prompt", None, "model", 0.7, 1000, False, "openai", {"data": "value"})
        result = cache.get("prompt", None, "model", 0.7, 1000, False, "openai")
        
        # Disabled cache should return None
        assert result is None


class TestRateLimitDetection:
    """Tests for rate limit error detection."""
    
    def test_detects_rate_limit_in_message(self):
        """Test detection of rate limit error from message."""
        error = Exception("rate limit exceeded")
        assert is_rate_limit_error(error) is True
        
        error = Exception("Rate Limit Exceeded")
        assert is_rate_limit_error(error) is True
    
    def test_detects_429_error(self):
        """Test detection of 429 status code."""
        error = Exception("429 Too Many Requests")
        assert is_rate_limit_error(error) is True
    
    def test_detects_quota_exceeded(self):
        """Test detection of quota exceeded error."""
        error = Exception("quota exceeded for this account")
        assert is_rate_limit_error(error) is True
    
    def test_non_rate_limit_error(self):
        """Test non-rate-limit errors return False."""
        error = Exception("Invalid API key")
        assert is_rate_limit_error(error) is False
        
        error = ValueError("Bad input")
        assert is_rate_limit_error(error) is False


class TestRetryAfterExtraction:
    """Tests for retry-after header extraction."""
    
    def test_extract_from_message_with_minutes_seconds(self):
        """Test extracting retry-after from message with minutes and seconds."""
        error = Exception("Rate limited. try again in 4m30s")
        
        result = extract_retry_after(error)
        assert result == 270.0  # 4*60 + 30
    
    def test_extract_from_retry_after_header(self):
        """Test extracting retry-after from header-style message."""
        error = Exception("Rate limited. Retry-After: 45")
        
        result = extract_retry_after(error)
        assert result == 45
    
    def test_no_retry_after(self):
        """Test when no retry-after is available."""
        error = Exception("Rate limited with no hint")
        
        result = extract_retry_after(error)
        assert result is None
    
    def test_extract_from_seconds_only(self):
        """Test extracting when only seconds are present."""
        error = Exception("try again in 60s")
        
        result = extract_retry_after(error)
        assert result == 60.0


class TestSmartRetry:
    """Tests for SmartRetry decorator."""
    
    def test_successful_call_no_retry(self):
        """Test that successful calls don't retry."""
        config = RetryConfig(max_retries=3)
        retry = SmartRetry(config)
        
        call_count = 0
        
        @retry
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_func()
        
        assert result == "success"
        assert call_count == 1
    
    def test_retries_on_transient_error(self):
        """Test that transient errors cause retries."""
        config = RetryConfig(max_retries=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
        retry = SmartRetry(config)
        
        call_count = 0
        
        @retry
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("503 Service Unavailable")
            return "success"
        
        result = failing_func()
        
        assert result == "success"
        assert call_count == 3
    
    def test_retries_on_rate_limit(self):
        """Test that rate limit errors cause retries."""
        config = RetryConfig(max_retries=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
        retry = SmartRetry(config)
        
        call_count = 0
        
        @retry
        def rate_limited_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("429 Too Many Requests")
            return "success"
        
        result = rate_limited_func()
        
        assert result == "success"
        assert call_count == 2
    
    def test_max_retries_exceeded(self):
        """Test that max retries raises final error."""
        config = RetryConfig(max_retries=2, min_wait_seconds=0.01, max_wait_seconds=0.1)
        retry = SmartRetry(config)
        
        @retry
        def always_fails():
            raise Exception("503 Service Unavailable")
        
        with pytest.raises(Exception):
            always_fails()
    
    def test_non_retryable_error_not_retried(self):
        """Test that non-retryable errors are not retried."""
        config = RetryConfig(max_retries=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
        retry = SmartRetry(config)
        
        call_count = 0
        
        @retry
        def auth_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid API key - this is a non-transient error")
        
        with pytest.raises(ValueError):
            auth_error_func()
        
        # Should only be called once (no retries for auth errors)
        assert call_count == 1
    
    def test_retry_stats(self):
        """Test that retry statistics are tracked."""
        config = RetryConfig(max_retries=3, min_wait_seconds=0.01, max_wait_seconds=0.1)
        retry = SmartRetry(config)
        
        @retry
        def successful_func():
            return "success"
        
        successful_func()
        
        stats = retry.get_stats()
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 0


class TestConfigureLLMResilience:
    """Tests for the configure_llm_resilience helper."""
    
    def test_returns_both_configs(self):
        """Test that helper returns both cache and retry instances."""
        cache, retry = configure_llm_resilience()
        
        assert isinstance(cache, LLMCache)
        assert isinstance(retry, SmartRetry)
    
    def test_custom_retry_config(self):
        """Test customizing retry configuration."""
        retry_config = RetryConfig(max_retries=10)
        cache, retry = configure_llm_resilience(retry_config=retry_config)
        
        assert retry.config.max_retries == 10
    
    def test_custom_cache_config(self):
        """Test customizing cache configuration."""
        cache_config = CacheConfig(ttl_seconds=3600)
        cache, retry = configure_llm_resilience(cache_config=cache_config)
        
        assert cache.config.ttl_seconds == 3600


class TestRateLimitError:
    """Tests for RateLimitError exception."""
    
    def test_error_creation(self):
        """Test creating a RateLimitError."""
        error = RateLimitError("Too many requests", retry_after=30)
        
        assert str(error) == "Too many requests"
        assert error.retry_after == 30
    
    def test_error_without_retry_after(self):
        """Test RateLimitError without retry_after."""
        error = RateLimitError("Rate limited")
        
        assert str(error) == "Rate limited"
        assert error.retry_after is None


class TestTransientError:
    """Tests for TransientError exception."""
    
    def test_error_creation(self):
        """Test creating a TransientError."""
        error = TransientError("Server unavailable")
        
        assert str(error) == "Server unavailable"
    
    def test_inheritance(self):
        """Test TransientError is an Exception."""
        error = TransientError("Test")
        
        assert isinstance(error, Exception)
