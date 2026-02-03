"""
Critic Agents Module - Rival multi-agent validation system.

This module implements the Organizational Intelligence framework's
validation team with specialized critics that provide different perspectives:

- CodeCritic: General code quality, style, and correctness
- OutputCritic: Output validation and requirements matching
- SecurityCritic: Security vulnerabilities and best practices
- PerformanceCritic: Efficiency, optimization, and resource usage
- UXCritic: User experience, accessibility, and usability

Each critic operates as a rival agent, competing to identify issues
from their specialized perspective. This creates emergent coherence
through constructive tension.
"""

from .code_critic import CodeCritic
from .output_critic import OutputCritic
from .performance_critic import PerformanceCritic
from .security_critic import SecurityCritic
from .ux_critic import UXCritic

__all__ = [
    "CodeCritic",
    "OutputCritic",
    "SecurityCritic",
    "PerformanceCritic",
    "UXCritic",
]
