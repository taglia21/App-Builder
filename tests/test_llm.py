"""Tests for multi-LLM provider support."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.llm.client import (
    LLMResponse,
    BaseLLMClient,
    PerplexityClient,
    GroqClient,
    MockLLMClient,
)


class TestLLMResponse:
    """Test LLMResponse model."""

    def test_create_response(self):
        """Test creating an LLM response."""
        response = LLMResponse(
            content="Test response",
            model="gpt-4",
            provider="openai",
            usage={"prompt_tokens": 10, "completion_tokens": 20}
        )
        assert response.content == "Test response"
        assert response.model == "gpt-4"
        assert response.provider == "openai"

    def test_response_to_dict(self):
        """Test converting response to dictionary."""
        response = LLMResponse(
            content="Test",
            model="claude-3",
            provider="anthropic"
        )
        data = response.to_dict()
        assert isinstance(data, dict)
        assert data["content"] == "Test"
        assert data["cached"] is True

    def test_response_from_dict(self):
        """Test creating response from dictionary."""
        data = {
            "content": "Test content",
            "model": "gemini-pro",
            "provider": "google",
            "usage": {},
            "latency_ms": 100
        }
        response = LLMResponse.from_dict(data)
        assert response.content == "Test content"
        assert response.provider == "google"


class TestOpenAIProvider:
    """Test OpenAI provider implementation."""

    def test_openai_client_exists(self):
        """Test that OpenAI client can be imported."""
        from src.llm.client import OpenAIClient
        assert OpenAIClient is not None

    @patch('openai.OpenAI')
    def test_openai_client_initialization(self, mock_openai):
        """Test OpenAI client initialization."""
        from src.llm.client import OpenAIClient
        
        client = OpenAIClient(api_key="test_key", model="gpt-4")
        assert client.provider_name == "openai"
        assert client.model == "gpt-4"

    @patch('openai.OpenAI')
    def test_openai_generate_text(self, mock_openai):
        """Test OpenAI text generation."""
        from src.llm.client import OpenAIClient
        
        # Mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Generated text"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        client = OpenAIClient(api_key="test_key", use_cache=False, use_retry=False)
        result = client.complete("Test prompt")
        
        assert isinstance(result, LLMResponse)
        assert result.content == "Generated text"
        assert result.provider == "openai"

    def test_openai_available_models(self):
        """Test OpenAI available models."""
        from src.llm.client import OpenAIClient
        
        assert hasattr(OpenAIClient, 'MODELS')
        assert "gpt-4" in OpenAIClient.MODELS or "gpt-4o" in OpenAIClient.MODELS


class TestAnthropicProvider:
    """Test Anthropic provider implementation."""

    def test_anthropic_client_exists(self):
        """Test that Anthropic client can be imported."""
        from src.llm.client import AnthropicClient
        assert AnthropicClient is not None

    @patch('anthropic.Anthropic')
    def test_anthropic_client_initialization(self, mock_anthropic):
        """Test Anthropic client initialization."""
        from src.llm.client import AnthropicClient
        
        client = AnthropicClient(api_key="test_key", model="claude-3-opus-20240229")
        assert client.provider_name == "anthropic"

    @patch('anthropic.Anthropic')
    def test_anthropic_generate_text(self, mock_anthropic):
        """Test Anthropic text generation."""
        from src.llm.client import AnthropicClient
        
        # Mock response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Claude response"
        mock_response.usage.input_tokens = 15
        mock_response.usage.output_tokens = 25
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        client = AnthropicClient(api_key="test_key", use_cache=False, use_retry=False)
        result = client.complete("Test prompt")
        
        assert isinstance(result, LLMResponse)
        assert result.content == "Claude response"
        assert result.provider == "anthropic"

    def test_anthropic_available_models(self):
        """Test Anthropic available models."""
        from src.llm.client import AnthropicClient
        
        assert hasattr(AnthropicClient, 'MODELS')
        assert any("claude" in model.lower() for model in AnthropicClient.MODELS.keys())


class TestGoogleProvider:
    """Test Google provider implementation."""

    def test_google_client_exists(self):
        """Test that Google client can be imported."""
        from src.llm.client import GoogleClient
        assert GoogleClient is not None

    @patch('google.generativeai.GenerativeModel')
    def test_google_client_initialization(self, mock_google):
        """Test Google client initialization."""
        from src.llm.client import GoogleClient
        
        with patch('google.generativeai.configure'):
            client = GoogleClient(api_key="test_key", model="gemini-pro")
            assert client.provider_name == "google"

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    def test_google_generate_text(self, mock_model_class, mock_configure):
        """Test Google text generation."""
        from src.llm.client import GoogleClient
        
        # Mock response
        mock_response = Mock()
        mock_response.text = "Gemini response"
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        client = GoogleClient(api_key="test_key", use_cache=False, use_retry=False)
        result = client.complete("Test prompt")
        
        assert isinstance(result, LLMResponse)
        assert result.content == "Gemini response"
        assert result.provider == "google"

    def test_google_available_models(self):
        """Test Google available models."""
        from src.llm.client import GoogleClient
        
        assert hasattr(GoogleClient, 'MODELS')
        assert any("gemini" in model.lower() for model in GoogleClient.MODELS.keys())


class TestProviderAbstraction:
    """Test provider abstraction and interface."""

    def test_base_client_is_abstract(self):
        """Test that BaseLLMClient is abstract."""
        from abc import ABC
        assert issubclass(BaseLLMClient, ABC)

    def test_all_providers_have_generate_method(self):
        """Test all providers implement complete method."""
        from src.llm.client import OpenAIClient, AnthropicClient, GoogleClient
        
        for client_class in [OpenAIClient, AnthropicClient, GoogleClient, PerplexityClient, GroqClient]:
            assert hasattr(client_class, 'complete')

    def test_all_providers_have_provider_name(self):
        """Test all providers have provider_name attribute."""
        from src.llm.client import OpenAIClient, AnthropicClient, GoogleClient
        
        for client_class in [OpenAIClient, AnthropicClient, GoogleClient]:
            assert hasattr(client_class, 'provider_name')


class TestMultiProviderFallback:
    """Test multi-provider fallback logic."""

    def test_multi_provider_client_exists(self):
        """Test MultiProviderClient exists."""
        from src.llm.client import MultiProviderClient
        assert MultiProviderClient is not None

    @patch('src.llm.client.OpenAIClient')
    @patch('src.llm.client.AnthropicClient')
    def test_fallback_to_secondary_provider(self, mock_anthropic, mock_openai):
        """Test fallback when primary provider fails."""
        from src.llm.client import MultiProviderClient
        
        # Primary fails
        mock_openai_instance = Mock()
        mock_openai_instance.complete.side_effect = Exception("API Error")
        mock_openai_instance.provider_name = "openai"
        
        # Secondary succeeds
        mock_anthropic_instance = Mock()
        mock_anthropic_instance.complete.return_value = LLMResponse(
            content="Fallback response",
            model="claude-3",
            provider="anthropic"
        )
        mock_anthropic_instance.provider_name = "anthropic"
        
        client = MultiProviderClient(providers=[mock_openai_instance, mock_anthropic_instance])
        result = client.complete("Test prompt")
        
        assert result.content == "Fallback response"
        assert result.provider == "anthropic"


class TestProviderSelection:
    """Test provider selection logic."""

    def test_get_llm_client_function_exists(self):
        """Test get_llm_client helper function exists."""
        from src.llm.client import get_llm_client
        assert callable(get_llm_client)

    @patch('src.llm.client.OpenAIClient')
    def test_get_llm_client_openai(self, mock_openai):
        """Test getting OpenAI client."""
        from src.llm.client import get_llm_client
        
        client = get_llm_client(provider="openai")
        mock_openai.assert_called_once()

    @patch('src.llm.client.AnthropicClient')
    def test_get_llm_client_anthropic(self, mock_anthropic):
        """Test getting Anthropic client."""
        from src.llm.client import get_llm_client
        
        client = get_llm_client(provider="anthropic")
        mock_anthropic.assert_called_once()

    @patch('src.llm.client.GoogleClient')
    def test_get_llm_client_google(self, mock_google):
        """Test getting Google client."""
        from src.llm.client import get_llm_client
        
        with patch('google.generativeai.configure'):
            client = get_llm_client(provider="google")
            mock_google.assert_called_once()
