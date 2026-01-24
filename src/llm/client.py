"""
Multi-Provider LLM Client
Supports: Google Gemini, Groq, OpenRouter, OpenAI, Anthropic, and Mock mode.
"""

import os
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field

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


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    provider_name: str = "base"
    
    @abstractmethod
    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        """Generate a completion from the LLM."""
        pass
    
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
        """Complete with automatic retry on failure."""
        last_error = None
        for attempt in range(max_retries):
            try:
                return self.complete(prompt, system_prompt, max_tokens, temperature, json_mode)
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
        raise last_error


class GeminiClient(BaseLLMClient):
    """Google Gemini (AI Studio) client."""
    
    provider_name = "gemini"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash"
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not found. Set GOOGLE_API_KEY environment variable.")
        
        self.model = model
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.genai = genai
            self.client = genai.GenerativeModel(model)
            logger.info(f"Initialized Gemini client with model {model}")
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
    
    def complete(
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
        model: str = "llama-3.3-70b-versatile"
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key not found. Set GROQ_API_KEY environment variable.")
        
        self.model = model
        
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
            logger.info(f"Initialized Groq client with model {model}")
        except ImportError:
            raise ImportError("groq package not installed. Run: pip install groq")
    
    def complete(
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
        "mistralai/mistral-7b-instruct:free",
        "microsoft/phi-3-mini-128k-instruct:free",
        "google/gemma-2-9b-it:free",
        "qwen/qwen-2-7b-instruct:free",
        "meta-llama/llama-3-8b-instruct:free",
    ]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "mistralai/mistral-7b-instruct:free"
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable.")
        
        self.model = model
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
    
    def complete(
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
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4-turbo-preview"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        self.model = model
        
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"Initialized OpenAI client with model {model}")
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
    
    def complete(
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
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
        
        self.model = model
        
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info(f"Initialized Anthropic client with model {model}")
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
    
    def complete(
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


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing without API calls."""
    
    provider_name = "mock"
    
    def __init__(self):
        logger.info("Initialized Mock LLM client (no API calls)")
    
    def complete(
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
            model=model or os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free")
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
    
    if provider == "multi":
        providers = []
        
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
        # Try providers in order (free/fast first)
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
        "gemini": bool(os.getenv("GOOGLE_API_KEY")),
        "groq": bool(os.getenv("GROQ_API_KEY")),
        "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "mock": True
    }
