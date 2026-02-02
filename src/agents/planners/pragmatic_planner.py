"""
Pragmatic Planner Agent - Balanced, outcome-focused perspective.

Part of the Organizational Intelligence framework implementing rival
planning agents that propose competing strategies for synthesis.
"""

from typing import Any, Dict, List, Optional
import logging
import json

from ..base import LLMProvider
from ..messages import (
    AgentRole, ExecutionPlan, PlanStep, CodeGenerationRequest
)

logger = logging.getLogger(__name__)


class PragmaticPlanner:
    """
    Pragmatic planning agent that balances innovation with practicality.
    
    This planner represents the "experienced tech lead" perspective,
    favoring:
    - Right tool for the job mentality
    - Balance between speed and quality
    - Practical trade-off analysis
    - Team capabilities consideration
    - Time-to-market focus
    - Maintainability by average developers
    """
    
    role = AgentRole.PLANNER
    personality = "pragmatic"
    
    PLANNING_PROMPT = '''You are a Pragmatic Planner Agent - balancing innovation with practicality.

Your role is to create a PRAGMATIC, BALANCED execution plan.
You are part of a rival multi-agent system where different planners propose competing strategies.

YOUR PLANNING PHILOSOPHY:
- Choose the right tool for the job, not the newest or most conservative
- Balance speed of delivery with code quality
- Consider real-world constraints (team skills, timeline, budget)
- Make practical trade-offs with clear reasoning
- Focus on business value and user needs
- Ensure code can be maintained by average developers
- Consider time-to-market alongside long-term sustainability
- Use "boring" technology when appropriate, new tech when it solves real problems

YOUR DECISION FRAMEWORK:
- What\'s the simplest solution that actually solves the problem?
- What trade-offs are we making, and are they acceptable?
- Can the team realistically execute this plan?
- What\'s the ROI of complexity vs. simplicity?

Requirements to plan for:
{requirements}

Context/constraints:
{context}

Respond with JSON:
{{
    "plan_id": "pragmatic_plan_001",
    "philosophy": "pragmatic",
    "confidence_score": 0-100,
    "practicality_score": 0-100,
    "risk_assessment": "low|medium|high",
    "estimated_complexity": "simple|moderate|complex",
    "steps": [
        {{
            "step_id": 1,
            "name": "step name",
            "description": "detailed description",
            "pragmatic_rationale": "why this is the practical choice",
            "trade_offs": ["what we\'re giving up and gaining"],
            "dependencies": ["list of step_ids this depends on"],
            "acceptance_criteria": ["clear definition of done"],
            "estimated_effort": "low|medium|high",
            "business_value": "low|medium|high"
        }}
    ],
    "technology_choices": [
        {{
            "category": "e.g., database, framework, library",
            "choice": "specific technology",
            "pragmatic_rationale": "why this is the right tool for the job",
            "trade_offs": ["acknowledged trade-offs"],
            "team_familiarity": "low|medium|high"
        }}
    ],
    "trade_off_analysis": [
        {{
            "decision": "what decision was made",
            "alternatives": ["other options"],
            "chosen_because": "practical reason for choice",
            "accepted_downsides": ["acknowledged limitations"]
        }}
    ],
    "mvp_scope": "what\'s the minimum viable solution",
    "future_iterations": ["what can be added later"],
    "reasoning": "overall plan rationale"
}}

Be practical and honest about trade-offs. The best plan delivers value efficiently.'''

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
    
    async def create_plan(self, request: CodeGenerationRequest, context: Optional[Dict[str, Any]] = None) -> ExecutionPlan:
        """Create a pragmatic execution plan."""
        logger.info(f"Pragmatic planner creating plan for: {request.requirements[:50]}...")
        
        prompt = self.PLANNING_PROMPT.format(
            requirements=request.requirements,
            context=json.dumps(context or {}, indent=2)
        )
        
        response = await self.llm.generate(prompt)
        
        try:
            plan_data = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse pragmatic planner response as JSON")
            plan_data = self._create_fallback_plan(request)
        
        # Convert to ExecutionPlan
        steps = [
            PlanStep(
                step_id=s.get("step_id", i),
                name=s.get("name", f"Step {i}"),
                description=s.get("description", ""),
                dependencies=s.get("dependencies", []),
                validation_criteria=s.get("acceptance_criteria", []),
                estimated_effort=s.get("estimated_effort", "medium"),
                metadata={
                    "pragmatic_rationale": s.get("pragmatic_rationale", ""),
                    "trade_offs": s.get("trade_offs", []),
                    "business_value": s.get("business_value", "medium")
                }
            )
            for i, s in enumerate(plan_data.get("steps", []), 1)
        ]
        
        return ExecutionPlan(
            plan_id=plan_data.get("plan_id", "pragmatic_plan"),
            planner_type=self.personality,
            steps=steps,
            confidence_score=plan_data.get("confidence_score", 80),
            risk_assessment=plan_data.get("risk_assessment", "low"),
            estimated_complexity=plan_data.get("estimated_complexity", "moderate"),
            technology_choices=plan_data.get("technology_choices", []),
            risk_mitigations=[],
            testing_strategy="Focused testing on critical paths and edge cases",
            reasoning=plan_data.get("reasoning", "Pragmatic approach balancing speed and quality"),
            metadata={
                "practicality_score": plan_data.get("practicality_score", 80),
                "trade_off_analysis": plan_data.get("trade_off_analysis", []),
                "mvp_scope": plan_data.get("mvp_scope", ""),
                "future_iterations": plan_data.get("future_iterations", [])
            }
        )
    
    def _create_fallback_plan(self, request: CodeGenerationRequest) -> Dict[str, Any]:
        """Create a basic fallback plan if LLM fails."""
        return {
            "plan_id": "pragmatic_fallback",
            "philosophy": "pragmatic",
            "confidence_score": 70,
            "practicality_score": 85,
            "risk_assessment": "low",
            "estimated_complexity": "moderate",
            "steps": [
                {
                    "step_id": 1,
                    "name": "Quick Analysis",
                    "description": "Rapid requirements analysis focusing on core needs",
                    "pragmatic_rationale": "Get started quickly while understanding the problem",
                    "trade_offs": ["May miss edge cases - will address in iteration"],
                    "dependencies": [],
                    "acceptance_criteria": ["Core requirements understood"],
                    "estimated_effort": "low",
                    "business_value": "high"
                },
                {
                    "step_id": 2,
                    "name": "MVP Implementation",
                    "description": "Build the minimum viable solution",
                    "pragmatic_rationale": "Deliver value quickly, iterate based on feedback",
                    "trade_offs": ["Not all features included - prioritized for impact"],
                    "dependencies": [1],
                    "acceptance_criteria": ["Core functionality works"],
                    "estimated_effort": "medium",
                    "business_value": "high"
                },
                {
                    "step_id": 3,
                    "name": "Essential Testing",
                    "description": "Test critical paths and common scenarios",
                    "pragmatic_rationale": "Focus testing where it matters most",
                    "trade_offs": ["Not 100% coverage - focused on high-risk areas"],
                    "dependencies": [2],
                    "acceptance_criteria": ["Critical paths tested", "No blocking bugs"],
                    "estimated_effort": "low",
                    "business_value": "medium"
                },
                {
                    "step_id": 4,
                    "name": "Iterate & Improve",
                    "description": "Refine based on feedback and add features",
                    "pragmatic_rationale": "Continuous improvement based on real usage",
                    "trade_offs": ["Ongoing effort required"],
                    "dependencies": [3],
                    "acceptance_criteria": ["User feedback addressed"],
                    "estimated_effort": "medium",
                    "business_value": "high"
                }
            ],
            "technology_choices": [],
            "trade_off_analysis": [
                {
                    "decision": "MVP-first approach",
                    "alternatives": ["Build complete solution", "Extensive planning"],
                    "chosen_because": "Faster time to value, allows course correction",
                    "accepted_downsides": ["May need refactoring later"]
                }
            ],
            "mvp_scope": "Core functionality that delivers the primary value",
            "future_iterations": [
                "Additional features based on feedback",
                "Performance optimization if needed",
                "Enhanced error handling"
            ],
            "reasoning": "Pragmatic fallback plan focused on delivering value quickly"
        }
