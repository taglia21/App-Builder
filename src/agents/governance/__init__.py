"""
Governance Module - Organizational Intelligence governance model.

This module implements the separation of powers for the multi-agent system:

- Executive Branch: Executes approved plans
- Legislative Branch: Proposes and debates plans through rival planners
- Judicial Branch: Reviews and can veto decisions through rival critics

The governance model ensures:
1. No single agent has unchecked authority
2. Multiple perspectives are considered before action
3. Quality standards are enforced through veto authority
4. Conflicts are resolved through arbitration
"""

from .executive import (
    ExecutiveBranch,
    ExecutionStatus,
    ExecutionContext,
    ExecutionResult
)
from .legislative import (
    LegislativeBranch,
    LegislativeSession,
    PlanProposal,
    DebateStatus
)
from .judicial import (
    JudicialBranch,
    JudicialReview,
    ReviewDecision,
    ArbitrationCase
)

__all__ = [
    # Executive
    "ExecutiveBranch",
    "ExecutionStatus",
    "ExecutionContext",
    "ExecutionResult",
    # Legislative
    "LegislativeBranch",
    "LegislativeSession",
    "PlanProposal",
    "DebateStatus",
    # Judicial
    "JudicialBranch",
    "JudicialReview",
    "ReviewDecision",
    "ArbitrationCase",
]
