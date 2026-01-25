"""
Dashboard Routes

HTML routes for the LaunchForge dashboard using HTMX.
"""

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import logging

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
            "title": "LaunchForge",
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
        return self.render(request, "pages/home.html")
    
    async def dashboard(self, request: Request) -> HTMLResponse:
        """Main dashboard page."""
        # Mock data for now
        projects = [
            {
                "id": "proj_1",
                "name": "My SaaS App",
                "status": "deployed",
                "url": "https://my-saas.vercel.app",
                "created_at": "2024-01-15",
            },
            {
                "id": "proj_2",
                "name": "Portfolio Site",
                "status": "building",
                "url": None,
                "created_at": "2024-01-20",
            },
        ]
        
        return self.render(request, "pages/dashboard.html", {
            "projects": projects,
            "stats": {
                "total_projects": 2,
                "deployed": 1,
                "apps_remaining": 3,
            },
        })
    
    async def new_project(self, request: Request) -> HTMLResponse:
        """New project wizard."""
        return self.render(request, "pages/new_project.html", {
            "step": 1,
            "steps": [
                {"num": 1, "title": "Describe Your Idea"},
                {"num": 2, "title": "Choose Features"},
                {"num": 3, "title": "Review & Generate"},
            ],
        })
    
    async def project_detail(
        self,
        request: Request,
        project_id: str,
    ) -> HTMLResponse:
        """Project detail page."""
        # Mock project data
        project = {
            "id": project_id,
            "name": "My SaaS App",
            "description": "A productivity app for teams",
            "status": "deployed",
            "urls": {
                "frontend": "https://my-saas.vercel.app",
                "backend": "https://my-saas-api.onrender.com",
                "github": "https://github.com/user/my-saas",
            },
            "tech_stack": ["Next.js", "FastAPI", "PostgreSQL"],
            "created_at": "2024-01-15",
            "deployed_at": "2024-01-16",
        }
        
        return self.render(request, "pages/project_detail.html", {
            "project": project,
        })
    
    async def settings(self, request: Request) -> HTMLResponse:
        """Settings page."""
        return self.render(request, "pages/settings.html", {
            "sections": ["Profile", "API Keys", "Billing", "Notifications"],
        })
    
    async def compare(self, request: Request) -> HTMLResponse:
        """Competitive comparison page."""
        return self.render(request, "pages/compare.html", {})
    
    async def health_dashboard(self, request: Request) -> HTMLResponse:
        """Deployment health dashboard."""
        # Mock deployment data
        deployments = [
            {
                "id": "dep_1",
                "project_id": "proj_1",
                "name": "My SaaS App",
                "url": "https://my-saas.vercel.app",
                "status": "healthy",
                "response_time": 120,
                "uptime": 99.95,
                "ssl_valid": True,
                "ssl_days_remaining": 45,
            },
        ]
        
        stats = {
            "total_deployments": len(deployments),
            "healthy": len([d for d in deployments if d["status"] == "healthy"]),
            "degraded": len([d for d in deployments if d["status"] == "degraded"]),
            "down": len([d for d in deployments if d["status"] == "down"]),
        }
        
        return self.render(request, "pages/health.html", {
            "deployments": deployments,
            "stats": stats,
            "incidents": [],
        })
    
    async def contact(self, request: Request) -> HTMLResponse:
        """Contact page."""
        return self.render(request, "pages/contact.html", {})
    
    async def billing(self, request: Request) -> HTMLResponse:
        """Billing and subscription page."""
        return self.render(request, "pages/billing.html", {
            "current_plan": "pro",
            "billing_period": "monthly",
            "next_invoice": "Feb 1, 2024",
            "amount": "$29.00",
        })
    
    # ==================== HTMX Partial Routes ====================
    
    async def htmx_project_list(self, request: Request) -> HTMLResponse:
        """HTMX partial: Project list."""
        projects = [
            {"id": "proj_1", "name": "My SaaS App", "status": "deployed"},
            {"id": "proj_2", "name": "Portfolio Site", "status": "building"},
        ]
        
        return self.render(request, "partials/project_list.html", {
            "projects": projects,
        })
    
    async def htmx_project_card(
        self,
        request: Request,
        project_id: str,
    ) -> HTMLResponse:
        """HTMX partial: Single project card."""
        project = {
            "id": project_id,
            "name": "My SaaS App",
            "status": "deployed",
            "url": "https://my-saas.vercel.app",
        }
        
        return self.render(request, "partials/project_card.html", {
            "project": project,
        })
    
    async def htmx_deployment_status(
        self,
        request: Request,
        project_id: str,
    ) -> HTMLResponse:
        """HTMX partial: Deployment status (for polling)."""
        # This would poll actual deployment status
        import random
        statuses = ["building", "deploying", "deployed"]
        status = random.choice(statuses)
        
        return self.render(request, "partials/deployment_status.html", {
            "project_id": project_id,
            "status": status,
            "progress": 75 if status == "deploying" else 100 if status == "deployed" else 25,
        })
    
    async def htmx_generate_progress(
        self,
        request: Request,
        project_id: str,
    ) -> HTMLResponse:
        """HTMX partial: Generation progress."""
        return self.render(request, "partials/generation_progress.html", {
            "project_id": project_id,
            "steps": [
                {"name": "Analyzing idea", "status": "complete"},
                {"name": "Generating architecture", "status": "complete"},
                {"name": "Writing code", "status": "in_progress"},
                {"name": "Creating tests", "status": "pending"},
                {"name": "Deploying", "status": "pending"},
            ],
        })
    
    # ==================== Form Handlers ====================
    
    async def create_project(
        self,
        request: Request,
        idea: str = Form(...),
        name: str = Form(None),
        features: str = Form(None),
    ) -> HTMLResponse:
        """Handle new project creation form."""
        # Create project (mock)
        project_id = "proj_new"
        
        # Redirect to project page or return HTMX partial
        if request.headers.get("HX-Request"):
            return self.render(request, "partials/generation_started.html", {
                "project_id": project_id,
                "message": "Generation started!",
            })
        
        return RedirectResponse(
            url=f"/projects/{project_id}",
            status_code=303,
        )
    
    async def update_settings(
        self,
        request: Request,
        name: str = Form(None),
        email: str = Form(None),
    ) -> HTMLResponse:
        """Handle settings update form."""
        # Update settings (mock)
        
        if request.headers.get("HX-Request"):
            return self.render(request, "partials/settings_saved.html", {
                "message": "Settings saved successfully!",
            })
        
        return RedirectResponse(url="/settings", status_code=303)


def create_dashboard_router(templates: Jinja2Templates) -> APIRouter:
    """
    Create dashboard router with all routes.
    
    Args:
        templates: Jinja2 templates instance
        
    Returns:
        Configured APIRouter
    """
    router = APIRouter()
    routes = DashboardRoutes(templates)
    
    # Page routes
    router.add_api_route("/", routes.home, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/dashboard", routes.dashboard, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/compare", routes.compare, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/health", routes.health_dashboard, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/contact", routes.contact, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/projects/new", routes.new_project, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/projects/{project_id}", routes.project_detail, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/settings", routes.settings, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/billing", routes.billing, methods=["GET"], response_class=HTMLResponse)
    
    # HTMX partial routes
    router.add_api_route("/htmx/projects", routes.htmx_project_list, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/htmx/projects/{project_id}", routes.htmx_project_card, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/htmx/projects/{project_id}/status", routes.htmx_deployment_status, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/htmx/projects/{project_id}/progress", routes.htmx_generate_progress, methods=["GET"], response_class=HTMLResponse)
    
    # Form handlers
    router.add_api_route("/projects", routes.create_project, methods=["POST"])
    router.add_api_route("/settings", routes.update_settings, methods=["POST"])
    
    return router
