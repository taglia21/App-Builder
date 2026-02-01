"""
Planner Agent - Creates execution plans for app generation.

The planner is responsible for:
1. Analyzing user requirements
2. Creating acceptance criteria (pre-declared, as per paper)
3. Defining execution steps
4. Identifying required agents
"""

from typing import Any, Dict, List, Optional
import json
import logging

from ..base import BaseAgent, LLMProvider
from ..messages import (
    AgentRole, ExecutionPlan, PlanningRequest
)

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """
    Creates execution plans with pre-declared acceptance criteria.
    
    Key principle from paper: Define success criteria BEFORE execution
    to prevent post-hoc rationalization of failures.
    """
    
    def __init__(
        self,
        agent_id: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None
    ):
        super().__init__(
            role=AgentRole.PLANNER,
            agent_id=agent_id,
            llm_provider=llm_provider
        )
    
    def get_system_prompt(self) -> str:
        return """You are a Planning Agent for an AI-powered app builder.

Your role is to analyze user requirements and create detailed execution plans.

IMPORTANT: You must define ACCEPTANCE CRITERIA before any work begins.
These criteria will be used by critic agents to validate the output.

For each request, you must provide:
1. A clear understanding of what the user wants
2. The appropriate tech stack (FastAPI, Django, Flask, Express, Next.js)
3. Specific, testable acceptance criteria
4. Step-by-step execution plan
5. Estimated complexity (low/medium/high)

Respond in JSON format with this structure:
{
    "app_description": "Clear description of the app",
    "tech_stack": "fastapi|django|flask|express|nextjs",
    "acceptance_criteria": [
        "Specific testable criterion 1",
        "Specific testable criterion 2"
    ],
    "execution_steps": [
        {"step": 1, "action": "description", "agent": "code_writer"},
        {"step": 2, "action": "description", "agent": "code_critic"}
    ],
    "estimated_complexity": "low|medium|high",
    "required_files": ["main.py", "models.py", "etc"]
}

Be thorough but practical. Focus on what can be realistically generated."""

    async def process(self, input_data: Any) -> ExecutionPlan:
        """Process a planning request and return an execution plan."""
        if isinstance(input_data, PlanningRequest):
            request = input_data
        elif isinstance(input_data, dict):
            request = PlanningRequest(**input_data)
        else:
            request = PlanningRequest(app_description=str(input_data))
        
        return await self.create_plan(request)
    
    async def create_plan(self, request: PlanningRequest) -> ExecutionPlan:
        """
        Create an execution plan from a planning request.
        
        This is the main entry point for planning.
        """
        # Build the user message
        user_message = f"""Create an execution plan for this app:

Description: {request.app_description}

Requested Tech Stack: {request.tech_stack or 'Choose the best fit'}

Requested Features:
{chr(10).join(f'- {f}' for f in request.features) if request.features else 'Not specified'}

Constraints:
{json.dumps(request.constraints, indent=2) if request.constraints else 'None'}

Provide a complete execution plan in JSON format."""
        
        # Get plan from LLM
        response = await self._call_llm(user_message, temperature=0.5)
        
        # Parse the response
        plan_data = self._parse_json_response(response)
        
        # Determine required agents based on steps
        required_agents = self._determine_required_agents(plan_data)
        
        # Create the execution plan
        plan = ExecutionPlan(
            app_description=plan_data.get("app_description", request.app_description),
            tech_stack=plan_data.get("tech_stack", request.tech_stack or "fastapi"),
            acceptance_criteria=plan_data.get("acceptance_criteria", []),
            execution_steps=plan_data.get("execution_steps", []),
            estimated_complexity=plan_data.get("estimated_complexity", "medium"),
            required_agents=required_agents,
            metadata={
                "original_request": request.model_dump(),
                "required_files": plan_data.get("required_files", [])
            }
        )
        
        # Log the plan
        logger.info(f"Created plan {plan.plan_id} with {len(plan.acceptance_criteria)} criteria")
        
        return plan
    
    def _determine_required_agents(self, plan_data: Dict) -> List[AgentRole]:
        """Determine which agents are needed based on the plan."""
        agents = set()
        agents.add(AgentRole.CODE_WRITER)  # Always need code writer
        agents.add(AgentRole.CODE_CRITIC)  # Always need code critic
        agents.add(AgentRole.OUTPUT_CRITIC)  # Always need output critic
        
        # Check execution steps for additional agents
        for step in plan_data.get("execution_steps", []):
            agent_name = step.get("agent", "").lower()
            if "security" in agent_name:
                agents.add(AgentRole.SECURITY_CRITIC)
            if "deployment" in agent_name:
                agents.add(AgentRole.DEPLOYMENT_WRITER)
                agents.add(AgentRole.DEPLOYMENT_CRITIC)
        
        return list(agents)
