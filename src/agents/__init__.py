"""
Organizational Intelligence - Multi-Agent System

Implements the "Team of Rivals" architecture for app generation
with pre-declared acceptance criteria and veto authority.
"""

from .base import BaseAgent, CriticAgent, LLMProvider, WriterAgent
from .messages import (
    AgentMessage,
    AgentRole,
    CodeGenerationRequest,
    CriticDecision,
    CriticReview,
    ExecutionPlan,
    GeneratedCode,
    OrchestrationState,
    PlanningRequest,
    TaskStatus,
    ValidationResult,
)
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
from .governance import (
    ExecutionResult,
    ExecutiveBranch,
    JudicialBranch,
    JudicialReview,
    LegislativeBranch,
    LegislativeSession,
    ReviewDecision,
)
from .governance_orchestrator import GovernanceOrchestrator

__all__.extend([
    # Governance Framework
    "GovernanceOrchestrator",
    "ExecutiveBranch",
    "LegislativeBranch",
    "JudicialBranch",
    "ExecutionResult",
    "LegislativeSession",
    "JudicialReview",
    "ReviewDecision",
])
