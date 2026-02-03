"""Error handler middleware for FastAPI."""
import logging
import traceback
import uuid
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.exceptions import AppError, ValidationError, ProviderError

logger = logging.getLogger(__name__)


async def error_handler_middleware(request: Request, call_next):
    """Middleware to add request ID and handle errors.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/handler
        
    Returns:
        Response
    """
    # Generate request ID
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        logger.error(
            f"Unhandled exception in request {request_id}: {exc}",
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": str(exc),
                "request_id": request_id
            }
        )


async def app_error_exception_handler(request: Request, exc: AppError):
    """Handle AppError exceptions.
    
    Args:
        request: FastAPI request
        exc: AppError exception
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(f"AppError in request {request_id}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Application Error",
            "message": exc.message,
            "request_id": request_id,
            **exc.context
        }
    )


async def validation_error_exception_handler(request: Request, exc: ValidationError):
    """Handle ValidationError exceptions.
    
    Args:
        request: FastAPI request
        exc: ValidationError exception
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(f"ValidationError in request {request_id}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": exc.message,
            "field": exc.field,
            "request_id": request_id
        }
    )


async def provider_error_exception_handler(request: Request, exc: ProviderError):
    """Handle ProviderError exceptions.
    
    Args:
        request: FastAPI request
        exc: ProviderError exception
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(f"ProviderError in request {request_id}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": "Provider Error",
            "message": exc.message,
            "provider": exc.provider,
            "request_id": request_id
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions.
    
    Args:
        request: FastAPI request
        exc: Exception
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Unhandled exception in request {request_id}: {exc}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "request_id": request_id
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTPException from Starlette.
    
    Args:
        request: FastAPI request
        exc: HTTPException
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "detail": exc.detail,
            "request_id": request_id
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle RequestValidationError from FastAPI.
    
    Args:
        request: FastAPI request
        exc: RequestValidationError
        
    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", "unknown")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": exc.errors(),
            "request_id": request_id
        }
    )


def add_exception_handlers(app: FastAPI):
    """Add all exception handlers to FastAPI app.
    
    Args:
        app: FastAPI application
    """
    # Custom exception handlers
    app.add_exception_handler(AppError, app_error_exception_handler)
    app.add_exception_handler(ValidationError, validation_error_exception_handler)
    app.add_exception_handler(ProviderError, provider_error_exception_handler)
    
    # Built-in exception handlers
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    # Add middleware
    app.middleware("http")(error_handler_middleware)
