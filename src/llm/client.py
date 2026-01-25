"""
Multi-Provider LLM Client
Supports: Google Gemini, Groq, OpenRouter, OpenAI, Anthropic, and Mock mode.

Features:
- Automatic retry with exponential backoff for rate limits and transient errors
- Response caching to reduce API costs and improve performance
- Unified interface across all providers
"""

import os
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field, asdict

from .retry_cache import (
    LLMCache,
    SmartRetry,
    RetryConfig,
    CacheConfig,
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
    cached: bool = False  # Whether this response was from cache
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for caching."""
        return {
            'content': self.content,
            'model': self.model,
            'provider': self.provider,
            'usage': self.usage,
            'latency_ms': self.latency_ms,
            'cached': True,  # Will be cached
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


class GeminiClient(BaseLLMClient):
    """Google Gemini (AI Studio) client."""
    
    provider_name = "gemini"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        use_cache: bool = True,
        use_retry: bool = True,
    ):
        super().__init__(use_cache=use_cache, use_retry=use_retry)
        
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not found. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")
        
        self._model = model
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.genai = genai
            self.client = genai.GenerativeModel(model)
            logger.info(f"Initialized Gemini client with model {model}")
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
    
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
        
        # Build the full prompt
        full_prompt = ""
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n"
        full_prompt += prompt
        
        if json_mode:
            full_prompt += "\n\nRespond with valid JSON only. No other text or markdown."
        
        # Configure generation
        generation_config = self.genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
        
        # Generate response
        response = self.client.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Extract content
        content = response.text
        
        # Clean JSON if needed
        if json_mode:
            content = self._clean_json_response(content)
        
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.provider_name,
            usage={
                "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
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


class GroqClient(BaseLLMClient):
    """Groq Cloud client - extremely fast inference."""
    
    provider_name = "groq"
    
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
            raise ValueError("Groq API key not found. Set GROQ_API_KEY environment variable.")
        
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


class OpenRouterClient(BaseLLMClient):
    """OpenRouter client - access to multiple model providers."""
    
    provider_name = "openrouter"
    
    FREE_MODELS = [
        "meta-llama/llama-3.2-3b-instruct:free",
        "microsoft/phi-3-mini-128k-instruct:free",
        "google/gemma-2-9b-it:free",
        "qwen/qwen-2-7b-instruct:free",
        "meta-llama/llama-3-8b-instruct:free",
    ]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "meta-llama/llama-3.2-3b-instruct:free",
        use_cache: bool = True,
        use_retry: bool = True,
    ):
        super().__init__(use_cache=use_cache, use_retry=use_retry)
        
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable.")
        
        self._model = model
        self.base_url = "https://openrouter.ai/api/v1"
        
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"Initialized OpenRouter client with model {model}")
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
            user_content += "\n\nRespond with valid JSON only. No other text."
        
        messages.append({"role": "user", "content": user_content})
        
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "extra_headers": {
                "HTTP-Referer": "https://github.com/startup-generator",
                "X-Title": "Startup Generator"
            }
        }
        
        response = self.client.chat.completions.create(**kwargs)
        
        latency_ms = (time.time() - start_time) * 1000
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.model,
            provider=self.provider_name,
            usage={
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0) if response.usage else 0,
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0) if response.usage else 0,
            },
            latency_ms=latency_ms,
            raw_response=response
        )


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""
    
    provider_name = "openai"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4-turbo-preview",
        use_cache: bool = True,
        use_retry: bool = True,
    ):
        super().__init__(use_cache=use_cache, use_retry=use_retry)
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self._model = model
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"Initialized OpenAI client with model {model}")
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
        messages.append({"role": "user", "content": prompt})
        
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


class AnthropicClient(BaseLLMClient):
    """Anthropic Claude client."""
    
    provider_name = "anthropic"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        use_cache: bool = True,
        use_retry: bool = True,
    ):
        super().__init__(use_cache=use_cache, use_retry=use_retry)
        
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
        
        self._model = model
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info(f"Initialized Anthropic client with model {model}")
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
    
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
        
        messages = [{"role": "user", "content": prompt}]
        
        if json_mode:
            if system_prompt:
                system_prompt += "\n\nYou must respond with valid JSON only. No other text."
            else:
                system_prompt = "You must respond with valid JSON only. No other text."
        
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        response = self.client.messages.create(**kwargs)
        
        latency_ms = (time.time() - start_time) * 1000
        
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            provider=self.provider_name,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            latency_ms=latency_ms,
            raw_response=response
        )


class PerplexityClient(BaseLLMClient):
    """Perplexity AI client with real-time web search built into responses.
    
    Perplexity is especially valuable for market intelligence because it has
    REAL-TIME web search capabilities integrated into the model's responses.
    
    Available models:
    - sonar-pro: Flagship model, best for general use
    - sonar-deep-research: For comprehensive research tasks
    - sonar-reasoning: For complex analysis and reasoning
    """
    
    provider_name = "perplexity"
    
    # Available Perplexity models
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
            raise ValueError("Perplexity API key not found. Set PERPLEXITY_API_KEY environment variable.")
        
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
        
        # Clean JSON if needed
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
        """Perform deep research on a topic using Perplexity's web search.
        
        This is a convenience method that uses the deep-research model
        for comprehensive market intelligence gathering.
        """
        original_model = self._model
        self._model = "sonar-deep-research"
        try:
            response = self.complete(
                prompt=query,
                system_prompt="You are a market research analyst. Provide comprehensive, factual research with citations.",
                max_tokens=max_tokens,
                temperature=0.3  # Lower temp for more factual responses
            )
        finally:
            self._model = original_model
        return response
    
    def analyze(self, data: str, question: str, max_tokens: int = 4096) -> LLMResponse:
        """Analyze data using Perplexity's reasoning model.
        
        This is a convenience method that uses the reasoning model
        for complex analysis tasks.
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


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing without API calls."""
    
    provider_name = "mock"
    
    def __init__(self, use_cache: bool = False, use_retry: bool = False):
        # Mock client doesn't need caching or retry
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
            # Core entity for code generation
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
            # Feature detection for code generation
            return json.dumps({
                "needs_payments": False,
                "needs_background_jobs": False,
                "needs_ai_integration": True,
                "needs_email": False
            })
        
        else:
            return json.dumps({"mock": True, "message": "Mock response generated"})


class MultiProviderClient(BaseLLMClient):
    """Client that can failover between multiple providers."""
    
    provider_name = "multi"
    
    def __init__(self, providers: List[BaseLLMClient]):
        self.providers = providers
        logger.info(f"Initialized MultiProvider client with {len(providers)} providers")
    
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
    """Factory function to get an LLM client."""
    
    if provider == "auto":
        provider = os.getenv("DEFAULT_LLM_PROVIDER", "auto")
    
    if provider == "mock":
        return MockLLMClient()
    
    if provider == "gemini":
        return GeminiClient(
            api_key=api_key,
            model=model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        )
    
    if provider == "groq":
        return GroqClient(
            api_key=api_key,
            model=model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        )
    
    if provider == "openrouter":
        return OpenRouterClient(
            api_key=api_key,
            model=model or os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.2-3b-instruct:free")
        )
    
    if provider == "openai":
        return OpenAIClient(
            api_key=api_key,
            model=model or os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
        )
    
    if provider == "anthropic":
        return AnthropicClient(
            api_key=api_key,
            model=model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        )
    
    if provider == "perplexity":
        return PerplexityClient(
            api_key=api_key,
            model=model or os.getenv("PERPLEXITY_MODEL", "sonar-pro")
        )
    
    if provider == "multi":
        providers = []
        
        # Perplexity first for its real-time web search capabilities
        if os.getenv("PERPLEXITY_API_KEY"):
            try:
                providers.append(PerplexityClient())
            except (ValueError, ImportError) as e:
                logger.debug(f"Skipping Perplexity in multi-provider: {type(e).__name__}: {e}")
        
        if os.getenv("GROQ_API_KEY"):
            try:
                providers.append(GroqClient())
            except (ValueError, ImportError) as e:
                logger.debug(f"Skipping Groq in multi-provider: {type(e).__name__}: {e}")
        
        if os.getenv("GOOGLE_API_KEY"):
            try:
                providers.append(GeminiClient())
            except (ValueError, ImportError) as e:
                logger.debug(f"Skipping Gemini in multi-provider: {type(e).__name__}: {e}")
        
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                providers.append(OpenRouterClient())
            except (ValueError, ImportError) as e:
                logger.debug(f"Skipping OpenRouter in multi-provider: {type(e).__name__}: {e}")
        
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                providers.append(AnthropicClient())
            except (ValueError, ImportError) as e:
                logger.debug(f"Skipping Anthropic in multi-provider: {type(e).__name__}: {e}")
        
        if os.getenv("OPENAI_API_KEY"):
            try:
                providers.append(OpenAIClient())
            except (ValueError, ImportError) as e:
                logger.debug(f"Skipping OpenAI in multi-provider: {type(e).__name__}: {e}")
        
        if not providers:
            logger.warning("No providers available for multi-provider client, using mock")
            return MockLLMClient()
        
        return MultiProviderClient(providers)
    
    if provider == "auto":
        # Try providers in order (Perplexity preferred for web search, then free/fast)
        if os.getenv("PERPLEXITY_API_KEY"):
            try:
                return PerplexityClient()
            except Exception as e:
                logger.warning(f"Could not initialize Perplexity: {e}")
        
        if os.getenv("GROQ_API_KEY"):
            try:
                return GroqClient()
            except Exception as e:
                logger.warning(f"Could not initialize Groq: {e}")
        
        if os.getenv("GOOGLE_API_KEY"):
            try:
                return GeminiClient()
            except Exception as e:
                logger.warning(f"Could not initialize Gemini: {e}")
        
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                return OpenRouterClient()
            except Exception as e:
                logger.warning(f"Could not initialize OpenRouter: {e}")
        
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                return AnthropicClient()
            except Exception as e:
                logger.warning(f"Could not initialize Anthropic: {e}")
        
        if os.getenv("OPENAI_API_KEY"):
            try:
                return OpenAIClient()
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI: {e}")
        
        logger.warning("No API keys found, using mock client")
        return MockLLMClient()
    
    raise ValueError(f"Unknown provider: {provider}")


def list_available_providers() -> Dict[str, bool]:
    """Check which providers are available based on environment variables."""
    return {
        "perplexity": bool(os.getenv("PERPLEXITY_API_KEY")),
        "gemini": bool(os.getenv("GOOGLE_API_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "mock": True
    }
