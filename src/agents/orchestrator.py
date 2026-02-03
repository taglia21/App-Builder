"""
AI Office Orchestrator - Coordinates multi-agent workflows.

Implements the hierarchical organization structure with:
- Planning team
- Execution team (writers)
- Validation team (critics with veto authority)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .base import LLMProvider
from .critics.code_critic import CodeCritic
from .critics.output_critic import OutputCritic
from .messages import (
    CodeGenerationRequest,
    CriticDecision,
    CriticReview,
    ExecutionPlan,
    GeneratedCode,
    OrchestrationState,
    PlanningRequest,
    TaskStatus,
)
from .planners.planner_agent import PlannerAgent
from .writers.code_writer import CodeWriterAgent

logger = logging.getLogger(__name__)


class AIOfficeOrchestrator:
    """
    Orchestrates the multi-agent workflow for app generation.

    Key principles from the paper:
    1. Pre-declared acceptance criteria (defined before execution)
    2. Veto authority for critics (can reject at any stage)
    3. Iterative improvement (retry with feedback)
    4. Checkpointing (state can be serialized/resumed)
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        max_retries: int = 3
    ):
        self.llm_provider = llm_provider or LLMProvider()
        self.max_retries = max_retries

        # Initialize agents
        self.planner = PlannerAgent(llm_provider=self.llm_provider)
        self.code_writer = CodeWriterAgent(llm_provider=self.llm_provider)
        self.code_critic = CodeCritic(llm_provider=self.llm_provider)
        self.output_critic = OutputCritic(llm_provider=self.llm_provider)

        # State tracking
        self.current_state: Optional[OrchestrationState] = None

    async def generate_app(
        self,
        description: str,
        tech_stack: Optional[str] = None,
        features: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> Tuple[GeneratedCode, OrchestrationState]:
        """
        Main entry point for app generation with multi-agent validation.

        Returns:
            Tuple of (generated_code, orchestration_state)
        """
        # Initialize state
        self.current_state = OrchestrationState(
            max_retries=self.max_retries
        )

        try:
            # PHASE 1: Planning
            self.current_state.current_step = "planning"
            self.current_state.status = TaskStatus.IN_PROGRESS
            logger.info(f"Starting planning phase for: {description[:100]}...")

            plan = await self._execute_planning(
                description, tech_stack, features, user_id
            )
            self.current_state.plan = plan

            # PHASE 2: Code Generation with Validation Loop
            self.current_state.current_step = "code_generation"

            code = await self._execute_code_generation_with_validation(plan)
            self.current_state.generated_code = code

            # Success!
            self.current_state.status = TaskStatus.COMPLETED
            self.current_state.current_step = "completed"
            self.current_state.updated_at = datetime.now(timezone.utc)

            logger.info(f"Successfully generated app: {plan.plan_id}")
            return code, self.current_state

        except Exception as e:
            self.current_state.status = TaskStatus.FAILED
            self.current_state.add_error(str(e))
            logger.error(f"App generation failed: {e}")
            raise

    async def _execute_planning(
        self,
        description: str,
        tech_stack: Optional[str],
        features: Optional[List[str]],
        user_id: Optional[str]
    ) -> ExecutionPlan:
        """Execute the planning phase."""
        request = PlanningRequest(
            app_description=description,
            tech_stack=tech_stack,
            features=features or [],
            user_id=user_id
        )

        plan = await self.planner.create_plan(request)

        logger.info(f"Plan created with {len(plan.acceptance_criteria)} acceptance criteria")
        return plan

    async def _execute_code_generation_with_validation(
        self,
        plan: ExecutionPlan
    ) -> GeneratedCode:
        """
        Execute code generation with the validation loop.

        This implements the core "Team of Rivals" pattern:
        1. Writer generates code
        2. Critics review and can veto
        3. If vetoed, retry with feedback
        4. After max retries, fail
        """
        previous_feedback: Optional[str] = None

        for attempt in range(self.max_retries):
            self.current_state.retry_count = attempt
            logger.info(f"Code generation attempt {attempt + 1}/{self.max_retries}")

            # Generate code
            request = CodeGenerationRequest(
                plan=plan,
                target_files=plan.metadata.get("required_files", []),
                retry_count=attempt,
                previous_feedback=previous_feedback
            )

            code = await self.code_writer.write(request)

            # Validate with Code Critic
            code_review = await self._validate_with_code_critic(code, plan)
            self.current_state.critic_reviews.append(code_review)

            if self.code_critic.should_veto(code_review):
                logger.warning(f"Code critic vetoed: {code_review.veto_reason}")
                previous_feedback = self._compile_feedback(code_review)
                continue  # Retry

            # Validate with Output Critic
            output_review = await self._validate_with_output_critic(code, plan)
            self.current_state.critic_reviews.append(output_review)

            if self.output_critic.should_veto(output_review):
                logger.warning(f"Output critic vetoed: {output_review.veto_reason}")
                previous_feedback = self._compile_feedback(output_review)
                continue  # Retry

            # Both critics approved!
            logger.info("All critics approved the generated code")
            return code

        # Exhausted retries
        self.current_state.status = TaskStatus.VETOED
        raise ValueError(
            f"Failed to generate acceptable code after {self.max_retries} attempts. "
            f"Last feedback: {previous_feedback}"
        )

    async def _validate_with_code_critic(
        self,
        code: GeneratedCode,
        plan: ExecutionPlan
    ) -> CriticReview:
        """Validate code with the code critic."""
        logger.info("Validating with code critic...")
        return await self.code_critic.review(
            artifact=code,
            context={"plan": plan.model_dump()}
        )

    async def _validate_with_output_critic(
        self,
        code: GeneratedCode,
        plan: ExecutionPlan
    ) -> CriticReview:
        """Validate code against acceptance criteria."""
        logger.info("Validating against acceptance criteria...")
        return await self.output_critic.review(
            artifact=code,
            context={"plan": plan}
        )

    def _compile_feedback(self, review: CriticReview) -> str:
        """Compile feedback from a critic review for the next attempt."""
        feedback_parts = [f"REJECTION REASON: {review.veto_reason or review.reasoning}"]

        if review.issues:
            feedback_parts.append("\nISSUES TO FIX:")
            for issue in review.issues:
                severity = issue.get("severity", "unknown")
                desc = issue.get("description", str(issue))
                location = issue.get("location", "")
                feedback_parts.append(f"- [{severity}] {desc} {location}")

        if review.suggestions:
            feedback_parts.append("\nSUGGESTIONS:")
            for suggestion in review.suggestions:
                feedback_parts.append(f"- {suggestion}")

        return "\n".join(feedback_parts)

    def get_state(self) -> Optional[OrchestrationState]:
        """Get current orchestration state for checkpointing."""
        return self.current_state

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the current/last run."""
        if not self.current_state:
            return {}

        return {
            "session_id": self.current_state.session_id,
            "status": self.current_state.status.value,
            "retry_count": self.current_state.retry_count,
            "total_reviews": len(self.current_state.critic_reviews),
            "approvals": sum(
                1 for r in self.current_state.critic_reviews
                if r.decision == CriticDecision.APPROVE
            ),
            "rejections": sum(
                1 for r in self.current_state.critic_reviews
                if r.decision == CriticDecision.REJECT
            ),
            "error_count": len(self.current_state.error_log)
        }
