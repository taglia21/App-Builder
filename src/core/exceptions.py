"""Custom exceptions for Valeric."""


class AppError(Exception):
    """Base application error."""
    
    def __init__(self, message: str, **kwargs):
        """Initialize AppError.
        
        Args:
            message: Error message
            **kwargs: Additional context
        """
        self.message = message
        self.context = kwargs
        super().__init__(message)
    
    def __str__(self) -> str:
        return self.message


class ValidationError(AppError):
    """Validation error for input data."""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        """Initialize ValidationError.
        
        Args:
            message: Error message
            field: Field name that failed validation
            **kwargs: Additional context
        """
        self.field = field
        super().__init__(message, field=field, **kwargs)
    
    def __str__(self) -> str:
        if self.field:
            return f"{self.message} (field: {self.field})"
        return self.message


class ProviderError(AppError):
    """Error from external provider (LLM, deployment, etc)."""
    
    def __init__(self, message: str, provider: str = None, **kwargs):
        """Initialize ProviderError.
        
        Args:
            message: Error message
            provider: Provider name (openai, anthropic, etc)
            **kwargs: Additional context
        """
        self.provider = provider
        super().__init__(message, provider=provider, **kwargs)
    
    def __str__(self) -> str:
        if self.provider:
            return f"{self.message} (provider: {self.provider})"
        return self.message


class ConfigurationError(AppError):
    """Configuration error."""
    pass


class AuthenticationError(AppError):
    """Authentication error."""
    pass


class AuthorizationError(AppError):
    """Authorization error."""
    pass
