"""
Output Critic Agent - Validates output against requirements.

Validates that generated code meets the pre-declared
acceptance criteria from the planning phase.
"""

from typing import Any, Dict, List, Optional
import logging

from ..base import CriticAgent, LLMProvider
from ..messages import (
    AgentRole, CriticDecision, CriticReview, GeneratedCode, ExecutionPlan
)

logger = logging.getLogger(__name__)


class OutputCritic(CriticAgent):
    """
    Validates that output meets acceptance criteria.
    
    This is the final quality gate before user sees the code.
    Implements the "pre-declared acceptance criteria" concept.
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None,
        veto_threshold: float = 0.7
    ):
        super().__init__(
            role=AgentRole.OUTPUT_CRITIC,
            agent_id=agent_id,
            llm_provider=llm_provider,
            veto_threshold=veto_threshold
        )
    
    def get_system_prompt(self) -> str:
        return """You are an Output Critic Agent with VETO AUTHORITY.

Your role is to verify that generated code meets ALL acceptance criteria.

CRITICAL: These criteria were defined BEFORE code generation.
You must objectively evaluate whether each criterion is met.

For each acceptance criterion, you must:
1. Determine if it is FULLY MET, PARTIALLY MET, or NOT MET
2. Provide evidence from the code
3. If not met, explain what's missing

Respond in JSON format:
{
    "decision": "approve" | "reject" | "request_changes",
    "score": 0.0-1.0,
    "reasoning": "Overall assessment",
    "criteria_evaluation": [
        {
            "criterion": "The criterion text",
            "status": "met" | "partial" | "not_met",
            "evidence": "Code evidence or explanation"
        }
    ],
    "issues": [{"severity": "...", "description": "..."}],
    "suggestions": ["..."]
}

ALL criteria must be MET for APPROVE. Any NOT MET = REJECT."""

    async def review(self, artifact: Any, context: Dict[str, Any]) -> CriticReview:
        """Review output against acceptance criteria."""
        # Extract code and plan from artifact/context
        if isinstance(artifact, GeneratedCode):
            code = artifact
        elif isinstance(artifact, dict):
            code = GeneratedCode(**artifact) if "files" in artifact else None
        else:
            code = None
        
        plan = context.get("plan")
        if isinstance(plan, dict):
            plan = ExecutionPlan(**plan)
        
        if not code or not plan:
            return CriticReview(
                critic_role=self.role,
                decision=CriticDecision.REJECT,
                reasoning="Missing code or plan for validation",
                score=0.0,
                veto_reason="Cannot validate without code and plan"
            )
        
        # Get LLM evaluation against criteria
        return await self._evaluate_against_criteria(code, plan)
    
    async def _evaluate_against_criteria(self, code: GeneratedCode, plan: ExecutionPlan) -> CriticReview:
        """Evaluate code against acceptance criteria."""
        # Build file summary
        files_summary = "\n\n".join(
            f"=== {name} ===\n{content[:3000]}{'...(truncated)' if len(content) > 3000 else ''}"
            for name, content in code.files.items()
        )
        
        criteria_list = "\n".join(
            f"{i+1}. {c}" for i, c in enumerate(plan.acceptance_criteria)
        )
        
        user_message = f"""Evaluate this code against the acceptance criteria:

ORIGINAL DESCRIPTION:
{plan.app_description}

ACCEPTANCE CRITERIA (defined before code generation):
{criteria_list}

GENERATED CODE:
{files_summary}

Dependencies: {', '.join(code.dependencies)}

Evaluate EACH criterion and provide your decision in JSON format."""
        
        response = await self._call_llm(user_message, temperature=0.3)
        review_data = self._parse_json_response(response)
        
        # Calculate score based on criteria met
        criteria_eval = review_data.get("criteria_evaluation", [])
        if criteria_eval:
            met_count = sum(1 for c in criteria_eval if c.get("status") == "met")
            score = met_count / len(criteria_eval)
        else:
            score = review_data.get("score", 0.5)
        
        # Determine decision
        decision_str = review_data.get("decision", "reject").lower()
        
        # If any criterion is not met, override to reject
        not_met = [c for c in criteria_eval if c.get("status") == "not_met"]
        if not_met:
            decision = CriticDecision.REJECT
            veto_reason = f"{len(not_met)} acceptance criteria not met"
        else:
            decision_map = {
                "approve": CriticDecision.APPROVE,
                "reject": CriticDecision.REJECT,
                "request_changes": CriticDecision.REQUEST_CHANGES
            }
            decision = decision_map.get(decision_str, CriticDecision.REJECT)
            veto_reason = review_data.get("reasoning") if decision == CriticDecision.REJECT else None
        
        # Build issues from unmet criteria
        issues = []
        for c in criteria_eval:
            if c.get("status") != "met":
                issues.append({
                    "severity": "high" if c.get("status") == "not_met" else "medium",
                    "description": f"Criterion '{c.get('criterion')}': {c.get('evidence', 'Not met')}"
                })
        
        # Add any additional issues from LLM
        issues.extend(review_data.get("issues", []))
        
        return CriticReview(
            critic_role=self.role,
            decision=decision,
            reasoning=review_data.get("reasoning", "Evaluated against acceptance criteria"),
            issues=issues,
            suggestions=review_data.get("suggestions", []),
            score=score,
            veto_reason=veto_reason
        )
