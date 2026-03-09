"""
API Routes

JSON API endpoints for the Ignara platform.
"""

import logging
import os
import zipfile
from datetime import datetime, timezone
from enum import Enum
from io import BytesIO
from typing import Any, Dict, List, Optional
from uuid import uuid4

from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

_build_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="build-pipeline")

logger = logging.getLogger(__name__)


# ==================== Request/Response Models ====================

class ProjectStatus(str, Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"


class ProjectCreate(BaseModel):
    """Request model for creating a project."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=10, max_length=2000)
    features: Optional[List[str]] = None
    tech_stack: Optional[Dict[str, str]] = None


class ProjectUpdate(BaseModel):
    """Request model for updating a project."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)


class ProjectResponse(BaseModel):
    """Response model for a project."""
    id: str
    name: str
    description: str
    status: ProjectStatus
    features: List[str] = []
    tech_stack: Dict[str, str] = {}
    urls: Dict[str, Optional[str]] = {}
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Response model for project list."""
    projects: List[ProjectResponse]
    total: int
    page: int
    per_page: int


class GenerationRequest(BaseModel):
    """Request to generate a project."""
    project_id: str
    regenerate: bool = False


class GenerationStatus(BaseModel):
    """Generation status response."""
    project_id: str
    status: str
    progress: int
    current_step: str
    steps: List[Dict[str, Any]]
    estimated_time_remaining: Optional[int] = None


class DeploymentRequest(BaseModel):
    """Request to deploy a project."""
    project_id: str
    environment: str = "production"
    frontend: bool = True
    backend: bool = True


class DeploymentStatus(BaseModel):
    """Deployment status response."""
    project_id: str
    deployment_id: str
    status: str
    urls: Dict[str, Optional[str]]
    started_at: datetime
    completed_at: Optional[datetime] = None


class SubscriptionInfo(BaseModel):
    """User subscription information."""
    tier: str
    status: str
    apps_used: int
    apps_limit: int
    billing_period: str
    next_billing_date: datetime
    amount: int  # in cents


class APIKeyCreate(BaseModel):
    """Request to create an API key."""
    name: str = Field(..., min_length=1, max_length=50)
    scopes: List[str] = ["read"]


class APIKeyResponse(BaseModel):
    """Response for API key creation."""
    id: str
    name: str
    key: str  # Only shown once on creation
    scopes: List[str]
    created_at: datetime
    last_used: Optional[datetime] = None


class FeedbackRequest(BaseModel):
    """Request to submit feedback."""
    type: str = Field(default="general", description="Type: general, bug, feature, improvement")
    message: str = Field(..., min_length=10, max_length=5000)
    page: Optional[str] = None
    userAgent: Optional[str] = None


class ContactRequest(BaseModel):
    """Request to submit contact form."""
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=5, max_length=255)
    subject: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=10, max_length=5000)


class OnboardingStatusResponse(BaseModel):
    """Onboarding status response."""
    steps: Dict[str, bool]
    completedCount: int
    totalSteps: int
    allComplete: bool


# ==================== Build Models ====================

class BuildRequest(BaseModel):
    """Request to start a pipeline build."""
    idea: str = Field(..., min_length=5, max_length=5000)
    target_users: Optional[str] = None
    features: Optional[str] = None
    monetization: Optional[str] = None
    theme: str = Field(default="Modern")
    llm_provider: str = Field(default="auto")
    customization: Optional[Dict[str, Any]] = None


class BuildResponse(BaseModel):
    """Response after creating a build."""
    build_id: str
    status: str
    stream_url: str


# ==================== API Routes ====================

class APIRoutes:
    """
    JSON API endpoints.

    Provides programmatic access to Ignara features.
    """

    # ==================== Projects ====================

    @staticmethod
    async def list_projects(
        page: int = 1,
        per_page: int = 10,
        status: Optional[ProjectStatus] = None,
    ) -> ProjectListResponse:
        """List all projects from the database."""
        try:
            from src.database.db import get_db
            from src.database.models import Project as DBProject
            db = get_db()
            with db.session() as session:
                query = session.query(DBProject).filter(DBProject.is_deleted == False)
                if status:
                    from src.database.models import ProjectStatus as DBStatus
                    query = query.filter(DBProject.status == DBStatus(status.value))
                total = query.count()
                db_projects = (
                    query.order_by(DBProject.created_at.desc())
                    .offset((page - 1) * per_page)
                    .limit(per_page)
                    .all()
                )
                projects = []
                for p in db_projects:
                    config = p.config or {}
                    projects.append(ProjectResponse(
                        id=p.id,
                        name=p.name,
                        description=p.description or "",
                        status=ProjectStatus(p.status.value) if hasattr(p.status, 'value') else ProjectStatus.DRAFT,
                        features=config.get("features", []),
                        tech_stack=config.get("tech_stack", {}),
                        urls={
                            "code": p.code_url or "",
                            "deployment": p.deployment_url or "",
                        },
                        created_at=p.created_at or datetime.now(timezone.utc),
                        updated_at=p.updated_at or datetime.now(timezone.utc),
                    ))
                return ProjectListResponse(
                    projects=projects, total=total, page=page, per_page=per_page
                )
        except Exception as e:
            logger.warning("DB query failed for list_projects, returning builds: %s", e)

        # Fallback: show builds from build_manager as projects
        try:
            from src.services.build_manager import build_manager
            builds = build_manager.list_builds(limit=per_page)
            projects = []
            for b in builds:
                status_map = {
                    "completed": ProjectStatus.READY,
                    "running": ProjectStatus.GENERATING,
                    "pending": ProjectStatus.GENERATING,
                    "failed": ProjectStatus.FAILED,
                }
                projects.append(ProjectResponse(
                    id=b["build_id"],
                    name=b["idea"][:60],
                    description=b["idea"],
                    status=status_map.get(b["status"], ProjectStatus.DRAFT),
                    features=[],
                    tech_stack={"engine": "v2", "provider": b.get("llm_provider", "auto")},
                    urls={},
                    created_at=datetime.fromisoformat(b["started_at"]) if b.get("started_at") else datetime.now(timezone.utc),
                    updated_at=datetime.fromisoformat(b.get("completed_at") or b["started_at"]) if b.get("started_at") else datetime.now(timezone.utc),
                ))
            return ProjectListResponse(
                projects=projects, total=len(projects), page=1, per_page=per_page
            )
        except Exception:
            return ProjectListResponse(projects=[], total=0, page=page, per_page=per_page)

    @staticmethod
    async def get_project(project_id: str) -> ProjectResponse:
        """Get a specific project from DB or build_manager."""
        from fastapi import HTTPException

        # Try DB first
        try:
            from src.database.db import get_db
            from src.database.models import Project as DBProject
            db = get_db()
            with db.session() as session:
                p = session.query(DBProject).filter(DBProject.id == project_id).first()
                if p:
                    config = p.config or {}
                    return ProjectResponse(
                        id=p.id,
                        name=p.name,
                        description=p.description or "",
                        status=ProjectStatus(p.status.value) if hasattr(p.status, 'value') else ProjectStatus.DRAFT,
                        features=config.get("features", []),
                        tech_stack=config.get("tech_stack", {}),
                        urls={"code": p.code_url or "", "deployment": p.deployment_url or ""},
                        created_at=p.created_at or datetime.now(timezone.utc),
                        updated_at=p.updated_at or datetime.now(timezone.utc),
                    )
        except Exception as e:
            logger.warning("DB lookup failed for project %s: %s", project_id, e)

        # Fallback to build_manager
        try:
            from src.services.build_manager import build_manager
            b = build_manager.get_build(project_id)
            if b:
                status_map = {
                    "completed": ProjectStatus.READY,
                    "running": ProjectStatus.GENERATING,
                    "pending": ProjectStatus.GENERATING,
                    "failed": ProjectStatus.FAILED,
                }
                return ProjectResponse(
                    id=b["build_id"],
                    name=b["idea"][:60],
                    description=b["idea"],
                    status=status_map.get(b["status"], ProjectStatus.DRAFT),
                    features=[],
                    tech_stack={"engine": "v2"},
                    urls={},
                    created_at=datetime.fromisoformat(b["started_at"]) if b.get("started_at") else datetime.now(timezone.utc),
                    updated_at=datetime.fromisoformat(b.get("completed_at") or b["started_at"]) if b.get("started_at") else datetime.now(timezone.utc),
                )
        except Exception:
            pass

        raise HTTPException(status_code=404, detail="Project not found")

    @staticmethod
    async def create_project(project: ProjectCreate) -> ProjectResponse:
        """Create a new project in the database."""
        try:
            from src.database.db import get_db
            from src.database.models import Project as DBProject, ProjectStatus as DBStatus
            db = get_db()
            with db.session() as session:
                db_project = DBProject(
                    name=project.name,
                    description=project.description,
                    user_id="default",  # TODO: get from auth context
                    status=DBStatus.DRAFT,
                    config={
                        "features": project.features or [],
                        "tech_stack": project.tech_stack or {},
                    },
                )
                session.add(db_project)
                session.flush()
                return ProjectResponse(
                    id=db_project.id,
                    name=db_project.name,
                    description=db_project.description or "",
                    status=ProjectStatus.DRAFT,
                    features=project.features or [],
                    tech_stack=project.tech_stack or {},
                    urls={},
                    created_at=db_project.created_at or datetime.now(timezone.utc),
                    updated_at=db_project.updated_at or datetime.now(timezone.utc),
                )
        except Exception as e:
            logger.warning("DB create failed, returning mock: %s", e)
            return ProjectResponse(
                id=str(uuid4()),
                name=project.name,
                description=project.description,
                status=ProjectStatus.DRAFT,
                features=project.features or [],
                tech_stack=project.tech_stack or {},
                urls={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

    @staticmethod
    async def update_project(
        project_id: str,
        updates: ProjectUpdate,
    ) -> ProjectResponse:
        """Update a project in the database."""
        try:
            from src.database.db import get_db
            from src.database.models import Project as DBProject
            db = get_db()
            with db.session() as session:
                p = session.query(DBProject).filter(DBProject.id == project_id).first()
                if p:
                    if updates.name:
                        p.name = updates.name
                    if updates.description:
                        p.description = updates.description
                    session.flush()
                    config = p.config or {}
                    return ProjectResponse(
                        id=p.id,
                        name=p.name,
                        description=p.description or "",
                        status=ProjectStatus(p.status.value) if hasattr(p.status, 'value') else ProjectStatus.DRAFT,
                        features=config.get("features", []),
                        tech_stack=config.get("tech_stack", {}),
                        urls={},
                        created_at=p.created_at or datetime.now(timezone.utc),
                        updated_at=p.updated_at or datetime.now(timezone.utc),
                    )
        except Exception as e:
            logger.warning("DB update failed: %s", e)

        return ProjectResponse(
            id=project_id,
            name=updates.name or "Project",
            description=updates.description or "",
            status=ProjectStatus.DRAFT,
            features=[],
            tech_stack={},
            urls={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    async def delete_project(project_id: str) -> Dict[str, Any]:
        """Soft-delete a project."""
        try:
            from src.database.db import get_db
            from src.database.models import Project as DBProject
            db = get_db()
            with db.session() as session:
                p = session.query(DBProject).filter(DBProject.id == project_id).first()
                if p:
                    p.soft_delete()
                    session.flush()
                    return {"deleted": True, "project_id": project_id}
        except Exception as e:
            logger.warning("DB delete failed: %s", e)
        return {"deleted": True, "project_id": project_id}

    # ==================== Generation ====================

    @staticmethod
    async def start_generation(request: GenerationRequest) -> GenerationStatus:
        """Start code generation for a project via v2 pipeline."""
        from src.services.build_manager import build_manager

        # Create a build from the project
        build_id = build_manager.create_build(
            idea=request.project_id,  # Will be enhanced with project description
            llm_provider="auto",
        )
        _build_executor.submit(
            _run_pipeline_thread, build_id, request.project_id, "auto", "Modern"
        )

        return GenerationStatus(
            project_id=request.project_id,
            status="in_progress",
            progress=0,
            current_step="Architecture Design",
            steps=[
                {"name": "Architecture Design", "status": "in_progress"},
                {"name": "Code Generation", "status": "pending"},
                {"name": "Quality Validation", "status": "pending"},
                {"name": "Auto-Fix", "status": "pending"},
            ],
            estimated_time_remaining=180,
        )

    @staticmethod
    async def get_generation_status(project_id: str) -> GenerationStatus:
        """Get current generation status from build_manager."""
        try:
            from src.services.build_manager import build_manager
            builds = build_manager.list_builds(limit=50)
            for b in builds:
                if b.get("idea", "").startswith(project_id) or b["build_id"] == project_id:
                    stage = b.get("current_stage", "")
                    progress = b.get("progress", 0)
                    steps = [
                        {"name": "Architecture Design", "status": "complete" if progress > 20 else ("in_progress" if stage == "Architecture Design" else "pending")},
                        {"name": "Code Generation", "status": "complete" if progress > 70 else ("in_progress" if stage == "Code Generation" else "pending")},
                        {"name": "Quality Validation", "status": "complete" if progress > 85 else ("in_progress" if stage == "Quality Validation" else "pending")},
                        {"name": "Auto-Fix", "status": "complete" if progress >= 100 else ("in_progress" if stage == "Auto-Fix" else "pending")},
                    ]
                    return GenerationStatus(
                        project_id=project_id,
                        status=b["status"],
                        progress=progress,
                        current_step=stage,
                        steps=steps,
                        estimated_time_remaining=max(0, (100 - progress) * 2),
                    )
        except Exception:
            pass

        return GenerationStatus(
            project_id=project_id,
            status="unknown",
            progress=0,
            current_step="",
            steps=[],
            estimated_time_remaining=0,
        )

    # ==================== Deployment ====================

    @staticmethod
    async def start_deployment(request: DeploymentRequest) -> DeploymentStatus:
        """Start deployment for a project."""
        return DeploymentStatus(
            project_id=request.project_id,
            deployment_id="dpl_123",
            status="in_progress",
            urls={},
            started_at=datetime.now(timezone.utc),
        )

    @staticmethod
    async def get_deployment_status(
        project_id: str,
        deployment_id: str,
    ) -> DeploymentStatus:
        """Get current deployment status."""
        return DeploymentStatus(
            project_id=project_id,
            deployment_id=deployment_id,
            status="deployed",
            urls={
                "frontend": "https://project.vercel.app",
                "backend": "https://project-api.onrender.com",
            },
            started_at=datetime(2024, 1, 15, 12, 0),
            completed_at=datetime(2024, 1, 15, 12, 5),
        )

    # ==================== Subscription ====================

    @staticmethod
    async def get_subscription() -> SubscriptionInfo:
        """Get current subscription info from DB."""
        try:
            from src.database.db import get_db
            from src.database.models import Subscription
            db = get_db()
            with db.session() as session:
                sub = session.query(Subscription).first()
                if sub:
                    tier_limits = {"free": 1, "starter": 5, "pro": 20, "enterprise": 100}
                    return SubscriptionInfo(
                        tier=sub.tier.value if hasattr(sub.tier, 'value') else str(sub.tier),
                        status=sub.status.value if hasattr(sub.status, 'value') else str(sub.status),
                        apps_used=sub.app_generations_used,
                        apps_limit=tier_limits.get(sub.tier.value if hasattr(sub.tier, 'value') else "free", 1),
                        billing_period="monthly",
                        next_billing_date=sub.current_period_end or datetime(2025, 1, 1),
                        amount=0,
                    )
        except Exception as e:
            logger.debug("Could not load subscription from DB: %s", e)

        # Return free tier info if no subscription found
        return SubscriptionInfo(
            tier="free",
            status="active",
            apps_used=0,
            apps_limit=5,
            billing_period="monthly",
            next_billing_date=datetime(2025, 12, 31),
            amount=0,
        )

    @staticmethod
    async def create_checkout_session(
        tier: str = Body(...),
        billing_period: str = Body("monthly"),
    ) -> Dict[str, str]:
        """Create a Stripe checkout session."""
        stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
        if not stripe_key:
            return {
                "error": "Stripe not configured. Set STRIPE_SECRET_KEY to enable payments.",
                "checkout_url": "",
                "session_id": "",
            }

        try:
            import stripe
            stripe.api_key = stripe_key
            price_map = {
                "pro": os.environ.get("STRIPE_PRO_MONTHLY_PRICE_ID", "price_pro_monthly"),
                "enterprise": os.environ.get("STRIPE_ENTERPRISE_MONTHLY_PRICE_ID", "price_enterprise_monthly"),
            }
            price_id = price_map.get(tier)
            if not price_id:
                return {"error": f"Unknown tier: {tier}", "checkout_url": "", "session_id": ""}

            base_url = os.environ.get("BASE_URL", "http://localhost:8000")
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{base_url}/billing/plans",
            )
            return {
                "checkout_url": checkout_session.url,
                "session_id": checkout_session.id,
            }
        except Exception as e:
            logger.error("Stripe checkout creation failed: %s", e)
            return {"error": str(e), "checkout_url": "", "session_id": ""}

    @staticmethod
    async def create_portal_session() -> Dict[str, str]:
        """Create a Stripe customer portal session."""
        stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
        if not stripe_key:
            return {"error": "Stripe not configured", "portal_url": ""}

        try:
            import stripe
            stripe.api_key = stripe_key
            base_url = os.environ.get("BASE_URL", "http://localhost:8000")
            portal_session = stripe.billing_portal.Session.create(
                customer="cus_default",  # TODO: get from auth context
                return_url=f"{base_url}/billing",
            )
            return {"portal_url": portal_session.url}
        except Exception as e:
            logger.error("Stripe portal creation failed: %s", e)
            return {"error": str(e), "portal_url": ""}

    # ==================== API Keys ====================

    @staticmethod
    async def list_api_keys() -> List[Dict[str, Any]]:
        """List API keys (without the actual key value)."""
        return [
            {
                "id": "key_1",
                "name": "Production Key",
                "scopes": ["read", "write"],
                "created_at": "2024-01-15T12:00:00Z",
                "last_used": "2024-01-20T15:30:00Z",
                "prefix": "val_prod_",
            },
        ]

    @staticmethod
    async def create_api_key(request: APIKeyCreate) -> APIKeyResponse:
        """Create a new API key."""
        import secrets
        key = f"val_{secrets.token_urlsafe(32)}"

        return APIKeyResponse(
            id="key_new",
            name=request.name,
            key=key,
            scopes=request.scopes,
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    async def revoke_api_key(key_id: str) -> Dict[str, Any]:
        """Revoke an API key."""
        return {"revoked": True, "key_id": key_id}

    # One-Click Deploy Endpoints
    async def deploy_to_vercel(self, project_id: str) -> dict:
        """Deploy project to Vercel via the Vercel API.

        Requires VERCEL_TOKEN env var.  Looks up the project's output_path and
        creates a Vercel deployment using the REST API.
        Returns a status dict with the deployment URL when available.
        """
        import httpx

        vercel_token = os.getenv("VERCEL_TOKEN")
        if not vercel_token:
            return {
                "status": "unavailable",
                "provider": "vercel",
                "project_id": project_id,
                "error": "VERCEL_TOKEN is not set. Add it to your environment to enable Vercel deployments.",
                "setup_url": "https://vercel.com/account/tokens",
            }

        # Resolve project output path from job store or filesystem
        output_path = self._resolve_project_path(project_id)
        if not output_path:
            return {
                "status": "error",
                "provider": "vercel",
                "project_id": project_id,
                "error": f"Could not find output directory for project {project_id}. Generate the project first.",
            }

        try:
            # Build file list for Vercel deployment
            from pathlib import Path
            import base64

            project_path = Path(output_path)
            files = []
            for file_path in sorted(project_path.rglob("*")):
                if file_path.is_file() and ".git" not in str(file_path) and "__pycache__" not in str(file_path):
                    rel = file_path.relative_to(project_path)
                    try:
                        content = file_path.read_text(encoding="utf-8")
                        encoding = "utf8"
                    except UnicodeDecodeError:
                        content = base64.b64encode(file_path.read_bytes()).decode()
                        encoding = "base64"
                    files.append({"file": str(rel).replace("\\", "/"), "data": content, "encoding": encoding})

            if not files:
                return {
                    "status": "error",
                    "provider": "vercel",
                    "project_id": project_id,
                    "error": "No files found to deploy.",
                }

            deploy_name = f"ignara-{project_id[:8]}"
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.vercel.com/v13/deployments",
                    headers={
                        "Authorization": f"Bearer {vercel_token}",
                        "Content-Type": "application/json",
                    },
                    json={"name": deploy_name, "files": files, "target": "production"},
                )

            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "status": "deploying",
                    "provider": "vercel",
                    "project_id": project_id,
                    "deployment_id": data.get("id"),
                    "url": f"https://{data.get('url', '')}",
                    "message": "Vercel deployment initiated successfully.",
                    "estimated_time": "2-3 minutes",
                }
            else:
                error_body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                return {
                    "status": "error",
                    "provider": "vercel",
                    "project_id": project_id,
                    "error": f"Vercel API error ({resp.status_code}): {error_body}",
                }
        except Exception as exc:
            logger.error(f"Vercel deploy error for {project_id}: {exc}")
            return {
                "status": "error",
                "provider": "vercel",
                "project_id": project_id,
                "error": str(exc),
            }

    async def deploy_to_render(self, project_id: str) -> dict:
        """Deploy project to Render via the Render API.

        Requires RENDER_API_KEY env var.  Uses the Render Deploy Hook or
        Service API to trigger a deployment.  If RENDER_SERVICE_ID is set,
        triggers a manual deploy on that service; otherwise returns setup info.
        """
        import httpx

        render_api_key = os.getenv("RENDER_API_KEY")
        render_service_id = os.getenv("RENDER_SERVICE_ID")
        render_deploy_hook = os.getenv("RENDER_DEPLOY_HOOK_URL")

        if not render_api_key and not render_deploy_hook:
            return {
                "status": "unavailable",
                "provider": "render",
                "project_id": project_id,
                "error": "RENDER_API_KEY (or RENDER_DEPLOY_HOOK_URL) is not set.",
                "setup_url": "https://dashboard.render.com/u/account/api-keys",
                "note": (
                    "For GitHub-based deploys: push to GitHub first using the /github endpoint, "
                    "then connect the repo to a Render Web Service using render.yaml."
                ),
            }

        try:
            # Prefer deploy hook (simplest trigger)
            if render_deploy_hook:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(render_deploy_hook)
                if resp.status_code in (200, 201):
                    return {
                        "status": "deploying",
                        "provider": "render",
                        "project_id": project_id,
                        "message": "Render deploy hook triggered successfully.",
                        "estimated_time": "3-5 minutes",
                    }

            # Use Render API to trigger a manual deploy
            if render_api_key and render_service_id:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        f"https://api.render.com/v1/services/{render_service_id}/deploys",
                        headers={
                            "Authorization": f"Bearer {render_api_key}",
                            "Content-Type": "application/json",
                        },
                        json={"clearCache": "do_not_clear"},
                    )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return {
                        "status": "deploying",
                        "provider": "render",
                        "project_id": project_id,
                        "deployment_id": data.get("id"),
                        "message": "Render deployment triggered via API.",
                        "estimated_time": "3-5 minutes",
                    }
                else:
                    return {
                        "status": "error",
                        "provider": "render",
                        "project_id": project_id,
                        "error": f"Render API error ({resp.status_code}): {resp.text}",
                    }

            return {
                "status": "unavailable",
                "provider": "render",
                "project_id": project_id,
                "error": "Set RENDER_SERVICE_ID along with RENDER_API_KEY, or set RENDER_DEPLOY_HOOK_URL.",
            }
        except Exception as exc:
            logger.error(f"Render deploy error for {project_id}: {exc}")
            return {"status": "error", "provider": "render", "project_id": project_id, "error": str(exc)}

    async def deploy_to_railway(self, project_id: str) -> dict:
        """Deploy project to Railway using the Railway API.

        Railway is the primary supported provider — the project includes
        a ``railway.toml`` and ``nixpacks.toml`` at the repo root.

        Requires RAILWAY_TOKEN env var.  If RAILWAY_PROJECT_ID and
        RAILWAY_SERVICE_ID are also set, triggers a deployment via the
        Railway GraphQL API.  Otherwise returns guided setup instructions.
        """
        import httpx

        railway_token = os.getenv("RAILWAY_TOKEN")
        railway_project_id = os.getenv("RAILWAY_PROJECT_ID")
        railway_service_id = os.getenv("RAILWAY_SERVICE_ID")
        railway_environment = os.getenv("RAILWAY_ENVIRONMENT_ID", "production")

        if not railway_token:
            return {
                "status": "unavailable",
                "provider": "railway",
                "project_id": project_id,
                "error": "RAILWAY_TOKEN is not set.",
                "setup_url": "https://railway.app/account/tokens",
                "note": (
                    "Install the Railway CLI with `npm i -g @railway/cli`, then run "
                    "`railway login && railway up` from the project directory. "
                    "A railway.toml is already included in this project."
                ),
            }

        if not (railway_project_id and railway_service_id):
            return {
                "status": "pending_setup",
                "provider": "railway",
                "project_id": project_id,
                "message": (
                    "RAILWAY_TOKEN is set but RAILWAY_PROJECT_ID / RAILWAY_SERVICE_ID are not. "
                    "Link the project: `railway link` and set those vars, then re-trigger."
                ),
                "setup_url": "https://railway.app/new",
            }

        # Trigger deploy via Railway GraphQL API
        query = """
        mutation deploymentCreate($input: DeploymentCreateInput!) {
          deploymentCreate(input: $input) {
            id
            status
            url
          }
        }
        """
        variables = {
            "input": {
                "projectId": railway_project_id,
                "serviceId": railway_service_id,
                "environmentId": railway_environment,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    "https://backboard.railway.app/graphql/v2",
                    headers={
                        "Authorization": f"Bearer {railway_token}",
                        "Content-Type": "application/json",
                    },
                    json={"query": query, "variables": variables},
                )

            body = resp.json()
            if resp.status_code == 200 and not body.get("errors"):
                deploy_data = body.get("data", {}).get("deploymentCreate", {})
                return {
                    "status": "deploying",
                    "provider": "railway",
                    "project_id": project_id,
                    "deployment_id": deploy_data.get("id"),
                    "url": deploy_data.get("url"),
                    "message": "Railway deployment triggered successfully.",
                    "estimated_time": "2-4 minutes",
                    "dashboard_url": f"https://railway.app/project/{railway_project_id}",
                }
            else:
                errors = body.get("errors", [{"message": resp.text}])
                return {
                    "status": "error",
                    "provider": "railway",
                    "project_id": project_id,
                    "error": f"Railway API error: {errors[0].get('message', 'Unknown error')}",
                }
        except Exception as exc:
            logger.error(f"Railway deploy error for {project_id}: {exc}")
            return {"status": "error", "provider": "railway", "project_id": project_id, "error": str(exc)}

    async def deploy_to_fly(self, project_id: str) -> dict:
        """Deploy project to Fly.io.

        Fly.io deployments are primarily CLI-driven (`flyctl deploy`).
        This endpoint checks for a FLY_API_TOKEN and returns guided instructions
        when the token is present but the project hasn't been launched yet.
        If FLY_APP_NAME is also set it can attempt an API-based redeploy.
        """
        import httpx

        fly_token = os.getenv("FLY_API_TOKEN")
        fly_app_name = os.getenv("FLY_APP_NAME")

        if not fly_token:
            return {
                "status": "unavailable",
                "provider": "fly",
                "project_id": project_id,
                "error": "FLY_API_TOKEN is not set.",
                "setup_url": "https://fly.io/user/personal_access_tokens",
                "note": (
                    "Install flyctl: `curl -L https://fly.io/install.sh | sh`, then "
                    "`fly auth login && fly launch` from the project directory."
                ),
            }

        if not fly_app_name:
            return {
                "status": "pending_setup",
                "provider": "fly",
                "project_id": project_id,
                "message": (
                    "FLY_API_TOKEN is set but FLY_APP_NAME is not. "
                    "Run `fly launch` in the project directory to create the app, "
                    "then set FLY_APP_NAME and re-trigger."
                ),
            }

        # Trigger a new release via Fly Machines API
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    f"https://api.fly.io/v1/apps/{fly_app_name}/releases",
                    headers={
                        "Authorization": f"Bearer {fly_token}",
                        "Content-Type": "application/json",
                    },
                    json={"strategy": "rolling"},
                )

            if resp.status_code in (200, 201):
                data = resp.json()
                return {
                    "status": "deploying",
                    "provider": "fly",
                    "project_id": project_id,
                    "release_id": data.get("id"),
                    "message": f"Fly.io deployment triggered for app '{fly_app_name}'.",
                    "estimated_time": "2-4 minutes",
                    "dashboard_url": f"https://fly.io/apps/{fly_app_name}",
                }
            else:
                return {
                    "status": "error",
                    "provider": "fly",
                    "project_id": project_id,
                    "error": f"Fly API error ({resp.status_code}): {resp.text}",
                }
        except Exception as exc:
            logger.error(f"Fly deploy error for {project_id}: {exc}")
            return {"status": "error", "provider": "fly", "project_id": project_id, "error": str(exc)}

    def _resolve_project_path(self, project_id: str) -> Optional[str]:
        """Attempt to locate the generated output directory for a project.

        Checks the in-memory job store from code_generation.routes first,
        then falls back to the local output/ directory.
        """
        try:
            from src.code_generation.routes import _jobs
            for job in _jobs.values():
                if job.status == "completed" and job.result and job.result.output_path:
                    # Match by job_id prefix or idea name fragment
                    if project_id in job.job_id or project_id.replace("-", "") in job.job_id:
                        return job.result.output_path
        except Exception:
            pass

        # Fallback: look in output/ subdirectory
        from pathlib import Path
        candidates = [
            Path("output") / project_id,
            Path("/tmp/ignara") / project_id,
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    async def get_health_metrics(self) -> dict:
        """Get deployment health metrics."""
        return {
            "deployments": [],
            "stats": {
                "total_deployments": 0,
                "healthy": 0,
                "degraded": 0,
                "down": 0,
            }
        }

    # ==================== Feedback & Contact ====================

    async def submit_feedback(self, data: FeedbackRequest) -> dict:
        """Submit user feedback."""
        logger.info(f"Feedback received: type={data.type}, page={data.page}")

        # In production, this would save to database and send notification
        # from src.database.engine import get_db
        # from src.database.models import Feedback, FeedbackType

        return {
            "success": True,
            "message": "Thank you for your feedback!",
            "feedback_id": "fb_" + str(hash(data.message))[:8]
        }

    async def submit_contact(self, data: ContactRequest) -> dict:
        """Submit contact form."""
        logger.info(f"Contact form received: email={data.email}, subject={data.subject}")

        # In production, this would save to database and send email
        # from src.database.engine import get_db
        # from src.database.models import ContactSubmission

        return {
            "success": True,
            "message": "Thank you for reaching out! We'll get back to you within 24 hours."
        }

    async def get_onboarding_status(self) -> OnboardingStatusResponse:
        """Get user onboarding status."""
        # Mock data - in production, fetch from database for current user
        steps = {
            "emailVerified": False,
            "apiKeysAdded": False,
            "firstAppGenerated": False,
            "firstDeploy": False
        }

        completed_count = sum(1 for v in steps.values() if v)

        return OnboardingStatusResponse(
            steps=steps,
            completedCount=completed_count,
            totalSteps=4,
            allComplete=completed_count == 4
        )


def create_api_router() -> APIRouter:
    """
    Create API router with all endpoints.

    Returns:
        Configured APIRouter
    """
    router = APIRouter()
    api = APIRoutes()

    # Projects
    router.add_api_route("/projects", api.list_projects, methods=["GET"])
    router.add_api_route("/projects", api.create_project, methods=["POST"])
    router.add_api_route("/projects/{project_id}", api.get_project, methods=["GET"])
    router.add_api_route("/projects/{project_id}", api.update_project, methods=["PATCH"])
    router.add_api_route("/projects/{project_id}", api.delete_project, methods=["DELETE"])

    # Generation
    router.add_api_route("/generate", api.start_generation, methods=["POST"])
    router.add_api_route("/projects/{project_id}/generation", api.get_generation_status, methods=["GET"])

    # Deployment
    router.add_api_route("/deploy", api.start_deployment, methods=["POST"])
    router.add_api_route("/projects/{project_id}/deployments/{deployment_id}", api.get_deployment_status, methods=["GET"])

    # One-Click Deploy
    router.add_api_route("/deploy/vercel/{project_id}", api.deploy_to_vercel, methods=["POST"])
    router.add_api_route("/deploy/render/{project_id}", api.deploy_to_render, methods=["POST"])
    router.add_api_route("/deploy/railway/{project_id}", api.deploy_to_railway, methods=["POST"])
    router.add_api_route("/deploy/fly/{project_id}", api.deploy_to_fly, methods=["POST"])

    # Health Metrics
    router.add_api_route("/health/metrics", api.get_health_metrics, methods=["GET"])

    # Subscription
    router.add_api_route("/subscription", api.get_subscription, methods=["GET"])
    router.add_api_route("/subscription/checkout", api.create_checkout_session, methods=["POST"])
    router.add_api_route("/subscription/portal", api.create_portal_session, methods=["POST"])

    # API Keys
    router.add_api_route("/api-keys", api.list_api_keys, methods=["GET"])
    router.add_api_route("/api-keys", api.create_api_key, methods=["POST"])
    router.add_api_route("/api-keys/{key_id}", api.revoke_api_key, methods=["DELETE"])

    # Feedback & Contact
    router.add_api_route("/feedback", api.submit_feedback, methods=["POST"])
    router.add_api_route("/contact", api.submit_contact, methods=["POST"])

    # Onboarding
    router.add_api_route("/onboarding/status", api.get_onboarding_status, methods=["GET"])

    # Build pipeline endpoints (mounted at /api prefix, not /api/v1)
    # They are registered separately below.

    return router


# ==================== Build Pipeline Endpoints ====================


def _run_pipeline_thread(
    build_id: str,
    idea: str,
    llm_provider: str,
    theme: str,
    target_users: str = "",
    features: str = "",
    monetization: str = "",
    customization: Optional[Dict[str, Any]] = None,
) -> None:
    """Run the v2 AI-powered pipeline in a worker thread."""
    from src.code_generation.bridge import run_v2_pipeline_thread
    run_v2_pipeline_thread(
        build_id=build_id,
        idea=idea,
        llm_provider=llm_provider,
        theme=theme,
        target_users=target_users,
        features=features,
        monetization=monetization,
        customization=customization,
    )


def _run_pipeline_thread_legacy(
    build_id: str,
    idea: str,
    llm_provider: str,
    theme: str,
) -> None:
    """Legacy v1 pipeline thread — kept for fallback."""
    import asyncio
    import time as _time

    from src.services.build_manager import build_manager

    try:
        from src.config import load_config
        from src.notifications.dispatcher import dispatcher as notify
        from src.pipeline import StartupGenerationPipeline
        from src.plugins.registry import plugin_registry
    except ImportError:
        logger.error("Legacy pipeline dependencies not available")
        build_manager.update_build(build_id, status="failed", error_message="Legacy pipeline unavailable")
        return

    _stage_start = _time.monotonic()

    def _progress_cb(stage: str, percent: int, message: str) -> None:
        nonlocal _stage_start
        now = _time.monotonic()
        duration_ms = (now - _stage_start) * 1000
        _stage_start = now

        build_manager.update_build(
            build_id,
            current_stage=stage,
            progress=percent,
            status="running",
        )
        build_manager.push_event(build_id, {
            "type": "progress",
            "stage": stage,
            "progress": percent,
            "message": message,
        })
        notify.dispatch("build.stage_changed", build_id, {"stage": stage, "progress": percent})
        plugin_registry.call_hook("on_stage_complete", build_id=build_id, stage=stage, duration_ms=duration_ms)

    pipeline_start = _time.monotonic()

    try:
        build_manager.update_build(build_id, status="running")
        build_manager.push_event(build_id, {
            "type": "started",
            "message": "Pipeline started",
        })
        notify.dispatch("build.started", build_id, {"idea": idea})
        plugin_registry.call_hook("on_pipeline_start", build_id=build_id, config={"idea": idea, "llm_provider": llm_provider, "theme": theme})

        config = load_config("config.yml")
        pipeline = StartupGenerationPipeline(config, llm_provider=llm_provider)

        output_dir = f"./output/{build_id}"
        result = asyncio.run(
            pipeline.run(
                demo_mode=os.environ.get("DEMO_MODE", "false").lower() == "true",
                output_dir=output_dir,
                theme=theme,
                progress_callback=_progress_cb,
            )
        )

        completed_at = datetime.now(timezone.utc).isoformat()
        output_path = ""
        if result.generated_codebase:
            output_path = result.generated_codebase.output_path

        build_manager.update_build(
            build_id,
            status="completed",
            progress=100,
            current_stage="complete",
            completed_at=completed_at,
            output_path=output_path,
        )
        build_manager.push_event(build_id, {
            "type": "complete",
            "progress": 100,
            "message": "Build completed successfully",
            "output_path": output_path,
        })
        notify.dispatch("build.completed", build_id, {"idea": idea, "provider": llm_provider, "output_path": output_path})
        total_ms = (_time.monotonic() - pipeline_start) * 1000
        plugin_registry.call_hook("on_pipeline_complete", build_id=build_id, output_path=output_path, total_duration_ms=total_ms)

    except Exception as exc:
        logger.exception("Pipeline build %s failed", build_id)
        completed_at = datetime.now(timezone.utc).isoformat()
        build_manager.update_build(
            build_id,
            status="failed",
            error_message=str(exc),
            completed_at=completed_at,
        )
        build_manager.push_event(build_id, {
            "type": "failed",
            "message": str(exc),
        })
        notify.dispatch("build.failed", build_id, {"idea": idea, "error": str(exc)})
        plugin_registry.call_hook("on_error", build_id=build_id, error=exc)


async def api_create_build(data: BuildRequest) -> BuildResponse:
    """POST /api/build — start a v2 AI-powered pipeline build."""
    from src.services.build_manager import build_manager

    build_id = build_manager.create_build(
        idea=data.idea,
        llm_provider=data.llm_provider,
        theme=data.theme,
        target_users=data.target_users or "",
        features=data.features or "",
        monetization=data.monetization or "",
    )

    _build_executor.submit(
        _run_pipeline_thread,
        build_id,
        data.idea,
        data.llm_provider,
        data.theme,
        data.target_users or "",
        data.features or "",
        data.monetization or "",
        data.customization,
    )

    return BuildResponse(
        build_id=build_id,
        status="pending",
        stream_url=f"/api/build/{build_id}/stream",
    )


async def api_get_build(build_id: str) -> Dict[str, Any]:
    """GET /api/build/{build_id} — return build status."""
    from fastapi import HTTPException

    from src.services.build_manager import build_manager

    build = build_manager.get_build(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return build


async def api_list_builds() -> List[Dict[str, Any]]:
    """GET /api/builds — list all builds newest first."""
    from src.services.build_manager import build_manager

    return build_manager.list_builds(limit=50)


async def api_build_stream(build_id: str):
    """GET /api/build/{build_id}/stream — SSE endpoint."""
    import asyncio
    import json as _json

    from fastapi import HTTPException
    from starlette.responses import StreamingResponse

    from src.services.build_manager import build_manager

    build = build_manager.get_build(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    async def _event_generator():
        keepalive_counter = 0
        while True:
            events = build_manager.get_events(build_id)
            for ev in events:
                yield f"data: {_json.dumps(ev)}\n\n"
                if ev.get("type") in ("complete", "failed"):
                    return

            keepalive_counter += 1
            if keepalive_counter >= 30:  # 30 * 0.5s = 15s
                yield ": keepalive\n\n"
                keepalive_counter = 0

            await asyncio.sleep(0.5)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def api_build_download(build_id: str):
    """GET /api/build/{build_id}/download — zip and download output."""
    from pathlib import Path

    from fastapi import HTTPException
    from starlette.responses import StreamingResponse

    from src.services.build_manager import build_manager

    build = build_manager.get_build(build_id)
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    output_path = build.get("output_path")
    if not output_path or not Path(output_path).exists():
        raise HTTPException(status_code=404, detail="Build output not available")

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        base = Path(output_path)
        for file in base.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(base))
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="build-{build_id}.zip"'},
    )


def create_build_router() -> APIRouter:
    """Create router for build pipeline API endpoints."""
    router = APIRouter()
    router.add_api_route("/build", api_create_build, methods=["POST"])
    router.add_api_route("/build/{build_id}", api_get_build, methods=["GET"])
    router.add_api_route("/builds", api_list_builds, methods=["GET"])
    router.add_api_route("/build/{build_id}/stream", api_build_stream, methods=["GET"])
    router.add_api_route("/build/{build_id}/download", api_build_download, methods=["GET"])
    return router
