"""
Intelligence gathering module.
"""

from .engine import IntelligenceGatheringEngine

# Alias for consistency with prompt spec
IntelligenceEngine = IntelligenceGatheringEngine

__all__ = ["IntelligenceGatheringEngine", "IntelligenceEngine"]
