"""Tests for configuration validation.

Tests the ConfigValidator to ensure proper validation of:
- Required environment variables
- Insecure default detection
- Database URL validation
- Secret key strength
- Stripe configuration
- LLM provider configuration
"""

import os
from unittest.mock import patch

import pytest

from src.config_validation import ConfigValidator, validate_config_silent


@pytest.fixture
def clean_env(monkeypatch):
    """Clear all environment variables for testing."""
    # Clear all env vars that might affect tests
    env_vars_to_clear = [
        "DATABASE_URL",
        "SECRET_KEY",
        "ENVIRONMENT",
        "SENTRY_DSN",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "RESEND_API_KEY",
        "SENDGRID_API_KEY",
        "SMTP_HOST",
    ]
    for var in env_vars_to_clear:
        monkeypatch.delenv(var, raising=False)


def test_validator_initialization():
    """Test ConfigValidator can be initialized."""
    validator = ConfigValidator()
    assert validator is not None
    assert validator.environment in ("development", "production")


def test_validator_detects_production_mode():
    """Test production mode detection."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        validator = ConfigValidator()
        assert validator.is_production is True
    
    with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
        validator = ConfigValidator()
        assert validator.is_production is False


def test_missing_required_core_vars(clean_env):
    """Test detection of missing required variables."""
    validator = ConfigValidator(environment="development")
    errors, warnings = validator.validate_all()
    
    # Should error on missing DATABASE_URL and SECRET_KEY
    assert len(errors) > 0
    assert any("DATABASE_URL" in error for error in errors)


def test_missing_required_production_vars(clean_env):
    """Test detection of missing production variables."""
    validator = ConfigValidator(environment="production")
    errors, warnings = validator.validate_all()
    
    # Should error on missing production requirements
    assert len(errors) > 0
    assert any("SENTRY_DSN" in error or "required" in error.lower() for error in errors)


def test_valid_core_configuration():
    """Test valid core configuration passes."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://localhost/test",
        "SECRET_KEY": "a" * 32,  # Strong 32-char key
        "ENVIRONMENT": "development",
    }):
        validator = ConfigValidator(environment="development")
        errors, _ = validator.validate_all()
        
        # Should have no critical errors with valid config
        assert not any("DATABASE_URL" in e or "SECRET_KEY" in e for e in errors)


def test_insecure_defaults_in_production():
    """Test detection of insecure defaults in production."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "sqlite:///./app.db",
        "SECRET_KEY": "change-me-to-a-secure-random-string",
        "ENVIRONMENT": "production",
        "SENTRY_DSN": "https://test@sentry.io/123",
    }):
        validator = ConfigValidator(environment="production")
        errors, _ = validator.validate_all()
        
        # Should error on insecure defaults in production
        assert len(errors) > 0
        assert any("Insecure default" in error for error in errors)


def test_insecure_defaults_allowed_in_dev():
    """Test insecure defaults allowed in development."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "sqlite:///./app.db",
        "SECRET_KEY": "change-me-to-a-secure-random-string",
        "ENVIRONMENT": "development",
    }):
        validator = ConfigValidator(environment="development")
        validator.validate_insecure_defaults()
        
        # Should NOT error in development
        assert not any("Insecure default" in error for error in validator.errors)


def test_sqlite_rejected_in_production():
    """Test SQLite database rejected in production."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "sqlite+aiosqlite:///./prod.db",
        "SECRET_KEY": "very-secure-production-key-with-enough-chars",
        "ENVIRONMENT": "production",
        "SENTRY_DSN": "https://test@sentry.io/123",
    }):
        validator = ConfigValidator(environment="production")
        errors, _ = validator.validate_all()
        
        assert any("SQLite" in error and "PRODUCTION" in error for error in errors)


def test_postgresql_accepted():
    """Test PostgreSQL database URLs are accepted."""
    valid_urls = [
        "postgresql://localhost/db",
        "postgresql+asyncpg://user:pass@host:5432/db",
    ]
    
    for db_url in valid_urls:
        with patch.dict(os.environ, {
            "DATABASE_URL": db_url,
            "SECRET_KEY": "a" * 32,
            "ENVIRONMENT": "development",
        }):
            validator = ConfigValidator()
            validator.validate_database_url()
            
            assert not any("Invalid DATABASE_URL" in error for error in validator.errors)


def test_invalid_database_url_scheme():
    """Test invalid database URL schemes are rejected."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "mongodb://localhost/db",  # Invalid scheme
        "SECRET_KEY": "a" * 32,
    }):
        validator = ConfigValidator()
        validator.validate_database_url()
        
        assert any("Invalid DATABASE_URL scheme" in error for error in validator.errors)


def test_weak_secret_key():
    """Test weak secret keys are detected."""
    weak_keys = [
        "short",  # Too short
        "this-is-a-password-string-but-weak",  # Contains 'password'
        "change-me-to-something-better",  # Contains 'change-me'
        "dev-secret-key-for-development",  # Contains 'dev'
    ]
    
    for weak_key in weak_keys:
        with patch.dict(os.environ, {
            "SECRET_KEY": weak_key,
            "DATABASE_URL": "postgresql://localhost/db",
        }):
            validator = ConfigValidator()
            validator.validate_secret_key()
            
            # Should have error or warning
            assert len(validator.errors) > 0 or len(validator.warnings) > 0


