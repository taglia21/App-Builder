"""
Organizational Intelligence - Message Types

Pydantic-validated message types for inter-agent communication.
Based on the "Team of Rivals" paper architecture.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import timezone, datetime
from pydantic import BaseModel, Field
import uuid


class AgentRole(str, Enum):
    """Roles agents can have in the organization."""
    PLANNER = "planner"
    CODE_WRITER = "code_writer"
    CODE_CRITIC = "code_critic"
    OUTPUT_CRITIC = "output_critic"
    SECURITY_CRITIC = "security_critic"
    DEPLOYMENT_WRITER = "deployment_writer"
    DEPLOYMENT_CRITIC = "deployment_critic"
    ORCHESTRATOR = "orchestrator"


class CriticDecision(str, Enum):
    """Decisions a critic can make - key to the veto authority system."""
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


class TaskStatus(str, Enum):
    """Status of a task in the pipeline."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VETOED = "vetoed"


class AgentMessage(BaseModel):
    """Base message type for inter-agent communication."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    sender_role: AgentRole
    sender_id: str
    content: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlanningRequest(BaseModel):
    """Request for the planner to create an execution plan."""
    app_description: str
    tech_stack: Optional[str] = None
    features: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None


class ExecutionPlan(BaseModel):
    """Execution plan created by the planner."""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    app_description: str
    tech_stack: str
    acceptance_criteria: List[str]
    execution_steps: List[Dict[str, Any]]
    estimated_complexity: str  # "low", "medium", "high"
    required_agents: List[AgentRole]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CodeGenerationRequest(BaseModel):
    """Request for code writer to generate code."""
    plan: ExecutionPlan
    target_files: List[str]
    context: Dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    previous_feedback: Optional[str] = None


class GeneratedCode(BaseModel):
    """Output from a code writer agent."""
    files: Dict[str, str]  # filename -> content
    tech_stack: str
    dependencies: List[str]
    execution_instructions: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CriticReview(BaseModel):
    """Review result from a critic agent - implements veto authority."""
    critic_role: AgentRole
    decision: CriticDecision
    reasoning: str
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    score: Optional[float] = None  # 0.0 to 1.0
    veto_reason: Optional[str] = None  # If decision is REJECT


class ValidationResult(BaseModel):
    """Result of validation checks."""
    passed: bool
    checks_run: List[str]
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OrchestrationState(BaseModel):
    """State of the orchestration process - enables checkpointing."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.PENDING
    current_step: str = ""
    plan: Optional[ExecutionPlan] = None
    generated_code: Optional[GeneratedCode] = None
    critic_reviews: List[CriticReview] = Field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    error_log: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_error(self, error: str):
        """Add error to log and update timestamp."""
        self.error_log.append(f"{datetime.now(timezone.utc).isoformat()}: {error}")
        self.updated_at = datetime.now(timezone.utc)

    def can_retry(self) -> bool:
        """Check if we can retry based on max retries."""
        return self.retry_count < self.max_retries
