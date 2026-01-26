"""
Dashboard Routes

HTML routes for the NexusAI dashboard using HTMX.
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
    
    
    async def projects_list(self, request: Request) -> HTMLResponse:
        """Projects listing page."""
        return self.render(request, "pages/projects.html", {"active_page": "projects"})

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


class AdminRoutes:
    """
    Admin dashboard routes.
    
    Provides admin-only access to manage feedback, contacts, and system settings.
    """
    
    def __init__(self, templates: Jinja2Templates):
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
            "title": "Admin - NexusAI",
            "user": getattr(request.state, "user", None),
        }
        if context:
            ctx.update(context)
        
        return self.templates.TemplateResponse(
            template,
            ctx,
            status_code=status_code,
        )
    
    @staticmethod
    def check_admin(request: Request) -> bool:
        """Check if current user is an admin."""
        user = getattr(request.state, "user", None)
        if not user:
            return False
        # Check if user has admin flag or email is in admin list
        if hasattr(user, 'is_admin') and user.is_admin:
            return True
        # Check against admin email environment variable
        import os
        admin_emails = os.getenv("ADMIN_EMAILS", os.getenv("ADMIN_EMAIL", ""))
        admin_list = [e.strip().lower() for e in admin_emails.split(",") if e.strip()]
        user_email = getattr(user, 'email', '').lower()
        return user_email in admin_list
    
    async def admin_dashboard(self, request: Request) -> HTMLResponse:
        """Admin dashboard with feedback and contacts."""
        if not self.check_admin(request):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get query params
        page = int(request.query_params.get("page", 1))
        status_filter = request.query_params.get("status", "")
        category_filter = request.query_params.get("category", "")
        date_filter = request.query_params.get("date", "")
        per_page = 20
        offset = (page - 1) * per_page
        
        # Mock data - replace with actual database queries
        feedback_items = [
            {
                "id": "fb_1",
                "user_email": "user@example.com",
                "message": "Great product! Would love to see more integrations.",
                "category": "feature",
                "status": "pending",
                "page_url": "/dashboard",
                "user_agent": "Mozilla/5.0...",
                "created_at": type('obj', (object,), {'strftime': lambda self, f: '2026-01-25 10:30'})(),
            },
            {
                "id": "fb_2",
                "user_email": None,
                "message": "Found a bug when deploying to Vercel.",
                "category": "bug",
                "status": "reviewed",
                "page_url": "/projects/123",
                "user_agent": "Mozilla/5.0...",
                "created_at": type('obj', (object,), {'strftime': lambda self, f: '2026-01-24 15:45'})(),
            },
        ]
        
        contact_items = [
            {
                "id": "ct_1",
                "name": "John Smith",
                "email": "john@company.com",
                "subject": "Enterprise pricing question",
                "message": "We're interested in using NexusAI for our team...",
                "status": "pending",
                "created_at": type('obj', (object,), {'strftime': lambda self, f: '2026-01-25 09:00'})(),
            },
        ]
        
        stats = {
            "total_feedback": 42,
            "pending_feedback": 15,
            "total_contacts": 18,
            "pending_contacts": 5,
            "total_users": 127,
            "verified_users": 98,
            "onboarding_complete": 45,
            "onboarding_complete_pct": 35,
        }
        
        return self.render(request, "pages/admin.html", {
            "feedback_items": feedback_items,
            "contact_items": contact_items,
            "stats": stats,
            "page": page,
            "offset": offset,
            "items": feedback_items,
            "total_items": len(feedback_items),
            "has_next": len(feedback_items) >= per_page,
        })
    
    async def admin_feedback(self, request: Request) -> HTMLResponse:
        """View all feedback submissions."""
        if not self.check_admin(request):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return await self.admin_dashboard(request)
    
    async def admin_contacts(self, request: Request) -> HTMLResponse:
        """View all contact submissions."""
        if not self.check_admin(request):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return await self.admin_dashboard(request)
    
    async def resolve_feedback(
        self,
        request: Request,
        feedback_id: str,
    ) -> HTMLResponse:
        """Mark feedback as resolved."""
        if not self.check_admin(request):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Update feedback status in database
        # feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
        # feedback.status = "resolved"
        # db.commit()
        
        # Return updated row for HTMX swap
        return HTMLResponse(
            content=f'''
            <tr id="feedback-{feedback_id}">
                <td colspan="6" class="px-6 py-4 text-center text-green-600">
                    ✓ Feedback marked as resolved
                </td>
            </tr>
            ''',
            status_code=200
        )
    
    async def reply_to_contact(
        self,
        request: Request,
        contact_id: str,
    ):
        """Reply to a contact submission."""
        if not self.check_admin(request):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        from fastapi.responses import JSONResponse
        
        try:
            body = await request.json()
            message = body.get("message", "")
            subject = body.get("subject", "")
            
            if not message:
                return JSONResponse(
                    {"error": "Message is required"},
                    status_code=400
                )
            
            # Get contact from database
            # contact = db.query(ContactSubmission).filter(ContactSubmission.id == contact_id).first()
            
            # Send reply email
            # from src.emails import get_email_client
            # client = get_email_client()
            # await client.send_email(
            #     to=contact.email,
            #     subject=subject,
            #     text=message
            # )
            
            # Update contact status
            # contact.status = "replied"
            # contact.replied_at = datetime.utcnow()
            # contact.reply_message = message
            # db.commit()
            
            return JSONResponse({"success": True})
            
        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid data for contact reply {contact_id}: {e}")
            return JSONResponse(
                {"error": "Invalid request data"},
                status_code=400
            )
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Network error replying to contact {contact_id}: {e}")
            return JSONResponse(
                {"error": "Failed to send reply - network error"},
                status_code=503
            )
    
    async def email_templates(self, request: Request) -> HTMLResponse:
        """Email template preview page."""
        if not self.check_admin(request):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return self.render(request, "pages/email_preview.html", {})


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
    admin_routes = AdminRoutes(templates)
    
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
    
    # Admin routes
    router.add_api_route("/admin", admin_routes.admin_dashboard, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/admin/feedback", admin_routes.admin_feedback, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/admin/contacts", admin_routes.admin_contacts, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/admin/feedback/{feedback_id}/resolve", admin_routes.resolve_feedback, methods=["POST"])
    router.add_api_route("/admin/contacts/{contact_id}/reply", admin_routes.reply_to_contact, methods=["POST"])
    router.add_api_route("/admin/email-templates", admin_routes.email_templates, methods=["GET"], response_class=HTMLResponse)
    
    # HTMX partial routes
    router.add_api_route("/htmx/projects", routes.htmx_project_list, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/htmx/projects/{project_id}", routes.htmx_project_card, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/htmx/projects/{project_id}/status", routes.htmx_deployment_status, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/htmx/projects/{project_id}/progress", routes.htmx_generate_progress, methods=["GET"], response_class=HTMLResponse)
    
    # Form handlers
    router.add_api_route("/projects", routes.create_project, methods=["POST"])
    router.add_api_route("/settings", routes.update_settings, methods=["POST"])
    
    @router.get("/about", response_class=HTMLResponse)
    async def about_page(request: Request):
        """About page"""
        return templates.TemplateResponse(
            "pages/about.html",
            {"request": request}
        )

    @router.get("/privacy", response_class=HTMLResponse)
    async def privacy_page(request: Request):
        """Privacy policy page"""
        return templates.TemplateResponse("pages/privacy.html", {"request": request})

    @router.get("/terms", response_class=HTMLResponse)
    async def terms_page(request: Request):
        """Terms of service page"""
        return templates.TemplateResponse("pages/terms.html", {"request": request})

    @router.get("/api-keys", response_class=HTMLResponse)
    async def api_keys_page(request: Request):
        """API keys management page"""
        return templates.TemplateResponse("pages/api_keys.html", {"request": request})
    return router