def test_strong_secret_key():
    """Test strong secret key passes validation."""
    strong_key = "k8#mP2$vN9@qR7!xL4^tY6&wZ3*eF5%aS1"
    
    with patch.dict(os.environ, {
        "SECRET_KEY": strong_key,
        "DATABASE_URL": "postgresql://localhost/db",
    }):
        validator = ConfigValidator()
        validator.validate_secret_key()
        
        # Should have no errors about secret key
        assert not any("SECRET_KEY" in error for error in validator.errors)


def test_llm_provider_warning():
    """Test warning when no LLM providers configured."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://localhost/db",
        "SECRET_KEY": "a" * 32,
    }, clear=True):
        validator = ConfigValidator()
        validator.validate_llm_providers()
        
        assert any("LLM" in warning for warning in validator.warnings)


def test_llm_provider_configured():
    """Test no warning when LLM provider is configured."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://localhost/db",
        "SECRET_KEY": "a" * 32,
        "ANTHROPIC_API_KEY": "sk-ant-test123",
    }):
        validator = ConfigValidator()
        validator.validate_llm_providers()
        
        assert not any("LLM" in warning for warning in validator.warnings)


def test_stripe_webhook_secret_warning():
    """Test warning when Stripe key set but no webhook secret."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://localhost/db",
        "SECRET_KEY": "a" * 32,
        "STRIPE_SECRET_KEY": "sk_test_123",
    }):
        validator = ConfigValidator()
        validator.validate_stripe_config()
        
        assert any("STRIPE_WEBHOOK_SECRET" in warning for warning in validator.warnings)


def test_stripe_test_key_in_production():
    """Test error when Stripe test key used in production."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://localhost/db",
        "SECRET_KEY": "a" * 32,
        "STRIPE_SECRET_KEY": "sk_test_123456789",
        "ENVIRONMENT": "production",
        "SENTRY_DSN": "https://test@sentry.io/123",
    }):
        validator = ConfigValidator(environment="production")
        validator.validate_stripe_config()
        
        assert any("TEST key" in error and "PRODUCTION" in error for error in validator.errors)


def test_stripe_live_key_accepted():
    """Test Stripe live keys accepted in production."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://localhost/db",
        "SECRET_KEY": "a" * 32,
        "STRIPE_SECRET_KEY": "sk_live_123456789",
        "STRIPE_WEBHOOK_SECRET": "whsec_test",
        "ENVIRONMENT": "production",
        "SENTRY_DSN": "https://test@sentry.io/123",
    }):
        validator = ConfigValidator(environment="production")
        validator.validate_stripe_config()
        
        assert not any("Stripe" in error for error in validator.errors)


def test_sentry_warning_in_production():
    """Test warning when Sentry not configured in production."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://localhost/db",
        "SECRET_KEY": "a" * 32,
        "ENVIRONMENT": "production",
    }):
        validator = ConfigValidator(environment="production")
        validator.validate_sentry_config()
        
        assert any("SENTRY_DSN" in warning for warning in validator.warnings)


def test_email_provider_warning():
    """Test warning when no email provider configured."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://localhost/db",
        "SECRET_KEY": "a" * 32,
    }, clear=True):
        validator = ConfigValidator()
        validator.validate_email_config()
        
        assert any("email" in warning.lower() for warning in validator.warnings)


def test_email_provider_configured():
    """Test no warning when email provider configured."""
    email_configs = [
        {"RESEND_API_KEY": "re_test"},
        {"SENDGRID_API_KEY": "SG.test"},
        {"SMTP_HOST": "smtp.gmail.com"},
    ]
    
    for config in email_configs:
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql://localhost/db",
            "SECRET_KEY": "a" * 32,
            **config,
        }):
            validator = ConfigValidator()
            validator.validate_email_config()
            
            # Should not warn about email if any provider configured
            assert not any("email provider" in warning.lower() for warning in validator.warnings)


def test_validate_config_silent():
    """Test silent validation returns errors and warnings."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://localhost/db",
        "SECRET_KEY": "a" * 32,
    }):
        errors, warnings = validate_config_silent(environment="development")
        
        assert isinstance(errors, list)
        assert isinstance(warnings, list)


def test_sensitive_vars_defined():
    """Test SENSITIVE_VARS set is comprehensive."""
    validator = ConfigValidator()
    
    # Should include common sensitive variables
    assert "SECRET_KEY" in validator.SENSITIVE_VARS
    assert "DATABASE_URL" in validator.SENSITIVE_VARS
    assert "STRIPE_SECRET_KEY" in validator.SENSITIVE_VARS
    assert "ANTHROPIC_API_KEY" in validator.SENSITIVE_VARS
    assert len(validator.SENSITIVE_VARS) >= 20  # Should have many entries


def test_print_report_no_crash():
    """Test print_report doesn't crash."""
    with patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://localhost/db",
        "SECRET_KEY": "a" * 32,
    }):
        validator = ConfigValidator()
        validator.validate_all()
        
        # Should not raise exception
        validator.print_report()
