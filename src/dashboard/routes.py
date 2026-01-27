"""
Dashboard Routes

HTML routes for the NexusAI dashboard using HTMX.
"""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import logging
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class DashboardRoutes:
    """
    Dashboard HTML routes.
    
    Uses HTMX for dynamic updates without full page reloads.
    """
    
    def __init__(self, templates: Jinja2Templates):
        """
        Initialize dashboard routes.
        
        Args:
            templates: Jinja2 templates instance
        """
        self.templates = templates
    
    def render(
        self,
        request: Request,
        template: str,
        context: dict = None,
        status_code: int = 200,
    ) -> HTMLResponse:
        """Render a template with context."""
        ctx = {
            "request": request,
            "title": "NexusAI",
            "user": getattr(request.state, "user", None),
        }
        if context:
            ctx.update(context)
        
        return self.templates.TemplateResponse(
            template,
            ctx,
            status_code=status_code,
        )
    
    # ==================== Page Routes ====================
    
    async def home(self, request: Request) -> HTMLResponse:
        """Landing page."""
        import os
        template_path = os.path.join(os.path.dirname(__file__), 'templates', 'pages', 'landing.html')
        with open(template_path, 'r') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)

async def business_formation(request: Request) -> HTMLResponse:
    """Business formation page for LLC registration."""
    project_id = request.path_params.get('project_id')
    
    project = _projects_store.get(project_id)
    if not project:
        from starlette.responses import RedirectResponse
        return RedirectResponse(url="/dashboard", status_code=302)
    
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("pages/business_formation.html")
    html_content = template.render(project=project)
    return HTMLResponse(content=html_content)

async def deploy_page(request: Request) -> HTMLResponse:
    """Deploy page for one-click deployment."""
    project_id = request.path_params.get('project_id')
    
    project = _projects_store.get(project_id)
    if not project:
        from starlette.responses import RedirectResponse
        return RedirectResponse(url="/dashboard", status_code=302)
    
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("pages/deploy.html")
    html_content = template.render(project=project)
    return HTMLResponse(content=html_content)

async def agent_workspace(request: Request) -> HTMLResponse:
    """Agent workspace for customizing generated apps."""
    project_id = request.path_params.get('project_id')
    
    project = _projects_store.get(project_id)
    if not project:
        from starlette.responses import RedirectResponse
        return RedirectResponse(url="/dashboard", status_code=302)
    
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("pages/agent_workspace.html")
    html_content = template.render(project=project)
    return HTMLResponse(content=html_content)

async def project_generated(request: Request) -> HTMLResponse:
    """Project generated page showing download and next steps."""
    project_id = request.path_params.get('project_id')
    
    project = _projects_store.get(project_id)
    if not project:
        from starlette.responses import RedirectResponse
        return RedirectResponse(url="/dashboard", status_code=302)
    
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("pages/project_generated.html")
    html_content = template.render(project=project)
    return HTMLResponse(content=html_content)

async def project_review(request: Request) -> HTMLResponse:
    """Project review page showing idea analysis."""
    project_id = request.path_params.get('project_id')
    
    # Get project from store
    project = _projects_store.get(project_id)
    if not project:
        # Return 404 or redirect
        from starlette.responses import RedirectResponse
        return RedirectResponse(url="/dashboard", status_code=302)
    
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("pages/project_review.html")
    html_content = template.render(project=project)
    return HTMLResponse(content=html_content)



async def generate_app_api(request: Request) -> JSONResponse:
    """Generate a full app codebase from a project idea."""
    try:
        body = await request.json()
        project_id = body.get('project_id')
        
        if project_id not in _projects_store:
            return JSONResponse({'error': 'Project not found'}, status_code=404)
        
        project = _projects_store[project_id]
        idea = project['idea']
        
        # Update status to generating
        project['status'] = 'generating'
        
        # For now, simulate generation with a mock response
        # In production, this would call the EnhancedCodeGenerator
        import time
        project['status'] = 'generated'
        project['generated_at'] = datetime.utcnow().isoformat()
        project['download_ready'] = True
        project['files'] = [
            {'name': 'app.py', 'type': 'python', 'lines': 150},
            {'name': 'models.py', 'type': 'python', 'lines': 80},
            {'name': 'routes.py', 'type': 'python', 'lines': 200},
            {'name': 'templates/base.html', 'type': 'html', 'lines': 100},
            {'name': 'templates/dashboard.html', 'type': 'html', 'lines': 120},
            {'name': 'static/styles.css', 'type': 'css', 'lines': 300},
            {'name': 'requirements.txt', 'type': 'text', 'lines': 15},
            {'name': 'README.md', 'type': 'markdown', 'lines': 50},
            {'name': 'Dockerfile', 'type': 'docker', 'lines': 20},
            {'name': '.env.example', 'type': 'env', 'lines': 10},
        ]
        
        return JSONResponse({
            'success': True,
            'project_id': project_id,
            'status': 'generated',
            'message': 'App generated successfully',
            'files_count': len(project['files']),
            'download_url': f'/api/projects/{project_id}/download'
        })
        
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)

# Idea Analysis API Endpoints
# ============================================
import uuid
from datetime import datetime

# In-memory project store (will be migrated to database)
_projects_store = {}

async def analyze_idea_api(request: Request) -> JSONResponse:
    """Analyze a business idea and create a new project."""
    try:
        body = await request.json()
        idea = body.get('idea', '').strip()
        
        if not idea:
            return JSONResponse({'error': 'Please provide your business idea'}, status_code=400)
        
        project_id = str(uuid.uuid4())[:8]
        
        project = {
            'id': project_id,
            'idea': idea,
            'status': 'analyzing',
            'created_at': datetime.utcnow().isoformat(),
            'analysis': {
                'market_size': 'Analyzing...',
                'competition': 'Researching...',
                'feasibility': 'Evaluating...',
                'recommended_features': []
            }
        }
        
        _projects_store[project_id] = project
        
        return JSONResponse({
            'success': True,
            'project_id': project_id,
            'message': 'Project created successfully'
        })
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


async def get_project_api(request: Request) -> JSONResponse:
    """Get project by ID."""
    project_id = request.path_params.get('project_id')
    if project_id not in _projects_store:
        return JSONResponse({'error': 'Project not found'}, status_code=404)
    return JSONResponse(_projects_store[project_id])
