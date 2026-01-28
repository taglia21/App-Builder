"""API routes for app generation."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import json
import logging

from .service import AppGeneratorService
from .models import GenerationRequest, AppType, TechStack, Feature

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate", tags=["generation"])
generator_service = AppGeneratorService()


@router.post("/")
async def start_generation(data: dict):
    """Start a new app generation."""
    try:
        # Parse the request
        request = GenerationRequest(
            project_name=data.get("project_name", "My App"),
            description=data.get("description", ""),
            app_type=AppType(data.get("app_type", "saas")),
            tech_stack=TechStack(data.get("tech_stack", "python-fastapi")),
            features=[Feature(f) for f in data.get("features", [])],
            user_id=data.get("user_id", "anonymous")
        )
        
        # Generate the app (blocking)
        app = await generator_service.generate_app(request)
        
        return {
            "status": "success",
            "id": app.id,
            "project_name": app.project_name,
            "files_count": len(app.files),
            "message": "App generated successfully"
        }
    
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{generation_id}")
async def generation_websocket(websocket: WebSocket, generation_id: str):
    """WebSocket for real-time generation progress."""
    await websocket.accept()
    
    try:
        # Wait for start message
        data = await websocket.receive_json()
        
        # Parse generation request
        request = GenerationRequest(
            id=generation_id,
            project_name=data.get("project_name", "My App"),
            description=data.get("description", ""),
            app_type=AppType(data.get("app_type", "saas")),
            tech_stack=TechStack(data.get("tech_stack", "python-fastapi")),
            features=[Feature(f) for f in data.get("features", [])],
            user_id=data.get("user_id", "anonymous")
        )
        
        # Stream generation progress
        async for progress in generator_service.generate_app_stream(request):
            await websocket.send_json({
                "step": progress.step,
                "progress": progress.progress,
                "message": progress.message,
                "files_generated": progress.files_generated,
                "total_files": progress.total_files
            })
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for generation {generation_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()


@router.get("/{generation_id}")
async def get_generation(generation_id: str):
    """Get a generated app by ID."""
    app = generator_service.get_generated_app(generation_id)
    
    if not app:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    return app.to_dict()


@router.get("/{generation_id}/files")
async def get_files(generation_id: str):
    """Get all files for a generated app."""
    app = generator_service.get_generated_app(generation_id)
    
    if not app:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    return {
        "files": [f.to_dict() for f in app.files]
    }


@router.get("/{generation_id}/download")
async def download_generation(generation_id: str):
    """Download generated app as ZIP (placeholder)."""
    # TODO: Implement ZIP creation and download
    raise HTTPException(status_code=501, detail="Download not yet implemented")
