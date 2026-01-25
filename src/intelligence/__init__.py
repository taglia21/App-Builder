"""
Intelligence gathering module.

Includes both traditional data source collectors and Perplexity-powered
real-time market research for comprehensive market intelligence.
"""

from .engine import IntelligenceGatheringEngine
from .perplexity_research import (
    PerplexityMarketResearch,
    MarketTrend,
    CompetitorInsight,
    DiscoveredPainPoint,
    get_perplexity_research,
)

# Alias for consistency with prompt spec
IntelligenceEngine = IntelligenceGatheringEngine

__all__ = [
    "IntelligenceGatheringEngine",
    "IntelligenceEngine",
    # Perplexity-powered research
    "PerplexityMarketResearch",
    "MarketTrend",
    "CompetitorInsight",
    "DiscoveredPainPoint",
    "get_perplexity_research",
]
