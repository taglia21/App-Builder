"""
Plan Synthesizer - Merges rival plans into a coherent execution strategy.

Part of the Organizational Intelligence framework, this component takes
competing plans from rival planners and synthesizes them into an optimal
final plan through debate, voting, and intelligent merging.
"""

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List

from ..base import LLMProvider
from ..messages import ExecutionPlan, PlanStep

logger = logging.getLogger(__name__)


@dataclass
class PlanComparison:
    """Result of comparing two plans."""
    agreement_score: float  # 0-1, how much plans agree
    conflicting_areas: List[str]
    complementary_areas: List[str]
    recommended_approach: str


@dataclass
class SynthesisResult:
    """Result of plan synthesis."""
    final_plan: ExecutionPlan
    synthesis_reasoning: str
    contributions: Dict[str, List[str]]  # planner -> what they contributed
    conflicts_resolved: List[Dict[str, Any]]
    confidence_score: float


class PlanSynthesizer:
    """
    Synthesizes multiple rival plans into an optimal execution strategy.

    This implements the "legislative" function of organizational intelligence,
    where different perspectives debate and merge into a coherent outcome.

    Synthesis strategies:
    1. Voting: Let plans vote on individual decisions
    2. Best-of-breed: Take best elements from each plan
    3. Consensus: Find common ground across all plans
    4. Arbitration: Use LLM to resolve conflicts
    """

    SYNTHESIS_PROMPT = '''You are a Plan Synthesizer - combining rival plans into an optimal strategy.

You have received plans from three rival planners with different philosophies:
- CONSERVATIVE: Risk-averse, proven patterns, stability-focused
- INNOVATIVE: Cutting-edge, modern, scalability-focused
- PRAGMATIC: Balanced, practical, value-focused

Your task is to synthesize these into ONE optimal plan that:
1. Takes the best ideas from each approach
2. Resolves conflicts intelligently
3. Creates a coherent, executable strategy
4. Maintains internal consistency

PLAN 1 (Conservative):
{conservative_plan}

PLAN 2 (Innovative):
{innovative_plan}

PLAN 3 (Pragmatic):
{pragmatic_plan}

Original Requirements:
{requirements}

Respond with JSON:
{{
    "synthesized_plan": {{
        "plan_id": "synthesized_plan_001",
        "steps": [
            {{
                "step_id": 1,
                "name": "step name",
                "description": "detailed description",
                "source_planners": ["which planners contributed to this step"],
                "synthesis_rationale": "why this approach was chosen",
                "dependencies": [],
                "validation_criteria": ["how to verify success"],
                "estimated_effort": "low|medium|high"
            }}
        ],
        "technology_choices": [
            {{
                "category": "category",
                "choice": "technology",
                "selected_from": "which planner suggested this",
                "selection_rationale": "why this choice won"
            }}
        ]
    }},
    "conflict_resolutions": [
        {{
            "conflict": "description of conflict",
            "conservative_position": "what conservative suggested",
            "innovative_position": "what innovative suggested",
            "pragmatic_position": "what pragmatic suggested",
            "resolution": "how it was resolved",
            "rationale": "why this resolution"
        }}
    ],
    "contributions": {{
        "conservative": ["list of contributions from conservative plan"],
        "innovative": ["list of contributions from innovative plan"],
        "pragmatic": ["list of contributions from pragmatic plan"]
    }},
    "overall_confidence": 0-100,
    "synthesis_reasoning": "overall explanation of synthesis approach"
}}

Create a plan that gets the best of all worlds while remaining coherent and executable.'''

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    async def synthesize(
        self,
        plans: List[ExecutionPlan],
        requirements: str
    ) -> SynthesisResult:
        """Synthesize multiple plans into an optimal execution strategy."""
        logger.info(f"Synthesizing {len(plans)} rival plans")

        # Organize plans by type
        plans_by_type = {p.planner_type: p for p in plans}

        # Get each plan type (with fallbacks)
        conservative = plans_by_type.get("conservative")
        innovative = plans_by_type.get("innovative")
        pragmatic = plans_by_type.get("pragmatic")

        # If we only have one plan, return it directly
        if len(plans) == 1:
            return SynthesisResult(
                final_plan=plans[0],
                synthesis_reasoning="Single plan received, no synthesis needed",
                contributions={plans[0].planner_type: ["entire plan"]},
                conflicts_resolved=[],
                confidence_score=plans[0].confidence_score
            )

        # Perform synthesis
        prompt = self.SYNTHESIS_PROMPT.format(
            conservative_plan=self._plan_to_json(conservative) if conservative else "Not provided",
            innovative_plan=self._plan_to_json(innovative) if innovative else "Not provided",
            pragmatic_plan=self._plan_to_json(pragmatic) if pragmatic else "Not provided",
            requirements=requirements
        )

        response = await self.llm.generate(prompt)

        try:
            synthesis_data = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse synthesis response, using fallback")
            return self._fallback_synthesis(plans, requirements)

        # Build the final plan from synthesis
        synth_plan = synthesis_data.get("synthesized_plan", {})
        steps = [
            PlanStep(
                step_id=s.get("step_id", i),
                name=s.get("name", f"Step {i}"),
                description=s.get("description", ""),
                dependencies=s.get("dependencies", []),
                validation_criteria=s.get("validation_criteria", []),
                estimated_effort=s.get("estimated_effort", "medium"),
                metadata={
                    "source_planners": s.get("source_planners", []),
                    "synthesis_rationale": s.get("synthesis_rationale", "")
                }
            )
            for i, s in enumerate(synth_plan.get("steps", []), 1)
        ]

        final_plan = ExecutionPlan(
            plan_id=synth_plan.get("plan_id", "synthesized_plan"),
            planner_type="synthesized",
            steps=steps,
            confidence_score=synthesis_data.get("overall_confidence", 75),
            risk_assessment="medium",  # Synthesized plans balance risk
            estimated_complexity="moderate",
            technology_choices=synth_plan.get("technology_choices", []),
            risk_mitigations=[],
            testing_strategy="Balanced testing strategy from all perspectives",
            reasoning=synthesis_data.get("synthesis_reasoning", "Synthesized from rival plans")
        )

        return SynthesisResult(
            final_plan=final_plan,
            synthesis_reasoning=synthesis_data.get("synthesis_reasoning", ""),
            contributions=synthesis_data.get("contributions", {}),
            conflicts_resolved=synthesis_data.get("conflict_resolutions", []),
            confidence_score=synthesis_data.get("overall_confidence", 75)
        )

    def _plan_to_json(self, plan: ExecutionPlan) -> str:
        """Convert ExecutionPlan to JSON string for prompt."""
        return json.dumps({
            "plan_id": plan.plan_id,
            "planner_type": plan.planner_type,
            "confidence_score": plan.confidence_score,
            "risk_assessment": plan.risk_assessment,
            "steps": [
                {
                    "step_id": s.step_id,
                    "name": s.name,
                    "description": s.description,
                    "dependencies": s.dependencies,
                    "estimated_effort": s.estimated_effort
                }
                for s in plan.steps
            ],
            "technology_choices": plan.technology_choices,
            "reasoning": plan.reasoning
        }, indent=2)

    def _fallback_synthesis(self, plans: List[ExecutionPlan], requirements: str) -> SynthesisResult:
        """Fallback synthesis using voting/merging heuristics."""
        logger.info("Using fallback synthesis strategy")

        # Simple strategy: merge steps from all plans, deduplicate
        all_steps = []
        step_names_seen = set()
        contributions = defaultdict(list)

        # Sort plans by confidence score
        sorted_plans = sorted(plans, key=lambda p: p.confidence_score, reverse=True)

        for plan in sorted_plans:
            for step in plan.steps:
                # Simple deduplication by name similarity
                if step.name.lower() not in step_names_seen:
                    all_steps.append(step)
                    step_names_seen.add(step.name.lower())
                    contributions[plan.planner_type].append(step.name)

        # Renumber steps
        for i, step in enumerate(all_steps, 1):
            step.step_id = i

        # Average confidence
        avg_confidence = sum(p.confidence_score for p in plans) / len(plans)

        final_plan = ExecutionPlan(
            plan_id="fallback_synthesized_plan",
            planner_type="synthesized",
            steps=all_steps,
            confidence_score=avg_confidence,
            risk_assessment="medium",
            estimated_complexity="moderate",
            technology_choices=[],
            risk_mitigations=[],
            testing_strategy="Combined testing approach",
            reasoning="Fallback synthesis combining unique steps from all plans"
        )

        return SynthesisResult(
            final_plan=final_plan,
            synthesis_reasoning="Fallback synthesis: merged unique steps from all plans",
            contributions=dict(contributions),
            conflicts_resolved=[],
            confidence_score=avg_confidence
        )

    def compare_plans(self, plan1: ExecutionPlan, plan2: ExecutionPlan) -> PlanComparison:
        """Compare two plans to identify agreements and conflicts."""
        # Extract step names for comparison
        steps1 = {s.name.lower() for s in plan1.steps}
        steps2 = {s.name.lower() for s in plan2.steps}

        # Find overlaps and differences
        common_steps = steps1 & steps2
        only_in_1 = steps1 - steps2
        only_in_2 = steps2 - steps1

        # Calculate agreement score
        total_unique = len(steps1 | steps2)
        agreement_score = len(common_steps) / total_unique if total_unique > 0 else 0

        # Identify conflicts (different approaches to same goal)
        conflicts = []
        if plan1.risk_assessment != plan2.risk_assessment:
            conflicts.append(f"Risk assessment: {plan1.planner_type}={plan1.risk_assessment} vs {plan2.planner_type}={plan2.risk_assessment}")

        # Identify complementary areas
        complementary = list(only_in_1) + list(only_in_2)

        return PlanComparison(
            agreement_score=agreement_score,
            conflicting_areas=conflicts,
            complementary_areas=complementary,
            recommended_approach="merge" if agreement_score > 0.5 else "arbitrate"
        )
