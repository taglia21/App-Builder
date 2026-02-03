"""
App Generation API - Handles generating full app codebases from ideas.
"""

# Import code generation modules
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

sys.path.insert(0, str(Path(__file__).parent.parent))

from code_generation.enhanced_engine import EnhancedCodeGenerator
from models import ProductPrompt, StartupIdea

# Store for generated projects
_generated_projects = {}


async def generate_app(request: Request) -> JSONResponse:
    """
    Generate a full app codebase from a project idea.

    Expected JSON body:
    {
        "project_id": "abc123",
        "idea": "AI tool that helps real estate agents...",
        "features": ["feature1", "feature2"],
        "theme": "Modern"  # optional
    }
    """
    try:
        body = await request.json()
        project_id = body.get('project_id')
        idea = body.get('idea', '').strip()
        body.get('features', [])
        theme = body.get('theme', 'Modern')

        if not idea:
            return JSONResponse(
                {'error': 'Please provide your business idea'},
                status_code=400
            )

        # Create a ProductPrompt from the idea
        startup_idea = StartupIdea(
            name=f"Project_{project_id or 'new'}",
            description=idea,
            target_market="B2B SaaS",
            pain_points=[],
            emerging_industries=[],
            opportunity_categories=[],
            competitor_analysis=[]
        )

        prompt = ProductPrompt(
            ideas=[startup_idea]
        )

        # Initialize the code generator
        generator = EnhancedCodeGenerator()

        # Generate the codebase
        output_dir = Path(f"/tmp/generated_apps/{project_id or uuid.uuid4().hex[:8]}")
        output_dir.mkdir(parents=True, exist_ok=True)

        generated = generator.generate(
            prompt=prompt,
            output_dir=str(output_dir),
            theme=theme
        )

        # Store the generation result
        result = {
            'project_id': project_id or generated.project_name,
            'status': 'generated',
            'output_dir': str(output_dir),
            'files_count': len(generated.files) if hasattr(generated, 'files') else 0,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'download_ready': True
        }

        _generated_projects[project_id] = result

        return JSONResponse({
            'success': True,
            'project_id': result['project_id'],
            'status': 'generated',
            'message': 'App generated successfully',
            'download_url': f"/api/projects/{project_id}/download"
        })

    except Exception as e:
        import traceback
        return JSONResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status_code=500)


async def get_generation_status(request: Request) -> JSONResponse:
    """Get the status of a generated project."""
    project_id = request.path_params.get('project_id')

    if project_id not in _generated_projects:
        return JSONResponse(
            {'status': 'not_found', 'message': 'Project not generated yet'},
            status_code=404
        )

    return JSONResponse(_generated_projects[project_id])


async def download_project(request: Request) -> JSONResponse:
    """Download the generated project as a ZIP file."""
    import shutil

    from starlette.responses import FileResponse

    project_id = request.path_params.get('project_id')

    if project_id not in _generated_projects:
        return JSONResponse(
            {'error': 'Project not found'},
            status_code=404
        )

    project = _generated_projects[project_id]
    output_dir = Path(project['output_dir'])

    if not output_dir.exists():
        return JSONResponse(
            {'error': 'Generated files not found'},
            status_code=404
        )

    # Create ZIP file
    zip_path = f"/tmp/{project_id}.zip"
    shutil.make_archive(f"/tmp/{project_id}", 'zip', output_dir)

    return FileResponse(
        zip_path,
        media_type='application/zip',
        filename=f"{project_id}_app.zip"
    )


# API Routes
generation_routes = [
    Route('/api/generate', generate_app, methods=['POST']),
    Route('/api/projects/{project_id}/status', get_generation_status, methods=['GET']),
    Route('/api/projects/{project_id}/download', download_project, methods=['GET']),
]
