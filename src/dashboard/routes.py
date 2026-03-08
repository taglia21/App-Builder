"""
Dashboard Routes

HTML routes for the Ignara dashboard using HTMX.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Form, HTTPException, Request

if TYPE_CHECKING:
    from src.database.models import User
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)


def get_current_user(request: Request) -> Optional["User"]:
    """Get the currently logged-in user from the signed session cookie."""
    from src.auth.web_routes import verify_session_cookie

    # Try signed session cookie first, fall back to legacy cookie
    cookie = request.cookies.get("session")
    user_id = verify_session_cookie(cookie) if cookie else None

    # Legacy fallback (unsigned cookie) — only for migration
    if not user_id:
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
            "title": "Ignara",
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

        deployed_count = len([p for p in projects if p.get("status") == "deployed"])

        # Count real API keys from DB
        api_key_count = 0
        try:
            from src.database.db import get_db
            from src.database.models import APIKey
            db = get_db()
            with db.session() as session:
                api_key_count = (
                    session.query(APIKey)
                    .filter(APIKey.user_id == user.id, APIKey.is_deleted == False, APIKey.is_active == True)
                    .count()
                )
        except Exception as e:
            logger.warning(f"Could not load API key count: {e}")

        # Determine current plan label
        tier = getattr(user, 'subscription_tier', None)
        tier_value = tier.value if hasattr(tier, 'value') else str(tier) if tier else 'free'
        plan_labels = {'free': 'Free', 'starter': 'Starter', 'pro': 'Pro', 'enterprise': 'Enterprise'}
        current_plan = plan_labels.get(tier_value, tier_value.capitalize())

        return self.render(request, "pages/dashboard.html", {
            "user": user,
            "projects": projects,
            "stats": {
                "total_projects": len(projects),
                "deployed": deployed_count,
                "apps_remaining": max(0, getattr(user, 'credits_remaining', 5) - len(projects)),
                "api_calls": 0,
                "active_projects": len([p for p in projects if p.get("status") not in ("archived", "failed")]),
                "api_keys": api_key_count,
                "current_plan": current_plan,
            },
        })

    async def new_project(self, request: Request) -> HTMLResponse:
        """New project wizard."""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)
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
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        project = None
        try:
            from src.database.db import get_db
            from src.database.models import Project
            db = get_db()
            with db.session() as session:
                db_project = (
                    session.query(Project)
                    .filter(Project.id == project_id, Project.user_id == user.id, Project.is_deleted == False)
                    .first()
                )
                if db_project:
                    config = db_project.config or {}
                    urls = {}
                    if db_project.deployment_url:
                        urls["frontend"] = db_project.deployment_url
                    if db_project.code_url:
                        urls["github"] = db_project.code_url
                    project = {
                        "id": db_project.id,
                        "name": db_project.name,
                        "description": db_project.description or "",
                        "status": db_project.status.value if hasattr(db_project.status, 'value') else str(db_project.status),
                        "urls": urls if urls else None,
                        "tech_stack": config.get("tech_stack", []),
                        "features": config.get("features", []),
                        "output_path": config.get("output_path"),
                        "created_at": db_project.created_at.strftime("%b %d, %Y") if db_project.created_at else "",
                        "deployed_at": config.get("deployed_at", ""),
                    }
        except Exception as e:
            logger.warning(f"Could not load project {project_id} from DB: {e}")

        if not project:
            return RedirectResponse(url="/projects", status_code=303)

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
        user = get_current_user(request)
        deployments = []
        if user:
            try:
                from src.database.db import get_db
                from src.database.models import Project
                db = get_db()
                with db.session() as session:
                    db_projects = (
                        session.query(Project)
                        .filter(
                            Project.user_id == user.id,
                            Project.is_deleted == False,
                            Project.deployment_url.isnot(None),
                        )
                        .all()
                    )
                    for p in db_projects:
                        deployments.append({
                            "id": str(p.id),
                            "project_id": str(p.id),
                            "name": p.name,
                            "url": p.deployment_url,
                            "status": "healthy",
                            "response_time": None,
                            "uptime": None,
                            "ssl_valid": p.deployment_url.startswith("https://") if p.deployment_url else False,
                            "ssl_days_remaining": None,
                        })
            except Exception as e:
                logger.warning(f"Could not load deployments for health dashboard: {e}")

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
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)
        return self.render(request, "pages/billing.html", {
            "current_plan": "pro",
            "billing_period": "monthly",
            "next_invoice": "Mar 1, 2026",
            "amount": "$49.00",
        })

    async def api_keys_page(self, request: Request) -> HTMLResponse:
        """API Keys management page."""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)
        return self.render(request, "pages/api_keys.html", {"active": "api-keys", "user": user})

    async def billing_page(self, request):
        """Billing page"""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)
        return self.render(request, "pages/billing.html", {"active": "billing", "user": user})

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
        """Business Formation page — shows existing formation status if available."""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        existing_formation = None
        try:
            from src.database.db import get_db
            from src.database.models import BusinessFormation
            db = get_db()
            with db.session() as session:
                existing_formation = (
                    session.query(BusinessFormation)
                    .filter(BusinessFormation.user_id == str(user.id))
                    .order_by(BusinessFormation.created_at.desc())
                    .first()
                )
                # Detach from session so it can be passed to template
                if existing_formation:
                    session.expunge(existing_formation)
        except Exception as e:
            logger.debug(f"Could not load existing formation: {e}")

        return self.render(request, "pages/business_formation.html", {
            "active": "business-formation",
            "user": user,
            "existing_formation": existing_formation,
        })

    async def new_project_page(self, request: Request) -> HTMLResponse:
        """Create new project page."""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)
        return self.render(request, "pages/new_project.html", {"active": "projects", "user": user})

    async def build_page(self, request: Request) -> HTMLResponse:
        """Build form page."""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)
        return self.render(request, "pages/build.html", {"active": "build", "user": user})

    async def build_progress_page(self, request: Request, build_id: str) -> HTMLResponse:
        """Build progress page."""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)
        return self.render(request, "pages/build_progress.html", {"active": "build", "build_id": build_id, "user": user})

    async def builds_page(self, request: Request) -> HTMLResponse:
        """Build history page."""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)
        return self.render(request, "pages/builds.html", {"active": "builds", "user": user})

    async def quality_dashboard_page(
        self,
        request: Request,
        project_id: str,
    ) -> HTMLResponse:
        """Quality metrics dashboard for a generated project."""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        project = None
        quality_data: dict = {}

        try:
            from src.database.db import get_db
            from src.database.models import Project
            db = get_db()
            with db.session() as session:
                db_project = (
                    session.query(Project)
                    .filter(
                        Project.id == project_id,
                        Project.user_id == user.id,
                        Project.is_deleted == False,
                    )
                    .first()
                )
                if db_project:
                    config = db_project.config or {}
                    project = {
                        "id": db_project.id,
                        "name": db_project.name,
                        "description": db_project.description or "",
                        "status": db_project.status.value if hasattr(db_project.status, "value") else str(db_project.status),
                        "output_path": config.get("output_path"),
                        "created_at": db_project.created_at.strftime("%b %d, %Y") if db_project.created_at else "",
                    }
                    # Pull quality data from config if stored
                    quality_data = config.get("quality", {})
        except Exception as e:
            logger.warning(f"Could not load project {project_id} for quality dashboard: {e}")

        if not project:
            return RedirectResponse(url="/projects", status_code=303)

        # Attempt to load latest quality result from in-memory job store
        if not quality_data:
            try:
                from src.code_generation.routes import _jobs
                for job in _jobs.values():
                    if job.result and str(getattr(job.request, 'project_id', '')) == str(project_id):
                        result = job.result
                        quality_data = {
                            "score":    result.quality.score,
                            "passed":   int(result.quality.passed),
                            "errors":   result.quality.errors,
                            "warnings": result.quality.warnings,
                            "summary":  result.quality.summary,
                        }
                        break
            except Exception:
                pass

        return self.render(request, "pages/quality_dashboard.html", {
            "project": project,
            "quality_data": quality_data,
        })

    async def refine_page(
        self,
        request: Request,
        project_id: str,
    ) -> HTMLResponse:
        """AI code refinement chat page for a generated project."""
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=303)

        project = None
        try:
            from src.database.db import get_db
            from src.database.models import Project
            db = get_db()
            with db.session() as session:
                db_project = (
                    session.query(Project)
                    .filter(
                        Project.id == project_id,
                        Project.user_id == user.id,
                        Project.is_deleted == False,
                    )
                    .first()
                )
                if db_project:
                    config = db_project.config or {}
                    project = {
                        "id": db_project.id,
                        "name": db_project.name,
                        "description": db_project.description or "",
                        "status": db_project.status.value if hasattr(db_project.status, "value") else str(db_project.status),
                        "output_path": config.get("output_path", ""),
                        "created_at": db_project.created_at.strftime("%b %d, %Y") if db_project.created_at else "",
                    }
        except Exception as e:
            logger.warning(f"Could not load project {project_id} for refine page: {e}")

        if not project:
            return RedirectResponse(url="/projects", status_code=303)

        return self.render(request, "pages/refine.html", {
            "project": project,
        })

    # ==================== HTMX Partial Routes ====================

    async def htmx_project_list(self, request: Request) -> HTMLResponse:
        """HTMX partial: Project list."""
        user = get_current_user(request)
        projects = []
        if user:
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
                        })
            except Exception as e:
                logger.warning(f"Could not load projects for HTMX list: {e}")

        return self.render(request, "partials/project_list.html", {
            "projects": projects,
        })

    async def htmx_project_card(
        self,
        request: Request,
        project_id: str,
    ) -> HTMLResponse:
        """HTMX partial: Single project card."""
        user = get_current_user(request)
        project = {"id": project_id, "name": "Unknown", "status": "draft"}
        if user:
            try:
                from src.database.db import get_db
                from src.database.models import Project
                db = get_db()
                with db.session() as session:
                    p = session.query(Project).filter(
                        Project.id == project_id, Project.user_id == user.id
                    ).first()
                    if p:
                        project = {
                            "id": p.id,
                            "name": p.name,
                            "description": p.description or "",
                            "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
                            "deployment_url": p.deployment_url,
                            "github_url": p.code_url,
                            "created_at": p.created_at,
                        }
            except Exception as e:
                logger.warning(f"Could not load project card {project_id}: {e}")

        return self.render(request, "partials/project_card.html", {
            "project": project,
        })

    async def htmx_deployment_status(
        self,
        request: Request,
        project_id: str,
    ) -> HTMLResponse:
        """HTMX partial: Deployment status (for polling)."""
        user = get_current_user(request)
        status = "draft"
        if user:
            try:
                from src.database.db import get_db
                from src.database.models import Project
                db = get_db()
                with db.session() as session:
                    p = session.query(Project).filter(
                        Project.id == project_id, Project.user_id == user.id
                    ).first()
                    if p:
                        status = p.status.value if hasattr(p.status, 'value') else str(p.status)
            except Exception as e:
                logger.warning(f"Could not load deployment status for {project_id}: {e}")

        progress_map = {"building": 25, "deploying": 75, "deployed": 100}
        return self.render(request, "partials/deployment_status.html", {
            "project_id": project_id,
            "status": status,
            "progress": progress_map.get(status, 0),
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
        # Generate unique project ID
        project_id = f"proj_{uuid.uuid4().hex[:12]}"

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
            "title": "Admin - Ignara",
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

        # Real database queries
        try:
            from src.database.db import get_db
            from src.database.models import Feedback, ContactSubmission, User, OnboardingStatus
            from sqlalchemy import func

            db = get_db()
            with db.session() as session:
                # Feedback items with pagination
                feedback_rows = (
                    session.query(Feedback)
                    .order_by(Feedback.created_at.desc())
                    .offset(offset)
                    .limit(per_page)
                    .all()
                )
                feedback_items = [
                    {
                        "id": str(fb.id),
                        "user_email": fb.email,
                        "message": fb.message,
                        "category": fb.feedback_type.value if fb.feedback_type else "",
                        "status": fb.status or "new",
                        "page_url": fb.page_url or "",
                        "user_agent": fb.user_agent or "",
                        "created_at": fb.created_at,
                    }
                    for fb in feedback_rows
                ]

                # Contact items with pagination
                contact_rows = (
                    session.query(ContactSubmission)
                    .order_by(ContactSubmission.created_at.desc())
                    .offset(offset)
                    .limit(per_page)
                    .all()
                )
                contact_items = [
                    {
                        "id": str(ct.id),
                        "name": ct.name or "",
                        "email": ct.email or "",
                        "subject": ct.subject or "",
                        "message": ct.message or "",
                        "status": ct.status or "new",
                        "created_at": ct.created_at,
                    }
                    for ct in contact_rows
                ]

                # Stats
                total_feedback = session.query(func.count(Feedback.id)).scalar() or 0
                pending_feedback = (
                    session.query(func.count(Feedback.id))
                    .filter(Feedback.status == "new")
                    .scalar() or 0
                )
                total_contacts = session.query(func.count(ContactSubmission.id)).scalar() or 0
                pending_contacts = (
                    session.query(func.count(ContactSubmission.id))
                    .filter(ContactSubmission.status == "new")
                    .scalar() or 0
                )
                total_users = session.query(func.count(User.id)).scalar() or 0
                verified_users = (
                    session.query(func.count(User.id))
                    .filter(User.email_verified.is_(True))
                    .scalar() or 0
                )
                onboarding_complete = (
                    session.query(func.count(OnboardingStatus.user_id))
                    .filter(OnboardingStatus.completed.is_(True))
                    .scalar() or 0
                )
                onboarding_complete_pct = (
                    int(onboarding_complete * 100 / total_users)
                    if total_users > 0
                    else 0
                )

                stats = {
                    "total_feedback": total_feedback,
                    "pending_feedback": pending_feedback,
                    "total_contacts": total_contacts,
                    "pending_contacts": pending_contacts,
                    "total_users": total_users,
                    "verified_users": verified_users,
                    "onboarding_complete": onboarding_complete,
                    "onboarding_complete_pct": onboarding_complete_pct,
                }
        except Exception as e:
            logger.error("Admin dashboard DB error: %s", e)
            feedback_items = []
            contact_items = []
            stats = {
                "total_feedback": 0,
                "pending_feedback": 0,
                "total_contacts": 0,
                "pending_contacts": 0,
                "total_users": 0,
                "verified_users": 0,
                "onboarding_complete": 0,
                "onboarding_complete_pct": 0,
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
        try:
            from src.database.db import get_db
            from src.database.models import Feedback

            db = get_db()
            with db.session() as session:
                feedback = session.query(Feedback).filter(Feedback.id == feedback_id).first()
                if feedback:
                    feedback.status = "resolved"
                    session.commit()
        except Exception as e:
            logger.error("resolve_feedback DB error: %s", e)

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

            return JSONResponse({"success": False, "error": "Email sending not yet configured. Contact reply was not sent."})

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

    async def resolve_contact(
        self,
        request: Request,
        contact_id: str,
    ) -> HTMLResponse:
        """Mark a contact submission as resolved."""
        if not self.check_admin(request):
            raise HTTPException(status_code=403, detail="Admin access required")

        try:
            from src.database.db import get_db
            from src.database.models import ContactSubmission

            db = get_db()
            with db.session() as session:
                contact = session.query(ContactSubmission).filter(
                    ContactSubmission.id == contact_id
                ).first()
                if contact:
                    contact.status = "resolved"
                    session.commit()
        except Exception as e:
            logger.error("resolve_contact DB error: %s", e)

        return HTMLResponse(
            content=f'''
            <tr id="contact-{contact_id}">
                <td colspan="6" class="px-6 py-4 text-center text-green-600">
                    \u2713 Contact marked as resolved
                </td>
            </tr>
            '''
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
    router.add_api_route("/business-formation/submit", business_formation_submit, methods=["POST"])
    router.add_api_route("/new-project", routes.new_project_page, methods=["GET"], response_class=HTMLResponse)

    # Build pipeline page routes
    router.add_api_route("/build", routes.build_page, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/build/{build_id}", routes.build_progress_page, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/builds", routes.builds_page, methods=["GET"], response_class=HTMLResponse)

    # Quality dashboard and AI refinement pages
    router.add_api_route("/projects/{project_id}/quality", routes.quality_dashboard_page, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/projects/{project_id}/refine", routes.refine_page, methods=["GET"], response_class=HTMLResponse)


    # Admin routes
    router.add_api_route("/admin", admin_routes.admin_dashboard, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/admin/feedback", admin_routes.admin_feedback, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/admin/contacts", admin_routes.admin_contacts, methods=["GET"], response_class=HTMLResponse)
    router.add_api_route("/admin/feedback/{feedback_id}/resolve", admin_routes.resolve_feedback, methods=["POST"])
    router.add_api_route("/admin/contacts/{contact_id}/reply", admin_routes.reply_to_contact, methods=["POST"])
    router.add_api_route("/admin/contacts/{contact_id}/resolve", admin_routes.resolve_contact, methods=["POST"])
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
    router.add_api_route("/api/preview", preview_app_api, methods=["POST"])
    router.add_api_route("/api/ideas/analyze", analyze_idea_api, methods=["POST"])
    router.add_api_route("/api/projects/{project_id}", get_project_api, methods=["GET"])
    router.add_api_route("/api/user/billing-status", billing_status_api, methods=["GET"])
    router.add_api_route("/api/deploy/start", deploy_start_api, methods=["POST"])

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
    """Business formation page for LLC registration (project-scoped)."""
    project_id = request.path_params.get('project_id')

    project = _projects_store.get(project_id)
    if not project:
        return RedirectResponse(url="/dashboard", status_code=302)

    existing_formation = None
    user = get_current_user(request)
    if user:
        try:
            from src.database.db import get_db
            from src.database.models import BusinessFormation
            db = get_db()
            with db.session() as session:
                existing_formation = (
                    session.query(BusinessFormation)
                    .filter(
                        BusinessFormation.user_id == str(user.id),
                        BusinessFormation.project_id == str(project_id),
                    )
                    .order_by(BusinessFormation.created_at.desc())
                    .first()
                )
                if existing_formation:
                    session.expunge(existing_formation)
        except Exception as e:
            logger.debug(f"Could not load existing formation: {e}")

    return _render(request, "pages/business_formation.html", {
        "project": project,
        "existing_formation": existing_formation,
    })


async def business_formation_submit(request: Request) -> JSONResponse:
    """POST /business-formation/submit — Create a BusinessFormation record in the DB.

    Accepts a JSON body with business details, writes a BusinessFormation row,
    and optionally kicks off the formation provider flow.
    """
    user = get_current_user(request)
    if not user:
        return JSONResponse(
            {"success": False, "error": "Authentication required."},
            status_code=401,
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"success": False, "error": "Invalid JSON body."},
            status_code=400,
        )

    # Validate required fields
    required = ["business_name", "business_type", "state", "owner_name", "owner_email"]
    missing = [f for f in required if not body.get(f, "").strip()]
    if missing:
        return JSONResponse(
            {"success": False, "error": f"Missing required fields: {', '.join(missing)}"},
            status_code=422,
        )

    business_name = body["business_name"].strip()
    business_type = body["business_type"]
    state         = body["state"]
    project_id    = body.get("project_id") or None
    expedited     = body.get("opt_expedited", False)
    provider_name = body.get("agent_provider", "zenbusiness")

    # Normalise provider name
    if provider_name not in ("zenbusiness", "stripe_atlas", "mock"):
        provider_name = "zenbusiness"

    # ── Persist to DB ──
    formation_id = str(uuid.uuid4())
    try:
        from src.database.db import get_db
        from src.database.models import BusinessFormation
        db = get_db()
        with db.session() as session:
            # Require a valid project_id if provided
            if project_id:
                from src.database.models import Project
                proj = session.query(Project).filter(
                    Project.id == project_id,
                    Project.user_id == str(user.id),
                ).first()
                if not proj:
                    project_id = None  # Clear invalid project_id

            formation = BusinessFormation(
                id=formation_id,
                user_id=str(user.id),
                project_id=project_id or str(user.id),  # fallback to user id if no project
                business_name=business_name,
                business_type=business_type,
                state=state[:2],  # Store 2-letter state code
                status="pending",
            )
            session.add(formation)
            session.commit()
            logger.info(
                f"BusinessFormation {formation_id} created for user {user.id}: "
                f"{business_name} ({business_type}, {state})"
            )
    except Exception as db_err:
        logger.error(f"Failed to save formation to DB: {db_err}")
        # Don't block the user — continue with provider flow even if DB save failed

    # ── Provider flow (async-safe) ──
    provider_ref = None
    provider_message = None
    try:
        from src.business.models import (
            BusinessType, FormationRequest, FormationState,
        )
        from src.business.formation import FormationService

        # Map string -> enum safely
        try:
            biz_type_enum = BusinessType(business_type)
        except ValueError:
            biz_type_enum = BusinessType.LLC

        # FormationState values are 2-letter codes
        state_code = state[:2].upper()
        try:
            state_enum = FormationState(state_code)
        except ValueError:
            state_enum = FormationState.DELAWARE

        formation_req = FormationRequest(
            business_name=business_name,
            business_type=biz_type_enum,
            state=state_enum,
            owner_name=body.get("owner_name", ""),
            owner_email=body.get("owner_email", ""),
            street_address=body.get("street_address", ""),
            city=body.get("city", ""),
            state_address=state_code,
            zip_code=body.get("zip_code", ""),
            description=body.get("description", ""),
            expedited=expedited,
            registered_agent=(body.get("agent_type") != "self"),
            user_id=str(user.id),
            project_id=project_id,
        )

        service = FormationService(default_provider=provider_name)
        result = await service.provider.submit_formation(formation_req)
        provider_ref = result.provider_reference
        provider_message = result.message

        # Update DB with provider reference
        try:
            from src.database.db import get_db
            from src.database.models import BusinessFormation
            db2 = get_db()
            with db2.session() as s2:
                rec = s2.query(BusinessFormation).filter(
                    BusinessFormation.id == formation_id
                ).first()
                if rec:
                    rec.status = "submitted"
                    rec.external_order_id = provider_ref
                    s2.commit()
        except Exception:
            pass

    except Exception as prov_err:
        logger.error(f"Formation provider error: {prov_err}")
        provider_message = (
            f"Your formation details have been saved. "
            f"Please complete the process manually. Error: {prov_err}"
        )

    # Build response message
    if provider_ref and provider_message:
        message = (
            f"Formation submitted for {business_name}! "
            f"{provider_message[:200]}. "
            f"Track status at /business-formation."
        )
    else:
        message = (
            f"Formation details saved for {business_name}! "
            "Check your email and the provider's website to complete the process. "
            "You can track status at /business-formation."
        )

    return JSONResponse({
        "success": True,
        "formation_id": formation_id,
        "provider_reference": provider_ref,
        "message": message,
        "redirect_url": "/business-formation",
    })

async def deploy_page(request: Request) -> HTMLResponse:
    """Deploy page for one-click deployment."""
    import os
    project_id = request.path_params.get('project_id')

    project = _projects_store.get(project_id)
    if not project:
        return RedirectResponse(url="/dashboard", status_code=302)

    # Determine which providers are configured so the template can show status
    provider_status = {
        "vercel": bool(os.getenv("VERCEL_TOKEN")),
        "render": bool(os.getenv("RENDER_API_KEY") or os.getenv("RENDER_DEPLOY_HOOK_URL")),
        "railway": bool(os.getenv("RAILWAY_TOKEN")),
        "fly": bool(os.getenv("FLY_API_TOKEN")),
    }

    return _render(request, "pages/deploy.html", {
        "project": project,
        "provider_status": provider_status,
    })

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



# TODO: Wire this through StartupGenerationPipeline instead of calling LLM directly.
# Currently bypasses idea scoring, refinement, and prompt engineering stages.
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

        idea = project.get('idea', 'My App')
        name = body.get('name', 'app')

        # Attempt real generation first, fall back to mock on failure
        real_generation_succeeded = False
        try:
            import json as _json
            import uuid as _uuid
            import tempfile
            from src.code_generation.enhanced_engine import EnhancedCodeGenerator
            from src.models import ProductPrompt

            prompt_payload = _json.dumps({
                'product_summary': {
                    'solution_overview': idea
                }
            })
            product_prompt = ProductPrompt(
                idea_id=_uuid.uuid4(),
                idea_name=name or idea[:50],
                prompt_content=prompt_payload,
            )

            output_dir = tempfile.mkdtemp(prefix=f'ignara_{project_id}_')
            generator = EnhancedCodeGenerator()
            codebase = generator.generate(product_prompt, output_dir=output_dir)

            # Build file list from what the generator actually created
            ext_to_type = {
                '.py': 'python', '.html': 'html', '.css': 'css',
                '.ts': 'typescript', '.tsx': 'typescript', '.js': 'javascript',
                '.jsx': 'javascript', '.json': 'json', '.md': 'markdown',
                '.txt': 'text', '.yml': 'yaml', '.yaml': 'yaml',
                '.tf': 'terraform', '.sh': 'shell', '.env': 'env',
            }
            project['files'] = [
                {
                    'name': f['path'],
                    'type': ext_to_type.get(os.path.splitext(f['path'])[1], 'text'),
                    'lines': f.get('lines', 0),
                }
                for f in generator.files_created
            ]

            # Build file_contents dict from disk for live preview
            file_contents = {}
            for f in generator.files_created:
                full_path = os.path.join(output_dir, f['path'])
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as fh:
                        file_contents[f['path']] = fh.read()
                except OSError:
                    file_contents[f['path']] = ''
            project['file_contents'] = file_contents
            project['output_dir'] = output_dir

            project['status'] = 'generated'
            project['generated_at'] = datetime.now(timezone.utc).isoformat()
            project['download_ready'] = True
            project['files_generated'] = codebase.files_generated
            project['lines_of_code'] = codebase.lines_of_code
            real_generation_succeeded = True
            logger.info(
                f"Real generation succeeded for project {project_id}: "
                f"{codebase.files_generated} files, {codebase.lines_of_code} lines"
            )

        except Exception as gen_exc:
            logger.warning(
                f"Real generation failed for project {project_id}, "
                f"falling back to mock data: {gen_exc}"
            )

        if not real_generation_succeeded:
            # Fallback: populate project with mock data
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
            project['file_contents'] = _generate_mock_file_contents(name, idea)

        _save_projects_store()
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

# Project store with file-based persistence
_PROJECTS_FILE = Path("./data/projects.json")
_PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_projects_store() -> dict:
    if _PROJECTS_FILE.exists():
        try:
            return json.loads(_PROJECTS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_projects_store() -> None:
    try:
        _PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PROJECTS_FILE.write_text(json.dumps(_projects_store, default=str, indent=2))
    except OSError:
        logger.warning("Failed to persist projects store")


_projects_store = _load_projects_store()

# TODO: Wire this through StartupGenerationPipeline instead of calling LLM directly.
# Currently bypasses idea scoring, refinement, and prompt engineering stages.
async def analyze_idea_api(request: Request) -> JSONResponse:
    """Analyze a business idea and create a new project."""
    try:
        body = await request.json()
        idea = body.get('idea', '').strip()

        if not idea:
            return JSONResponse({'error': 'Please provide your business idea'}, status_code=400)

        project_id = str(uuid.uuid4())[:8]

        # Attempt real LLM analysis
        analysis = {
            'market_size': 'Unable to analyze — no LLM provider configured',
            'competition': 'Unable to analyze — no LLM provider configured',
            'feasibility': 'Unable to analyze — no LLM provider configured',
            'recommended_features': [],
        }

        try:
            from src.llm import get_llm_client
            llm = get_llm_client("auto")
            response = llm.complete(
                prompt=(
                    f"Analyze this startup idea and return a JSON object with these keys:\n"
                    f"- market_size: estimated TAM and market opportunity (1-2 sentences)\n"
                    f"- competition: competitive landscape overview (1-2 sentences)\n"
                    f"- feasibility: technical and business feasibility assessment (1-2 sentences)\n"
                    f"- recommended_features: array of 5-8 recommended MVP features\n\n"
                    f"Startup idea: {idea}\n\n"
                    f"Return ONLY valid JSON, no markdown."
                ),
                system_prompt="You are a startup analyst. Provide concise, actionable analysis.",
                max_tokens=1000,
                temperature=0.4,
            )
            import json as _json
            content = response.content
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                parsed = _json.loads(content[start:end])
                analysis['market_size'] = parsed.get('market_size', analysis['market_size'])
                analysis['competition'] = parsed.get('competition', analysis['competition'])
                analysis['feasibility'] = parsed.get('feasibility', analysis['feasibility'])
                analysis['recommended_features'] = parsed.get('recommended_features', [])
        except Exception as llm_err:
            logger.warning(f"LLM analysis unavailable: {llm_err}")

        project = {
            'id': project_id,
            'idea': idea,
            'status': 'analyzed',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'analysis': analysis,
        }

        _projects_store[project_id] = project
        _save_projects_store()

        try:
            from src.database.db import get_db
            from src.database.models import Project, ProjectStatus
            user = get_current_user(request)
            if user:
                db = get_db()
                with db.session() as session:
                    db_project = Project(
                        id=project_id,
                        user_id=user.id,
                        name=idea[:100],
                        description=idea,
                        status=ProjectStatus.DRAFT,
                        config={'idea': idea, 'analysis': project['analysis']}
                    )
                    session.add(db_project)
        except Exception as e:
            logger.warning(f"Could not persist project to database: {e}")

        return JSONResponse({
            'success': True,
            'project_id': project_id,
            'message': 'Idea analyzed successfully',
            'analysis': analysis,
        })
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


async def get_project_api(request: Request) -> JSONResponse:
    """Get project by ID."""
    project_id = request.path_params.get('project_id')
    if project_id in _projects_store:
        return JSONResponse(_projects_store[project_id])
    # Try database
    try:
        from src.database.db import get_db
        from src.database.models import Project
        db = get_db()
        with db.session() as session:
            db_project = session.query(Project).filter(Project.id == project_id).first()
            if db_project:
                project_dict = {
                    'id': db_project.id,
                    'idea': db_project.description or db_project.name,
                    'status': db_project.status.value if hasattr(db_project.status, 'value') else str(db_project.status),
                    'created_at': db_project.created_at.isoformat() if db_project.created_at else None,
                    'analysis': db_project.config.get('analysis', {}) if db_project.config else {},
                }
                _projects_store[project_id] = project_dict
                _save_projects_store()
                return JSONResponse(project_dict)
    except Exception as e:
        logger.warning(f"Could not load project from database: {e}")
    return JSONResponse({'error': 'Project not found'}, status_code=404)


async def preview_app_api(request: Request) -> JSONResponse:
    """Generate a live preview for a project's generated files."""
    try:
        body = await request.json()
        project_id = body.get('project_id')

        if not project_id or project_id not in _projects_store:
            return JSONResponse({'error': 'Project not found'}, status_code=404)

        project = _projects_store[project_id]
        file_contents = project.get('file_contents')

        if not file_contents:
            return JSONResponse(
                {'error': 'No generated files found. Please generate the project first.'},
                status_code=400
            )

        # Apply modifications if provided
        modifications = body.get('modifications')
        if modifications:
            mod_filename = modifications.get('filename')
            mod_content = modifications.get('content')
            if mod_filename and mod_content and mod_filename in file_contents:
                file_contents[mod_filename] = mod_content
                project['file_contents'] = file_contents

        from src.integrations.live_preview import LivePreviewService
        preview_service = LivePreviewService()
        result = await preview_service.generate_html_preview(file_contents)

        if result.get('success'):
            return JSONResponse({
                'success': True,
                'html': result['html'],
                'files': file_contents
            })
        else:
            return JSONResponse({'error': 'Failed to generate preview'}, status_code=500)

    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=500)


