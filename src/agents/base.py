"""
Organizational Intelligence - Base Agent Classes

Defines the base classes for all agents in the system.
Implements the "Brains vs Hands" separation from the paper.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
import logging
import json
from datetime import timezone, datetime

from anthropic import Anthropic
from openai import OpenAI
from pydantic import BaseModel

from .messages import (
    AgentRole, AgentMessage, CriticDecision, CriticReview,
    ValidationResult, TaskStatus
)

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class LLMProvider:
    """Abstraction for different LLM providers - enables vendor diversity."""
    
    def __init__(
        self,
        provider: str = "anthropic",
        model: str = "claude-sonnet-4-20250514",
        api_key: Optional[str] = None
    ):
        self.provider = provider
        self.model = model
        
        if provider == "anthropic":
            self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        elif provider == "openai":
            self.client = OpenAI(api_key=api_key) if api_key else OpenAI()
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        """Generate a response from the LLM."""
        try:
            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                    temperature=temperature
                )
                return response.content[0].text
            elif self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=temperature
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise


class BaseAgent(ABC):
    """
    Base class for all agents in the organization.
    
    Implements the "Brain" role - reasoning and decision making.
    Agents don't execute code directly; they produce outputs that
    are validated and then executed by the orchestrator.
    """
    
    def __init__(
        self,
        role: AgentRole,
        agent_id: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None
    ):
        self.role = role
        self.agent_id = agent_id or f"{role.value}_{datetime.now(timezone.utc).timestamp()}"
        self.llm = llm_provider or LLMProvider()
        self.message_history: List[AgentMessage] = []
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """Process input and return output."""
        pass
    
    def create_message(self, content: Dict[str, Any]) -> AgentMessage:
        """Create a message from this agent."""
        msg = AgentMessage(
            sender_role=self.role,
            sender_id=self.agent_id,
            content=content
        )
        self.message_history.append(msg)
        return msg
    
    async def _call_llm(self, user_message: str, temperature: float = 0.7) -> str:
        """Call the LLM with this agent's system prompt."""
        return await self.llm.generate(
            system_prompt=self.get_system_prompt(),
            user_message=user_message,
            temperature=temperature
        )
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Remove markdown code blocks if present
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        return json.loads(response.strip())


class CriticAgent(BaseAgent):
    """
    Base class for critic agents that have veto authority.
    
    Critics implement the "Team of Rivals" concept - they validate
    outputs from other agents and can reject/approve work.
    """
    
    def __init__(
        self,
        role: AgentRole,
        agent_id: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None,
        veto_threshold: float = 0.5  # Score below this triggers veto
    ):
        super().__init__(role, agent_id, llm_provider)
        self.veto_threshold = veto_threshold
        self.reviews: List[CriticReview] = []
    
    @abstractmethod
    async def review(self, artifact: Any, context: Dict[str, Any]) -> CriticReview:
        """
        Review an artifact and return a decision.
        
        This is the core veto authority implementation.
        """
        pass
    
    async def process(self, input_data: Any) -> CriticReview:
        """Process input by reviewing it."""
        context = input_data.get("context", {}) if isinstance(input_data, dict) else {}
        artifact = input_data.get("artifact", input_data) if isinstance(input_data, dict) else input_data
        
        review = await self.review(artifact, context)
        self.reviews.append(review)
        return review
    
    def should_veto(self, review: CriticReview) -> bool:
        """Determine if the review should trigger a veto."""
        if review.decision == CriticDecision.REJECT:
            return True
        if review.score is not None and review.score < self.veto_threshold:
            return True
        return False


class WriterAgent(BaseAgent):
    """
    Base class for writer agents that produce code/content.
    
    Writers are the "producers" in the organization - they create
    artifacts that are then reviewed by critics.
    """
    
    def __init__(
        self,
        role: AgentRole,
        agent_id: Optional[str] = None,
        llm_provider: Optional[LLMProvider] = None
    ):
        super().__init__(role, agent_id, llm_provider)
        self.outputs: List[Any] = []
    
    @abstractmethod
    async def write(self, request: Any) -> Any:
        """Generate the requested artifact."""
        pass
    
    async def process(self, input_data: Any) -> Any:
        """Process input by writing output."""
        output = await self.write(input_data)
        self.outputs.append(output)
        return output
    
    async def rewrite_with_feedback(
        self,
        original_request: Any,
        feedback: CriticReview
    ) -> Any:
        """
        Rewrite artifact incorporating critic feedback.
        
        This is key to the iterative improvement loop.
        """
        # Add feedback to context
        if isinstance(original_request, dict):
            original_request["previous_feedback"] = feedback.reasoning
            original_request["issues_to_fix"] = feedback.issues
            original_request["suggestions"] = feedback.suggestions
        
        return await self.write(original_request)
