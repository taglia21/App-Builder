"""
Legislative Branch - Planning, debate, and policy authority.

Part of the Organizational Intelligence governance model implementing
the separation of powers. The Legislative branch is responsible for:
1. Coordinating rival planners to propose competing strategies
2. Facilitating debate between different perspectives
3. Synthesizing rival plans into coherent proposals
4. Submitting plans for Judicial review before execution
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..messages import CodeGenerationRequest, ExecutionPlan
from ..planners import (
    ConservativePlanner,
    InnovativePlanner,
    PlanSynthesizer,
    PragmaticPlanner,
    SynthesisResult,
)

logger = logging.getLogger(__name__)


class DebateStatus(Enum):
    """Status of the planning debate."""
    GATHERING_PROPOSALS = "gathering_proposals"
    DEBATING = "debating"
    SYNTHESIZING = "synthesizing"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class PlanProposal:
    """A plan proposal from a planner."""
    plan: ExecutionPlan
    planner_type: str
    submitted_at: datetime
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    votes_for: int = 0
    votes_against: int = 0


@dataclass
class LegislativeSession:
    """A planning session with debate and synthesis."""
    session_id: str
    requirements: str
    proposals: List[PlanProposal] = field(default_factory=list)
    debate_log: List[Dict[str, Any]] = field(default_factory=list)
    synthesis_result: Optional[SynthesisResult] = None
    final_plan: Optional[ExecutionPlan] = None
    status: DebateStatus = DebateStatus.GATHERING_PROPOSALS
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class LegislativeBranch:
    """
    The Legislative Branch proposes and debates plans.

    Responsibilities:
    - Coordinate rival planners to propose strategies
    - Facilitate debate between different perspectives
    - Synthesize rival plans into optimal proposals
    - Submit plans to Judicial for review

    The Legislative cannot:
    - Execute plans directly (must go through Executive)
    - Override Judicial vetoes
    - Bypass the synthesis process
    """

    def __init__(self, llm_provider):
        self.llm = llm_provider

        # Initialize rival planners
        self.conservative_planner = ConservativePlanner(llm_provider)
        self.innovative_planner = InnovativePlanner(llm_provider)
        self.pragmatic_planner = PragmaticPlanner(llm_provider)

        # Plan synthesizer
        self.synthesizer = PlanSynthesizer(llm_provider)

        # Session tracking
        self._active_sessions: Dict[str, LegislativeSession] = {}
        self._session_history: List[LegislativeSession] = []
        self._session_counter = 0

    async def propose_plan(
        self,
        request: CodeGenerationRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> LegislativeSession:
        """Initiate a planning session with rival proposals."""
        self._session_counter += 1
        session_id = f"legislative_session_{self._session_counter}"

        session = LegislativeSession(
            session_id=session_id,
            requirements=request.requirements
        )
        self._active_sessions[session_id] = session

        logger.info(f"Legislative: Starting session {session_id}")

        # Phase 1: Gather proposals from all planners concurrently
        session.status = DebateStatus.GATHERING_PROPOSALS
        proposals = await self._gather_proposals(request, context)
        session.proposals = proposals

        logger.info(f"Legislative: Gathered {len(proposals)} proposals")

        # Phase 2: Debate - compare and contrast proposals
        session.status = DebateStatus.DEBATING
        debate_results = await self._conduct_debate(proposals)
        session.debate_log = debate_results

        # Phase 3: Synthesize into final plan
        session.status = DebateStatus.SYNTHESIZING
        synthesis = await self.synthesizer.synthesize(
            [p.plan for p in proposals],
            request.requirements
        )
        session.synthesis_result = synthesis
        session.final_plan = synthesis.final_plan

        # Mark as awaiting review
        session.status = DebateStatus.AWAITING_REVIEW
        session.completed_at = datetime.now()

        logger.info(f"Legislative: Session {session_id} complete, awaiting Judicial review")

        return session

    async def _gather_proposals(
        self,
        request: CodeGenerationRequest,
        context: Optional[Dict[str, Any]]
    ) -> List[PlanProposal]:
        """Gather proposals from all rival planners concurrently."""
        # Run all planners in parallel
        tasks = [
            self._get_proposal(self.conservative_planner, request, context),
            self._get_proposal(self.innovative_planner, request, context),
            self._get_proposal(self.pragmatic_planner, request, context),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        proposals = []
        for result in results:
            if isinstance(result, PlanProposal):
                proposals.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Legislative: A planner failed: {result}")

        return proposals

    async def _get_proposal(
        self,
        planner,
        request: CodeGenerationRequest,
        context: Optional[Dict[str, Any]]
    ) -> PlanProposal:
        """Get a proposal from a single planner."""
        plan = await planner.create_plan(request, context)

        return PlanProposal(
            plan=plan,
            planner_type=planner.personality,
            submitted_at=datetime.now()
        )

    async def _conduct_debate(
        self,
        proposals: List[PlanProposal]
    ) -> List[Dict[str, Any]]:
        """Conduct a debate between proposals, identifying strengths and weaknesses."""
        debate_log = []

        # Compare each pair of proposals
        for i, p1 in enumerate(proposals):
            for p2 in proposals[i+1:]:
                comparison = self.synthesizer.compare_plans(p1.plan, p2.plan)

                debate_entry = {
                    "planner_1": p1.planner_type,
                    "planner_2": p2.planner_type,
                    "agreement_score": comparison.agreement_score,
                    "conflicts": comparison.conflicting_areas,
                    "complementary": comparison.complementary_areas,
                    "recommendation": comparison.recommended_approach
                }
                debate_log.append(debate_entry)

                # Update proposal strengths/weaknesses based on comparison
                if comparison.agreement_score > 0.7:
                    p1.strengths.append(f"High alignment with {p2.planner_type} approach")
                    p2.strengths.append(f"High alignment with {p1.planner_type} approach")

        return debate_log

    def get_session(self, session_id: str) -> Optional[LegislativeSession]:
        """Get a specific session."""
        return self._active_sessions.get(session_id)

    def approve_plan(self, session_id: str) -> Optional[ExecutionPlan]:
        """Mark a session's plan as approved (called by Judicial)."""
        session = self._active_sessions.get(session_id)
        if session and session.status == DebateStatus.AWAITING_REVIEW:
            session.status = DebateStatus.APPROVED
            self._session_history.append(session)
            del self._active_sessions[session_id]
            return session.final_plan
        return None

    def reject_plan(
        self,
        session_id: str,
        reason: str,
        feedback: List[str]
    ) -> bool:
        """Mark a session's plan as rejected (called by Judicial)."""
        session = self._active_sessions.get(session_id)
        if session:
            session.status = DebateStatus.REJECTED
            session.debate_log.append({
                "event": "judicial_rejection",
                "reason": reason,
                "feedback": feedback
            })
            return True
        return False

    async def revise_plan(
        self,
        session_id: str,
        feedback: List[str]
    ) -> Optional[LegislativeSession]:
        """Revise a rejected plan based on Judicial feedback."""
        session = self._active_sessions.get(session_id)
        if not session or session.status != DebateStatus.REJECTED:
            return None

        # Re-run synthesis with feedback incorporated
        # This would typically involve re-querying planners with the feedback
        logger.info(f"Legislative: Revising session {session_id} based on feedback")

        # For now, just re-synthesize with the same proposals
        session.status = DebateStatus.SYNTHESIZING
        synthesis = await self.synthesizer.synthesize(
            [p.plan for p in session.proposals],
            session.requirements + "\n\nFeedback to address: " + "\n".join(feedback)
        )

        session.synthesis_result = synthesis
        session.final_plan = synthesis.final_plan
        session.status = DebateStatus.AWAITING_REVIEW

        return session
