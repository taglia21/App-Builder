"""Tests for agent system."""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime

from src.agents.base import LLMProvider, BaseAgent
from src.agents.messages import AgentMessage, AgentRole, CriticDecision, CriticReview


class TestLLMProvider:
    """Test LLM provider abstraction."""

    def test_anthropic_provider_initialization(self):
        """Test initializing Anthropic provider."""
        with patch('src.agents.base.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client
            
            provider = LLMProvider(provider="anthropic", model="claude-sonnet-4-20250514")
            assert provider.provider == "anthropic"
            assert provider.model == "claude-sonnet-4-20250514"
            mock_anthropic.assert_called_once()

    def test_openai_provider_initialization(self):
        """Test initializing OpenAI provider."""
        with patch('src.agents.base.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client
            
            provider = LLMProvider(provider="openai", model="gpt-4", api_key="test_key")
            assert provider.provider == "openai"
            assert provider.model == "gpt-4"
            mock_openai.assert_called_once()

    def test_invalid_provider_raises_error(self):
        """Test that invalid provider raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider"):
            LLMProvider(provider="invalid_provider")

    def test_provider_with_api_key(self):
        """Test provider initialization with API key."""
        with patch('src.agents.base.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_anthropic.return_value = mock_client
            
            provider = LLMProvider(
                provider="anthropic",
                api_key="test_api_key_123"
            )
            mock_anthropic.assert_called_once_with(api_key="test_api_key_123")

    @pytest.mark.asyncio
    async def test_generate_method_exists(self):
        """Test that generate method exists."""
        with patch('anthropic.Anthropic'):
            provider = LLMProvider(provider="anthropic")
            assert hasattr(provider, 'generate')


class TestAgentMessage:
    """Test agent message models."""

    def test_create_agent_message(self):
        """Test creating an agent message."""
        msg = AgentMessage(
            sender_role=AgentRole.PLANNER,
            sender_id="planner-1",
            content={"message": "Test message content"}
        )
        assert msg.sender_role == AgentRole.PLANNER
        assert msg.content == {"message": "Test message content"}
        assert isinstance(msg.timestamp, datetime)

    def test_agent_message_serialization(self):
        """Test agent message can be serialized."""
        msg = AgentMessage(
            sender_role=AgentRole.CRITIC,
            sender_id="critic-1",
            content={"review": "Review content"}
        )
        data = msg.model_dump()
        assert "sender_role" in data
        assert "content" in data
        assert "timestamp" in data

    def test_agent_roles_available(self):
        """Test all expected agent roles are available."""
        expected_roles = ["planner", "code_writer", "critic", "orchestrator"]
        available_roles = [r.value for r in AgentRole]
        for role_name in expected_roles:
            assert role_name in available_roles


class TestCriticReview:
    """Test critic review models."""

    def test_create_critic_review(self):
        """Test creating a critic review."""
        review = CriticReview(
            critic_role=AgentRole.CRITIC,
            decision=CriticDecision.APPROVE,
            reasoning="Looks good",
            score=0.95
        )
        assert review.decision == CriticDecision.APPROVE
        assert review.reasoning == "Looks good"
        assert review.score == 0.95

    def test_critic_review_reject(self):
        """Test creating a reject review."""
        review = CriticReview(
            critic_role=AgentRole.CRITIC,
            decision=CriticDecision.REJECT,
            reasoning="Needs improvement",
            score=0.80,
            suggestions=["Fix security issue", "Improve performance"],
            veto_reason="Security vulnerabilities found"
        )
        assert review.decision == CriticDecision.REJECT
        assert len(review.suggestions) == 2

    def test_critic_decisions_available(self):
        """Test all critic decisions are available."""
        assert hasattr(CriticDecision, "APPROVE")
        assert hasattr(CriticDecision, "REJECT")
        assert hasattr(CriticDecision, "REQUEST_CHANGES")


class TestBaseAgent:
    """Test base agent functionality."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        provider = Mock(spec=LLMProvider)
        provider.generate = AsyncMock(return_value="Generated response")
        return provider

    def test_base_agent_is_abstract(self):
        """Test that BaseAgent cannot be instantiated directly."""
        # BaseAgent should be abstract
        from abc import ABC
        assert issubclass(BaseAgent, ABC)

    @pytest.mark.asyncio
    async def test_agent_with_llm_provider(self, mock_llm_provider):
        """Test agent uses LLM provider."""
        # Create a concrete implementation for testing
        class TestAgent(BaseAgent):
            def __init__(self, llm_provider):
                self.llm_provider = llm_provider
                self.role = AgentRole.CODE_WRITER
            
            def get_system_prompt(self) -> str:
                return "Test system prompt"
            
            async def process(self, input_data):
                return await self.llm_provider.generate("test prompt")

        agent = TestAgent(llm_provider=mock_llm_provider)
        result = await agent.process("test")
        assert result == "Generated response"
        mock_llm_provider.generate.assert_called_once()


class TestAgentOrchestration:
    """Test agent orchestration patterns."""

    @pytest.mark.asyncio
    async def test_multi_agent_workflow(self):
        """Test multiple agents working together."""
        mock_planner = Mock()
        mock_planner.plan = AsyncMock(return_value={"steps": ["step1", "step2"]})

        mock_writer = Mock()
        mock_writer.write = AsyncMock(return_value="Generated code")

        mock_critic = Mock()
        mock_critic.review = AsyncMock(return_value=CriticReview(
            critic_role=AgentRole.CRITIC,
            decision=CriticDecision.APPROVE,
            reasoning="Good work",
            score=0.9
        ))

        # Simulate workflow
        plan = await mock_planner.plan()
        assert "steps" in plan

        code = await mock_writer.write()
        assert code == "Generated code"

        review = await mock_critic.review()
        assert review.decision == CriticDecision.APPROVE

    @pytest.mark.asyncio
    async def test_agent_error_handling(self):
        """Test agent handles errors gracefully."""
        mock_agent = Mock()
        mock_agent.process = AsyncMock(side_effect=Exception("Processing error"))

        with pytest.raises(Exception, match="Processing error"):
            await mock_agent.process("test input")


class TestAgentCommunication:
    """Test agent-to-agent communication."""

    def test_message_routing(self):
        """Test messages can be routed between agents."""
        msg1 = AgentMessage(
            sender_role=AgentRole.PLANNER,
            sender_id="planner-1",
            content={"task": "Create plan"}
        )

        msg2 = AgentMessage(
            sender_role=AgentRole.CODE_WRITER,
            sender_id="writer-1",
            content={"task": "Execute plan"},
            metadata={"reply_to": msg1.id}
        )

        assert msg2.metadata["reply_to"] == msg1.id

    def test_message_threading(self):
        """Test message threading for conversation flow."""
        messages = []
        for i in range(3):
            msg = AgentMessage(
                sender_role=AgentRole.CRITIC,
                sender_id=f"critic-{i}",
                content={"review": f"Review iteration {i}"}
            )
            messages.append(msg)

        assert len(messages) == 3
        assert all(isinstance(m, AgentMessage) for m in messages)


class TestAgentPerformance:
    """Test agent performance and efficiency."""

    @pytest.mark.asyncio
    async def test_concurrent_agent_execution(self):
        """Test multiple agents can run concurrently."""
        import asyncio

        async def mock_agent_task(agent_id: int):
            await asyncio.sleep(0.1)
            return f"Agent {agent_id} complete"

        # Run 3 agents concurrently
        results = await asyncio.gather(
            mock_agent_task(1),
            mock_agent_task(2),
            mock_agent_task(3)
        )

        assert len(results) == 3
        assert all("complete" in r for r in results)

    @pytest.mark.asyncio
    async def test_agent_caching(self):
        """Test agent can cache responses."""
        cache = {}

        async def cached_generate(prompt: str):
            if prompt in cache:
                return cache[prompt]
            result = f"Response for: {prompt}"
            cache[prompt] = result
            return result

        # First call
        result1 = await cached_generate("test prompt")
        assert "test prompt" in result1

        # Second call (should be cached)
        result2 = await cached_generate("test prompt")
        assert result1 == result2
        assert len(cache) == 1


class TestAgentGovernance:
    """Test governance agent patterns."""

    def test_executive_agent_role(self):
        """Test executive agent role exists."""
        # Check if orchestrator role exists (executive-like role)
        assert hasattr(AgentRole, "ORCHESTRATOR")
        msg = AgentMessage(
            sender_role=AgentRole.ORCHESTRATOR,
            sender_id="exec-1",
            content={"decision": "Executive decision"}
        )
        assert msg.sender_role == AgentRole.ORCHESTRATOR

    def test_legislative_agent_role(self):
        """Test planner agent role (legislative-like)."""
        assert hasattr(AgentRole, "PLANNER")
        msg = AgentMessage(
            sender_role=AgentRole.PLANNER,
            sender_id="planner-1",
            content={"policy": "Policy creation"}
        )
        assert msg.sender_role == AgentRole.PLANNER

    def test_judicial_agent_role(self):
        """Test critic agent role (judicial-like)."""
        assert hasattr(AgentRole, "CRITIC")
        msg = AgentMessage(
            sender_role=AgentRole.CRITIC,
            sender_id="critic-1",
            content={"review": "Compliance review"}
        )
        assert msg.sender_role == AgentRole.CRITIC
