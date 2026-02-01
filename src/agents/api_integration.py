"""
API Integration for the Multi-Agent Orchestrator.

Provides a clean interface between FastAPI routes and the
organizational intelligence system.
"""

from typing import Any, Dict, List, Optional
import logging
import os

from fastapi import HTTPException
from pydantic import BaseModel

from .orchestrator import AIOfficeOrchestrator
from .base import LLMProvider
from .messages import GeneratedCode, OrchestrationState, TaskStatus

logger = logging.getLogger(__name__)


class AppGenerationRequest(BaseModel):
    """Request model for app generation API."""
    description: str
    tech_stack: Optional[str] = None
    features: Optional[List[str]] = None
    use_multi_agent: bool = True  # Flag to enable/disable multi-agent


class AppGenerationResponse(BaseModel):
    """Response model for app generation API."""
    status: str
    message: str
    files: Dict[str, str]
    tech_stack: str
    dependencies: List[str]
    execution_instructions: Optional[str] = None
    orchestration_stats: Optional[Dict[str, Any]] = None


class MultiAgentService:
    """
    Service class for multi-agent app generation.
    
    Manages the orchestrator lifecycle and provides
    methods for the API layer.
    """
    
    _instance: Optional['MultiAgentService'] = None
    
    def __init__(self):
        # Initialize LLM provider from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.llm_provider = LLMProvider(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            api_key=api_key
        )
        self.orchestrator = AIOfficeOrchestrator(
            llm_provider=self.llm_provider,
            max_retries=3
        )
    
    @classmethod
    def get_instance(cls) -> 'MultiAgentService':
        """Get singleton instance of the service."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def generate_app(
        self,
        request: AppGenerationRequest
    ) -> AppGenerationResponse:
        """
        Generate an app using the multi-agent orchestrator.
        
        This is the main entry point from the API layer.
        """
        try:
            logger.info(f"Starting multi-agent app generation: {request.description[:50]}...")
            
            # Call the orchestrator
            code, state = await self.orchestrator.generate_app(
                description=request.description,
                tech_stack=request.tech_stack,
                features=request.features
            )
            
            # Get stats for monitoring
            stats = self.orchestrator.get_stats()
            
            return AppGenerationResponse(
                status="success",
                message="App generated successfully with multi-agent validation",
                files=code.files,
                tech_stack=code.tech_stack,
                dependencies=code.dependencies,
                execution_instructions=code.execution_instructions,
                orchestration_stats=stats
            )
            
        except ValueError as e:
            # Validation failures (vetoed after max retries)
            logger.warning(f"App generation vetoed: {e}")
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "generation_vetoed",
                    "message": str(e),
                    "stats": self.orchestrator.get_stats()
                }
            )
        except Exception as e:
            logger.error(f"App generation failed: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "generation_failed",
                    "message": str(e)
                }
            )


# Convenience function for route handlers
async def generate_app_with_agents(
    description: str,
    tech_stack: Optional[str] = None,
    features: Optional[List[str]] = None
) -> AppGenerationResponse:
    """Convenience function for generating apps with multi-agent system."""
    service = MultiAgentService.get_instance()
    request = AppGenerationRequest(
        description=description,
        tech_stack=tech_stack,
        features=features
    )
    return await service.generate_app(request)
