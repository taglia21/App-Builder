from dataclasses import dataclass
import pytest

from src.agents.messages import (
    AgentRole, CriticDecision, TaskStatus, ExecutionPlan,
    GeneratedCode, CriticReview, OrchestrationState
)

from src.agents.critics.code_critic import CodeCritic

class TestMessages:
    def test_execution_plan_creation(self):
        plan = ExecutionPlan(
            app_description="A todo app",
            tech_stack="fastapi",
            acceptance_criteria=["Has todos", "Has acceptance criteria"],
            execution_steps=[{"step": "create models"}],
            estimated_complexity="low",
            required_agents=[AgentRole.CODE_WRITER]
        )
        assert plan.app_description == "A todo app"
        assert "acceptance_criteria" in plan.__dict__

    def test_critic_review(self):
        review = CriticReview(
            critic_role=AgentRole.CODE_CRITIC,
            decision=CriticDecision.APPROVE,
            reasoning="Code looks good",
            suggestions=["Consider adding tests"]
        )
        assert review.decision == CriticDecision.APPROVE
        assert len(review.suggestions) == 1

class TestCodeCritic:
    def test_code_critic_creation(self):
        critic = CodeCritic()
        assert critic.role == AgentRole.CODE_CRITIC
        assert hasattr(critic, 'review')
