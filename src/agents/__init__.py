"""
Organizational Intelligence - Multi-Agent System

Implements the "Team of Rivals" architecture for app generation
with pre-declared acceptance criteria and veto authority.
"""

from .messages import (
    AgentRole, CriticDecision, TaskStatus,
    AgentMessage, PlanningRequest, ExecutionPlan,
    CodeGenerationRequest, GeneratedCode, CriticReview,
    ValidationResult, OrchestrationState
)
from .base import BaseAgent, CriticAgent, WriterAgent, LLMProvider
from .orchestrator import AIOfficeOrchestrator

__all__ = [
    # Enums
    "AgentRole", "CriticDecision", "TaskStatus",
    # Messages
    "AgentMessage", "PlanningRequest", "ExecutionPlan",
    "CodeGenerationRequest", "GeneratedCode", "CriticReview",
    "ValidationResult", "OrchestrationState",
    # Base classes
    "BaseAgent", "CriticAgent", "WriterAgent", "LLMProvider",
    # Orchestrator
    "AIOfficeOrchestrator",
]

# Organizational Intelligence Framework
from .governance_orchestrator import GovernanceOrchestrator
from .governance import (
    ExecutiveBranch,
    LegislativeBranch,
    JudicialBranch,
    ExecutionResult,
    LegislativeSession,
    JudicialReview,
    ReviewDecision
)

__all__.extend([
    # Governance Orchestrator
    "GovernanceOrchestrator",
    # Governance Branches
    "ExecutiveBranch",
    "LegislativeBranch",
    "JudicialBranch",
    "ExecutionResult",
    "LegislativeSession",
    "JudicialReview",
    "ReviewDecision",
])
