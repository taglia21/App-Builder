"""
Governance Orchestrator - Organizational Intelligence Integration.

This orchestrator integrates the three branches of governance:
- Legislative: Rival planners propose and debate strategies
- Judicial: Rival critics review with veto authority
- Executive: Controlled execution with oversight

This replaces the single-agent approach with a multi-agent system
that achieves coherence through constructive rivalry.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import LLMProvider
from .governance import (
    ExecutiveBranch,
    JudicialBranch,
    LegislativeBranch,
    ReviewDecision,
)
from .messages import (
    CodeGenerationRequest,
    GeneratedCode,
    GovernanceState,
    OrchestrationState,
)
from .writers.code_writer import CodeWriterAgent as CodeWriter

logger = logging.getLogger(__name__)


class GovernanceOrchestrator:
    """
    Orchestrator implementing the Organizational Intelligence framework.

    This orchestrator coordinates three branches of governance:

    1. LEGISLATIVE BRANCH (Planning)
       - Rival planners (conservative, innovative, pragmatic) propose strategies
       - Plans are debated and synthesized
       - Final plan submitted for review

    2. JUDICIAL BRANCH (Validation)
       - Rival critics (code, security, performance, UX, output) review code
       - Veto authority for quality standards
       - Arbitration for conflicts

    3. EXECUTIVE BRANCH (Execution)
       - Executes approved plans
       - Respects judicial veto
       - Reports progress transparently

    The separation of powers ensures no single agent has unchecked authority,
    leading to higher quality outputs through constructive rivalry.
    """

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

        # Initialize the three branches
        self.legislative = LegislativeBranch(llm_provider)
        self.judicial = JudicialBranch(llm_provider)

        # Executive needs a code writer and judicial callback
        self.code_writer = CodeWriter(llm_provider)
        self.executive = ExecutiveBranch(
            code_writer=self.code_writer,
            judicial_callback=self.judicial.veto_check
        )

        # State tracking
        self.governance_state = GovernanceState()
        self.current_state = OrchestrationState()

        # Statistics
        self.stats = {
            "plans_proposed": 0,
            "plans_synthesized": 0,
            "reviews_conducted": 0,
            "vetoes_issued": 0,
            "executions_completed": 0,
            "revisions_requested": 0
        }

    async def generate_app(
        self,
        requirements: str,
        context: Optional[Dict[str, Any]] = None
    ) -> GeneratedCode:
        """
        Generate an application using the full governance model.

        Flow:
        1. Legislative: Rival planners propose -> debate -> synthesize
        2. Judicial: Review synthesized plan (can request revision)
        3. Executive: Execute approved plan
        4. Judicial: Review generated code
        5. If approved, return code; else iterate

        Args:
            requirements: Natural language requirements
            context: Optional context (tech stack preferences, etc.)

        Returns:
            GeneratedCode with all files and metadata
        """
        logger.info("Governance Orchestrator: Starting app generation")
        datetime.now()

        request = CodeGenerationRequest(
            requirements=requirements,
            context=context or {}
        )

        max_iterations = 3
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Governance Orchestrator: Iteration {iteration}")

            # ================================================================
            # PHASE 1: LEGISLATIVE - Plan Proposal and Synthesis
            # ================================================================
            self.governance_state.phase = "planning"
            logger.info("Phase 1: Legislative - Gathering rival plans")

            session = await self.legislative.propose_plan(request, context)
            self.stats["plans_proposed"] += len(session.proposals)
            self.stats["plans_synthesized"] += 1

            self.governance_state.current_session_id = session.session_id
            self.governance_state.proposals_received = len(session.proposals)
            self.governance_state.synthesis_complete = True

            logger.info(f"Legislative: Synthesized plan from {len(session.proposals)} proposals")

            # ================================================================
            # PHASE 2: EXECUTIVE - Code Generation
            # ================================================================
            self.governance_state.phase = "execution"
            logger.info("Phase 2: Executive - Generating code")

            # Execute the plan to generate code
            execution_result = await self.executive.execute_plan(
                plan=session.final_plan,
                requirements=requirements,
                approval_token=session.session_id,
                context=context
            )

            if execution_result.vetoed:
                logger.warning(f"Executive: Execution vetoed - {execution_result.veto_reason}")
                self.stats["vetoes_issued"] += 1
                continue

            if not execution_result.success or not execution_result.generated_code:
                logger.error(f"Executive: Execution failed - {execution_result.errors}")
                self.governance_state.error_log.extend(execution_result.errors)
                continue

            generated_code = execution_result.generated_code

            # ================================================================
            # PHASE 3: JUDICIAL - Code Review
            # ================================================================
            self.governance_state.phase = "review"
            logger.info("Phase 3: Judicial - Reviewing generated code")

            review = await self.judicial.review_code(
                code=generated_code,
                requirements=requirements,
                plan=session.final_plan
            )

            self.stats["reviews_conducted"] += 1
            self.governance_state.review_id = review.review_id
            self.governance_state.critics_completed = len(review.critic_reviews)
            self.governance_state.approval_status = review.decision.value

            logger.info(f"Judicial: Review complete - {review.decision.value} (consensus: {review.consensus_score:.2f})")

            # ================================================================
            # PHASE 4: Handle Review Decision
            # ================================================================
            if review.decision == ReviewDecision.APPROVED:
                logger.info("Judicial: Code APPROVED")
                self.stats["executions_completed"] += 1
                self.governance_state.phase = "complete"

                # Add governance metadata to the result
                generated_code.metadata["governance"] = {
                    "session_id": session.session_id,
                    "review_id": review.review_id,
                    "planners_consulted": [p.planner_type for p in session.proposals],
                    "critics_consulted": [c.specialty for c in review.critic_reviews],
                    "consensus_score": review.consensus_score,
                    "iterations": iteration,
                    "synthesis_contributions": session.synthesis_result.contributions if session.synthesis_result else {}
                }

                return generated_code

            elif review.decision == ReviewDecision.CONDITIONAL_APPROVAL:
                logger.info(f"Judicial: CONDITIONAL approval - {review.conditions}")
                # Accept with noted conditions
                generated_code.metadata["governance"] = {
                    "session_id": session.session_id,
                    "review_id": review.review_id,
                    "approval": "conditional",
                    "conditions": review.conditions,
                    "consensus_score": review.consensus_score
                }
                self.governance_state.phase = "complete"
                return generated_code

            elif review.decision == ReviewDecision.NEEDS_REVISION:
                logger.info(f"Judicial: Revision requested - {review.feedback[:3]}")
                self.stats["revisions_requested"] += 1

                # Add feedback to context for next iteration
                if context is None:
                    context = {}
                context["revision_feedback"] = review.feedback
                context["previous_issues"] = [str(r.issues) for r in review.critic_reviews]

                # Update requirements with feedback
                requirements = f"{requirements}\n\nPrevious review feedback to address:\n" + "\n".join(review.feedback[:5])

            else:  # REJECTED
                logger.warning(f"Judicial: Code REJECTED - {review.veto_reasons}")
                self.stats["vetoes_issued"] += 1

                if context is None:
                    context = {}
                context["rejection_reasons"] = review.veto_reasons
                requirements = f"{requirements}\n\nCritical issues to fix:\n" + "\n".join(review.veto_reasons)

        # Max iterations reached
        logger.error(f"Governance Orchestrator: Max iterations ({max_iterations}) reached")
        self.governance_state.phase = "failed"

        # Return last generated code with failure metadata
        if generated_code:
            generated_code.metadata["governance"] = {
                "status": "max_iterations_reached",
                "iterations": iteration,
                "last_review_decision": review.decision.value if review else "none"
            }
            return generated_code

        raise RuntimeError("Failed to generate code after maximum iterations")

    def get_state(self) -> Dict[str, Any]:
        """Get current governance state."""
        return {
            "governance": self.governance_state.dict(),
            "orchestration": self.current_state.dict() if hasattr(self.current_state, 'dict') else {},
            "stats": self.stats
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestration statistics."""
        return {
            **self.stats,
            "legislative_sessions": len(self.legislative._session_history),
            "judicial_reviews": len(self.judicial._reviews),
            "executive_history": len(self.executive._execution_history)
        }

    async def get_debate_log(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get the debate log from a legislative session."""
        session = self.legislative.get_session(session_id)
        if session:
            return session.debate_log
        return None

    async def get_review_details(self, review_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a judicial review."""
        review = self.judicial.get_review(review_id)
        if review:
            return {
                "review_id": review.review_id,
                "decision": review.decision.value,
                "consensus_score": review.consensus_score,
                "critic_reviews": [
                    {
                        "specialty": r.specialty,
                        "decision": r.decision.value if hasattr(r.decision, 'value') else str(r.decision),
                        "score": r.score,
                        "issues_count": len(r.issues) if r.issues else 0
                    }
                    for r in review.critic_reviews
                ],
                "feedback": review.feedback,
                "veto_reasons": review.veto_reasons
            }
        return None
