"""
Planner Agents Module - Rival multi-agent planning system.

This module implements the Organizational Intelligence framework's
planning team with rival planners that propose competing strategies:

- PlannerAgent: Original planner (maintained for backward compatibility)
- ConservativePlanner: Risk-averse, stability-focused planning
- InnovativePlanner: Forward-thinking, modern approaches
- PragmaticPlanner: Balanced, practical planning
- PlanSynthesizer: Merges rival plans into optimal strategy

Each planner operates as a rival agent, competing to propose the
best strategy from their unique perspective. The synthesizer then
merges these into a coherent execution plan.
"""

from .planner_agent import PlannerAgent
from .conservative_planner import ConservativePlanner
from .innovative_planner import InnovativePlanner
from .pragmatic_planner import PragmaticPlanner
from .plan_synthesizer import PlanSynthesizer, SynthesisResult, PlanComparison

__all__ = [
    "PlannerAgent",
    "ConservativePlanner",
    "InnovativePlanner",
    "PragmaticPlanner",
    "PlanSynthesizer",
    "SynthesisResult",
    "PlanComparison",
]
