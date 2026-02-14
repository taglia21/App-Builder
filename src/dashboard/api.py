"""
API Routes

JSON API endpoints for the Valeric platform.
"""

import logging
import zipfile
from datetime import datetime, timezone
from enum import Enum
from io import BytesIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

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


class BuildResponse(BaseModel):
    """Response after creating a build."""
    build_id: str
    status: str
    stream_url: str


# ==================== API Routes ====================

class APIRoutes:
    """
    JSON API endpoints.

    Provides programmatic access to Valeric features.
    """

    # ==================== Projects ====================

    @staticmethod
    async def list_projects(
        page: int = 1,
        per_page: int = 10,
        status: Optional[ProjectStatus] = None,
    ) -> ProjectListResponse:
        """List all projects for the current user."""
        # Mock data
        projects = [
            ProjectResponse(
                id="proj_1",
                name="My SaaS App",
                description="A productivity app for teams",
                status=ProjectStatus.DEPLOYED,
                features=["auth", "billing", "dashboard"],
                tech_stack={"frontend": "nextjs", "backend": "fastapi"},
                urls={"frontend": "https://my-saas.vercel.app"},
                created_at=datetime(2024, 1, 15),
                updated_at=datetime(2024, 1, 16),
            ),
        ]

        return ProjectListResponse(
            projects=projects,
            total=len(projects),
            page=page,
            per_page=per_page,
        )

    @staticmethod
    async def get_project(project_id: str) -> ProjectResponse:
        """Get a specific project."""
        # Mock data
        return ProjectResponse(
            id=project_id,
            name="My SaaS App",
            description="A productivity app for teams",
            status=ProjectStatus.DEPLOYED,
            features=["auth", "billing", "dashboard"],
            tech_stack={"frontend": "nextjs", "backend": "fastapi"},
            urls={
                "frontend": "https://my-saas.vercel.app",
                "backend": "https://my-saas-api.onrender.com",
                "github": "https://github.com/user/my-saas",
            },
            created_at=datetime(2024, 1, 15),
            updated_at=datetime(2024, 1, 16),
        )

    @staticmethod
    async def create_project(project: ProjectCreate) -> ProjectResponse:
        """Create a new project."""
        # Mock creation
        return ProjectResponse(
            id="proj_new",
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
        """Update a project."""
        # Mock update
        return ProjectResponse(
            id=project_id,
            name=updates.name or "My SaaS App",
            description=updates.description or "A productivity app for teams",
            status=ProjectStatus.DEPLOYED,
            features=[],
            tech_stack={},
            urls={},
            created_at=datetime(2024, 1, 15),
            updated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    async def delete_project(project_id: str) -> Dict[str, Any]:
        """Delete a project."""
        return {"deleted": True, "project_id": project_id}

    # ==================== Generation ====================

    @staticmethod
    async def start_generation(request: GenerationRequest) -> GenerationStatus:
        """Start code generation for a project."""
        return GenerationStatus(
            project_id=request.project_id,
            status="in_progress",
            progress=0,
            current_step="Analyzing requirements",
            steps=[
                {"name": "Analyzing requirements", "status": "in_progress"},
                {"name": "Generating architecture", "status": "pending"},
                {"name": "Writing code", "status": "pending"},
                {"name": "Creating tests", "status": "pending"},
            ],
            estimated_time_remaining=120,
        )

    @staticmethod
    async def get_generation_status(project_id: str) -> GenerationStatus:
        """Get current generation status."""
        return GenerationStatus(
            project_id=project_id,
            status="in_progress",
            progress=50,
            current_step="Writing code",
            steps=[
                {"name": "Analyzing requirements", "status": "complete"},
                {"name": "Generating architecture", "status": "complete"},
                {"name": "Writing code", "status": "in_progress"},
                {"name": "Creating tests", "status": "pending"},
            ],
            estimated_time_remaining=60,
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
        """Get current subscription info."""
        return SubscriptionInfo(
            tier="pro",
            status="active",
            apps_used=2,
            apps_limit=5,
            billing_period="monthly",
            next_billing_date=datetime(2024, 2, 1),
            amount=2900,
        )

    @staticmethod
    async def create_checkout_session(
        tier: str = Body(...),
        billing_period: str = Body("monthly"),
    ) -> Dict[str, str]:
        """Create a Stripe checkout session."""
        return {
            "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_123",
            "session_id": "cs_test_123",
        }

    @staticmethod
    async def create_portal_session() -> Dict[str, str]:
        """Create a Stripe customer portal session."""
        return {
            "portal_url": "https://billing.stripe.com/p/session/123",
        }

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
        """Deploy project to Vercel."""
        return {
            "status": "deploying",
            "provider": "vercel",
            "project_id": project_id,
            "message": "Deployment initiated to Vercel",
            "estimated_time": "2-3 minutes",
        }

    async def deploy_to_render(self, project_id: str) -> dict:
        """Deploy project to Render."""
        return {
            "status": "deploying",
            "provider": "render",
            "project_id": project_id,
            "message": "Deployment initiated to Render",
            "estimated_time": "3-5 minutes",
        }

    async def deploy_to_railway(self, project_id: str) -> dict:
        """Deploy project to Railway."""
        return {
            "status": "deploying",
            "provider": "railway",
            "project_id": project_id,
            "message": "Deployment initiated to Railway",
            "estimated_time": "2-4 minutes",
        }

    async def deploy_to_fly(self, project_id: str) -> dict:
        """Deploy project to Fly.io."""
        return {
            "status": "deploying",
            "provider": "fly",
            "project_id": project_id,
            "message": "Deployment initiated to Fly.io",
            "estimated_time": "3-5 minutes",
        }

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
) -> None:
    """Run the pipeline in a daemon thread, updating the build manager."""
    import asyncio
    import time as _time

    from src.config import load_config
    from src.notifications.dispatcher import dispatcher as notify
    from src.pipeline import StartupGenerationPipeline
    from src.plugins.registry import plugin_registry
    from src.services.build_manager import build_manager

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
                demo_mode=True,
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
    """POST /api/build — start a pipeline build."""
    import threading

    from src.services.build_manager import build_manager

    build_id = build_manager.create_build(
        idea=data.idea,
        llm_provider=data.llm_provider,
        theme=data.theme,
    )

    t = threading.Thread(
        target=_run_pipeline_thread,
        args=(build_id, data.idea, data.llm_provider, data.theme),
        daemon=True,
    )
    t.start()

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
