"""
Idea Analysis API - Handles idea submission, vetting, and project creation.
"""
import uuid
from datetime import datetime, timezone

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

# In-memory storage for now (will be replaced with database)
projects_store = {}


async def analyze_idea(request: Request) -> JSONResponse:
    """
    Analyze a user's business idea and create a new project.
    """
    try:
        body = await request.json()
        idea = body.get('idea', '').strip()

        if not idea:
            return JSONResponse(
                {'error': 'Please provide your business idea'},
                status_code=400
            )

        project_id = str(uuid.uuid4())[:8]

        project = {
            'id': project_id,
            'idea': idea,
            'status': 'analyzing',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'analysis': {
                'market_size': 'Analyzing...',
                'competition': 'Researching...',
                'feasibility': 'Evaluating...',
                'recommended_features': []
            },
            'generated_app': None
        }

        projects_store[project_id] = project

        return JSONResponse({
            'success': True,
            'project_id': project_id,
            'message': 'Project created successfully'
        })

    except Exception as e:
        return JSONResponse(
            {'error': str(e)},
            status_code=500
        )


async def get_project(request: Request) -> JSONResponse:
    project_id = request.path_params.get('project_id')
    if project_id not in projects_store:
        return JSONResponse({'error': 'Project not found'}, status_code=404)
    return JSONResponse(projects_store[project_id])


async def list_projects(request: Request) -> JSONResponse:
    return JSONResponse({'projects': list(projects_store.values())})


ideas_routes = [
    Route('/api/ideas/analyze', analyze_idea, methods=['POST']),
    Route('/api/projects', list_projects, methods=['GET']),
    Route('/api/projects/{project_id}', get_project, methods=['GET']),
]
