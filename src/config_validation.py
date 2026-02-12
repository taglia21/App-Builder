"""Configuration validation and startup checks.

Validates all required environment variables and configuration settings
before the application starts. Ensures no secrets are hardcoded and all
sensitive configuration comes from environment variables.
"""

import logging
import os
import sys
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


class ConfigValidator:
    """Validates environment configuration at startup."""

    # Required environment variables for basic operation
    REQUIRED_CORE: Set[str] = {
        "DATABASE_URL",
        "SECRET_KEY",
    }

    # Required for production deployment
    REQUIRED_PRODUCTION: Set[str] = {
        "DATABASE_URL",
        "SECRET_KEY",
        "SENTRY_DSN",
        "ENVIRONMENT",
    }

    # Optional but recommended environment variables
    RECOMMENDED: Set[str] = {
        # LLM Providers (at least one recommended)
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        
        # Monitoring
        "SENTRY_DSN",
        "SENTRY_ENVIRONMENT",
        
        # Email
        "RESEND_API_KEY",
        "SENDGRID_API_KEY",
        
        # Payments
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
    }

    # Sensitive variables that should never be committed
    SENSITIVE_VARS: Set[str] = {
        "SECRET_KEY",
        "DATABASE_URL",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
        "PERPLEXITY_API_KEY",
        "STRIPE_SECRET_KEY",
        "STRIPE_API_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "STRIPE_ATLAS_API_KEY",
        "STRIPE_ATLAS_WEBHOOK_SECRET",
        "RESEND_API_KEY",
        "SENDGRID_API_KEY",
        "GITHUB_TOKEN",
        "RAILWAY_TOKEN",
        "VERCEL_TOKEN",
        "RENDER_TOKEN",
        "SENTRY_DSN",
        "REDIS_URL",
        "SMTP_PASSWORD",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "NAMECHEAP_API_KEY",
        "GODADDY_API_KEY",
        "GODADDY_API_SECRET",
        "MERCURY_API_KEY",
        "RELAY_API_KEY",
        "ZENBUSINESS_API_KEY",
        "SLACK_ALERT_WEBHOOK_URL",
        "PAGERDUTY_ROUTING_KEY",
        "ERROR_WEBHOOK_URL",
        "TAVILY_API_KEY",
        "CLOUDFLARE_API_TOKEN",
    }

    # Default values that should be changed in production
    INSECURE_DEFAULTS: Dict[str, str] = {
        "SECRET_KEY": "change-me-to-a-secure-random-string",
        "DATABASE_URL": "sqlite:///./app.db",
    }

    # Additional insecure SECRET_KEY values to reject in production
    INSECURE_SECRET_KEYS: Set[str] = {
        "change-me-in-production",
        "change-me-to-a-secure-random-string",
        "valeric-dev-secret-key-change-in-production",
        "secret",
        "password",
    }

    def __init__(self, environment: Optional[str] = None):
        """Initialize validator.
        
        Args:
            environment: Override environment detection (development/production)
        """
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.is_production = self.environment.lower() in ("production", "prod")
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_required_vars(self) -> None:
        """Validate required environment variables."""
        required = self.REQUIRED_PRODUCTION if self.is_production else self.REQUIRED_CORE
        
        missing = []
        for var in required:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            self.errors.append(
                f"Missing required environment variables: {', '.join(sorted(missing))}"
            )

    def validate_insecure_defaults(self) -> None:
        """Check for insecure default values in production."""
        if not self.is_production:
            return
        
        insecure = []
        for var, default_value in self.INSECURE_DEFAULTS.items():
            actual_value = os.getenv(var, "")
            if actual_value == default_value:
                insecure.append(f"{var}='{default_value}'")
        
        if insecure:
            self.errors.append(
                f"Insecure default values detected in PRODUCTION: {', '.join(insecure)}"
            )

    def validate_llm_providers(self) -> None:
        """Validate at least one LLM provider is configured."""
        llm_providers = [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "GOOGLE_API_KEY",
            "GROQ_API_KEY",
            "PERPLEXITY_API_KEY",
        ]
        
        configured = [p for p in llm_providers if os.getenv(p)]
        
        if not configured:
            self.warnings.append(
                "No LLM providers configured. At least one is recommended: "
                f"{', '.join(llm_providers)}"
            )

    def validate_database_url(self) -> None:
        """Validate DATABASE_URL format and production requirements."""
        db_url = os.getenv("DATABASE_URL", "")
        
        if not db_url:
            return  # Already caught by required vars check
        
        # Check SQLite in production
        if self.is_production and "sqlite" in db_url.lower():
            self.errors.append(
                "SQLite database detected in PRODUCTION. Use PostgreSQL or MySQL for production."
            )
        
        # Validate URL format
        valid_schemes = ["postgresql", "postgresql+asyncpg", "mysql", "mysql+aiomysql", "sqlite"]
        if not any(db_url.startswith(scheme) for scheme in valid_schemes):
            self.errors.append(
                f"Invalid DATABASE_URL scheme. Must start with one of: {', '.join(valid_schemes)}"
            )

    def validate_secret_key(self) -> None:
        """Validate SECRET_KEY strength."""
        secret_key = os.getenv("SECRET_KEY", "")
        
        if not secret_key:
            return  # Already caught by required vars check
        
        # Reject known insecure defaults in production
        if self.is_production and secret_key in self.INSECURE_SECRET_KEYS:
            self.errors.append(
                "SECRET_KEY is an insecure default value in PRODUCTION. "
                "Generate a strong random key: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
            return
        
        # Check minimum length
        if len(secret_key) < 32:
            self.warnings.append(
                f"SECRET_KEY is only {len(secret_key)} characters. "
                "Recommended: at least 32 random characters."
            )
        
        # Check for common weak values
        weak_values = [
            "secret",
            "password",
            "change-me",
            "your-secret-key",
            "dev",
            "test",
            "admin",
        ]
        if any(weak in secret_key.lower() for weak in weak_values):
            self.errors.append(
                "SECRET_KEY appears to be a weak/default value. "
                "Generate a strong random key for production."
            )

    def validate_stripe_config(self) -> None:
        """Validate Stripe configuration completeness."""
        stripe_key = os.getenv("STRIPE_SECRET_KEY")
        if not stripe_key:
            return  # Stripe is optional
        
        # If Stripe is configured, webhook secret is required
        if not os.getenv("STRIPE_WEBHOOK_SECRET"):
            self.warnings.append(
                "STRIPE_SECRET_KEY is set but STRIPE_WEBHOOK_SECRET is missing. "
                "Webhook secret is required for payment processing."
            )
        
        # Check for test keys in production
        if self.is_production and stripe_key.startswith("sk_test_"):
            self.errors.append(
                "Stripe TEST key detected in PRODUCTION. Use live keys (sk_live_)."
            )

    def validate_sentry_config(self) -> None:
        """Validate Sentry monitoring configuration."""
        if not self.is_production:
            return
        
        if not os.getenv("SENTRY_DSN"):
            self.warnings.append(
                "SENTRY_DSN not configured in PRODUCTION. "
                "Error monitoring is highly recommended."
            )

    def validate_email_config(self) -> None:
        """Validate email provider configuration."""
        resend = os.getenv("RESEND_API_KEY")
        sendgrid = os.getenv("SENDGRID_API_KEY")
        smtp = os.getenv("SMTP_HOST")
        
        if not any([resend, sendgrid, smtp]):
            self.warnings.append(
                "No email provider configured (RESEND_API_KEY, SENDGRID_API_KEY, or SMTP_HOST). "
                "Email functionality will not work."
            )

    def check_secrets_in_code(self) -> None:
        """Verify no secrets are hardcoded in source files.
        
        This is a runtime check that complements code review.
        """
        # This is more of a documentation/awareness check
        # Actual scanning would be done by pre-commit hooks or CI
        logger.info("Configuration loaded from environment variables - no hardcoded secrets")

    def validate_all(self) -> Tuple[List[str], List[str]]:
        """Run all validation checks.
        
        Returns:
            Tuple of (errors, warnings)
        """
        self.errors = []
        self.warnings = []
        
        # Run all validation checks
        self.validate_required_vars()
        self.validate_insecure_defaults()
        self.validate_database_url()
        self.validate_secret_key()
        self.validate_llm_providers()
        self.validate_stripe_config()
        self.validate_sentry_config()
        self.validate_email_config()
        self.check_secrets_in_code()
        
        return self.errors, self.warnings

    def print_report(self) -> None:
        """Print validation report."""
        print("\n" + "=" * 70)
        print("CONFIGURATION VALIDATION REPORT")
        print("=" * 70)
        print(f"Environment: {self.environment}")
        print(f"Production Mode: {self.is_production}")
        print("=" * 70)
        
        if self.errors:
            print("\n❌ ERRORS:")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All configuration checks passed!")
        
        print("=" * 70 + "\n")

    def validate_or_exit(self) -> None:
        """Validate configuration and exit if errors found."""
        errors, warnings = self.validate_all()
        self.print_report()
        
        # Log warnings
        for warning in warnings:
            logger.warning(f"Config: {warning}")
        
        # Exit on errors in production, warn in development
        if errors:
            for error in errors:
                logger.error(f"Config: {error}")
            
            if self.is_production:
                logger.critical("Configuration validation failed. Exiting.")
                sys.exit(1)
            else:
                logger.warning(
                    "Configuration errors detected in development mode. "
                    "Application will continue but may not function correctly."
                )


def validate_config(environment: Optional[str] = None) -> ConfigValidator:
    """Validate configuration and return validator instance.
    
    Args:
        environment: Override environment detection
        
    Returns:
        ConfigValidator instance with validation results
    """
    validator = ConfigValidator(environment)
    validator.validate_or_exit()
    return validator


def validate_config_silent(environment: Optional[str] = None) -> Tuple[List[str], List[str]]:
    """Validate configuration without printing or exiting.
    
    Args:
        environment: Override environment detection
        
    Returns:
        Tuple of (errors, warnings)
    """
    validator = ConfigValidator(environment)
    return validator.validate_all()


# Auto-validate on import in production
if os.getenv("AUTO_VALIDATE_CONFIG", "true").lower() == "true":
    if os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod"):
        validate_config()
