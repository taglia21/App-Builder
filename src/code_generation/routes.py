"""API routes for the v2 code generation pipeline."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from src.code_generation.pipeline import GenerationPipeline, PipelineProgress, PipelineResult
from src.code_generation.refinement import (
    RefinementEngine,
    RefinementHistory,
    RefinementRequest,
    RefinementResult,
    refinement_engine,
    refinement_history,
)
from src.code_generation.refinement_chat import ChatManager, RefinementChat, chat_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["code-generation-v2"])

# ---------------------------------------------------------------------------
# In-memory job store
# ---------------------------------------------------------------------------
# Shape: { job_id: JobRecord }
_jobs: Dict[str, "JobRecord"] = {}


class JobRecord:
    """Tracks the lifecycle of a single generation job."""

    def __init__(self, job_id: str, request: "GenerateRequest") -> None:
        self.job_id = job_id
        self.request = request
        self.status: str = "started"       # started | running | completed | failed
        self.created_at: datetime = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.result: Optional[PipelineResult] = None
        self.error: Optional[str] = None
        self.progress: Optional[PipelineProgress] = None
        # Subscribers waiting on WebSocket progress
        self._progress_queue: asyncio.Queue = asyncio.Queue()

    def push_progress(self, event: PipelineProgress) -> None:
        """Put a progress event onto the queue for WebSocket consumers."""
        self.progress = event
        try:
            self._progress_queue.put_nowait(event)
        except asyncio.QueueFull:
            pass  # Non-blocking — drop if no consumer

    async def next_progress(self, timeout: float = 60.0) -> Optional[PipelineProgress]:
        """Wait for the next progress event (used by WebSocket handler)."""
        try:
            return await asyncio.wait_for(self._progress_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    """Request body for POST /api/v2/generate."""

    idea_name: str = Field(..., min_length=1, max_length=120, description="Short application name.")
    description: str = Field(..., min_length=10, max_length=4000, description="Plain-English idea description.")
    features: Optional[List[str]] = Field(default=None, description="Optional feature list.")
    theme: str = Field(default="Modern", description="Visual theme, e.g. 'Modern', 'Minimal', 'Dark'.")
    max_fix_rounds: int = Field(default=2, ge=0, le=5, description="Auto-fix iterations (0 = disabled).")

    # --- Customization Options ---
    backend_framework: str = Field(default="fastapi", description="Backend framework: 'fastapi', 'express', 'django'.")
    database: str = Field(default="postgresql", description="Database: 'postgresql', 'mysql', 'sqlite', 'mongodb'.")
    auth_strategy: str = Field(default="jwt", description="Authentication: 'jwt', 'session', 'oauth2', 'none'.")
    frontend_framework: str = Field(default="nextjs", description="Frontend framework: 'nextjs', 'react-vite', 'vue', 'svelte'.")
    css_framework: str = Field(default="tailwind", description="CSS: 'tailwind', 'shadcn', 'material-ui', 'chakra', 'plain-css'.")
    deployment_target: str = Field(default="docker", description="Deployment: 'docker', 'vercel', 'railway', 'aws', 'bare'.")
    include_tests: bool = Field(default=True, description="Whether to generate test files.")
    include_ci: bool = Field(default=True, description="Whether to generate CI/CD config (GitHub Actions).")
    api_style: str = Field(default="rest", description="API style: 'rest', 'graphql'.")
    extra_instructions: str = Field(default="", max_length=2000, description="Additional instructions for the code generator (e.g., 'Use Stripe for payments').")


class StartResponse(BaseModel):
    """Response body for POST /api/v2/generate."""

    job_id: str
    status: str = "started"
    message: str = "Generation started. Poll GET /api/v2/generate/{job_id} for status."


class JobStatusResponse(BaseModel):
    """Response body for GET /api/v2/generate/{job_id}."""

    job_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SpecResponse(BaseModel):
    """Response body for GET /api/v2/generate/{job_id}/spec."""

    job_id: str
    spec: Dict[str, Any]


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------


async def _run_pipeline(job_id: str, req: "GenerateRequest") -> None:
    """Background coroutine that drives the full pipeline and updates job state."""
    job = _jobs.get(job_id)
    if job is None:
        logger.error("Background task started for unknown job_id=%s", job_id)
        return

    job.status = "running"
    pipeline = GenerationPipeline()

    customization = {
        "backend_framework": req.backend_framework,
        "database": req.database,
        "auth_strategy": req.auth_strategy,
        "frontend_framework": req.frontend_framework,
        "css_framework": req.css_framework,
        "deployment_target": req.deployment_target,
        "include_tests": req.include_tests,
        "include_ci": req.include_ci,
        "api_style": req.api_style,
        "extra_instructions": req.extra_instructions,
    }

    try:
        result: PipelineResult | None = None
        async for progress_event in pipeline.run_with_progress(
            idea_name=req.idea_name,
            idea_description=req.description,
            features=req.features,
            theme=req.theme,
            max_fix_rounds=req.max_fix_rounds,
            customization=customization,
        ):
            job.push_progress(progress_event)
            logger.debug(
                "[job %s] phase=%s progress=%d%% step=%s",
                job_id,
                progress_event.phase,
                progress_event.progress,
                progress_event.step,
            )
            # Grab the PipelineResult from the final "complete" event
            if progress_event.phase == "complete":
                result = getattr(progress_event, "_pipeline_result", None)

        # Extract the PipelineResult from the final "complete" event.
        # run_with_progress attaches the full result via _pipeline_result
        # attribute so we never need to call pipeline.run() a second time.
        if result is None:
            raise RuntimeError("Pipeline completed without producing a result")
        job.result = result
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        logger.info("[job %s] completed — status=%s", job_id, result.status)

    except Exception as exc:
        logger.exception("[job %s] pipeline error: %s", job_id, exc)
        job.error = str(exc)
        job.status = "failed"
        job.completed_at = datetime.now(timezone.utc)
        # Push a terminal progress event so WebSocket clients unblock
        job.push_progress(
            PipelineProgress(
                phase="complete",
                step="failed",
                progress=100,
                message=f"Pipeline failed: {exc}",
            )
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=StartResponse, status_code=202)
async def start_generation(
    req: GenerateRequest,
    background_tasks: BackgroundTasks,
) -> StartResponse:
    """Start a new generation job.

    The pipeline runs asynchronously. Use the returned *job_id* to:
    - Poll ``GET /api/v2/generate/{job_id}`` for status / result.
    - Stream real-time progress via ``WS /api/v2/generate/ws/{job_id}``.
    """
    job_id = uuid.uuid4().hex
    job = JobRecord(job_id=job_id, request=req)
    _jobs[job_id] = job

    logger.info("Starting job %s for idea '%s'", job_id, req.idea_name)
    background_tasks.add_task(_run_pipeline, job_id, req)

    return StartResponse(job_id=job_id)


@router.get("/generate/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Return the current status (and result when complete) of a generation job."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    result_dict: Optional[Dict[str, Any]] = None
    if job.result is not None:
        # Exclude heavy nested objects; surface key metrics
        result_dict = {
            "status": job.result.status,
            "output_path": job.result.output_path,
            "total_time_seconds": job.result.total_time_seconds,
            "fixes_applied": job.result.fixes_applied,
            "quality": {
                "passed": job.result.quality.passed,
                "score": job.result.quality.score,
                "errors": job.result.quality.errors,
                "warnings": job.result.quality.warnings,
                "summary": job.result.quality.summary,
            },
            "generation": {
                "total_files": job.result.generation.total_files,
                "total_lines": job.result.generation.total_lines,
                "backend_files": job.result.generation.backend_files,
                "frontend_files": job.result.generation.frontend_files,
                "generation_time_seconds": job.result.generation.generation_time_seconds,
                "llm_calls_made": job.result.generation.llm_calls_made,
                "warnings": job.result.generation.warnings,
            },
        }

    progress_dict: Optional[Dict[str, Any]] = None
    if job.progress is not None:
        progress_dict = job.progress.model_dump()

    return JobStatusResponse(
        job_id=job_id,
        status=job.status,
        created_at=job.created_at,
        completed_at=job.completed_at,
        progress=progress_dict,
        result=result_dict,
        error=job.error,
    )


@router.websocket("/generate/ws/{job_id}")
async def stream_generation_progress(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint — streams :class:`PipelineProgress` events as JSON.

    Connect immediately after calling ``POST /api/v2/generate``.
    The stream closes automatically when ``phase="complete"`` is reached.

    Example client (JavaScript)::

        const ws = new WebSocket(`wss://api.example.com/api/v2/generate/ws/${jobId}`);
        ws.onmessage = (e) => console.log(JSON.parse(e.data));
    """
    await websocket.accept()

    job = _jobs.get(job_id)
    if job is None:
        await websocket.send_json({"error": f"Job '{job_id}' not found."})
        await websocket.close(code=4004)
        return

    logger.info("[ws] Client connected to job %s", job_id)

    try:
        while True:
            event = await job.next_progress(timeout=120.0)

            if event is None:
                # Timeout — send a keepalive ping
                await websocket.send_json({"type": "ping"})
                if job.status in ("completed", "failed"):
                    break
                continue

            await websocket.send_json(event.model_dump())

            if event.phase == "complete":
                break

    except WebSocketDisconnect:
        logger.info("[ws] Client disconnected from job %s", job_id)
    except Exception as exc:
        logger.warning("[ws] Error on job %s: %s", job_id, exc)
        try:
            await websocket.send_json({"error": str(exc)})
        except Exception:
            pass
    finally:
        await websocket.close()


