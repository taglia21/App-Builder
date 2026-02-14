"""
Main orchestration pipeline for the Startup Generator.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from loguru import logger

from .code_generation import CodeGenerationEngine
from .config import PipelineConfig
from .idea_generation import IdeaGenerationEngine
from .intelligence import IntelligenceGatheringEngine
from .llm import get_llm_client
from .models import (
    PipelineMetadata,
    PipelineOutput,
    PipelineStage,
    PipelineStatus,
    StartupIdea,
)
from .prompt_engineering import PromptEngineeringEngine
from .quality_assurance import QualityAssuranceEngine
from .refinement import RefinementEngine
from .scoring import ScoringEngine


# ARCHITECTURE NOTE: This pipeline is declared async but LLM clients (src/llm/client.py)
# use synchronous HTTP calls via provider SDKs (openai, anthropic, groq).
# The async wrapper exists for future migration to httpx.AsyncClient.
# TODO: Migrate LLM clients to true async for non-blocking I/O in dashboard context.
class StartupGenerationPipeline:
    """Main pipeline for automated startup generation."""

    def __init__(self, config: PipelineConfig, llm_provider: str = "auto"):
        """Initialize the pipeline."""
        self.config = config
        self.llm_provider = llm_provider

        # Initialize LLM client (shared across engines)
        self._llm_client = None

        # Initialize all engines
        self.intelligence_engine = IntelligenceGatheringEngine(config)
        self.idea_engine = IdeaGenerationEngine(config)
        self.scoring_engine = ScoringEngine(config)
        self.qa_engine = QualityAssuranceEngine()

        # LLM-powered engines (initialized lazily)
        self._prompt_engine = None
        self._refinement_engine = None
        self._code_generator = None

        # Pipeline metadata
        self.metadata = PipelineMetadata()

    @property
    def llm_client(self):
        """Lazy initialization of LLM client."""
        if self._llm_client is None:
            self._llm_client = get_llm_client(self.llm_provider)
        return self._llm_client

    @property
    def prompt_engine(self):
        """Lazy initialization of prompt engineering engine."""
        if self._prompt_engine is None:
            self._prompt_engine = PromptEngineeringEngine(self.config, self.llm_client)
        return self._prompt_engine

    @property
    def refinement_engine(self):
        """Lazy initialization of refinement engine."""
        if self._refinement_engine is None:
            self._refinement_engine = RefinementEngine(self.config, self.llm_client)
        return self._refinement_engine

    @property
    def code_generator(self):
        """Lazy initialization of code generation engine."""
        if self._code_generator is None:
            self._code_generator = CodeGenerationEngine(self.config, self.llm_client)
        return self._code_generator

    async def run(self, demo_mode: bool = False, skip_refinement: bool = False, skip_code_gen: bool = False, output_dir: str = "./generated_project", theme: str = "Modern", progress_callback: Optional[Callable[[str, int, str], None]] = None) -> PipelineOutput:
        """Run the complete pipeline.

        Args:
            demo_mode: Use sample data instead of real API calls
            skip_refinement: Skip prompt refinement step
            skip_code_gen: Skip code generation step
            output_dir: Output directory for generated code
            theme: UI theme - one of "Modern", "Minimalist", "Cyberpunk", "Corporate"
            progress_callback: Optional callback(stage_name, percent, message) for progress reporting
        """
        logger.info("=" * 80)
        logger.info("STARTING STARTUP GENERATION PIPELINE")
        if demo_mode:
            logger.info("Running in DEMO MODE - using sample data")
        logger.info(f"Theme: {theme}")
        logger.info("=" * 80)

        self.metadata.status = PipelineStatus.RUNNING
        self.theme = theme  # Store for code generation step

        output = PipelineOutput(metadata=self.metadata)

        try:
            # Step 1: Gather Intelligence
            logger.info("\n[STEP 1/6] Gathering Intelligence")
            self.metadata.current_stage = PipelineStage.INTELLIGENCE
            if progress_callback is not None:
                progress_callback("intelligence", 10, "Gathering market intelligence")
            intelligence_data = await self.intelligence_engine.gather(demo_mode=demo_mode)
            output.intelligence = intelligence_data
            self._save_intermediate(intelligence_data, "intelligence")

            # Step 2: Generate Ideas
            logger.info("\n[STEP 2/6] Generating Startup Ideas")
            self.metadata.current_stage = PipelineStage.IDEA_GENERATION
            if progress_callback is not None:
                progress_callback("ideas", 25, "Generating startup ideas")
            ideas = await self.idea_engine.generate(intelligence_data)
            output.ideas = ideas
            self._save_intermediate(ideas, "ideas")

            # Step 3: Score and Rank Ideas
            logger.info("\n[STEP 3/6] Scoring and Ranking Ideas")
            self.metadata.current_stage = PipelineStage.SCORING
            if progress_callback is not None:
                progress_callback("scoring", 40, "Scoring and ranking ideas")
            evaluation = await self.scoring_engine.evaluate(ideas, intelligence_data)
            output.evaluation = evaluation
            self._save_intermediate(evaluation, "evaluation")

            # Get selected idea
            selected_idea = next(
                (idea for idea in ideas.ideas if idea.id == evaluation.selected_idea_id),
                None,
            )

            if not selected_idea:
                raise ValueError("Selected idea not found in idea catalog")

            output.selected_idea = selected_idea

            logger.info(f"\nSelected Idea: {selected_idea.name}")
            logger.info(f"Score: {evaluation.evaluated_ideas[0].total_score:.2f}")

            # Step 4: Generate Product Prompt
            logger.info("\n[STEP 4/6] Generating Product Prompt")
            self.metadata.current_stage = PipelineStage.PROMPT_ENGINEERING
            if progress_callback is not None:
                progress_callback("prompts", 55, "Engineering product prompt")
            product_prompt = self.prompt_engine.generate(selected_idea, intelligence_data)
            self._save_intermediate(product_prompt, "prompt")

            # Step 5: Refine Prompt to Gold Standard (optional)
            # Track the final prompt to use for code generation
            final_prompt = product_prompt

            if not skip_refinement:
                logger.info("\n[STEP 5/6] Refining Prompt to Gold Standard")
                self.metadata.current_stage = PipelineStage.REFINEMENT
                if progress_callback is not None:
                    progress_callback("refinement", 70, "Refining prompt to gold standard")
                gold_standard_prompt = self.refinement_engine.refine(product_prompt)
                output.gold_standard_prompt = gold_standard_prompt
                self._save_intermediate(gold_standard_prompt, "gold_standard_prompt")
                # Use the refined prompt for code generation
                final_prompt = gold_standard_prompt.product_prompt
                logger.info(f"Refinement complete: {gold_standard_prompt.certification.status.value}")
            else:
                logger.info("\n[STEP 5/6] Skipping Refinement (--skip-refinement flag)")

            # Step 6: Generate Code (optional)
            if not skip_code_gen:
                logger.info("\n[STEP 6/6] Generating Codebase")
                self.metadata.current_stage = PipelineStage.CODE_GENERATION
                if progress_callback is not None:
                    progress_callback("code_gen", 85, "Generating codebase")
                # Use final_prompt which is either refined or original based on skip_refinement flag
                codebase = self.code_generator.generate(final_prompt, output_dir, theme=self.theme)

                # Run Quality Assurance
                logger.info("Running Quality Assurance...")
                self.qa_engine.run_checks(codebase.output_path)

                output.generated_codebase = codebase
                self._save_intermediate(codebase, "codebase")
            else:
                logger.info("\n[STEP 6/6] Skipping Code Generation (--skip-code-gen flag)")

            # Quality Assurance stage
            if progress_callback is not None:
                progress_callback("qa", 95, "Running quality assurance checks")

            # Complete
            self.metadata.status = PipelineStatus.COMPLETED
            self.metadata.completed_at = datetime.now(timezone.utc)
            if progress_callback is not None:
                progress_callback("complete", 100, "Pipeline completed successfully")

            logger.info("\n" + "=" * 80)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"Execution ID: {self.metadata.execution_id}")
            logger.info(f"Duration: {self._get_duration()}")
            logger.info(f"Selected Idea: {selected_idea.name}")
            if output.generated_codebase:
                logger.info(f"Codebase Path: {output.generated_codebase.output_path}")
                logger.info(f"Files Generated: {output.generated_codebase.files_generated}")
            logger.info("=" * 80)

            # Save final output
            self._save_final_output(output)

            return output

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.metadata.status = PipelineStatus.FAILED
            self.metadata.error_message = str(e)
            self.metadata.completed_at = datetime.now(timezone.utc)
            raise

    async def run_from_idea(self, idea: StartupIdea, theme: str = "Modern", output_dir: str = "./generated_project", progress_callback: Optional[Callable[[str, int, str], None]] = None) -> PipelineOutput:
        """Run pipeline starting from an existing idea (skip intelligence and idea generation).

        Args:
            idea: StartupIdea to build
            theme: UI theme - one of "Modern", "Minimalist", "Cyberpunk", "Corporate"
            output_dir: Output directory for generated code
            progress_callback: Optional callback(stage_name, percent, message) for progress reporting
        """
        logger.info("Running pipeline from existing idea")
        logger.info(f"Theme: {theme}")
        logger.info(f"Output directory: {output_dir}")
        self.output_dir = output_dir

        self.metadata.status = PipelineStatus.RUNNING
        self.theme = theme  # Store for code generation
        output = PipelineOutput(metadata=self.metadata)

        try:
            output.selected_idea = idea

            # Create minimal intelligence and evaluation
            from .models import (
                DimensionScore,
                EvaluatedIdea,
                EvaluationReport,
                IdeaScores,
                IntelligenceData,
            )

            intelligence_data = IntelligenceData()
            output.intelligence = intelligence_data

            # Create dummy evaluation
            evaluation = EvaluationReport(
                evaluated_ideas=[
                    EvaluatedIdea(
                        idea_id=idea.id,
                        scores=IdeaScores(
                            market_demand=DimensionScore(
                                score=8, justification="User provided"
                            ),
                            urgency=DimensionScore(score=8, justification="User provided"),
                            enterprise_value=DimensionScore(
                                score=8, justification="User provided"
                            ),
                            recurring_revenue_potential=DimensionScore(
                                score=8, justification="User provided"
                            ),
                            time_to_mvp=DimensionScore(
                                score=8, justification="User provided"
                            ),
                            technical_complexity=DimensionScore(
                                score=8, justification="User provided"
                            ),
                            competition=DimensionScore(
                                score=8, justification="User provided"
                            ),
                            uniqueness=DimensionScore(
                                score=8, justification="User provided"
                            ),
                            automation_potential=DimensionScore(
                                score=8, justification="User provided"
                            ),
                        ),
                        total_score=80.0,
                        rank=1,
                    )
                ],
                selected_idea_id=idea.id,
                selection_reasoning="User-provided idea",
            )
            output.evaluation = evaluation

            # Continue with prompt generation
            self.metadata.current_stage = PipelineStage.PROMPT_ENGINEERING
            if progress_callback is not None:
                progress_callback("prompts", 55, "Engineering product prompt")
            product_prompt = self.prompt_engine.generate(
                idea, intelligence_data
            )

            self.metadata.current_stage = PipelineStage.REFINEMENT
            if progress_callback is not None:
                progress_callback("refinement", 70, "Refining prompt to gold standard")
            gold_standard_prompt = self.refinement_engine.refine(product_prompt)
            output.gold_standard_prompt = gold_standard_prompt
            logger.info(f"Refinement complete: {gold_standard_prompt.certification.status.value}")

            self.metadata.current_stage = PipelineStage.CODE_GENERATION
            if progress_callback is not None:
                progress_callback("code_gen", 85, "Generating codebase")
            # Use the refined prompt's product_prompt for code generation
            codebase = self.code_generator.generate(gold_standard_prompt.product_prompt, output_dir=self.output_dir, theme=self.theme)

            # Run Quality Assurance
            logger.info("Running Quality Assurance...")
            self.qa_engine.run_checks(codebase.output_path)

            output.generated_codebase = codebase

            if progress_callback is not None:
                progress_callback("qa", 95, "Running quality assurance checks")

            self.metadata.status = PipelineStatus.COMPLETED
            self.metadata.completed_at = datetime.now(timezone.utc)
            if progress_callback is not None:
                progress_callback("complete", 100, "Pipeline completed successfully")

            logger.info("Pipeline completed successfully")

            self._save_final_output(output)

            return output

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.metadata.status = PipelineStatus.FAILED
            self.metadata.error_message = str(e)
            raise

    def _save_intermediate(self, data, name: str) -> None:
        """Save intermediate results."""
        output_dir = Path("./output") / str(self.metadata.execution_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = output_dir / f"{name}.json"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data.model_dump(mode="json"), f, indent=2, default=str)

            logger.debug(f"Saved intermediate: {file_path}")

        except Exception as e:
            logger.warning(f"Failed to save intermediate {name}: {e}")

    def _save_final_output(self, output: PipelineOutput) -> None:
        """Save final pipeline output."""
        output_dir = Path("./output") / str(self.metadata.execution_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = output_dir / "pipeline_output.json"

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(output.model_dump(mode="json"), f, indent=2, default=str)

            logger.info(f"Saved final output: {file_path}")

        except Exception as e:
            logger.error(f"Failed to save final output: {e}")

    def _get_duration(self) -> str:
        """Get pipeline execution duration."""
        if self.metadata.completed_at:
            duration = self.metadata.completed_at - self.metadata.started_at
            return str(duration).split(".")[0]
        return "Unknown"


def run_on_schedule(config: PipelineConfig, cron_expression: str) -> None:
    """Run pipeline on a cron schedule.
    
    Args:
        config: Pipeline configuration
        cron_expression: Cron expression (e.g., "0 6 * * 1" for Monday 6am)
    """
    import time

    import schedule

    def job():
        pipeline = StartupGenerationPipeline(config)
        asyncio.run(pipeline.run())

    # Parse cron: "minute hour day_of_month month day_of_week"
    parts = cron_expression.split()
    if len(parts) >= 2:
        minute = parts[0] if parts[0] != "*" else "00"
        hour = parts[1] if parts[1] != "*" else "06"
        time_str = f"{hour.zfill(2)}:{minute.zfill(2)}"
    else:
        time_str = "06:00"

    logger.info(f"Pipeline scheduled daily at {time_str} (from cron: {cron_expression})")
    schedule.every().day.at(time_str).do(job)

    while True:
        schedule.run_pending()
        time.sleep(60)
