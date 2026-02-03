"""API Versioning Module - Provides version routing and middleware."""
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.routing import APIRouter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Middleware to handle API version headers and routing."""

    def __init__(self, app, default_version: str = "v1"):
        super().__init__(app)
        self.default_version = default_version

    async def dispatch(self, request: Request, call_next):
        # Extract API version from header or URL path
        version = request.headers.get("X-API-Version")
        
        if not version:
            # Try to extract from path
            path_parts = request.url.path.split("/")
            if len(path_parts) >= 3 and path_parts[1] == "api" and path_parts[2].startswith("v"):
                version = path_parts[2]
            else:
                version = self.default_version

        # Add version to request state for later use
        request.state.api_version = version

        response = await call_next(request)
        
        # Add version header to response
        response.headers["X-API-Version"] = version
        
        return response


def create_versioned_router(prefix: str = "/api", version: str = "v1") -> APIRouter:
    """
    Create a versioned API router.
    
    Args:
        prefix: Base prefix for the API (default: /api)
        version: API version (default: v1)
    
    Returns:
        APIRouter configured for the specified version
    """
    return APIRouter(
        prefix=f"{prefix}/{version}",
        tags=[f"API {version.upper()}"]
    )


def get_api_version(request: Request) -> str:
    """
    Get the API version from request state.
    
    Args:
        request: FastAPI Request object
    
    Returns:
        API version string (e.g., "v1")
    """
    return getattr(request.state, 'api_version', 'v1')


class VersionNotSupportedError(Exception):
    """Raised when an unsupported API version is requested."""
    pass


from fastapi import Depends, HTTPException


def check_api_version(supported_versions: list[str]):
    """
    Dependency to check API version.
    
    Usage:
        @app.get("/endpoint", dependencies=[Depends(check_api_version(["v1", "v2"]))])
        async def my_endpoint():
            ...
    """
    def version_checker(request: Request):
        version = get_api_version(request)
        if version not in supported_versions:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "API version not supported",
                    "requested_version": version,
                    "supported_versions": supported_versions
                }
            )
        return version
    return version_checker


def add_versioning_to_app(app: FastAPI, default_version: str = "v1"):
    """
    Add API versioning middleware and headers to FastAPI app.
    
    Args:
        app: FastAPI application instance
        default_version: Default API version if none specified
    """
    app.add_middleware(APIVersionMiddleware, default_version=default_version)


# API Version configuration
CURRENT_VERSION = "v1"
SUPPORTED_VERSIONS = ["v1"]
DEPRECATED_VERSIONS: list[str] = []
