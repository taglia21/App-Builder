"""
LLM Client Module - Streamlined
Provides unified access to LLM providers with retry and caching.

Supported Providers:
- Perplexity: PRIMARY - Real-time web search (sonar-pro, sonar-deep-research, sonar-reasoning)
- Groq: BACKUP - Ultra-fast inference
- Mock: Testing without API calls
"""

from src.llm.client import (
    BaseLLMClient,
    GroqClient,
    LLMResponse,
    MockLLMClient,
    MultiProviderClient,
    PerplexityClient,
    get_llm_client,
    list_available_providers,
)
from src.llm.retry_cache import (
    CacheConfig,
    LLMCache,
    RateLimitError,
    RetryConfig,
    SmartRetry,
    TransientError,
    configure_llm_resilience,
    get_default_cache,
    get_default_retry,
)

__all__ = [
    # Client classes
    "BaseLLMClient",
    "LLMResponse",
    "PerplexityClient",
    "GroqClient",
    "MockLLMClient",
    "MultiProviderClient",
    "get_llm_client",
    "list_available_providers",
    # Retry and caching
    "RetryConfig",
    "CacheConfig",
    "LLMCache",
    "SmartRetry",
    "RateLimitError",
    "TransientError",
    "get_default_cache",
    "get_default_retry",
    "configure_llm_resilience",
]
