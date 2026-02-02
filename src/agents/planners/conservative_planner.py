"""
Conservative Planner Agent - Risk-averse planning perspective.

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


class ConservativePlanner:
    """
    Conservative planning agent that prioritizes stability and proven patterns.
    
    This planner represents the "risk-averse executive" perspective,
    favoring:
    - Well-established patterns and libraries
    - Incremental changes over revolutionary approaches
    - Extensive validation and testing
    - Defensive programming practices
    - Backward compatibility
    - Thorough documentation
    """
    
    role = AgentRole.PLANNER
    personality = "conservative"
    
    PLANNING_PROMPT = '''You are a Conservative Planner Agent - prioritizing stability and reliability.

Your role is to create a CONSERVATIVE, RISK-AVERSE execution plan.
You are part of a rival multi-agent system where different planners propose competing strategies.

YOUR PLANNING PHILOSOPHY:
- Prefer well-established, battle-tested patterns and libraries
- Favor incremental, evolutionary changes over revolutionary approaches
- Include extensive validation, error handling, and testing steps
- Use defensive programming practices
- Ensure backward compatibility where possible
- Prioritize maintainability and readability over cleverness
- Include thorough documentation steps
- Add rollback/recovery mechanisms

YOU SHOULD AVOID:
- Cutting-edge or experimental technologies unless absolutely necessary
- Complex abstractions that may be hard to debug
- Over-engineering solutions
- Assuming happy paths - always plan for failures

Requirements to plan for:
{requirements}

Context/constraints:
{context}

Respond with JSON:
{{
    "plan_id": "conservative_plan_001",
    "philosophy": "conservative",
    "confidence_score": 0-100,
    "risk_assessment": "low|medium|high",
    "estimated_complexity": "simple|moderate|complex",
    "steps": [
        {{
            "step_id": 1,
            "name": "step name",
            "description": "detailed description",
            "rationale": "why this step and why this approach",
            "dependencies": ["list of step_ids this depends on"],
            "validation_criteria": ["how to verify this step succeeded"],
            "rollback_plan": "how to undo if this fails",
            "estimated_effort": "low|medium|high"
        }}
    ],
    "technology_choices": [
        {{
            "category": "e.g., database, framework, library",
            "choice": "specific technology",
            "rationale": "why this conservative choice",
            "alternatives_considered": ["what else was considered"]
        }}
    ],
    "risk_mitigations": ["list of risk mitigation strategies"],
    "testing_strategy": "overall testing approach",
    "documentation_plan": "documentation approach",
    "reasoning": "overall plan rationale"
}}

Be thorough and defensive. Better to over-plan than under-plan.'''

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
    
    async def create_plan(self, request: CodeGenerationRequest, context: Optional[Dict[str, Any]] = None) -> ExecutionPlan:
        """Create a conservative execution plan."""
        logger.info(f"Conservative planner creating plan for: {request.requirements[:50]}...")
        
        prompt = self.PLANNING_PROMPT.format(
            requirements=request.requirements,
            context=json.dumps(context or {}, indent=2)
        )
        
        response = await self.llm.generate(prompt)
        
        try:
            plan_data = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse conservative planner response as JSON")
            plan_data = self._create_fallback_plan(request)
        
        # Convert to ExecutionPlan
        steps = [
            PlanStep(
                step_id=s.get("step_id", i),
                name=s.get("name", f"Step {i}"),
                description=s.get("description", ""),
                dependencies=s.get("dependencies", []),
                validation_criteria=s.get("validation_criteria", []),
                estimated_effort=s.get("estimated_effort", "medium"),
                metadata={
                    "rationale": s.get("rationale", ""),
                    "rollback_plan": s.get("rollback_plan", "")
                }
            )
            for i, s in enumerate(plan_data.get("steps", []), 1)
        ]
        
        return ExecutionPlan(
            plan_id=plan_data.get("plan_id", "conservative_plan"),
            planner_type=self.personality,
            steps=steps,
            confidence_score=plan_data.get("confidence_score", 70),
            risk_assessment=plan_data.get("risk_assessment", "low"),
            estimated_complexity=plan_data.get("estimated_complexity", "moderate"),
            technology_choices=plan_data.get("technology_choices", []),
            risk_mitigations=plan_data.get("risk_mitigations", []),
            testing_strategy=plan_data.get("testing_strategy", "Comprehensive unit and integration testing"),
            reasoning=plan_data.get("reasoning", "Conservative approach prioritizing stability")
        )
    
    def _create_fallback_plan(self, request: CodeGenerationRequest) -> Dict[str, Any]:
        """Create a basic fallback plan if LLM fails."""
        return {
            "plan_id": "conservative_fallback",
            "philosophy": "conservative",
            "confidence_score": 50,
            "risk_assessment": "medium",
            "estimated_complexity": "moderate",
            "steps": [
                {
                    "step_id": 1,
                    "name": "Requirements Analysis",
                    "description": "Thoroughly analyze and validate requirements",
                    "rationale": "Ensure complete understanding before implementation",
                    "dependencies": [],
                    "validation_criteria": ["Requirements documented and verified"],
                    "rollback_plan": "N/A - analysis phase",
                    "estimated_effort": "low"
                },
                {
                    "step_id": 2,
                    "name": "Design with Proven Patterns",
                    "description": "Design using established architectural patterns",
                    "rationale": "Reduce risk with battle-tested approaches",
                    "dependencies": [1],
                    "validation_criteria": ["Design review completed"],
                    "rollback_plan": "Revise design based on feedback",
                    "estimated_effort": "medium"
                },
                {
                    "step_id": 3,
                    "name": "Incremental Implementation",
                    "description": "Implement in small, testable increments",
                    "rationale": "Easier to catch and fix issues early",
                    "dependencies": [2],
                    "validation_criteria": ["Each increment tested before proceeding"],
                    "rollback_plan": "Revert to last working increment",
                    "estimated_effort": "high"
                },
                {
                    "step_id": 4,
                    "name": "Comprehensive Testing",
                    "description": "Unit, integration, and edge case testing",
                    "rationale": "Ensure reliability and catch regressions",
                    "dependencies": [3],
                    "validation_criteria": ["All tests passing", "Coverage > 80%"],
                    "rollback_plan": "Fix failing tests before proceeding",
                    "estimated_effort": "medium"
                },
                {
                    "step_id": 5,
                    "name": "Documentation",
                    "description": "Create thorough documentation",
                    "rationale": "Enable maintainability and knowledge transfer",
                    "dependencies": [4],
                    "validation_criteria": ["Documentation complete and reviewed"],
                    "rollback_plan": "Update documentation as needed",
                    "estimated_effort": "low"
                }
            ],
            "technology_choices": [],
            "risk_mitigations": [
                "Incremental development reduces blast radius",
                "Comprehensive testing catches issues early",
                "Documentation enables easier debugging"
            ],
            "testing_strategy": "Test-driven development with comprehensive coverage",
            "documentation_plan": "Inline comments, API docs, and architectural overview",
            "reasoning": "Conservative fallback plan prioritizing stability and reliability"
        }