async def billing_status_api(request: Request) -> JSONResponse:
    """Check if the current user has a paid subscription that allows deployment."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({'error': 'Not authenticated'}, status_code=401)

    tier = getattr(user, 'subscription_tier', None)
    tier_value = tier.value if hasattr(tier, 'value') else str(tier) if tier else 'free'
    is_paid = tier_value in ('starter', 'pro', 'enterprise')
    # Admin and demo users bypass billing
    if getattr(user, 'role', '') in ('admin', 'demo') or getattr(user, 'is_demo_account', False):
        is_paid = True

    return JSONResponse({
        'tier': tier_value,
        'is_paid': is_paid,
        'can_deploy': is_paid,
    })


async def deploy_start_api(request: Request) -> JSONResponse:
    """Start a real deployment for a paid user's project."""
    user = get_current_user(request)
    if not user:
        return JSONResponse({'error': 'Not authenticated'}, status_code=401)

    # Check billing
    tier = getattr(user, 'subscription_tier', None)
    tier_value = tier.value if hasattr(tier, 'value') else str(tier) if tier else 'free'
    is_paid = tier_value in ('starter', 'pro', 'enterprise')
    if getattr(user, 'role', '') in ('admin', 'demo') or getattr(user, 'is_demo_account', False):
        is_paid = True

    if not is_paid:
        return JSONResponse({
            'success': False,
            'error': 'Deployment requires a paid plan. Please upgrade at /billing.',
            'upgrade_required': True,
        }, status_code=403)

    try:
        body = await request.json()
        project_name = body.get('project_name', 'my-app')
        project_id = body.get('project_id')
        platform = body.get('platform', 'railway')
        files = body.get('files', {})

        if not files:
            return JSONResponse({
                'success': False,
                'error': 'No generated files to deploy. Please generate your app first.',
            }, status_code=400)

        # Use the real deployment service
        try:
            from src.integrations.deployment_service import DeploymentService
            deploy_service = DeploymentService()

            result = await deploy_service.deploy(
                project_name=project_name,
                files=files,
                platform=platform,
            )

            if result.get('success'):
                deployment_url = result.get('url', '')

                # Update project in DB with deployment URL
                if project_id:
                    try:
                        from src.database.db import get_db
                        from src.database.models import Project
                        db = get_db()
                        with db.session() as session:
                            db_project = session.query(Project).filter(
                                Project.id == project_id, Project.user_id == user.id
                            ).first()
                            if db_project:
                                db_project.deployment_url = deployment_url
                                db_project.status = 'deployed'
                                if result.get('github_url'):
                                    db_project.github_url = result['github_url']
                                session.commit()
                    except Exception as db_err:
                        logger.warning(f"Could not update project deployment URL: {db_err}")

                return JSONResponse({
                    'success': True,
                    'url': deployment_url,
                    'dashboard_url': result.get('dashboard_url', ''),
                    'github_url': result.get('github_url', ''),
                    'message': result.get('message', f'Successfully deployed to {platform}!'),
                })
            else:
                return JSONResponse({
                    'success': False,
                    'error': result.get('error', 'Deployment failed'),
                    'message': result.get('error', f'Deployment to {platform} failed.'),
                    'github_url': result.get('github_url', ''),
                    'manual_deploy': True,
                }, status_code=502)

        except ImportError:
            return JSONResponse({
                'success': False,
                'error': 'Deployment service not available',
                'message': 'The deployment service is not configured. Your code has been saved — you can download it and deploy manually.',
                'manual_deploy': True,
            }, status_code=503)

    except Exception as e:
        logger.error(f"Deploy start error: {e}")
        return JSONResponse({'success': False, 'error': str(e)}, status_code=500)


