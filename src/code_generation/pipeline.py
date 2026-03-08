"""
Ignara Code Generation Pipeline v2.

Orchestrates the full code generation flow:
1. SystemArchitect designs the system spec from user's idea
2. CodeGeneratorV2 generates all files using LLM
3. CodeQualityPipeline validates everything
4. AutoFixer repairs any issues
5. Results are packaged and returned

This replaces the old template-based pipeline with a fully AI-driven one.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import AsyncGenerator, List, Optional

from pydantic import BaseModel, Field

from src.code_generation.architect import SystemArchitect, SystemSpec
from src.code_generation.critic_integration import CriticPanel, CriticReport
from src.code_generation.engine_v2 import CodeGeneratorV2, GenerationResult
from src.code_generation.quality import AutoFixer, CodeQualityPipeline, QualityReport

logger = logging.getLogger(__name__)


# =============================================================================
# Result / Progress Models
# =============================================================================


class PipelineResult(BaseModel):
    """Complete result of a full generation pipeline run."""

    spec: SystemSpec
    generation: GenerationResult
    quality: QualityReport
    fixes_applied: int = 0
    output_path: str = ""
    total_time_seconds: float = 0.0
    # "success" | "success_with_warnings" | "failed"
    status: str = "success"
    critic_report: Optional[dict] = None


class PipelineProgress(BaseModel):
    """Real-time progress event yielded by run_with_progress."""

    # "architect" | "generate" | "validate" | "critics" | "fix" | "complete"
    phase: str
    step: str
    progress: int = Field(ge=0, le=100)
    message: str = ""
    files_generated: int = 0
    total_files: int = 0
    critic_report: Optional[dict] = None


# =============================================================================
# GenerationPipeline
# =============================================================================


class GenerationPipeline:
    """Main pipeline orchestrating idea → working codebase.

    Usage::

        pipeline = GenerationPipeline()
        result = await pipeline.run(
            idea_name="TaskFlow",
            idea_description="A SaaS task-management tool for remote teams.",
            features=["Kanban board", "Time tracking", "Slack integration"],
        )
        print(result.output_path)

    For real-time progress use ``run_with_progress`` instead.
    """

    def __init__(self, output_base_dir: str = "./generated_projects") -> None:
        self.architect = SystemArchitect()
        self.generator = CodeGeneratorV2()
        self.quality = CodeQualityPipeline()
        self.fixer = AutoFixer()
        self.critic_panel = CriticPanel()
        self.output_base_dir = Path(output_base_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        idea_name: str,
        idea_description: str,
        features: Optional[List[str]] = None,
        theme: str = "Modern",
        max_fix_rounds: int = 2,
    ) -> PipelineResult:
        """Run the full generation pipeline.

        Args:
            idea_name:        Short name for the application (used as directory name).
            idea_description: Plain-English description of the idea.
            features:         Optional feature list forwarded to the architect.
            theme:            Visual theme hint passed to the code generator.
            max_fix_rounds:   Maximum auto-fix iterations (0 to skip fixing).

        Returns:
            A :class:`PipelineResult` containing the spec, generated files,
            quality report, and final status.
        """
        t_start = time.monotonic()
        features = features or []
        output_dir = self._output_dir(idea_name)

        logger.info(
            "GenerationPipeline.run → '%s' (features=%d, theme=%s, max_fix_rounds=%d)",
            idea_name,
            len(features),
            theme,
            max_fix_rounds,
        )

        # ----------------------------------------------------------------
        # Step 1: Architecture Design
        # ----------------------------------------------------------------
        logger.info("[pipeline] Step 1/4 — Architecture design")
        try:
            spec: SystemSpec = await self.architect.design(
                idea_name=idea_name,
                idea_description=idea_description,
                features=features,
            )
        except Exception as exc:
            logger.exception("[pipeline] Architect failed: %s", exc)
            raise RuntimeError(f"Architecture design failed: {exc}") from exc

        # ----------------------------------------------------------------
        # Step 2: Code Generation
        # ----------------------------------------------------------------
        logger.info("[pipeline] Step 2/4 — Code generation")
        try:
            generation: GenerationResult = await self.generator.generate(
                spec=spec,
                output_dir=str(output_dir),
                theme=theme,
            )
        except Exception as exc:
            logger.exception("[pipeline] Generator failed: %s", exc)
            raise RuntimeError(f"Code generation failed: {exc}") from exc

        # ----------------------------------------------------------------
        # Step 3: Quality Validation
        # ----------------------------------------------------------------
        logger.info("[pipeline] Step 3/4 — Quality validation")
        try:
            quality_report: QualityReport = await self.quality.validate(
                output_dir=str(output_dir),
                spec=spec.model_dump(),
            )
        except Exception as exc:
            logger.exception("[pipeline] Quality validation failed: %s", exc)
            raise RuntimeError(f"Quality validation failed: {exc}") from exc

        # ----------------------------------------------------------------
        # Step 3.5: Critic Panel
        # ----------------------------------------------------------------
        critic_report_dict: Optional[dict] = None
        try:
            logger.info("[pipeline] Step 3.5/4 — Multi-agent critic panel")
            critic_report = await self.critic_panel.run(
                output_dir=str(output_dir),
                spec=spec,
            )
            critic_report_dict = critic_report.to_dict()
            logger.info(
                "[pipeline] Critic panel complete — overall_score=%d, critical_issues=%d",
                critic_report.overall_score,
                len(critic_report.critical_issues),
            )
        except Exception as exc:
            logger.warning("[pipeline] Critic panel failed (non-blocking): %s", exc)

        # ----------------------------------------------------------------
        # Step 4: Auto-Fix loop
        # ----------------------------------------------------------------
        fixes_applied_total = 0
        for round_num in range(1, max_fix_rounds + 1):
            if quality_report.passed:
                logger.info("[pipeline] Quality gate passed — skipping fix round %d", round_num)
                break
            logger.info(
                "[pipeline] Step 4/%d — Auto-fix round %d (errors=%d, warnings=%d)",
                4 + round_num - 1,
                round_num,
                quality_report.errors,
                quality_report.warnings,
            )
            try:
                fixes_in_round, quality_report = await self.fixer.fix(
                    output_dir=str(output_dir),
                    report=quality_report,
                )
            except Exception as exc:
                logger.warning("[pipeline] AutoFixer round %d failed: %s", round_num, exc)
                break
            fixes_applied_total += fixes_in_round
            logger.info(
                "[pipeline] Fix round %d applied %d fix(es); new score=%d",
                round_num,
                fixes_in_round,
                quality_report.score,
            )
            if fixes_in_round == 0:
                logger.info("[pipeline] No fixes applied — stopping early.")
                break

        # ----------------------------------------------------------------
        # Step 5: Final report
        # ----------------------------------------------------------------
        total_time = round(time.monotonic() - t_start, 2)

        if quality_report.passed:
            status = "success_with_warnings" if quality_report.warnings > 0 else "success"
        else:
            status = "failed"

        result = PipelineResult(
            spec=spec,
            generation=generation,
            quality=quality_report,
            fixes_applied=fixes_applied_total,
            output_path=str(output_dir.resolve()),
            total_time_seconds=total_time,
            status=status,
            critic_report=critic_report_dict,
        )

        logger.info(
            "[pipeline] Done in %.1fs — status=%s, files=%d, score=%d/100",
            total_time,
            status,
            generation.total_files,
            quality_report.score,
        )
        return result

    async def run_with_progress(
        self,
        idea_name: str,
        idea_description: str,
        features: Optional[List[str]] = None,
        theme: str = "Modern",
        max_fix_rounds: int = 2,
    ) -> AsyncGenerator[PipelineProgress, None]:
        """Stream pipeline progress for real-time UI updates.

        Yields :class:`PipelineProgress` events as each phase advances.
        The final event has ``phase="complete"`` and ``progress=100``.

        Usage::

            async for event in pipeline.run_with_progress("MyApp", "An app that..."):
                print(event.phase, event.progress, event.message)

        Raises:
            RuntimeError: If any mandatory pipeline step fails.
        """
        features = features or []
        output_dir = self._output_dir(idea_name)
        t_start = time.monotonic()

        # ----------------------------------------------------------------
        # Phase: architect (0–20 %)
        # ----------------------------------------------------------------
        yield PipelineProgress(
            phase="architect",
            step="Designing system architecture",
            progress=0,
            message=f"Analysing idea: {idea_name}",
        )

        spec: SystemSpec = await self.architect.design(
            idea_name=idea_name,
            idea_description=idea_description,
            features=features,
        )

        entity_count = len(spec.entities) if spec.entities else 0
        route_count = len(spec.api_routes) if spec.api_routes else 0

        yield PipelineProgress(
            phase="architect",
            step="Architecture complete",
            progress=20,
            message=(
                f"Designed {entity_count} entities, "
                f"{route_count} API routes, "
                f"{len(spec.pages) if spec.pages else 0} pages"
            ),
        )

        # ----------------------------------------------------------------
        # Phase: generate (20–70 %)
        # ----------------------------------------------------------------
        yield PipelineProgress(
            phase="generate",
            step="Starting code generation",
            progress=21,
            message="LLM-powered file generation beginning",
        )

        # Collect events from the engine's progress stream
        files_done = 0
        total_files_estimate = 0
        last_gen_progress = 21

        gen_result_holder: List[GenerationResult] = []

        async def _run_generation() -> None:
            async for event in self.generator.generate_with_progress(
                spec=spec,
                output_dir=str(output_dir),
                theme=theme,
            ):
                nonlocal files_done, total_files_estimate, last_gen_progress
                # ProgressEvent from engine_v2 has .step, .percentage, .current_file
                files_done = getattr(event, "files_done", files_done)
                total_files_estimate = getattr(event, "total_files", total_files_estimate)
                # Map engine percentage (0–100) → pipeline 21–70
                mapped = int(21 + (event.percentage / 100) * 49)
                last_gen_progress = max(last_gen_progress, mapped)

        # We need to yield progress AND collect results, so run generation
        # in a background task while we synthesise progress ticks.
        gen_task = asyncio.create_task(_run_generation())

        # Poll for completion, yielding progress updates every 0.5 s
        while not gen_task.done():
            await asyncio.sleep(0.5)
            yield PipelineProgress(
                phase="generate",
                step="Generating files",
                progress=last_gen_progress,
                message=f"Generating project files…",
                files_generated=files_done,
                total_files=total_files_estimate,
            )

        # Retrieve any exception
        exc = gen_task.exception()
        if exc:
            raise RuntimeError(f"Code generation failed: {exc}") from exc

        # Now do the actual generate() call to get the GenerationResult
        generation: GenerationResult = await self.generator.generate(
            spec=spec,
            output_dir=str(output_dir),
            theme=theme,
        )

        yield PipelineProgress(
            phase="generate",
            step="Code generation complete",
            progress=70,
            message=f"Generated {generation.total_files} files ({generation.total_lines} lines)",
            files_generated=generation.total_files,
            total_files=generation.total_files,
        )

        # ----------------------------------------------------------------
        # Phase: validate (70–82 %)
        # ----------------------------------------------------------------
        yield PipelineProgress(
            phase="validate",
            step="Running quality checks",
            progress=71,
            message="Syntax, security, and completeness checks",
            files_generated=generation.total_files,
            total_files=generation.total_files,
        )

        quality_report: QualityReport = await self.quality.validate(
            output_dir=str(output_dir),
            spec=spec.model_dump(),
        )

        yield PipelineProgress(
            phase="validate",
            step="Quality validation complete",
            progress=82,
            message=quality_report.summary,
            files_generated=generation.total_files,
            total_files=generation.total_files,
        )

        # ----------------------------------------------------------------
        # Phase: critics (82–90 %)
        # ----------------------------------------------------------------
        yield PipelineProgress(
            phase="critics",
            step="Running multi-agent critic panel",
            progress=83,
            message="Code, security, performance, and UX critics reviewing…",
            files_generated=generation.total_files,
            total_files=generation.total_files,
        )

        _critic_report_holder: List[Optional[dict]] = [None]
        try:
            _cr = await self.critic_panel.run(
                output_dir=str(output_dir),
                spec=spec,
            )
            _critic_report_holder[0] = _cr.to_dict()
            logger.info(
                "[pipeline] Critic panel complete — overall_score=%d, critical_issues=%d",
                _cr.overall_score,
                len(_cr.critical_issues),
            )
            _critic_summary = _cr.summary
        except Exception as _exc:
            logger.warning("[pipeline] Critic panel failed (non-blocking): %s", _exc)
            _critic_summary = "Critic panel unavailable"

        yield PipelineProgress(
            phase="critics",
            step="Critic panel complete",
            progress=90,
            message=_critic_summary,
            files_generated=generation.total_files,
            total_files=generation.total_files,
        )

        # ----------------------------------------------------------------
        # Phase: fix (90–97 %)
        # ----------------------------------------------------------------
        fixes_total = 0
        for round_num in range(1, max_fix_rounds + 1):
            if quality_report.passed:
                break

            fix_progress = 90 + int((round_num / max_fix_rounds) * 7)
            yield PipelineProgress(
                phase="fix",
                step=f"Auto-fix round {round_num}",
                progress=fix_progress,
                message=(
                    f"Fixing {quality_report.errors} error(s) "
                    f"and {quality_report.warnings} warning(s)"
                ),
                files_generated=generation.total_files,
                total_files=generation.total_files,
            )

            try:
                fixes_in_round, quality_report = await self.fixer.fix(
                    output_dir=str(output_dir),
                    report=quality_report,
                )
            except Exception as exc:
                logger.warning("[pipeline] AutoFixer round %d failed: %s", round_num, exc)
                break

            fixes_total += fixes_in_round
            if fixes_in_round == 0:
                break

        # ----------------------------------------------------------------
        # Phase: complete (100 %)
        # ----------------------------------------------------------------
        total_time = round(time.monotonic() - t_start, 2)
        if quality_report.passed:
            status = "success_with_warnings" if quality_report.warnings > 0 else "success"
        else:
            status = "failed"

        yield PipelineProgress(
            phase="complete",
            step="Pipeline complete",
            progress=100,
            message=(
                f"Done in {total_time}s — {status} "
                f"(score {quality_report.score}/100, "
                f"{fixes_total} fix(es) applied)"
            ),
            files_generated=generation.total_files,
            total_files=generation.total_files,
            critic_report=_critic_report_holder[0],
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _output_dir(self, idea_name: str) -> Path:
        """Derive a safe output directory from the idea name."""
        safe_name = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in idea_name
        ).strip("_") or "project"
        path = self.output_base_dir / safe_name
        path.mkdir(parents=True, exist_ok=True)
        return path
