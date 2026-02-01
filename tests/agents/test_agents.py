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
            acceptance_criteria=["Has /todos endpoint"],
            execution_steps=[{"step": 1, "action": "generate"}],
            estimated_complexity="low",
            required_agents=[AgentRole.CODE_WRITER]
        )
        assert plan.tech_stack == "fastapi"
        assert plan.plan_id is not None

    def test_generated_code(self):
        code = GeneratedCode(
            files={"main.py": "print('hello')"},
            tech_stack="fastapi",
            dependencies=["fastapi"]
        )
        assert "main.py" in code.files

    def test_critic_review(self):
        review = CriticReview(
            critic_role=AgentRole.CODE_CRITIC,
            decision=CriticDecision.APPROVE,
            reasoning="Good code",
            score=0.9
        )
        assert review.decision == CriticDecision.APPROVE

    def test_orchestration_state_retry(self):
        state = OrchestrationState(max_retries=3)
        assert state.can_retry() == True
        state.retry_count = 3
        assert state.can_retry() == False

class TestCodeCritic:
    def test_syntax_valid(self):
        critic = CodeCritic()
        files = {"main.py": "from fastapi import FastAPI\napp = FastAPI()"}
        issues = critic._run_static_analysis(files)
        assert len(issues) == 0

    def test_syntax_invalid(self):
        critic = CodeCritic()
        files = {"main.py": "def broken(:\n    pass"}
        issues = critic._run_static_analysis(files)
        assert len(issues) > 0

    def test_security_eval(self):
        critic = CodeCritic()
        files = {"main.py": "result = eval(user_input)"}
        issues = critic._check_security(files)
        assert len(issues) > 0

    def test_veto_on_reject(self):
        critic = CodeCritic()
        review = CriticReview(
            critic_role=AgentRole.CODE_CRITIC,
            decision=CriticDecision.REJECT,
            reasoning="Failed",
            score=0.3
        )
        assert critic.should_veto(review) == True

    def test_no_veto_on_approve(self):
        critic = CodeCritic()
        review = CriticReview(
            critic_role=AgentRole.CODE_CRITIC,
            decision=CriticDecision.APPROVE,
            reasoning="Passed",
            score=0.9
        )
        assert critic.should_veto(review) == False
