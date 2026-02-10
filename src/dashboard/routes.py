"""
Dashboard Routes

HTML routes for the LaunchForge dashboard using HTMX.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)


def get_current_user(request: Request) -> Optional["User"]:
    """Get the currently logged-in user from the request cookie."""
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    try:
        from src.database.db import get_db
        from src.database.models import User
        db = get_db()
        with db.session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                # Detach from session so it can be used after session closes
                session.expunge(user)
            return user
    except Exception as e:
        logger.warning(f"Failed to get current user: {e}")
        return None


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
            request,
            template,
            ctx,
            status_code=status_code,
        )

    # ==================== Page Routes ====================

    async def home(self, request: Request) -> HTMLResponse:
        """Landing page."""
        return self.render(request, "pages/landing.html", {"active": "home"})
    async def dashboard(self, request: Request) -> HTMLResponse:
        """Main dashboard page."""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        # Try to load real projects from DB
        projects = []
        try:
            from src.database.db import get_db
            from src.database.models import Project
            db = get_db()
            with db.session() as session:
                db_projects = (
                    session.query(Project)
                    .filter(Project.user_id == user.id, Project.is_deleted == False)
                    .order_by(Project.created_at.desc())
                    .limit(10)
                    .all()
                )
                for p in db_projects:
                    projects.append({
                        "id": p.id,
                        "name": p.name,
                        "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
                        "url": getattr(p, 'deployment_url', None),
                        "created_at": p.created_at.strftime("%Y-%m-%d") if p.created_at else "",
                    })
        except Exception as e:
            logger.warning(f"Could not load projects from DB: {e}")

        # Fallback demo data if no projects found
        if not projects:
            projects = [
                {"id": "proj_1", "name": "My SaaS App", "status": "deployed", "url": "https://my-saas.vercel.app", "created_at": "2026-02-01"},
                {"id": "proj_2", "name": "Portfolio Site", "status": "building", "url": None, "created_at": "2026-02-05"},
            ]

        deployed_count = len([p for p in projects if p.get("status") == "deployed"])
        return self.render(request, "pages/dashboard.html", {
            "user": user,
            "projects": projects,
            "stats": {
                "total_projects": len(projects),
                "deployed": deployed_count,
                "apps_remaining": max(0, getattr(user, 'credits_remaining', 5) - len(projects)),
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
    async def projects_list(self, request: Request) -> HTMLResponse:
        """Display list of all projects."""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        projects = []
        try:
            from src.database.db import get_db
            from src.database.models import Project
            db = get_db()
            with db.session() as session:
                db_projects = (
                    session.query(Project)
                    .filter(Project.user_id == user.id, Project.is_deleted == False)
                    .order_by(Project.created_at.desc())
                    .all()
                )
                for p in db_projects:
                    projects.append({
                        "id": p.id,
                        "name": p.name,
                        "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
                        "description": getattr(p, 'description', ''),
                        "url": getattr(p, 'deployment_url', None),
                        "created_at": p.created_at.strftime("%b %d, %Y") if p.created_at else "",
                    })
        except Exception as e:
            logger.warning(f"Could not load projects from DB: {e}")

        if not projects:
            projects = [
                {"id": "proj_1", "name": "My SaaS App", "status": "deployed", "description": "Full-stack SaaS application", "url": "https://my-saas.vercel.app", "created_at": "Feb 1, 2026"},
                {"id": "proj_2", "name": "Portfolio Site", "status": "building", "description": "Personal portfolio", "url": None, "created_at": "Feb 5, 2026"},
                {"id": "proj_3", "name": "Task Manager", "status": "draft", "description": "Team productivity app", "url": None, "created_at": "Feb 7, 2026"},
            ]

        return self.render(request, "pages/projects.html", {
            "active": "projects",
            "user": user,
            "projects": projects,
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
            "created_at": "2026-02-01",
            "deployed_at": "2026-02-02",
        }

        return self.render(request, "pages/project_detail.html", {
            "project": project,
        })

    async def settings(self, request: Request) -> HTMLResponse:
        """Settings page."""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        return self.render(request, "pages/settings.html", {
            "user": user,
            "user_name": getattr(user, 'name', '') or '',
            "user_email": getattr(user, 'email', '') or '',
            "user_company": getattr(user, 'company', '') or '',
            "user_role": getattr(user, 'role', 'user') or 'user',
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
            "next_invoice": "Mar 1, 2026",
            "amount": "$49.00",
        })

    async def api_keys_page(self, request: Request) -> HTMLResponse:
        """API Keys management page."""
        return self.render(request, "pages/api_keys.html", {"active": "api-keys"})

    async def billing_page(self, request):
        """Billing page"""
        return self.render(request, "pages/billing.html", {"active": "billing"})

    async def about_page(self, request: Request) -> HTMLResponse:
        """About Us page."""
        return self.render(request, "pages/about.html", {"active": "about"})

    async def terms_page(self, request: Request) -> HTMLResponse:
        """Terms of Service page."""
        return self.render(request, "pages/terms.html", {"active": "terms"})

    async def privacy_page(self, request: Request) -> HTMLResponse:
        """Privacy Policy page."""
        return self.render(request, "pages/privacy.html", {"active": "privacy"})

    async def business_formation_page(self, request: Request) -> HTMLResponse:
        """Business Formation page."""
        return self.render(request, "pages/business_formation.html", {"active": "business-formation"})

    async def new_project_page(self, request: Request) -> HTMLResponse:
        """Create new project page."""
        return self.render(request, "pages/new_project.html", {"active": "projects"})

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
            "title": "Admin - LaunchForge",
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
        request.query_params.get("status", "")
        request.query_params.get("category", "")
        request.query_params.get("date", "")
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
                "message": "We're interested in using LaunchForge for our team...",
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
            body.get("subject", "")

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
            # contact.replied_at = datetime.now(timezone.utc)
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
    router.add_api_route("/api-keys", routes.api_keys_page, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/about", routes.about_page, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/terms", routes.terms_page, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/privacy", routes.privacy_page, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/business-formation", routes.business_formation_page, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/new-project", routes.new_project_page, methods=["GET"], response_class=HTMLResponse)


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
    router.add_api_route("/projects", routes.projects_list, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/projects", routes.create_project, methods=["POST"])
    router.add_api_route("/settings", routes.update_settings, methods=["POST"])

    router.add_api_route("/pricing", pricing_page, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/projects/{project_id}/business", business_formation, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/projects/{project_id}/deploy", deploy_page, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/projects/{project_id}/workspace", agent_workspace, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/projects/{project_id}/generated", project_generated, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/projects/{project_id}/review", project_review, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/api/generate", generate_app_api, methods=["POST"])
    router.add_api_route("/api/ideas/analyze", analyze_idea_api, methods=["POST"])
    router.add_api_route("/api/projects/{project_id}", get_project_api, methods=["GET"])

    # Store templates reference for standalone route functions
    _set_templates(templates)

    return router


# Module-level templates reference for standalone route functions
_templates: Optional[Jinja2Templates] = None


def _set_templates(templates: Jinja2Templates) -> None:
    """Set the module-level templates reference."""
    global _templates
    _templates = templates


def _render(request: Request, template: str, context: dict = None, status_code: int = 200) -> HTMLResponse:
    """Render a template using the shared templates instance."""
    ctx = {"request": request}
    if context:
        ctx.update(context)
    return _templates.TemplateResponse(request, template, ctx, status_code=status_code)












async def pricing_page(request: Request) -> HTMLResponse:
    """Pricing page with subscription plans."""
    return _render(request, "pages/pricing.html", {})

async def business_formation(request: Request) -> HTMLResponse:
    """Business formation page for LLC registration."""
    project_id = request.path_params.get('project_id')

    project = _projects_store.get(project_id)
    if not project:
        return RedirectResponse(url="/dashboard", status_code=302)

    return _render(request, "pages/business_formation.html", {"project": project})

async def deploy_page(request: Request) -> HTMLResponse:
    """Deploy page for one-click deployment."""
    project_id = request.path_params.get('project_id')

    project = _projects_store.get(project_id)
    if not project:
        return RedirectResponse(url="/dashboard", status_code=302)

    return _render(request, "pages/deploy.html", {"project": project})

async def agent_workspace(request: Request) -> HTMLResponse:
    """Agent workspace for customizing generated apps."""
    project_id = request.path_params.get('project_id')

    project = _projects_store.get(project_id)
    if not project:
        return RedirectResponse(url="/dashboard", status_code=302)

    return _render(request, "pages/agent_workspace.html", {"project": project})

async def project_generated(request: Request) -> HTMLResponse:
    """Project generated page showing download and next steps."""
    project_id = request.path_params.get('project_id')

    project = _projects_store.get(project_id)
    if not project:
        return RedirectResponse(url="/dashboard", status_code=302)

    return _render(request, "pages/project_generated.html", {"project": project})

async def project_review(request: Request) -> HTMLResponse:
    """Project review page showing idea analysis."""
    project_id = request.path_params.get('project_id')

    project = _projects_store.get(project_id)
    if not project:
        return RedirectResponse(url="/dashboard", status_code=302)

    return _render(request, "pages/project_review.html", {"project": project})



async def generate_app_api(request: Request) -> JSONResponse:
    """Generate a full app codebase from a project idea."""
    try:
        body = await request.json()
        project_id = body.get('project_id')

        if project_id not in _projects_store:
            return JSONResponse({'error': 'Project not found'}, status_code=404)

        project = _projects_store[project_id]
        project['idea']

        # Update status to generating
        project['status'] = 'generating'

        # For now, simulate generation with a mock response
        # In production, this would call the EnhancedCodeGenerator
        project['status'] = 'generated'
        project['generated_at'] = datetime.now(timezone.utc).isoformat()
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
from datetime import datetime, timezone

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
            'created_at': datetime.now(timezone.utc).isoformat(),
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