@router.post("/generate/{job_id}/download")
async def download_project(job_id: str):
    """Package the generated project as a ZIP and return it for download.

    Returns:
        A ``application/zip`` response with the full project tree.

    Raises:
        404: If the job does not exist.
        409: If the job has not completed yet.
        500: If the output directory cannot be found or zipped.
    """
    from fastapi.responses import StreamingResponse

    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    if job.status != "completed" or job.result is None:
        raise HTTPException(
            status_code=409,
            detail=f"Job '{job_id}' is not yet completed (status={job.status}).",
        )

    output_path = Path(job.result.output_path)
    if not output_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Output directory not found: {output_path}",
        )

    # Build zip in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(output_path.rglob("*")):
            if file_path.is_file():
                arcname = file_path.relative_to(output_path)
                zf.write(file_path, arcname)
    buf.seek(0)

    safe_name = "".join(
        c if c.isalnum() or c in "-_" else "_"
        for c in job.request.idea_name
    ).strip("_") or "project"
    filename = f"{safe_name}.zip"

    logger.info("[job %s] Serving ZIP download: %s", job_id, filename)
    return StreamingResponse(
        content=buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/generate/{job_id}/files")
async def list_project_files(job_id: str):
    """List all files in the generated project."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if job.status != "completed" or job.result is None:
        raise HTTPException(status_code=409, detail=f"Job not completed (status={job.status}).")

    output_path = Path(job.result.output_path)
    if not output_path.exists():
        raise HTTPException(status_code=500, detail="Output directory not found.")

    files = []
    for file_path in sorted(output_path.rglob("*")):
        if file_path.is_file():
            rel_path = str(file_path.relative_to(output_path))
            try:
                size = file_path.stat().st_size
            except OSError:
                size = 0
            files.append({
                "path": rel_path,
                "size": size,
                "extension": file_path.suffix,
            })

    return {"job_id": job_id, "total_files": len(files), "files": files}


@router.get("/generate/{job_id}/files/{file_path:path}")
async def get_file_content(job_id: str, file_path: str):
    """Return the content of a specific generated file."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if job.status != "completed" or job.result is None:
        raise HTTPException(status_code=409, detail=f"Job not completed (status={job.status}).")

    output_path = Path(job.result.output_path)
    full_path = output_path / file_path

    # Security: ensure the path doesn't escape the output directory
    try:
        full_path.resolve().relative_to(output_path.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Path traversal not allowed.")

    if not full_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    try:
        content = full_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = "(binary file - cannot display)"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {e}")

    return {"path": file_path, "content": content, "size": full_path.stat().st_size}


@router.get("/generate/{job_id}/spec", response_model=SpecResponse)
async def get_job_spec(job_id: str) -> SpecResponse:
    """Return the system architecture spec for a completed generation job.

    This is the full :class:`SystemSpec` produced by the architect phase,
    including entities, API routes, pages, roles, and integrations.

    Raises:
        404: If the job does not exist.
        409: If the job has not completed yet.
    """
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    if job.status not in ("completed", "failed") or job.result is None:
        raise HTTPException(
            status_code=409,
            detail=f"Job '{job_id}' has no spec yet (status={job.status}).",
        )

    return SpecResponse(
        job_id=job_id,
        spec=job.result.spec.model_dump(),
    )


# ---------------------------------------------------------------------------
# Refinement schemas
# ---------------------------------------------------------------------------


class RefineRequest(BaseModel):
    """Request body for POST /api/v2/refine."""

    project_path: str = Field(..., description="Absolute or relative path to the generated project root.")
    instruction: str  = Field(..., min_length=1, max_length=4000, description="Natural-language change instruction.")
    scope: Optional[str]          = Field(default=None, description="'backend', 'frontend', 'full', or None to auto-detect.")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context (e.g. SystemSpec).")
    undo: bool = Field(default=False, description="If true, revert the most recent refinement instead of applying a new one.")
    project_id: Optional[str]     = Field(default=None, description="Optional dashboard project ID for linkback.")


class RefineResponse(BaseModel):
    """Response body for POST /api/v2/refine."""

    files_modified: List[Dict[str, Any]] = []
    files_created:  List[Dict[str, Any]] = []
    files_deleted:  List[Dict[str, Any]] = []
    explanation: str
    warnings:    List[str] = []
    undone:      bool = False


class HistoryResponse(BaseModel):
    """Response body for GET /api/v2/refine/{project_path}/history."""

    project_path: str
    history: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Refinement routes
# ---------------------------------------------------------------------------


@router.post("/refine", response_model=RefineResponse, status_code=200)
async def refine_project(req: RefineRequest) -> RefineResponse:
    """Apply a natural-language refinement instruction to a generated project.

    Set ``undo=true`` to revert the most recent refinement instead of applying
    a new one.

    Returns:
        A :class:`RefineResponse` describing files changed and an explanation.

    Raises:
        400: If the project path is invalid.
        500: If the LLM call or file operations fail.
    """
    import os

    if req.undo:
        # Undo the last refinement for this project
        reverted = refinement_history.undo_last(req.project_path)
        if reverted is None:
            raise HTTPException(
                status_code=409,
                detail="No refinement history found to undo, or backup directory is missing.",
            )
        return RefineResponse(
            files_modified=reverted.get("files_modified", []),
            files_created=[],
            files_deleted=reverted.get("files_deleted", []),
            explanation=f"Reverted: {reverted.get('instruction', 'last refinement')}",
            warnings=reverted.get("warnings", []),
            undone=True,
        )

    # Validate project path early for a friendlier error
    project_path = os.path.abspath(req.project_path)
    if not os.path.isdir(project_path):
        raise HTTPException(
            status_code=400,
            detail=f"project_path does not exist or is not a directory: {req.project_path}",
        )

    try:
        result: RefinementResult = await refinement_engine.refine(
            RefinementRequest(
                instruction=req.instruction,
                project_path=req.project_path,
                scope=req.scope,
                context=req.context,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Refinement pipeline error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Refinement failed: {exc}")

    return RefineResponse(
        files_modified=[fc.model_dump() for fc in result.files_modified],
        files_created=[fc.model_dump()  for fc in result.files_created],
        files_deleted=[fc.model_dump()  for fc in result.files_deleted],
        explanation=result.explanation,
        warnings=result.warnings,
        undone=False,
    )


@router.get("/refine/{project_path:path}/history", response_model=HistoryResponse)
async def get_refinement_history(project_path: str) -> HistoryResponse:
    """Return the list of past refinements for a project.

    The ``project_path`` path parameter is the URL-encoded absolute or relative
    path to the project root.  History is read from the project's
    ``.ignara_backups/history.json`` file.

    Raises:
        404: If the project directory does not exist.
    """
    import os

    abs_path = os.path.abspath(project_path)
    if not os.path.isdir(abs_path):
        raise HTTPException(
            status_code=404,
            detail=f"Project directory not found: {project_path}",
        )

    history = refinement_history.get_history(abs_path)
    return HistoryResponse(project_path=abs_path, history=history)


# ---------------------------------------------------------------------------
# GitHub integration schemas
# ---------------------------------------------------------------------------


class GitHubPushRequest(BaseModel):
    """Request body for POST /api/v2/generate/{job_id}/github."""

    repo_name: Optional[str] = Field(
        default=None,
        description=(
            "Repository name to create. Defaults to the sanitised idea_name of the job. "
            "If the repo already exists the endpoint returns its URL without re-pushing."
        ),
    )
    private: bool = Field(
        default=True,
        description="Whether to create a private repository.",
    )
    description: Optional[str] = Field(
        default=None,
        description="Repository description (defaults to the job's idea description).",
    )


class GitHubPushResponse(BaseModel):
    """Response body for POST /api/v2/generate/{job_id}/github."""

    repo_url: str
    repo_name: str
    full_name: str
    private: bool
    files_uploaded: int
    errors: List[str] = []
    message: str


# ---------------------------------------------------------------------------
# GitHub endpoint
# ---------------------------------------------------------------------------


@router.post("/generate/{job_id}/github", response_model=GitHubPushResponse)
async def push_job_to_github(job_id: str, req: GitHubPushRequest = None) -> GitHubPushResponse:
    """Create a GitHub repository and push all generated files for a completed job.

    Environment variable required:
    - ``GITHUB_TOKEN`` — personal access token with ``repo`` scope.

    Optional:
    - ``req.repo_name`` — custom repo name (defaults to the sanitised idea name).
    - ``req.private`` — whether to make the repo private (default ``true``).

    Raises:
        400: Job not completed or output directory missing.
        404: Job not found.
        422: GITHUB_TOKEN not set.
        409: Repository name already exists.
        500: Upload or API failure.
    """
    import os
    import re

    # ------------------------------------------------------------------
    # 1. Validate job
    # ------------------------------------------------------------------
    if req is None:
        req = GitHubPushRequest()

    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    if job.status != "completed" or job.result is None:
        raise HTTPException(
            status_code=409,
            detail=f"Job '{job_id}' is not yet completed (status={job.status}). "
                   "Wait for completion before pushing to GitHub.",
        )

    output_path = Path(job.result.output_path)
    if not output_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Output directory not found: {output_path}. Cannot push to GitHub.",
        )

    # ------------------------------------------------------------------
    # 2. Require GITHUB_TOKEN
    # ------------------------------------------------------------------
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise HTTPException(
            status_code=422,
            detail=(
                "GITHUB_TOKEN environment variable is not set. "
                "Create a GitHub personal access token with 'repo' scope and set it "
                "as GITHUB_TOKEN to enable repository creation."
            ),
        )

    # ------------------------------------------------------------------
    # 3. Derive repo name
    # ------------------------------------------------------------------
    if req.repo_name:
        repo_name = re.sub(r"[^a-zA-Z0-9._-]", "-", req.repo_name).strip("-") or "generated-app"
    else:
        # Sanitise the idea name
        raw = job.request.idea_name
        repo_name = re.sub(r"[^a-zA-Z0-9._-]", "-", raw).strip("-") or "generated-app"
        # Ensure it's unique-ish by appending job ID prefix
        repo_name = f"{repo_name[:40]}-{job_id[:8]}"

    description = req.description or job.request.description[:255]

    # ------------------------------------------------------------------
    # 4. Create GitHub repo and push files
    # ------------------------------------------------------------------
    try:
        from src.deployment.github import (
            AuthenticationError,
            GitHubClient,
            GitHubError,
            RepositoryExistsError,
        )
    except ImportError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"GitHub integration not available: {exc}",
        )

    try:
        client = GitHubClient(token=github_token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"GitHub authentication failed: {exc}. Check your GITHUB_TOKEN.",
        )

    # Create repo (or use existing if the same name is already ours)
    try:
        repo = client.create_repository(
            name=repo_name,
            description=description,
            private=req.private,
            auto_init=False,
        )
        logger.info("[job %s] Created GitHub repo: %s", job_id, repo.full_name)
    except RepositoryExistsError:
        # Repo already exists — fetch it to get the URL
        try:
            repo = client.get_repository(f"{client.username}/{repo_name}")
            logger.info("[job %s] GitHub repo already exists: %s", job_id, repo.full_name)
        except GitHubError as exc:
            raise HTTPException(
                status_code=409,
                detail=f"Repository '{repo_name}' already exists but could not be fetched: {exc}",
            )
    except GitHubError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to create GitHub repository: {exc}")

    # Push all generated files
    try:
        upload_result = client.upload_directory(
            repo_name=repo.full_name,
            local_path=output_path,
            message=f"Initial commit — generated by Ignara (job {job_id})",
        )
        logger.info(
            "[job %s] Pushed %d files to %s (%d errors)",
            job_id,
            upload_result["uploaded"],
            repo.full_name,
            len(upload_result["errors"]),
        )
    except GitHubError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Repository created at {repo.html_url} but file upload failed: {exc}",
        )

    return GitHubPushResponse(
        repo_url=repo.html_url,
        repo_name=repo.name,
        full_name=repo.full_name,
        private=repo.private,
        files_uploaded=upload_result["uploaded"],
        errors=upload_result.get("errors", []),
        message=(
            f"Successfully pushed {upload_result['uploaded']} files to {repo.full_name}. "
            + (f"{len(upload_result['errors'])} files had errors." if upload_result.get("errors") else "")
        ),
    )


# ---------------------------------------------------------------------------
# Refinement Chat API
# ---------------------------------------------------------------------------

class CreateChatRequest(BaseModel):
    """Request body for POST /api/v2/chat."""
    project_path: str = Field(..., description="Absolute path to the generated project.")
    project_id: Optional[str] = Field(default=None, description="Optional dashboard project ID.")

class CreateChatResponse(BaseModel):
    chat_id: str
    project_path: str
    created_at: str

class ChatMessageRequest(BaseModel):
    """Request body for POST /api/v2/chat/{chat_id}/message."""
    instruction: str = Field(..., min_length=1, max_length=4000)
    scope: Optional[str] = Field(default=None)
    apply_changes: bool = Field(default=True, description="Whether to apply changes or just note the instruction.")

class ChatMessageResponse(BaseModel):
    message: str
    refinement_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ChatHistoryResponse(BaseModel):
    chat_id: str
    project_path: str
    messages: List[Dict[str, Any]]
    created_at: str
    updated_at: str

class ChatListResponse(BaseModel):
    chats: List[Dict[str, Any]]


@router.post("/chat", response_model=CreateChatResponse, status_code=201)
async def create_refinement_chat(req: CreateChatRequest) -> CreateChatResponse:
    """Start a new multi-turn refinement conversation for a project."""
    import os
    project_path = os.path.abspath(req.project_path)
    if not os.path.isdir(project_path):
        raise HTTPException(status_code=400, detail=f"Project path does not exist: {req.project_path}")

    chat = chat_manager.create_chat(project_path=project_path, project_id=req.project_id)
    return CreateChatResponse(
        chat_id=chat.chat_id,
        project_path=chat.project_path,
        created_at=chat.created_at,
    )


@router.post("/chat/{chat_id}/message", response_model=ChatMessageResponse)
async def send_chat_message(chat_id: str, req: ChatMessageRequest) -> ChatMessageResponse:
    """Send a message in a refinement chat. Changes are applied by default."""
    chat = chat_manager.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found.")

    try:
        result = await chat_manager.send_message(
            chat_id=chat_id,
            instruction=req.instruction,
            scope=req.scope,
            apply_changes=req.apply_changes,
        )
    except Exception as exc:
        logger.exception("Chat message error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {exc}")

    return ChatMessageResponse(
        message=result.get("message", ""),
        refinement_result=result.get("refinement_result"),
        error=result.get("error"),
    )


@router.get("/chat/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat_history(chat_id: str) -> ChatHistoryResponse:
    """Get the full conversation history for a refinement chat."""
    chat = chat_manager.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found.")

    return ChatHistoryResponse(
        chat_id=chat.chat_id,
        project_path=chat.project_path,
        messages=[m.model_dump() for m in chat.messages],
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


@router.get("/chats", response_model=ChatListResponse)
async def list_chats(project_path: Optional[str] = None) -> ChatListResponse:
    """List all active refinement chats, optionally filtered by project."""
    chats = chat_manager.list_chats(project_path=project_path)
    return ChatListResponse(
        chats=[
            {
                "chat_id": c.chat_id,
                "project_path": c.project_path,
                "message_count": len(c.messages),
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in chats
        ]
    )


@router.delete("/chat/{chat_id}", status_code=204)
async def delete_chat(chat_id: str):
    """Delete a refinement chat session."""
    if not chat_manager.delete_chat(chat_id):
        raise HTTPException(status_code=404, detail=f"Chat '{chat_id}' not found.")


@router.websocket("/chat/ws/{chat_id}")
async def refinement_chat_ws(websocket: WebSocket, chat_id: str):
    """WebSocket endpoint for real-time refinement chat.

    Send JSON messages: {"instruction": "...", "scope": "...", "apply_changes": true}
    Receive JSON responses: {"type": "status"|"result"|"error", "data": {...}}
    """
    await websocket.accept()

    chat = chat_manager.get_chat(chat_id)
    if not chat:
        await websocket.send_json({"type": "error", "data": {"message": f"Chat '{chat_id}' not found."}})
        await websocket.close(code=4004)
        return

    logger.info("[ws-chat] Connected to chat %s", chat_id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "data": {"message": "Invalid JSON"}})
                continue

            instruction = data.get("instruction", "").strip()
            if not instruction:
                await websocket.send_json({"type": "error", "data": {"message": "Missing 'instruction' field"}})
                continue

            # Send acknowledgment
            await websocket.send_json({
                "type": "status",
                "data": {"message": f"Processing: {instruction[:100]}...", "phase": "planning"},
            })

            try:
                result = await chat_manager.send_message(
                    chat_id=chat_id,
                    instruction=instruction,
                    scope=data.get("scope"),
                    apply_changes=data.get("apply_changes", True),
                )

                await websocket.send_json({
                    "type": "result",
                    "data": result,
                })
            except Exception as exc:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"Refinement failed: {exc}"},
                })

    except WebSocketDisconnect:
        logger.info("[ws-chat] Client disconnected from chat %s", chat_id)
    except Exception as exc:
        logger.warning("[ws-chat] Error on chat %s: %s", chat_id, exc)
        try:
            await websocket.send_json({"type": "error", "data": {"message": str(exc)}})
        except Exception:
            pass
    finally:
        await websocket.close()
