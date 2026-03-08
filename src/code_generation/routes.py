"""API routes for the v2 code generation pipeline."""

from __future__ import annotations

import asyncio
import io
import logging
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from src.code_generation.pipeline import GenerationPipeline, PipelineProgress, PipelineResult

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

    try:
        async for progress_event in pipeline.run_with_progress(
            idea_name=req.idea_name,
            idea_description=req.description,
            features=req.features,
            theme=req.theme,
            max_fix_rounds=req.max_fix_rounds,
        ):
            job.push_progress(progress_event)
            logger.debug(
                "[job %s] phase=%s progress=%d%% step=%s",
                job_id,
                progress_event.phase,
                progress_event.progress,
                progress_event.step,
            )

        # run_with_progress only yields — collect the full result via run()
        result = await pipeline.run(
            idea_name=req.idea_name,
            idea_description=req.description,
            features=req.features,
            theme=req.theme,
            max_fix_rounds=req.max_fix_rounds,
        )
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
