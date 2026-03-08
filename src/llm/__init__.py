"""
LLM Client Module - Streamlined
Provides unified access to LLM providers with retry and caching.

Supported Providers (fallback order):
1. OpenAI: PRIMARY - GPT models (most popular, reliable)
2. Anthropic: SECONDARY - Claude models (high quality)
3. Google: TERTIARY - Gemini models
4. Perplexity: QUATERNARY - Real-time web search (sonar-pro, sonar-deep-research, sonar-reasoning)
5. Groq: QUINARY - Ultra-fast inference
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
