"""Health and monitoring endpoints."""
from datetime import datetime, UTC
from typing import Dict, Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from src.config.settings import settings

router = APIRouter(tags=["health", "monitoring"])


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str
    version: str
    timestamp: str
    checks: Dict[str, Any]


class ReadinessResponse(BaseModel):
    """Readiness check response model."""
    
    status: str
    checks: Dict[str, Any]
    timestamp: str


class LivenessResponse(BaseModel):
    """Liveness check response model."""
    
    status: str
    timestamp: str


def check_llm_providers() -> Dict[str, bool]:
    """Check which LLM providers are configured.
    
    Returns:
        Dict mapping provider names to availability
    """
    providers = {}
    
    # Check each provider
    if settings.OPENAI_API_KEY:
        providers["openai"] = True
    
    if settings.ANTHROPIC_API_KEY:
        providers["anthropic"] = True
    
    if settings.GOOGLE_API_KEY:
        providers["google"] = True
    
    if settings.PERPLEXITY_API_KEY:
        providers["perplexity"] = True
    
    if settings.GROQ_API_KEY:
        providers["groq"] = True
    
    return providers


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.
    
    Returns overall health status and basic system information.
    Used for general health monitoring.
    
    Returns:
        Health status with version and checks
    """
    providers = check_llm_providers()
    
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(UTC).isoformat(),
        checks={
            "llm_providers": providers,
            "demo_mode": settings.DEMO_MODE,
            "environment": settings.ENVIRONMENT
        }
    )


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness_check(response: Response) -> ReadinessResponse:
    """Readiness check endpoint for Kubernetes.
    
    Checks if the application is ready to accept traffic.
    Returns ready if at least one LLM provider is configured.
    
    Returns:
        Readiness status with provider checks
    """
    providers = check_llm_providers()
    
    # Ready if at least one provider is available or demo mode is enabled
    is_ready = len(providers) > 0 or settings.DEMO_MODE
    
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        checks={
            "llm_providers": providers,
            "has_providers": len(providers) > 0,
            "demo_mode": settings.DEMO_MODE
        },
        timestamp=datetime.now(UTC).isoformat()
    )


@router.get("/health/live", response_model=LivenessResponse, status_code=status.HTTP_200_OK)
async def liveness_check() -> LivenessResponse:
    """Liveness check endpoint for Kubernetes.
    
    Indicates if the application process is alive.
    Always returns alive if the endpoint responds.
    
    Returns:
        Liveness status
    """
    return LivenessResponse(
        status="alive",
        timestamp=datetime.now(UTC).isoformat()
    )
