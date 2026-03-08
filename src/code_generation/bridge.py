"""
Bridge between the build_manager-based build API and the v2 GenerationPipeline.

This module replaces the old v1 pipeline thread (_run_pipeline_thread) with one
that drives the v2 architecture: Architect → CodeGeneratorV2 → QualityPipeline → AutoFixer.

Progress events are streamed into build_manager for SSE consumption by the frontend.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def run_v2_pipeline_thread(
    build_id: str,
    idea: str,
    llm_provider: str = "auto",
    theme: str = "Modern",
    target_users: Optional[str] = None,
    features: Optional[str] = None,
    monetization: Optional[str] = None,
) -> None:
    """Run the v2 GenerationPipeline in a worker thread.

    This replaces the old _run_pipeline_thread that used the v1 template-based engine.
    All progress updates are pushed into build_manager for SSE streaming.
    """
    from src.services.build_manager import build_manager

    # Lazy imports to avoid circular deps
    try:
        from src.notifications.dispatcher import dispatcher as notify
    except ImportError:
        notify = None
    try:
        from src.plugins.registry import plugin_registry
    except ImportError:
        plugin_registry = None

    pipeline_start = time.monotonic()

    try:
        build_manager.update_build(build_id, status="running")
        build_manager.push_event(build_id, {
            "type": "started",
            "message": "Pipeline started — designing architecture",
        })

        if notify:
            notify.dispatch("build.started", build_id, {"idea": idea})
        if plugin_registry:
            plugin_registry.call_hook(
                "on_pipeline_start",
                build_id=build_id,
                config={"idea": idea, "llm_provider": llm_provider, "theme": theme},
            )

        # Build a richer description from the optional fields
        description_parts = [idea]
        if target_users:
            description_parts.append(f"Target users: {target_users}")
        if monetization:
            description_parts.append(f"Monetization: {monetization}")
        full_description = "\n".join(description_parts)

        # Parse features from newline/comma separated string
        feature_list = []
        if features:
            for line in features.replace(",", "\n").split("\n"):
                line = line.strip()
                if line:
                    feature_list.append(line)

        # Derive a short name from the idea
        idea_name = idea.strip()[:60].strip()
        # Remove trailing punctuation
        while idea_name and idea_name[-1] in ".!?,;:":
            idea_name = idea_name[:-1]

        # Import the v2 pipeline
        from src.code_generation.pipeline import GenerationPipeline

        output_base = os.environ.get("STORAGE_PATH", "./generated_projects")
        pipeline = GenerationPipeline(output_base_dir=output_base)

        # Override LLM provider if specified
        if llm_provider and llm_provider != "auto":
            try:
                from src.llm.client import get_llm_client
                client = get_llm_client(llm_provider)
                pipeline.architect._client = client
                pipeline.generator._client = client
            except Exception as e:
                logger.warning("Could not set LLM provider '%s': %s", llm_provider, e)

        # Run the async pipeline with progress streaming
        async def _run():
            async for progress in pipeline.run_with_progress(
                idea_name=idea_name,
                idea_description=full_description,
                features=feature_list,
                theme=theme,
                max_fix_rounds=2,
            ):
                # Map v2 phases to build_manager stages
                stage_map = {
                    "architect": "Architecture Design",
                    "generate": "Code Generation",
                    "validate": "Quality Validation",
                    "critics": "Critic Review",
                    "fix": "Auto-Fix",
                    "complete": "Complete",
                }
                stage = stage_map.get(progress.phase, progress.phase)

                build_manager.update_build(
                    build_id,
                    current_stage=stage,
                    progress=progress.progress,
                    status="running",
                )

                progress_event: dict = {
                    "type": "progress",
                    "stage": stage,
                    "progress": progress.progress,
                    "message": progress.message,
                    "phase": progress.phase,
                    "files_generated": progress.files_generated,
                    "total_files": progress.total_files,
                }
                # Include critic report when available (attached to the
                # "critics" and "complete" progress events).
                if progress.critic_report is not None:
                    progress_event["critic_report"] = progress.critic_report

                build_manager.push_event(build_id, progress_event)

                if notify:
                    notify.dispatch("build.stage_changed", build_id, {
                        "stage": stage,
                        "progress": progress.progress,
                    })

            # Now get the final result
            result = await pipeline.run(
                idea_name=idea_name,
                idea_description=full_description,
                features=feature_list,
                theme=theme,
                max_fix_rounds=2,
            )
            return result

        # asyncio.run() is safe here — ThreadPoolExecutor threads have no event loop
        result = asyncio.run(_run())

        completed_at = datetime.now(timezone.utc).isoformat()
        total_time = round(time.monotonic() - pipeline_start, 2)

        # Store quality metrics in the build record
        quality_data: dict = {
            "score": result.quality.score,
            "passed": result.quality.passed,
            "errors": result.quality.errors,
            "warnings": result.quality.warnings,
            "summary": result.quality.summary,
            "total_files": result.generation.total_files,
            "total_lines": result.generation.total_lines,
            "llm_calls_made": result.generation.llm_calls_made,
            "fixes_applied": result.fixes_applied,
            "generation_time": result.total_time_seconds,
        }
        # Attach critic report when available
        if result.critic_report is not None:
            quality_data["critic_report"] = result.critic_report

        build_manager.update_build(
            build_id,
            status="completed",
            progress=100,
            current_stage="Complete",
            completed_at=completed_at,
            output_path=result.output_path,
            quality_score=result.quality.score,
            total_files=result.generation.total_files,
            total_lines=result.generation.total_lines,
        )
        build_manager.push_event(build_id, {
            "type": "complete",
            "progress": 100,
            "message": (
                f"Build completed in {total_time}s — "
                f"{result.generation.total_files} files, "
                f"score {result.quality.score}/100"
            ),
            "quality": quality_data,
            "output_path": result.output_path,
        })

        if notify:
            notify.dispatch("build.completed", build_id, {
                "status": result.status,
                "output_path": result.output_path,
                "total_time": total_time,
            })
        if plugin_registry:
            plugin_registry.call_hook(
                "on_pipeline_complete",
                build_id=build_id,
                status=result.status,
                duration_ms=total_time * 1000,
            )

        logger.info(
            "Build %s completed in %.1fs — %d files, score %d/100",
            build_id, total_time,
            result.generation.total_files,
            result.quality.score,
        )

    except Exception as exc:
        logger.exception("Build %s failed: %s", build_id, exc)
        completed_at = datetime.now(timezone.utc).isoformat()

        build_manager.update_build(
            build_id,
            status="failed",
            completed_at=completed_at,
            error_message=str(exc),
        )
        build_manager.push_event(build_id, {
            "type": "failed",
            "progress": 0,
            "message": f"Build failed: {exc}",
            "error": str(exc),
        })

        if notify:
            notify.dispatch("build.failed", build_id, {"error": str(exc)})
