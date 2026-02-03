"""
Innovative Planner Agent - Forward-thinking, experimental perspective.

Part of the Organizational Intelligence framework implementing rival
planning agents that propose competing strategies for synthesis.
"""

import json
import logging
from typing import Any, Dict, Optional

from ..base import LLMProvider
from ..messages import AgentRole, CodeGenerationRequest, ExecutionPlan, PlanStep

logger = logging.getLogger(__name__)


class InnovativePlanner:
    """
    Innovative planning agent that prioritizes cutting-edge solutions.

    This planner represents the "visionary CTO" perspective,
    favoring:
    - Modern, cutting-edge technologies
    - Elegant, DRY solutions
    - Scalability and future-proofing
    - Performance optimization
    - Clean architecture patterns
    - Automation and efficiency
    """

    role = AgentRole.PLANNER
    personality = "innovative"

    PLANNING_PROMPT = '''You are an Innovative Planner Agent - pushing boundaries with modern solutions.

Your role is to create an INNOVATIVE, FORWARD-THINKING execution plan.
You are part of a rival multi-agent system where different planners propose competing strategies.

YOUR PLANNING PHILOSOPHY:
- Embrace modern, cutting-edge technologies that solve problems elegantly
- Prioritize DRY (Don\'t Repeat Yourself) and clean code principles
- Design for scalability and future requirements
- Optimize for performance from the start
- Use modern architectural patterns (microservices, event-driven, etc.)
- Automate everything possible
- Leverage AI/ML where it adds value
- Consider developer experience and productivity

YOU SHOULD PURSUE:
- Novel approaches that could give competitive advantage
- Opportunities to reduce technical debt
- Modern tooling that improves the development workflow
- Patterns that enable rapid iteration

Requirements to plan for:
{requirements}

Context/constraints:
{context}

Respond with JSON:
{{
    "plan_id": "innovative_plan_001",
    "philosophy": "innovative",
    "confidence_score": 0-100,
    "innovation_score": 0-100,
    "risk_assessment": "low|medium|high",
    "estimated_complexity": "simple|moderate|complex",
    "steps": [
        {{
            "step_id": 1,
            "name": "step name",
            "description": "detailed description",
            "innovation_rationale": "why this innovative approach",
            "dependencies": ["list of step_ids this depends on"],
            "success_metrics": ["measurable outcomes"],
            "learning_opportunities": ["what we can learn from this"],
            "estimated_effort": "low|medium|high"
        }}
    ],
    "technology_choices": [
        {{
            "category": "e.g., database, framework, library",
            "choice": "specific modern technology",
            "innovation_rationale": "why this forward-thinking choice",
            "benefits": ["advantages of this choice"],
            "learning_curve": "low|medium|high"
        }}
    ],
    "scalability_considerations": ["how this plan scales"],
    "future_proofing": ["how this prepares for future needs"],
    "automation_opportunities": ["what can be automated"],
    "reasoning": "overall plan rationale"
}}

Be bold and visionary. Push the boundaries while remaining practical.'''

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider

    async def create_plan(self, request: CodeGenerationRequest, context: Optional[Dict[str, Any]] = None) -> ExecutionPlan:
        """Create an innovative execution plan."""
        logger.info(f"Innovative planner creating plan for: {request.requirements[:50]}...")

        prompt = self.PLANNING_PROMPT.format(
            requirements=request.requirements,
            context=json.dumps(context or {}, indent=2)
        )

        response = await self.llm.generate(prompt)

        try:
            plan_data = json.loads(response)
        except json.JSONDecodeError:
            logger.warning("Failed to parse innovative planner response as JSON")
            plan_data = self._create_fallback_plan(request)

        # Convert to ExecutionPlan
        steps = [
            PlanStep(
                step_id=s.get("step_id", i),
                name=s.get("name", f"Step {i}"),
                description=s.get("description", ""),
                dependencies=s.get("dependencies", []),
                validation_criteria=s.get("success_metrics", []),
                estimated_effort=s.get("estimated_effort", "medium"),
                metadata={
                    "innovation_rationale": s.get("innovation_rationale", ""),
                    "learning_opportunities": s.get("learning_opportunities", [])
                }
            )
            for i, s in enumerate(plan_data.get("steps", []), 1)
        ]

        return ExecutionPlan(
            plan_id=plan_data.get("plan_id", "innovative_plan"),
            planner_type=self.personality,
            steps=steps,
            confidence_score=plan_data.get("confidence_score", 75),
            risk_assessment=plan_data.get("risk_assessment", "medium"),
            estimated_complexity=plan_data.get("estimated_complexity", "moderate"),
            technology_choices=plan_data.get("technology_choices", []),
            risk_mitigations=plan_data.get("scalability_considerations", []),
            testing_strategy="Modern testing with property-based and snapshot testing",
            reasoning=plan_data.get("reasoning", "Innovative approach leveraging modern patterns"),
            metadata={
                "innovation_score": plan_data.get("innovation_score", 70),
                "future_proofing": plan_data.get("future_proofing", []),
                "automation_opportunities": plan_data.get("automation_opportunities", [])
            }
        )

    def _create_fallback_plan(self, request: CodeGenerationRequest) -> Dict[str, Any]:
        """Create a basic fallback plan if LLM fails."""
        return {
            "plan_id": "innovative_fallback",
            "philosophy": "innovative",
            "confidence_score": 60,
            "innovation_score": 70,
            "risk_assessment": "medium",
            "estimated_complexity": "moderate",
            "steps": [
                {
                    "step_id": 1,
                    "name": "Modern Stack Selection",
                    "description": "Choose cutting-edge but proven technologies",
                    "innovation_rationale": "Modern tools enable faster development",
                    "dependencies": [],
                    "success_metrics": ["Stack chosen and documented"],
                    "learning_opportunities": ["Evaluate new technologies"],
                    "estimated_effort": "low"
                },
                {
                    "step_id": 2,
                    "name": "Clean Architecture Design",
                    "description": "Design with clean architecture principles",
                    "innovation_rationale": "Enables flexibility and testability",
                    "dependencies": [1],
                    "success_metrics": ["Architecture diagram complete"],
                    "learning_opportunities": ["Apply modern design patterns"],
                    "estimated_effort": "medium"
                },
                {
                    "step_id": 3,
                    "name": "Rapid Prototyping",
                    "description": "Build fast with modern tooling",
                    "innovation_rationale": "Get feedback early",
                    "dependencies": [2],
                    "success_metrics": ["Working prototype"],
                    "learning_opportunities": ["Validate technical choices"],
                    "estimated_effort": "medium"
                },
                {
                    "step_id": 4,
                    "name": "Optimization & Polish",
                    "description": "Performance tuning and code quality",
                    "innovation_rationale": "Modern apps need to be fast",
                    "dependencies": [3],
                    "success_metrics": ["Performance benchmarks met"],
                    "learning_opportunities": ["Learn optimization techniques"],
                    "estimated_effort": "medium"
                }
            ],
            "technology_choices": [],
            "scalability_considerations": [
                "Design for horizontal scaling",
                "Use async patterns throughout"
            ],
            "future_proofing": [
                "Modular design allows easy updates",
                "API-first enables future integrations"
            ],
            "automation_opportunities": [
                "CI/CD pipeline",
                "Automated testing",
                "Infrastructure as code"
            ],
            "reasoning": "Innovative fallback plan using modern patterns and tools"
        }