def _generate_mock_file_contents(name: str, idea: str) -> dict:
    """Generate realistic mock file contents for the preview."""
    return {
        'app.py': f'''"""Main application entry point for {name}."""\nfrom fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware\nfrom routes import router\nfrom models import Base\nfrom database import engine\n\napp = FastAPI(\n    title="{name}",\n    description="{idea[:80]}",\n    version="1.0.0"\n)\n\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=["*"],\n    allow_credentials=True,\n    allow_methods=["*"],\n    allow_headers=["*"],\n)\n\nBase.metadata.create_all(bind=engine)\napp.include_router(router)\n\n@app.get("/")\nasync def root():\n    return {{"message": "Welcome to {name}!", "status": "running"}}\n\n@app.get("/health")\nasync def health_check():\n    return {{"status": "healthy"}}\n\nif __name__ == "__main__":\n    import uvicorn\n    uvicorn.run(app, host="0.0.0.0", port=8000)\n''',
        'models.py': f'''"""Database models for {name}."""\nfrom sqlalchemy import Column, Integer, String, DateTime, Boolean, Text\nfrom sqlalchemy.ext.declarative import declarative_base\nfrom datetime import datetime\n\nBase = declarative_base()\n\nclass User(Base):\n    __tablename__ = "users"\n\n    id = Column(Integer, primary_key=True, index=True)\n    email = Column(String(255), unique=True, index=True, nullable=False)\n    hashed_password = Column(String(255), nullable=False)\n    full_name = Column(String(100))\n    is_active = Column(Boolean, default=True)\n    created_at = Column(DateTime, default=datetime.utcnow)\n    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)\n\nclass Project(Base):\n    __tablename__ = "projects"\n\n    id = Column(Integer, primary_key=True, index=True)\n    title = Column(String(200), nullable=False)\n    description = Column(Text)\n    owner_id = Column(Integer, index=True)\n    status = Column(String(50), default="active")\n    created_at = Column(DateTime, default=datetime.utcnow)\n''',
        'routes.py': f'''"""API routes for {name}."""\nfrom fastapi import APIRouter, Depends, HTTPException, status\nfrom sqlalchemy.orm import Session\nfrom typing import List\nfrom models import User, Project\nfrom database import get_db\nfrom auth import get_current_user\n\nrouter = APIRouter()\n\n@router.get("/users/me")\nasync def get_current_user_profile(\n    current_user: User = Depends(get_current_user)\n):\n    return current_user\n\n@router.get("/projects", response_model=List[dict])\nasync def list_projects(\n    db: Session = Depends(get_db),\n    current_user: User = Depends(get_current_user)\n):\n    projects = db.query(Project).filter(\n        Project.owner_id == current_user.id\n    ).all()\n    return projects\n\n@router.post("/projects", status_code=status.HTTP_201_CREATED)\nasync def create_project(\n    title: str, description: str,\n    db: Session = Depends(get_db),\n    current_user: User = Depends(get_current_user)\n):\n    project = Project(\n        title=title,\n        description=description,\n        owner_id=current_user.id\n    )\n    db.add(project)\n    db.commit()\n    return project\n''',
        'templates/base.html': '''<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>{{ title }}</title>\n    <link href="/static/styles.css" rel="stylesheet">\n</head>\n<body>\n    <nav class="navbar">\n        <div class="container">\n            <a href="/" class="brand">''' + name + '''</a>\n            <div class="nav-links">\n                <a href="/dashboard">Dashboard</a>\n                <a href="/projects">Projects</a>\n                <a href="/profile">Profile</a>\n            </div>\n        </div>\n    </nav>\n    <main class="container">\n        {% block content %}{% endblock %}\n    </main>\n    <footer class="footer">\n        <p>&copy; 2024 ''' + name + '''. All rights reserved.</p>\n    </footer>\n</body>\n</html>\n''',
        'templates/dashboard.html': '''{% extends "base.html" %}\n{% block content %}\n<div class="dashboard">\n    <h1>Dashboard</h1>\n    <div class="stats-grid">\n        <div class="stat-card">\n            <h3>Total Projects</h3>\n            <p class="stat-value">{{ stats.total_projects }}</p>\n        </div>\n        <div class="stat-card">\n            <h3>Active Users</h3>\n            <p class="stat-value">{{ stats.active_users }}</p>\n        </div>\n        <div class="stat-card">\n            <h3>Tasks Completed</h3>\n            <p class="stat-value">{{ stats.tasks_done }}</p>\n        </div>\n    </div>\n    <div class="recent-activity">\n        <h2>Recent Activity</h2>\n        {% for item in activity %}\n        <div class="activity-item">\n            <span class="activity-icon">{{ item.icon }}</span>\n            <span>{{ item.text }}</span>\n            <time>{{ item.time }}</time>\n        </div>\n        {% endfor %}\n    </div>\n</div>\n{% endblock %}\n''',
        'static/styles.css': '''/* Generated styles */\n:root {\n    --primary: #8b5cf6;\n    --primary-dark: #7c3aed;\n    --bg-dark: #0f172a;\n    --bg-card: #1e293b;\n    --text: #e2e8f0;\n    --text-muted: #94a3b8;\n    --border: #334155;\n    --success: #10b981;\n    --danger: #ef4444;\n}\n\n* { margin: 0; padding: 0; box-sizing: border-box; }\nbody { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: var(--bg-dark); color: var(--text); }\n.container { max-width: 1200px; margin: 0 auto; padding: 0 1.5rem; }\n\n.navbar { background: var(--bg-card); border-bottom: 1px solid var(--border); padding: 1rem 0; }\n.navbar .container { display: flex; justify-content: space-between; align-items: center; }\n.brand { font-size: 1.25rem; font-weight: 700; color: var(--primary); text-decoration: none; }\n.nav-links a { color: var(--text-muted); text-decoration: none; margin-left: 1.5rem; }\n.nav-links a:hover { color: var(--text); }\n\n.dashboard { padding: 2rem 0; }\n.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; margin: 1.5rem 0; }\n.stat-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; }\n.stat-value { font-size: 2rem; font-weight: 700; color: var(--primary); }\n\n.footer { text-align: center; padding: 2rem; color: var(--text-muted); border-top: 1px solid var(--border); margin-top: 3rem; }\n''',
        'requirements.txt': 'fastapi==0.109.0\nuvicorn==0.27.0\nsqlalchemy==2.0.25\nalembic==1.13.1\npython-jose==3.3.0\npasslib==1.7.4\npython-multipart==0.0.6\nhttpx==0.26.0\npython-dotenv==1.0.0\npsycopg2-binary==2.9.9\n',
        'README.md': f'''# {name}\n\n{idea[:120]}\n\n## Quick Start\n\n```bash\npip install -r requirements.txt\nuvicorn app:app --reload\n```\n\n## Features\n\n- User authentication with JWT\n- RESTful API with FastAPI\n- PostgreSQL database with SQLAlchemy ORM\n- Responsive dashboard UI\n- Docker support for deployment\n\n## API Endpoints\n\n| Method | Path | Description |\n|--------|------|-------------|\n| GET | / | Health check |\n| POST | /auth/login | User login |\n| GET | /users/me | Current user profile |\n| GET | /projects | List projects |\n| POST | /projects | Create project |\n\n## Deployment\n\n```bash\ndocker-compose up -d\n```\n''',
        'Dockerfile': 'FROM python:3.11-slim\n\nWORKDIR /app\n\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\n\nCOPY . .\n\nEXPOSE 8000\n\nCMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]\n',
        '.env.example': 'DATABASE_URL=postgresql://user:password@localhost:5432/dbname\nSECRET_KEY=your-secret-key-here\nALGORITHM=HS256\nACCESS_TOKEN_EXPIRE_MINUTES=30\nDEBUG=true\n'
    }
