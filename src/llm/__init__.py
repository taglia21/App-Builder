"""
LLM Client Module
Provides unified access to multiple LLM providers with retry and caching.
"""

from src.llm.client import (
    BaseLLMClient,
    LLMResponse,
    GeminiClient,
    GroqClient,
    OpenRouterClient,
    OpenAIClient,
    AnthropicClient,
    MockLLMClient,
    MultiProviderClient,
    get_llm_client,
    list_available_providers
)

from src.llm.retry_cache import (
    RetryConfig,
    CacheConfig,
    LLMCache,
    SmartRetry,
    RateLimitError,
    TransientError,
    get_default_cache,
    get_default_retry,
    configure_llm_resilience,
)

__all__ = [
    # Client classes
    "BaseLLMClient",
    "LLMResponse",
    "GeminiClient",
    "GroqClient",
    "OpenRouterClient",
    "OpenAIClient",
    "AnthropicClient",
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
