"""
Streamlined Multi-Provider LLM Client
Supports: Perplexity (primary), Groq (backup), and Mock mode.

Perplexity is the primary provider because it has REAL-TIME web search
built into responses - perfect for market intelligence and idea validation.

Groq provides ultra-fast inference as a backup option.

Features:
- Automatic retry with exponential backoff for rate limits and transient errors
- Response caching to reduce API costs and improve performance
- Unified interface across all providers
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .retry_cache import (
    CacheConfig,
    LLMCache,
    RetryConfig,
    SmartRetry,
    get_default_cache,
    get_default_retry,
)

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0
    raw_response: Any = None
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for caching."""
        return {
            'content': self.content,
            'model': self.model,
            'provider': self.provider,
            'usage': self.usage,
            'latency_ms': self.latency_ms,
            'cached': True,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMResponse':
        """Create from cached dictionary."""
        return cls(
            content=data['content'],
            model=data['model'],
            provider=data['provider'],
            usage=data.get('usage', {}),
            latency_ms=data.get('latency_ms', 0),
            cached=True,
        )


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients with retry and caching support."""

    provider_name: str = "base"

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        cache_config: Optional[CacheConfig] = None,
        use_cache: bool = True,
        use_retry: bool = True,
    ):
        """Initialize base client with optional retry and cache configuration."""
        self._use_cache = use_cache
        self._use_retry = use_retry

        # Set up caching
        if use_cache:
            if cache_config:
                self._cache = LLMCache(cache_config)
            else:
                self._cache = get_default_cache()
        else:
            self._cache = None

        # Set up retry logic
        if use_retry:
            if retry_config:
                self._retry = SmartRetry(retry_config)
            else:
                self._retry = get_default_retry()
        else:
            self._retry = None

    @abstractmethod
    def _complete_impl(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        """Internal completion implementation. Override in subclasses."""
        pass

    @property
    @abstractmethod
    def model(self) -> str:
        """Get the current model name."""
        pass

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        """
        Generate a completion from the LLM with caching and retry support.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-2)
            json_mode: Request JSON output format

        Returns:
            LLMResponse with the completion
        """
        # Check cache first
        if self._cache is not None:
            cached = self._cache.get(
                prompt=prompt,
                system_prompt=system_prompt,
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
                provider=self.provider_name,
            )
            if cached:
                logger.debug(f"Using cached response for {self.provider_name}")
                return LLMResponse.from_dict(cached)

        # Make the actual call (with or without retry)
        if self._retry is not None:
            response = self._retry(self._complete_impl)(
                prompt, system_prompt, max_tokens, temperature, json_mode
            )
        else:
            response = self._complete_impl(
                prompt, system_prompt, max_tokens, temperature, json_mode
            )

        # Cache the response
        if self._cache is not None and response:
            self._cache.set(
                prompt=prompt,
                system_prompt=system_prompt,
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
                provider=self.provider_name,
                response=response.to_dict(),
            )

        return response

    def complete_with_retry(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> LLMResponse:
        """Legacy method for backward compatibility. Now just calls complete()."""
        return self.complete(prompt, system_prompt, max_tokens, temperature, json_mode)

    def clear_cache(self):
        """Clear the response cache."""
        if self._cache:
            self._cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if self._cache:
            return self._cache.stats()
        return {"enabled": False}

    def get_retry_stats(self) -> Dict[str, int]:
        """Get retry statistics."""
        if self._retry:
            return self._retry.get_stats()
        return {"enabled": False}


class PerplexityClient(BaseLLMClient):
    """
    Perplexity AI client with real-time web search built into responses.

    This is the PRIMARY provider because Perplexity has REAL-TIME web search
    capabilities integrated into the model's responses - perfect for:
    - Market intelligence and trend discovery
    - Competitor analysis
    - Pain point research
    - Idea validation with current data

    Available models:
    - sonar-pro: Flagship model, best for general use
    - sonar-deep-research: For comprehensive research tasks
    - sonar-reasoning: For complex analysis and reasoning
    """

    provider_name = "perplexity"

    MODELS = {
        "sonar-pro": "Flagship model - balanced performance",
        "sonar-deep-research": "Deep research - comprehensive analysis",
        "sonar-reasoning": "Reasoning model - complex analysis",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "sonar-pro",
        use_cache: bool = True,
        use_retry: bool = True,
    ):
        super().__init__(use_cache=use_cache, use_retry=use_retry)

        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Perplexity API key not found. Set PERPLEXITY_API_KEY environment variable.\n"
                "Get your API key at: https://www.perplexity.ai/settings/api"
            )

        self._model = model
        self.base_url = "https://api.perplexity.ai"

        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"Initialized Perplexity client with model {model}")
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    @property
    def model(self) -> str:
        return self._model

    def _complete_impl(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        start_time = time.time()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_content = prompt
        if json_mode:
            user_content += "\n\nRespond with valid JSON only. No other text or markdown."

        messages.append({"role": "user", "content": user_content})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        response = self.client.chat.completions.create(**kwargs)

        latency_ms = (time.time() - start_time) * 1000

        content = response.choices[0].message.content

        if json_mode:
            content = self._clean_json_response(content)

        return LLMResponse(
            content=content,
            model=response.model,
            provider=self.provider_name,
            usage={
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0) if response.usage else 0,
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0) if response.usage else 0,
            },
            latency_ms=latency_ms,
            raw_response=response
        )

    def _clean_json_response(self, content: str) -> str:
        """Clean markdown code blocks from JSON response."""
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    def research(self, query: str, max_tokens: int = 4096) -> LLMResponse:
        """
        Perform deep research on a topic using Perplexity's web search.

        Uses the deep-research model for comprehensive market intelligence.
        """
        original_model = self._model
        self._model = "sonar-deep-research"
        try:
            response = self.complete(
                prompt=query,
                system_prompt="You are a market research analyst. Provide comprehensive, factual research with citations.",
                max_tokens=max_tokens,
                temperature=0.3
            )
        finally:
            self._model = original_model
        return response

    def analyze(self, data: str, question: str, max_tokens: int = 4096) -> LLMResponse:
        """
        Analyze data using Perplexity's reasoning model.

        Uses the reasoning model for complex analysis tasks.
        """
        original_model = self._model
        self._model = "sonar-reasoning"
        try:
            response = self.complete(
                prompt=f"Data:\n{data}\n\nQuestion: {question}",
                system_prompt="You are an analytical expert. Provide thorough analysis with clear reasoning.",
                max_tokens=max_tokens,
                temperature=0.5
            )
        finally:
            self._model = original_model
        return response


class OpenAIClient(BaseLLMClient):
    """
    OpenAI client for GPT models.

    Available models:
    - gpt-4o: Latest GPT-4 Optimized model
    - gpt-4-turbo: GPT-4 Turbo with 128k context
    - gpt-4: Standard GPT-4
    - gpt-3.5-turbo: Fast and cost-effective
    """

    provider_name = "openai"

    MODELS = {
        "gpt-4o": "GPT-4 Optimized - Latest model",
        "gpt-4-turbo": "GPT-4 Turbo - 128k context",
        "gpt-4": "GPT-4 - Standard",
        "gpt-3.5-turbo": "GPT-3.5 Turbo - Fast and cheap",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        use_cache: bool = True,
        use_retry: bool = True,
    ):
        super().__init__(use_cache=use_cache, use_retry=use_retry)

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")

        self._model = model
        if model not in self.MODELS:
            logger.warning(f"Unknown model {model}, available: {list(self.MODELS.keys())}")

        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package is required. Install with: pip install openai")

    @property
    def model(self) -> str:
        return self._model

    def _complete_impl(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        start = time.time()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(**kwargs)
            latency_ms = (time.time() - start) * 1000

            return LLMResponse(
                content=response.choices[0].message.content,
                model=self._model,
                provider=self.provider_name,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                latency_ms=latency_ms,
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class AnthropicClient(BaseLLMClient):
    """
    Anthropic client for Claude models.

    Available models:
    - claude-3-5-sonnet-20241022: Claude 3.5 Sonnet (latest)
    - claude-3-opus-20240229: Claude 3 Opus - Most capable
    - claude-3-sonnet-20240229: Claude 3 Sonnet - Balanced
    - claude-3-haiku-20240307: Claude 3 Haiku - Fast
    """

    provider_name = "anthropic"

    MODELS = {
        "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet - Latest",
        "claude-3-opus-20240229": "Claude 3 Opus - Most capable",
        "claude-3-sonnet-20240229": "Claude 3 Sonnet - Balanced",
        "claude-3-haiku-20240307": "Claude 3 Haiku - Fast",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        use_cache: bool = True,
        use_retry: bool = True,
    ):
        super().__init__(use_cache=use_cache, use_retry=use_retry)

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable.")

        self._model = model
        if model not in self.MODELS:
            logger.warning(f"Unknown model {model}, available: {list(self.MODELS.keys())}")

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package is required. Install with: pip install anthropic")

    @property
    def model(self) -> str:
        return self._model

    def _complete_impl(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        start = time.time()

        kwargs = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            response = self.client.messages.create(**kwargs)
            latency_ms = (time.time() - start) * 1000

            content = response.content[0].text
            if json_mode and not content.strip().startswith("{"):
                # Try to extract JSON from markdown code blocks
                import re
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
                if json_match:
                    content = json_match.group(1)

            return LLMResponse(
                content=content,
                model=self._model,
                provider=self.provider_name,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                latency_ms=latency_ms,
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class GoogleClient(BaseLLMClient):
    """
    Google client for Gemini models (using google-genai SDK).

    Available models:
    - gemini-2.0-flash-exp: Gemini 2.0 Flash (experimental)
    - gemini-1.5-pro: Gemini 1.5 Pro - Most capable
    - gemini-1.5-flash: Gemini 1.5 Flash - Fast
    """

    provider_name = "google"

    MODELS = {
        "gemini-2.0-flash-exp": "Gemini 2.0 Flash - Experimental",
        "gemini-1.5-pro": "Gemini 1.5 Pro - Most capable",
        "gemini-1.5-flash": "Gemini 1.5 Flash - Fast",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-1.5-pro",
        use_cache: bool = True,
        use_retry: bool = True,
    ):
        super().__init__(use_cache=use_cache, use_retry=use_retry)

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable.")

        self._model = model
        if model not in self.MODELS:
            logger.warning(f"Unknown model {model}, available: {list(self.MODELS.keys())}")

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
        except ImportError:
            raise ImportError("google-genai package is required. Install with: pip install google-genai")

    @property
    def model(self) -> str:
        return self._model

    def _complete_impl(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        start = time.time()

        # Combine system and user prompts for Gemini
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        if json_mode:
            full_prompt += "\n\nRespond with valid JSON only."

        try:
            from google.genai import types
            response = self.client.models.generate_content(
                model=self._model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )
            latency_ms = (time.time() - start) * 1000

            return LLMResponse(
                content=response.text,
                model=self._model,
                provider=self.provider_name,
                usage={},
                latency_ms=latency_ms,
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"Google API error: {e}")
            raise


class GroqClient(BaseLLMClient):
    """
    Groq Cloud client - ultra-fast inference.

    This is the BACKUP provider offering:
    - Extremely fast inference speeds
    - Free tier available
    - Good for rapid iteration and testing
    """

    provider_name = "groq"

    MODELS = {
        "llama-3.3-70b-versatile": "Llama 3.3 70B - best quality",
        "llama-3.1-8b-instant": "Llama 3.1 8B - fastest",
        "mixtral-8x7b-32768": "Mixtral 8x7B - good balance",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        use_cache: bool = True,
        use_retry: bool = True,
    ):
        super().__init__(use_cache=use_cache, use_retry=use_retry)

        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Groq API key not found. Set GROQ_API_KEY environment variable.\n"
                "Get your free API key at: https://console.groq.com/keys"
            )

        self._model = model

        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
            logger.info(f"Initialized Groq client with model {model}")
        except ImportError:
            raise ImportError("groq package not installed. Run: pip install groq")

    @property
    def model(self) -> str:
        return self._model

    def _complete_impl(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        start_time = time.time()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        user_content = prompt
        if json_mode:
            user_content += "\n\nRespond with valid JSON only. No other text."

        messages.append({"role": "user", "content": user_content})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)

        latency_ms = (time.time() - start_time) * 1000

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            provider=self.provider_name,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            latency_ms=latency_ms,
            raw_response=response
        )


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing without API calls."""

    provider_name = "mock"

    def __init__(self, use_cache: bool = False, use_retry: bool = False):
        super().__init__(use_cache=False, use_retry=False)
        self._model = "mock-model"
        logger.info("Initialized Mock LLM client (no API calls)")

    @property
    def model(self) -> str:
        return self._model

    def _complete_impl(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        if json_mode:
            content = self._generate_mock_json(prompt)
        else:
            content = f"[MOCK RESPONSE] Processed prompt of {len(prompt)} characters."

        return LLMResponse(
            content=content,
            model="mock-model",
            provider=self.provider_name,
            usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": len(content) // 4},
            latency_ms=10
        )

    def _generate_mock_json(self, prompt: str) -> str:
        """Generate contextual mock JSON based on prompt content."""
        prompt_lower = prompt.lower()

        if "product summary" in prompt_lower:
            return json.dumps({
                "product_name": "Mock Product",
                "tagline": "A mock product for testing",
                "problem_statement": {
                    "primary_problem": "This is a mock problem statement",
                    "secondary_problems": ["Secondary problem 1"],
                    "current_solutions": ["Existing solution 1"],
                    "solution_gaps": ["Gap 1"]
                },
                "significance": {
                    "financial_impact": "$1M potential savings",
                    "operational_impact": "50% time reduction",
                    "strategic_impact": "Competitive advantage"
                },
                "target_buyer": {"title": "Manager", "company_size": "50-500"},
                "unique_value_proposition": "Mock value proposition"
            })

        elif "feature" in prompt_lower:
            return json.dumps({
                "core_features": [
                    {"id": "F-CORE-001", "name": "Mock Feature 1", "priority": "P0-Critical", "description": "A mock core feature"}
                ],
                "secondary_features": [
                    {"id": "F-SEC-001", "name": "Mock Secondary Feature", "priority": "P1-Important"}
                ],
                "ai_modules": [
                    {"id": "AI-001", "name": "Mock AI Module", "automation_type": "Generation"}
                ]
            })

        elif "architecture" in prompt_lower:
            return json.dumps({
                "backend": {"framework": "FastAPI", "runtime": "Python 3.11+"},
                "frontend": {"framework": "Next.js 14", "styling": "Tailwind CSS"},
                "database": {"primary": "PostgreSQL", "cache": "Redis"},
                "authentication": {"method": "JWT"},
                "infrastructure": {"hosting": "AWS"}
            })

        elif "database" in prompt_lower or "schema" in prompt_lower:
            return json.dumps({
                "entities": [
                    {"name": "users", "fields": [{"name": "id", "type": "UUID"}, {"name": "email", "type": "VARCHAR(255)"}]},
                    {"name": "organizations", "fields": [{"name": "id", "type": "UUID"}, {"name": "name", "type": "VARCHAR(255)"}]}
                ]
            })

        elif "api" in prompt_lower or "endpoint" in prompt_lower:
            return json.dumps({
                "base_url": "/api/v1",
                "authentication": "Bearer JWT",
                "endpoints": [
                    {"path": "/auth/login", "method": "POST"},
                    {"path": "/auth/register", "method": "POST"},
                    {"path": "/users/me", "method": "GET"}
                ]
            })

        elif "ui" in prompt_lower or "ux" in prompt_lower:
            return json.dumps({
                "screens": [
                    {"id": "SCR-001", "name": "Dashboard", "path": "/dashboard"},
                    {"id": "SCR-002", "name": "Login", "path": "/login"}
                ],
                "user_flows": [{"id": "UF-001", "name": "Login Flow"}],
                "components": [{"id": "CMP-001", "name": "Button"}]
            })

        elif "monetization" in prompt_lower or "pricing" in prompt_lower:
            return json.dumps({
                "pricing_model": "subscription",
                "tiers": [
                    {"name": "Free", "price_monthly": 0},
                    {"name": "Pro", "price_monthly": 29},
                    {"name": "Enterprise", "price_monthly": "custom"}
                ],
                "billing_provider": "Stripe"
            })

        elif "deployment" in prompt_lower:
            return json.dumps({
                "ci_cd": {"provider": "GitHub Actions"},
                "infrastructure": {"provider": "AWS", "iac_tool": "Terraform"},
                "monitoring": {"logging": "CloudWatch"}
            })

        elif "consistency" in prompt_lower or "check" in prompt_lower:
            return json.dumps({
                "passed": True,
                "issues": [],
                "severity": "none"
            })

        elif "feasibility" in prompt_lower:
            return json.dumps({
                "passed": True,
                "issues": [],
                "severity": "none",
                "estimated_mvp_weeks": 8
            })

        elif "entity" in prompt_lower or "database entity" in prompt_lower:
            return json.dumps({
                "name": "Item",
                "class": "Item",
                "lower": "item",
                "table": "items",
                "fields": [
                    {"name": "name", "sql_type": "String(255)", "python_type": "str", "required": True},
                    {"name": "description", "sql_type": "Text", "python_type": "Optional[str]", "required": False},
                    {"name": "status", "sql_type": "String(50)", "python_type": "str", "required": False},
                    {"name": "price", "sql_type": "Float", "python_type": "float", "required": False},
                    {"name": "is_active", "sql_type": "Boolean", "python_type": "bool", "required": True}
                ]
            })

        elif "feature" in prompt_lower and "detect" in prompt_lower:
            return json.dumps({
                "needs_payments": False,
                "needs_background_jobs": False,
                "needs_ai_integration": True,
                "needs_email": False
            })

        else:
            return json.dumps({"mock": True, "message": "Mock response generated"})


class MultiProviderClient(BaseLLMClient):
    """Client that fails over between Perplexity and Groq."""

    provider_name = "multi"

    def __init__(self, providers: Optional[List[BaseLLMClient]] = None):
        """
        Initialize with providers. If none provided, auto-detects available.

        Priority order:
        1. OpenAI (most popular, reliable)
        2. Anthropic (high quality Claude models)
        3. Google (Gemini models)
        4. Perplexity (real-time web search)
        5. Groq (fast inference)
        """
        if providers:
            self.providers = providers
        else:
            self.providers = []

            # Try OpenAI first (most popular)
            if os.getenv("OPENAI_API_KEY"):
                try:
                    self.providers.append(OpenAIClient())
                except (ValueError, ImportError) as e:
                    logger.debug(f"Skipping OpenAI: {e}")

            # Try Anthropic second (high quality)
            if os.getenv("ANTHROPIC_API_KEY"):
                try:
                    self.providers.append(AnthropicClient())
                except (ValueError, ImportError) as e:
                    logger.debug(f"Skipping Anthropic: {e}")

            # Try Google third (Gemini)
            if os.getenv("GOOGLE_API_KEY"):
                try:
                    self.providers.append(GoogleClient())
                except (ValueError, ImportError) as e:
                    logger.debug(f"Skipping Google: {e}")

            # Try Perplexity (real-time web search)
            if os.getenv("PERPLEXITY_API_KEY"):
                try:
                    self.providers.append(PerplexityClient())
                except (ValueError, ImportError) as e:
                    logger.debug(f"Skipping Perplexity: {e}")

            # Try Groq (fast inference)
            if os.getenv("GROQ_API_KEY"):
                try:
                    self.providers.append(GroqClient())
                except (ValueError, ImportError) as e:
                    logger.debug(f"Skipping Groq: {e}")

            if not self.providers:
                logger.warning("No providers available, adding mock")
                self.providers.append(MockLLMClient())

        logger.info(f"Initialized MultiProvider with {len(self.providers)} providers: {[p.provider_name for p in self.providers]}")

    @property
    def model(self) -> str:
        return self.providers[0].model if self.providers else "none"

    def _complete_impl(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        # This won't be called directly since we override complete()
        pass

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        last_error = None

        for provider in self.providers:
            try:
                logger.info(f"Trying provider: {provider.provider_name}")
                response = provider.complete(prompt, system_prompt, max_tokens, temperature, json_mode)
                logger.info(f"Success with provider: {provider.provider_name}")
                return response
            except Exception as e:
                logger.warning(f"Provider {provider.provider_name} failed: {e}")
                last_error = e
                continue

        raise Exception(f"All providers failed. Last error: {last_error}")


def get_llm_client(
    provider: str = "auto",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> BaseLLMClient:
    """
    Factory function to get an LLM client.

    Available providers:
    - openai: OpenAI GPT models (gpt-4o, gpt-4-turbo, gpt-3.5-turbo)
    - anthropic: Anthropic Claude models (claude-3-5-sonnet, claude-3-opus)
    - google: Google Gemini models (gemini-1.5-pro, gemini-1.5-flash)
    - perplexity: Perplexity with real-time web search (sonar-pro)
    - groq: Fast inference with open models (llama-3.3-70b)
    - mock: Testing without API calls
    - multi: Automatic failover between providers
    - auto: Auto-detect best available provider

    Args:
        provider: Provider name or 'auto'
        api_key: Optional API key override
        model: Optional model override

    Returns:
        Configured LLM client
    """
    if provider == "auto":
        provider = os.getenv("DEFAULT_LLM_PROVIDER", "auto")

    if provider == "mock":
        return MockLLMClient()

    if provider == "openai":
        return OpenAIClient(
            api_key=api_key,
            model=model or os.getenv("OPENAI_MODEL", "gpt-4o")
        )

    if provider == "anthropic":
        return AnthropicClient(
            api_key=api_key,
            model=model or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
        )

    if provider == "google":
        return GoogleClient(
            api_key=api_key,
            model=model or os.getenv("GOOGLE_MODEL", "gemini-1.5-pro")
        )

    if provider == "perplexity":
        return PerplexityClient(
            api_key=api_key,
            model=model or os.getenv("PERPLEXITY_MODEL", "sonar-pro")
        )

    if provider == "groq":
        return GroqClient(
            api_key=api_key,
            model=model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        )

    if provider == "multi":
        return MultiProviderClient()

    if provider == "auto":
        # Try providers in order of preference
        # 1. OpenAI (most popular, reliable)
        if os.getenv("OPENAI_API_KEY"):
            try:
                return OpenAIClient()
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI: {e}")

        # 2. Anthropic (high quality, Claude models)
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                return AnthropicClient()
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic: {e}")

        # 3. Google (Gemini models)
        if os.getenv("GOOGLE_API_KEY"):
            try:
                return GoogleClient()
            except Exception as e:
                logger.warning(f"Could not initialize Google: {e}")

        # 4. Perplexity (web search capabilities)
        if os.getenv("PERPLEXITY_API_KEY"):
            try:
                return PerplexityClient()
            except Exception as e:
                logger.warning(f"Could not initialize Perplexity: {e}")

        # 5. Groq (fast, cost-effective)
        if os.getenv("GROQ_API_KEY"):
            try:
                return GroqClient()
            except Exception as e:
                logger.warning(f"Could not initialize Groq: {e}")

        logger.warning("No API keys found, using mock client")
        return MockLLMClient()

    raise ValueError(
        f"Unknown provider: {provider}\n"
        f"Available: openai, anthropic, google, perplexity, groq, mock, multi, auto"
    )


def list_available_providers() -> Dict[str, bool]:
    """Check which providers are available based on environment variables."""
    return {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "google": bool(os.getenv("GOOGLE_API_KEY")),
        "perplexity": bool(os.getenv("PERPLEXITY_API_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "mock": True,
        "multi": any([
            os.getenv("OPENAI_API_KEY"),
            os.getenv("ANTHROPIC_API_KEY"),
            os.getenv("GOOGLE_API_KEY"),
            os.getenv("PERPLEXITY_API_KEY"),
            os.getenv("GROQ_API_KEY"),
        ]),
    }

