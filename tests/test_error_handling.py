"""Tests for error handling and logging."""
import pytest
import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestExceptions:
    """Test custom exception classes."""

    def test_app_error_exists(self):
        """Test AppError exception exists."""
        from src.core.exceptions import AppError
        assert AppError is not None

    def test_validation_error_exists(self):
        """Test ValidationError exception exists."""
        from src.core.exceptions import ValidationError
        assert ValidationError is not None

    def test_provider_error_exists(self):
        """Test ProviderError exception exists."""
        from src.core.exceptions import ProviderError
        assert ProviderError is not None

    def test_app_error_creation(self):
        """Test creating AppError with message."""
        from src.core.exceptions import AppError
        
        error = AppError("Test error")
        assert str(error) == "Test error"

    def test_validation_error_with_details(self):
        """Test ValidationError with field details."""
        from src.core.exceptions import ValidationError
        
        error = ValidationError("Invalid input", field="email")
        assert "Invalid input" in str(error)

    def test_provider_error_with_provider_name(self):
        """Test ProviderError with provider information."""
        from src.core.exceptions import ProviderError
        
        error = ProviderError("API failed", provider="openai")
        assert "API failed" in str(error)


class TestLogging:
    """Test logging configuration."""

    def test_setup_logging_function_exists(self):
        """Test setup_logging function exists."""
        from src.core.logging import setup_logging
        assert callable(setup_logging)

    def test_setup_logging_creates_logger(self):
        """Test setup_logging creates configured logger."""
        from src.core.logging import setup_logging
        
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)

    def test_get_logger_function(self):
        """Test get_logger returns logger instance."""
        from src.core.logging import get_logger
        
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)

    def test_logger_has_handlers(self):
        """Test logger has configured handlers."""
        from src.core.logging import setup_logging
        
        logger = setup_logging()
        # Should have at least one handler
        assert len(logger.handlers) > 0 or len(logging.root.handlers) > 0

    def test_log_levels(self):
        """Test logging at different levels."""
        from src.core.logging import get_logger
        
        logger = get_logger("test")
        
        # Should not raise errors
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")


class TestErrorHandler:
    """Test FastAPI error handler middleware."""

    def test_error_handler_middleware_exists(self):
        """Test error handler middleware exists."""
        from src.middleware.error_handler import error_handler_middleware
        assert error_handler_middleware is not None

    def test_app_error_exception_handler(self):
        """Test AppError exception handler."""
        from src.middleware.error_handler import app_error_exception_handler
        assert callable(app_error_exception_handler)

    def test_validation_error_exception_handler(self):
        """Test ValidationError exception handler."""
        from src.middleware.error_handler import validation_error_exception_handler
        assert callable(validation_error_exception_handler)

    def test_general_exception_handler(self):
        """Test general exception handler."""
        from src.middleware.error_handler import general_exception_handler
        assert callable(general_exception_handler)


class TestErrorHandlerIntegration:
    """Test error handler integration with FastAPI."""

    def test_app_error_returns_400(self):
        """Test AppError returns 400 status code."""
        from fastapi import FastAPI, HTTPException
        from fastapi.testclient import TestClient
        from src.core.exceptions import AppError
        from src.middleware.error_handler import add_exception_handlers
        
        app = FastAPI()
        add_exception_handlers(app)
        
        @app.get("/test-app-error")
        def trigger_app_error():
            raise AppError("Test app error")
        
        client = TestClient(app)
        response = client.get("/test-app-error")
        
        assert response.status_code == 400
        assert "error" in response.json()

    def test_validation_error_returns_422(self):
        """Test ValidationError returns 422 status code."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.core.exceptions import ValidationError
        from src.middleware.error_handler import add_exception_handlers
        
        app = FastAPI()
        add_exception_handlers(app)
        
        @app.get("/test-validation-error")
        def trigger_validation_error():
            raise ValidationError("Invalid field", field="email")
        
        client = TestClient(app)
        response = client.get("/test-validation-error")
        
        assert response.status_code == 422
        assert "error" in response.json()

    def test_provider_error_returns_502(self):
        """Test ProviderError returns 502 status code."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.core.exceptions import ProviderError
        from src.middleware.error_handler import add_exception_handlers
        
        app = FastAPI()
        add_exception_handlers(app)
        
        @app.get("/test-provider-error")
        def trigger_provider_error():
            raise ProviderError("Provider failed", provider="openai")
        
        client = TestClient(app)
        response = client.get("/test-provider-error")
        
        assert response.status_code == 502
        assert "error" in response.json()

    def test_generic_exception_returns_500(self):
        """Test generic exceptions return 500 status code."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.middleware.error_handler import add_exception_handlers
        
        app = FastAPI()
        add_exception_handlers(app)
        
        @app.get("/test-generic-error")
        def trigger_generic_error():
            raise ValueError("Unexpected error")
        
        client = TestClient(app)
        response = client.get("/test-generic-error")
        
        assert response.status_code == 500
        assert "error" in response.json()

    def test_error_response_structure(self):
        """Test error response has consistent structure."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.core.exceptions import AppError
        from src.middleware.error_handler import add_exception_handlers
        
        app = FastAPI()
        add_exception_handlers(app)
        
        @app.get("/test-error")
        def trigger_error():
            raise AppError("Test error")
        
        client = TestClient(app)
        response = client.get("/test-error")
        
        data = response.json()
        assert "error" in data
        assert "message" in data or "detail" in data
