"""
Judicial Branch - Review, arbitration, and veto authority.

Part of the Organizational Intelligence governance model implementing
the separation of powers. The Judicial branch is responsible for:
1. Reviewing plans before execution
2. Coordinating rival critics for comprehensive review
3. Exercising veto authority when standards aren't met
4. Arbitrating conflicts between branches
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..critics import CodeCritic, OutputCritic, PerformanceCritic, SecurityCritic, UXCritic
from ..messages import CriticDecision, CriticReview, ExecutionPlan, GeneratedCode

logger = logging.getLogger(__name__)


class ReviewDecision(Enum):
    """Judicial review decision."""
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    CONDITIONAL_APPROVAL = "conditional_approval"


@dataclass
class JudicialReview:
    """Result of a judicial review."""
    review_id: str
    decision: ReviewDecision
    critic_reviews: List[CriticReview]
    consensus_score: float  # 0-1, how much critics agreed
    majority_decision: CriticDecision
    dissenting_opinions: List[str]
    conditions: List[str]  # Conditions for conditional approval
    feedback: List[str]  # Feedback for revision
    veto_reasons: List[str]  # Reasons if vetoed
    reviewed_at: datetime = field(default_factory=datetime.now)


@dataclass
class ArbitrationCase:
    """A conflict case for arbitration."""
    case_id: str
    parties: List[str]  # Who is in conflict
    issue: str
    positions: Dict[str, str]  # party -> their position
    evidence: List[Dict[str, Any]]
    ruling: Optional[str] = None
    rationale: Optional[str] = None


class JudicialBranch:
    """
    The Judicial Branch reviews and can veto decisions.

    Responsibilities:
    - Review plans from Legislative before execution
    - Coordinate rival critics for comprehensive validation
    - Exercise veto authority when quality standards aren't met
    - Arbitrate conflicts between branches or agents

    The Judicial cannot:
    - Create or modify plans (Legislative's job)
    - Execute plans (Executive's job)
    - Be overruled without addressing feedback
    """

    def __init__(self, llm_provider):
        self.llm = llm_provider

        # Initialize all critics (the "judicial panel")
        self.critics = {
            "code": CodeCritic(llm_provider),
            "output": OutputCritic(llm_provider),
            "security": SecurityCritic(llm_provider),
            "performance": PerformanceCritic(llm_provider),
            "ux": UXCritic(llm_provider)
        }

        # Review tracking
        self._reviews: Dict[str, JudicialReview] = {}
        self._arbitrations: Dict[str, ArbitrationCase] = {}
        self._review_counter = 0

    async def review_code(
        self,
        code: GeneratedCode,
        requirements: str,
        plan: Optional[ExecutionPlan] = None
    ) -> JudicialReview:
        """Conduct a full judicial review of generated code."""
        self._review_counter += 1
        review_id = f"judicial_review_{self._review_counter}"

        logger.info(f"Judicial: Starting review {review_id}")

        # Run all critics concurrently (parallel review)
        critic_tasks = [
            self._run_critic(name, critic, code, requirements)
            for name, critic in self.critics.items()
        ]

        reviews = await asyncio.gather(*critic_tasks, return_exceptions=True)

        # Filter out failed reviews
        valid_reviews = [
            r for r in reviews
            if isinstance(r, CriticReview)
        ]

        # Analyze reviews and make decision
        decision, analysis = self._analyze_reviews(valid_reviews)

        review = JudicialReview(
            review_id=review_id,
            decision=decision,
            critic_reviews=valid_reviews,
            consensus_score=analysis["consensus_score"],
            majority_decision=analysis["majority_decision"],
            dissenting_opinions=analysis["dissenting_opinions"],
            conditions=analysis["conditions"],
            feedback=analysis["feedback"],
            veto_reasons=analysis["veto_reasons"]
        )

        self._reviews[review_id] = review

        logger.info(f"Judicial: Review {review_id} complete - {decision.value}")

        return review

    async def _run_critic(
        self,
        name: str,
        critic,
        code: GeneratedCode,
        requirements: str
    ) -> CriticReview:
        """Run a single critic's review."""
        try:
            return await critic.review(code, requirements)
        except Exception as e:
            logger.error(f"Judicial: Critic {name} failed: {e}")
            raise

    def _analyze_reviews(
        self,
        reviews: List[CriticReview]
    ) -> tuple[ReviewDecision, Dict[str, Any]]:
        """Analyze all critic reviews and determine final decision."""
        if not reviews:
            return ReviewDecision.NEEDS_REVISION, {
                "consensus_score": 0,
                "majority_decision": CriticDecision.NEEDS_REVISION,
                "dissenting_opinions": [],
                "conditions": [],
                "feedback": ["No critic reviews available"],
                "veto_reasons": []
            }

        # Count decisions
        decision_counts = {
            CriticDecision.APPROVE: 0,
            CriticDecision.REJECT: 0,
            CriticDecision.NEEDS_REVISION: 0
        }

        for review in reviews:
            if review.decision in decision_counts:
                decision_counts[review.decision] += 1

        # Find majority decision
        majority_decision = max(decision_counts, key=decision_counts.get)
        majority_count = decision_counts[majority_decision]

        # Calculate consensus score
        total_reviews = len(reviews)
        consensus_score = majority_count / total_reviews if total_reviews > 0 else 0

        # Collect dissenting opinions
        dissenting = []
        for review in reviews:
            if review.decision != majority_decision and review.veto_reason:
                dissenting.append(f"{review.specialty}: {review.veto_reason}")

        # Collect all feedback and issues
        all_feedback = []
        all_conditions = []
        veto_reasons = []

        for review in reviews:
            if review.suggestions:
                all_feedback.extend(review.suggestions)
            if review.decision == CriticDecision.REJECT and review.veto_reason:
                veto_reasons.append(f"{review.specialty}: {review.veto_reason}")

        # Determine final judicial decision
        # If ANY critic with veto authority rejects, we reject
        has_veto = any(
            r.decision == CriticDecision.REJECT
            for r in reviews
            if r.specialty in ["security", "code"]
        )

        if has_veto:
            final_decision = ReviewDecision.REJECTED
        elif decision_counts[CriticDecision.REJECT] >= 2:
            # Two or more rejections = rejected
            final_decision = ReviewDecision.REJECTED
        elif majority_decision == CriticDecision.APPROVE and consensus_score >= 0.6:
            if dissenting:
                final_decision = ReviewDecision.CONDITIONAL_APPROVAL
                all_conditions = [f"Address: {d}" for d in dissenting]
            else:
                final_decision = ReviewDecision.APPROVED
        elif majority_decision == CriticDecision.NEEDS_REVISION:
            final_decision = ReviewDecision.NEEDS_REVISION
        else:
            final_decision = ReviewDecision.NEEDS_REVISION

        return final_decision, {
            "consensus_score": consensus_score,
            "majority_decision": majority_decision,
            "dissenting_opinions": dissenting,
            "conditions": all_conditions,
            "feedback": all_feedback[:10],  # Limit feedback
            "veto_reasons": veto_reasons
        }

    async def veto_check(
        self,
        action: str,
        step: Any,
        context: Any
    ) -> Dict[str, Any]:
        """Real-time veto check during execution (called by Executive)."""
        # Quick check for obvious issues
        # This would be called before each execution step

        # For now, always allow (real implementation would do quick validation)
        return {"vetoed": False}

    def arbitrate(
        self,
        parties: List[str],
        issue: str,
        positions: Dict[str, str]
    ) -> ArbitrationCase:
        """Arbitrate a conflict between parties."""
        case_id = f"arbitration_{len(self._arbitrations) + 1}"

        case = ArbitrationCase(
            case_id=case_id,
            parties=parties,
            issue=issue,
            positions=positions,
            evidence=[]
        )

        # Simple arbitration: favor the more conservative position for safety
        if "conservative" in positions:
            case.ruling = positions["conservative"]
            case.rationale = "Conservative approach chosen for safety"
        elif "pragmatic" in positions:
            case.ruling = positions["pragmatic"]
            case.rationale = "Pragmatic approach chosen for balance"
        else:
            case.ruling = list(positions.values())[0]
            case.rationale = "First position adopted as default"

        self._arbitrations[case_id] = case
        return case

    def get_review(self, review_id: str) -> Optional[JudicialReview]:
        """Get a specific review."""
        return self._reviews.get(review_id)

    def get_all_reviews(self) -> List[JudicialReview]:
        """Get all reviews."""
        return list(self._reviews.values())
