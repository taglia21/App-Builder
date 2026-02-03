"""API routes for app generation."""
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from .models import AppType, Feature, GenerationRequest, TechStack
from .service import AppGeneratorService

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
async def download_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Download generated app as ZIP file."""
    import io
    import zipfile

    from fastapi.responses import StreamingResponse

    # Get the generation from database
    result = await db.execute(
        select(Generation).where(Generation.id == generation_id)
    )
    generation = result.scalar_one_or_none()

    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")

    if not generation.generated_code:
        raise HTTPException(status_code=400, detail="No generated code available")

    # Create ZIP file in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        generated_files = generation.generated_code

        # Handle both dict and list formats
        if isinstance(generated_files, dict):
            files_to_add = generated_files.get('files', generated_files)
        else:
            files_to_add = generated_files

        # Add each file to the ZIP
        if isinstance(files_to_add, dict):
            for filepath, content in files_to_add.items():
                if isinstance(content, str):
                    zf.writestr(filepath, content)
                elif isinstance(content, dict) and 'content' in content:
                    zf.writestr(filepath, content['content'])
        elif isinstance(files_to_add, list):
            for file_entry in files_to_add:
                if isinstance(file_entry, dict):
                    filepath = file_entry.get('path', file_entry.get('filename', 'unnamed_file'))
                    content = file_entry.get('content', '')
                    zf.writestr(filepath, content)

    zip_buffer.seek(0)

    # Generate filename from project name or generation ID
    project_name = generation.generated_code.get('project_name', generation_id) if isinstance(generation.generated_code, dict) else generation_id
    filename = f"{project_name.replace(' ', '_')}_app.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
