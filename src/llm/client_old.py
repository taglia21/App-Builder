"""
Unified LLM Client
Supports both OpenAI and Anthropic APIs with a common interface.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized response from LLM."""
    content: str
    model: str
    usage: Dict[str, int]
    raw_response: Any = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
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
    
    @abstractmethod
    def complete_with_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        """Generate a completion from a list of messages."""
        pass


class OpenAIClient(BaseLLMClient):
    """OpenAI API client."""
    
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
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return self.complete_with_messages(messages, max_tokens, temperature, json_mode)
    
    def complete_with_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        kwargs = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = self.client.chat.completions.create(**kwargs)
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            raw_response=response
        )


class AnthropicClient(BaseLLMClient):
    """Anthropic API client."""
    
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
        
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            raw_response=response
        )
    
    def complete_with_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        # Extract system message if present
        system_prompt = None
        filtered_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                filtered_messages.append(msg)
        
        if json_mode:
            if system_prompt:
                system_prompt += "\n\nYou must respond with valid JSON only. No other text."
            else:
                system_prompt = "You must respond with valid JSON only. No other text."
        
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": filtered_messages
        }
        
        if system_prompt:
            kwargs["system"] = system_prompt
        
        response = self.client.messages.create(**kwargs)
        
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            raw_response=response
        )


class MockLLMClient(BaseLLMClient):
    """Mock LLM client for testing without API calls."""
    
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
        # Return a mock response
        if json_mode:
            content = '{"mock": true, "message": "This is a mock response"}'
        else:
            content = f"[MOCK RESPONSE] Received prompt of {len(prompt)} characters."
        
        return LLMResponse(
            content=content,
            model="mock-model",
            usage={"prompt_tokens": len(prompt) // 4, "completion_tokens": 50, "total_tokens": len(prompt) // 4 + 50}
        )
    
    def complete_with_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        json_mode: bool = False
    ) -> LLMResponse:
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return self.complete(f"Messages with {total_chars} total characters", None, max_tokens, temperature, json_mode)


def get_llm_client(
    provider: str = "auto",
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> BaseLLMClient:
    """
    Factory function to get an LLM client.
    
    Args:
        provider: "openai", "anthropic", "mock", or "auto" (tries anthropic, then openai)
        api_key: Optional API key (otherwise uses environment variable)
        model: Optional model name override
        
    Returns:
        Configured LLM client
    """
    if provider == "mock":
        return MockLLMClient()
    
    if provider == "auto":
        # Try Anthropic first, then OpenAI
        if os.getenv("ANTHROPIC_API_KEY") or api_key:
            try:
                return AnthropicClient(api_key=api_key, model=model or "claude-sonnet-4-20250514")
            except (ValueError, ImportError):
                pass
        
        if os.getenv("OPENAI_API_KEY") or api_key:
            try:
                return OpenAIClient(api_key=api_key, model=model or "gpt-4-turbo-preview")
            except (ValueError, ImportError):
                pass
        
        logger.warning("No API keys found, using mock client")
        return MockLLMClient()
    
    if provider == "openai":
        return OpenAIClient(api_key=api_key, model=model or "gpt-4-turbo-preview")
    
    if provider == "anthropic":
        return AnthropicClient(api_key=api_key, model=model or "claude-sonnet-4-20250514")
    
    raise ValueError(f"Unknown provider: {provider}")


# Export alias for backward compatibility
LLMClient = BaseLLMClient
