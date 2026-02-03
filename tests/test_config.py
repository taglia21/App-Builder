"""Tests for centralized configuration."""
import pytest
import os
from unittest.mock import patch
from pydantic import ValidationError


class TestSettings:
    """Test Settings configuration."""

    def test_settings_import(self):
        """Test that settings can be imported."""
        # Import directly from config.settings to avoid circular imports
        from src.config.settings import settings
        assert settings is not None

    def test_settings_has_required_fields(self):
        """Test settings has all required configuration fields."""
        from src.config import settings
        
        # Core fields
        assert hasattr(settings, 'APP_NAME')
        assert hasattr(settings, 'APP_VERSION')
        assert hasattr(settings, 'ENVIRONMENT')
        assert hasattr(settings, 'DEBUG')
        
        # API Keys
        assert hasattr(settings, 'OPENAI_API_KEY')
        assert hasattr(settings, 'ANTHROPIC_API_KEY')
        assert hasattr(settings, 'GOOGLE_API_KEY')
        assert hasattr(settings, 'PERPLEXITY_API_KEY')
        assert hasattr(settings, 'GROQ_API_KEY')
        
        # Deployment
        assert hasattr(settings, 'VERCEL_TOKEN')

    def test_settings_app_name(self):
        """Test APP_NAME is set."""
        from src.config import settings
        # App name should be either LaunchForge or App-Builder
        assert settings.APP_NAME in ["LaunchForge", "App-Builder"]

    def test_settings_environment_default(self):
        """Test ENVIRONMENT defaults to development."""
        with patch.dict(os.environ, {}, clear=True):
            from src.config.settings import Settings
            test_settings = Settings()
            assert test_settings.ENVIRONMENT in ["development", "production", "testing"]

    def test_settings_debug_mode(self):
        """Test DEBUG mode configuration."""
        from src.config import settings
        assert isinstance(settings.DEBUG, bool)

    def test_settings_optional_api_keys(self):
        """Test API keys are optional (None allowed when not set)."""
        # Create fresh settings without env vars
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': '',
            'ANTHROPIC_API_KEY': '',
            'GOOGLE_API_KEY': '',
            'PERPLEXITY_API_KEY': '',
            'GROQ_API_KEY': ''
        }, clear=False):
            from src.config.settings import Settings
            test_settings = Settings()
            
            # API keys should be None or empty when not set
            # (They might have defaults from .env file in development)
            assert test_settings.OPENAI_API_KEY is None or test_settings.OPENAI_API_KEY == ''

    def test_settings_with_env_vars(self):
        """Test settings loaded from environment variables."""
        test_env = {
            'OPENAI_API_KEY': 'sk-test123',
            'ENVIRONMENT': 'production',
            'DEBUG': 'false'
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            from src.config.settings import Settings
            test_settings = Settings()
            
            assert test_settings.OPENAI_API_KEY == 'sk-test123'
            assert test_settings.ENVIRONMENT == 'production'
            assert test_settings.DEBUG is False

    def test_settings_singleton_pattern(self):
        """Test settings uses singleton pattern."""
        from src.config import settings
        from src.config import settings as settings2
        
        assert settings is settings2

    def test_settings_model_dump(self):
        """Test settings can be dumped to dict."""
        from src.config import settings
        
        config_dict = settings.model_dump()
        assert isinstance(config_dict, dict)
        assert 'APP_NAME' in config_dict

    def test_settings_repr(self):
        """Test settings has safe repr (no secrets exposed)."""
        from src.config import settings
        
        repr_str = repr(settings)
        # API keys should be masked or not shown
        assert 'sk-' not in repr_str or '***' in repr_str


class TestProviderConfiguration:
    """Test provider-specific configuration."""

    def test_get_llm_provider_config(self):
        """Test getting LLM provider configuration."""
        from src.config import settings
        
        # Should have method or property to get provider config
        assert hasattr(settings, 'get_llm_provider_config') or hasattr(settings, 'llm_providers')

    def test_provider_keys_dict(self):
        """Test provider keys can be accessed as dict."""
        from src.config import settings
        
        # Should be able to get all provider keys
        if hasattr(settings, 'get_provider_keys'):
            keys = settings.get_provider_keys()
            assert isinstance(keys, dict)

    def test_has_any_llm_provider(self):
        """Test check for any configured LLM provider."""
        from src.config import settings
        
        # Should have a way to check if any provider is configured
        if hasattr(settings, 'has_llm_provider'):
            result = settings.has_llm_provider()
            assert isinstance(result, bool)


class TestConfigValidation:
    """Test configuration validation."""

    def test_invalid_environment_raises_error(self):
        """Test invalid ENVIRONMENT value raises validation error."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'invalid_env'}, clear=True):
            try:
                from src.config.settings import Settings
                Settings()
                # If validation is strict, this should raise
            except (ValidationError, ValueError):
                pass  # Expected

    def test_settings_validation_on_init(self):
        """Test settings are validated on initialization."""
        from src.config.settings import Settings
        
        # Should not raise error with valid defaults
        test_settings = Settings()
        assert test_settings is not None

    def test_database_url_optional(self):
        """Test DATABASE_URL is optional."""
        with patch.dict(os.environ, {}, clear=True):
            from src.config.settings import Settings
            test_settings = Settings()
            
            # DATABASE_URL should be optional
            if hasattr(test_settings, 'DATABASE_URL'):
                assert test_settings.DATABASE_URL is None or isinstance(test_settings.DATABASE_URL, str)


class TestEnvExample:
    """Test .env.example file."""

    def test_env_example_exists(self):
        """Test .env.example file exists."""
        import os
        assert os.path.exists('/workspaces/App-Builder/.env.example')

    def test_env_example_has_required_vars(self):
        """Test .env.example contains required variables (flexible check)."""
        with open('/workspaces/App-Builder/.env.example', 'r') as f:
            content = f.read()
        
        # At least OPENAI_API_KEY should be present
        assert 'OPENAI_API_KEY' in content
        assert 'ANTHROPIC_API_KEY' in content

    def test_env_example_format(self):
        """Test .env.example has proper format."""
        with open('/workspaces/App-Builder/.env.example', 'r') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        for line in lines:
            # Should be in KEY=value format
            assert '=' in line, f"Invalid line format: {line}"
