"""
FastAPI routes for the Multi-Agent Orchestrator.

Provides endpoints for:
- App generation with multi-agent validation
- Generation status/stats
- Health checks for the agent system
"""

from typing import Optional, List
import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from .api_integration import (
    MultiAgentService, 
    AppGenerationRequest,
    AppGenerationResponse
)

logger = logging.getLogger(__name__)

# Create router for multi-agent endpoints
multi_agent_router = APIRouter(
    prefix="/api/v2",  # v2 to distinguish from existing endpoints
    tags=["multi-agent"]
)


class GenerateRequest(BaseModel):
    """Request body for app generation."""
    description: str
    tech_stack: Optional[str] = None
    features: Optional[List[str]] = None


@multi_agent_router.post("/generate", response_model=AppGenerationResponse)
async def generate_app_v2(request: GenerateRequest):
    """
    Generate an app using the multi-agent orchestrator.
    
    This endpoint uses the "Team of Rivals" architecture with:
    - PlannerAgent: Creates execution plans with acceptance criteria
    - CodeWriterAgent: Generates application code
    - CodeCritic: Validates syntax, security, best practices
    - OutputCritic: Validates against acceptance criteria
    
    The code goes through multiple validation rounds before being
    returned to ensure quality.
    """
    service = MultiAgentService.get_instance()
    
    gen_request = AppGenerationRequest(
        description=request.description,
        tech_stack=request.tech_stack,
        features=request.features
    )
    
    return await service.generate_app(gen_request)


@multi_agent_router.get("/stats")
async def get_orchestrator_stats():
    """
    Get statistics from the last orchestration run.
    
    Returns:
    - session_id: Unique ID for the generation session
    - status: Current status (pending/in_progress/completed/failed/vetoed)
    - retry_count: Number of retries attempted
    - total_reviews: Total critic reviews performed
    - approvals: Number of approvals from critics
    - rejections: Number of rejections from critics
    """
    service = MultiAgentService.get_instance()
    stats = service.orchestrator.get_stats()
    
    if not stats:
        return {"message": "No generation has been run yet"}
    
    return stats


@multi_agent_router.get("/health")
async def health_check():
    """
    Health check for the multi-agent system.
    
    Verifies that all components are properly initialized.
    """
    try:
        service = MultiAgentService.get_instance()
        
        return {
            "status": "healthy",
            "components": {
                "orchestrator": "initialized",
                "planner": "initialized",
                "code_writer": "initialized",
                "code_critic": "initialized",
                "output_critic": "initialized"
            },
            "llm_provider": service.llm_provider.provider,
            "llm_model": service.llm_provider.model
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "error": str(e)}
        )


@multi_agent_router.get("/info")
async def system_info():
    """
    Get information about the multi-agent system.
    
    Returns documentation about the architecture and capabilities.
    """
    return {
        "name": "LaunchForge Multi-Agent System",
        "version": "1.0.0",
        "architecture": "Team of Rivals (Organizational Intelligence)",
        "paper": "If You Want Coherence, Orchestrate a Team of Rival Multi-Agent Models",
        "components": {
            "PlannerAgent": {
                "role": "Creates execution plans with pre-declared acceptance criteria",
                "key_principle": "Define success criteria BEFORE execution"
            },
            "CodeWriterAgent": {
                "role": "Generates application code based on execution plans",
                "key_principle": "Produce artifacts for validation, not immediate execution"
            },
            "CodeCritic": {
                "role": "Validates code for syntax, security, and best practices",
                "key_principle": "VETO AUTHORITY - can reject code that fails validation"
            },
            "OutputCritic": {
                "role": "Validates that code meets acceptance criteria",
                "key_principle": "ALL criteria must be MET for approval"
            }
        },
        "key_features": [
            "Pre-declared acceptance criteria",
            "Veto authority for critics",
            "Iterative improvement with feedback",
            "Checkpointing for state persistence",
            "92% internal error interception (per paper)"
        ]
    }
