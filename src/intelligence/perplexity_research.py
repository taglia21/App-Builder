"""
Perplexity-Powered Market Research Module

Leverages Perplexity AI's real-time web search capabilities for comprehensive
market intelligence gathering. Perplexity is the ideal provider for this because
it has REAL-TIME web search built into the model's responses.

Usage:
    from src.intelligence.perplexity_research import PerplexityMarketResearch

    research = PerplexityMarketResearch()

    # Get market trends
    trends = research.get_market_trends("AI automation", industries=["SaaS", "Healthcare"])

    # Analyze competitors
    competitors = research.analyze_competitors("project management", top_n=10)

    # Find pain points from web
    pain_points = research.discover_pain_points("remote team collaboration")
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MarketTrend:
    """A market trend discovered through research."""
    name: str
    description: str
    growth_rate: Optional[str] = None
    market_size: Optional[str] = None
    key_players: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CompetitorInsight:
    """Competitive intelligence on a market player."""
    name: str
    website: Optional[str] = None
    description: str = ""
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    pricing: Optional[str] = None
    target_market: Optional[str] = None
    unique_features: List[str] = field(default_factory=list)
    user_complaints: List[str] = field(default_factory=list)


@dataclass
class DiscoveredPainPoint:
    """A pain point discovered from web research."""
    description: str
    source: str
    urgency: str  # high, medium, low
    frequency: str  # how often mentioned
    affected_industries: List[str] = field(default_factory=list)
    existing_solutions: List[str] = field(default_factory=list)
    solution_gaps: List[str] = field(default_factory=list)


class PerplexityMarketResearch:
    """
    Market research powered by Perplexity AI's real-time web search.

    Perplexity is uniquely suited for market intelligence because:
    1. Real-time web search integrated into responses
    2. Citations and source tracking
    3. Comprehensive analysis capabilities
    4. Current market data (not just training data)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "sonar-pro",
        research_model: str = "sonar-deep-research",
        analysis_model: str = "sonar-reasoning",
    ):
        """
        Initialize Perplexity market research.

        Args:
            api_key: Perplexity API key (or uses PERPLEXITY_API_KEY env var)
            default_model: Model for general queries
            research_model: Model for deep research
            analysis_model: Model for complex analysis
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.default_model = default_model
        self.research_model = research_model
        self.analysis_model = analysis_model

        self._client = None
        self._available = None

    @property
    def is_available(self) -> bool:
        """Check if Perplexity is available."""
        if self._available is None:
            self._available = bool(self.api_key)
        return self._available

    def _get_client(self, model: Optional[str] = None):
        """Get or create Perplexity client."""
        if not self.is_available:
            raise ValueError(
                "Perplexity API key not configured. "
                "Set PERPLEXITY_API_KEY environment variable."
            )

        from src.llm import PerplexityClient

        return PerplexityClient(
            api_key=self.api_key,
            model=model or self.default_model
        )

    def get_market_trends(
        self,
        topic: str,
        industries: Optional[List[str]] = None,
        timeframe: str = "last 6 months",
        max_trends: int = 10
    ) -> List[MarketTrend]:
        """
        Discover current market trends for a topic.

        Args:
            topic: The topic/market to research
            industries: Optional list of industries to focus on
            timeframe: Time period to focus on
            max_trends: Maximum number of trends to return

        Returns:
            List of MarketTrend objects
        """
        client = self._get_client(self.research_model)

        industries_str = ", ".join(industries) if industries else "technology, SaaS, enterprise"

        prompt = f"""Research current market trends for "{topic}" in the {industries_str} space.

Focus on the {timeframe} timeframe. For each trend, provide:
1. Trend name
2. Description (2-3 sentences)
3. Estimated growth rate or trajectory
4. Market size if available
5. Key companies/players in this space
6. Opportunities for new entrants
7. Source URLs for the information

Return exactly {max_trends} trends as a JSON array with this structure:
{{
    "trends": [
        {{
            "name": "Trend Name",
            "description": "Description here",
            "growth_rate": "X% CAGR" or null,
            "market_size": "$XB by 2025" or null,
            "key_players": ["Company1", "Company2"],
            "opportunities": ["Opportunity 1", "Opportunity 2"],
            "sources": ["https://source1.com", "https://source2.com"]
        }}
    ]
}}

Focus on actionable trends that represent real business opportunities."""

        try:
            response = client.complete(
                prompt=prompt,
                system_prompt="You are a market research analyst with access to real-time web data. Provide factual, well-sourced market intelligence.",
                temperature=0.3,
                json_mode=True
            )

            data = json.loads(response.content)
            trends = []

            for t in data.get("trends", []):
                trends.append(MarketTrend(
                    name=t.get("name", "Unknown"),
                    description=t.get("description", ""),
                    growth_rate=t.get("growth_rate"),
                    market_size=t.get("market_size"),
                    key_players=t.get("key_players", []),
                    opportunities=t.get("opportunities", []),
                    sources=t.get("sources", [])
                ))

            logger.info(f"Discovered {len(trends)} market trends for '{topic}'")
            return trends

        except Exception as e:
            logger.error(f"Error getting market trends: {e}")
            return []

    def analyze_competitors(
        self,
        market: str,
        top_n: int = 10,
        include_pricing: bool = True
    ) -> List[CompetitorInsight]:
        """
        Analyze competitors in a market.

        Args:
            market: The market/space to analyze
            top_n: Number of competitors to analyze
            include_pricing: Whether to include pricing information

        Returns:
            List of CompetitorInsight objects
        """
        client = self._get_client(self.research_model)

        pricing_instruction = ""
        if include_pricing:
            pricing_instruction = "- Pricing model and price points (if publicly available)"

        prompt = f"""Research and analyze the top {top_n} competitors in the "{market}" market.

For each competitor, provide:
- Company name and website
- Brief description (what they do)
- Key strengths (2-3 points)
- Known weaknesses or gaps (2-3 points)
{pricing_instruction}
- Target market/customer segment
- Unique features or differentiators
- Common user complaints (from reviews, Reddit, forums)

Return as a JSON array:
{{
    "competitors": [
        {{
            "name": "Company Name",
            "website": "https://example.com",
            "description": "What they do",
            "strengths": ["Strength 1", "Strength 2"],
            "weaknesses": ["Weakness 1", "Weakness 2"],
            "pricing": "$X/month" or null,
            "target_market": "SMBs, Enterprise, etc",
            "unique_features": ["Feature 1", "Feature 2"],
            "user_complaints": ["Common complaint 1", "Common complaint 2"]
        }}
    ]
}}

Focus on identifying gaps and opportunities that a new entrant could exploit."""

        try:
            response = client.complete(
                prompt=prompt,
                system_prompt="You are a competitive intelligence analyst. Provide honest, balanced assessments based on real-world data.",
                temperature=0.3,
                json_mode=True
            )

            data = json.loads(response.content)
            competitors = []

            for c in data.get("competitors", []):
                competitors.append(CompetitorInsight(
                    name=c.get("name", "Unknown"),
                    website=c.get("website"),
                    description=c.get("description", ""),
                    strengths=c.get("strengths", []),
                    weaknesses=c.get("weaknesses", []),
                    pricing=c.get("pricing"),
                    target_market=c.get("target_market"),
                    unique_features=c.get("unique_features", []),
                    user_complaints=c.get("user_complaints", [])
                ))

            logger.info(f"Analyzed {len(competitors)} competitors in '{market}'")
            return competitors

        except Exception as e:
            logger.error(f"Error analyzing competitors: {e}")
            return []

    def discover_pain_points(
        self,
        topic: str,
        sources: Optional[List[str]] = None,
        max_pain_points: int = 20
    ) -> List[DiscoveredPainPoint]:
        """
        Discover pain points from web research.

        Args:
            topic: Topic to research pain points for
            sources: Specific sources to focus on (Reddit, forums, reviews, etc.)
            max_pain_points: Maximum pain points to return

        Returns:
            List of DiscoveredPainPoint objects
        """
        client = self._get_client(self.research_model)

        sources_str = ", ".join(sources) if sources else "Reddit, Twitter/X, product reviews, forums, Hacker News, G2, Capterra"

        prompt = f"""Research pain points and frustrations people have with "{topic}".

Search across {sources_str} to find real user complaints and unmet needs.

For each pain point, provide:
1. Description of the pain point
2. Source where it was found
3. Urgency level (high/medium/low based on frequency and intensity)
4. How frequently this is mentioned
5. Industries most affected
6. Existing solutions (if any)
7. Gaps in existing solutions

Return exactly {max_pain_points} pain points as JSON:
{{
    "pain_points": [
        {{
            "description": "Clear description of the pain point",
            "source": "Reddit r/startup, Product Hunt comments, etc",
            "urgency": "high|medium|low",
            "frequency": "Mentioned in X% of discussions" or "Common complaint",
            "affected_industries": ["Industry1", "Industry2"],
            "existing_solutions": ["Solution1", "Solution2"],
            "solution_gaps": ["Gap 1", "Gap 2"]
        }}
    ]
}}

Focus on pain points that represent real business opportunities - things people actively complain about and would pay to solve."""

        try:
            response = client.complete(
                prompt=prompt,
                system_prompt="You are a user research specialist. Find real, validated pain points from actual user feedback across the web.",
                temperature=0.3,
                json_mode=True
            )

            data = json.loads(response.content)
            pain_points = []

            for pp in data.get("pain_points", []):
                pain_points.append(DiscoveredPainPoint(
                    description=pp.get("description", ""),
                    source=pp.get("source", "Unknown"),
                    urgency=pp.get("urgency", "medium"),
                    frequency=pp.get("frequency", "Unknown"),
                    affected_industries=pp.get("affected_industries", []),
                    existing_solutions=pp.get("existing_solutions", []),
                    solution_gaps=pp.get("solution_gaps", [])
                ))

            logger.info(f"Discovered {len(pain_points)} pain points for '{topic}'")
            return pain_points

        except Exception as e:
            logger.error(f"Error discovering pain points: {e}")
            return []

    def validate_idea(
        self,
        idea_name: str,
        problem_statement: str,
        target_market: str
    ) -> Dict[str, Any]:
        """
        Validate a startup idea using real-time market research.

        Args:
            idea_name: Name of the idea
            problem_statement: The problem it solves
            target_market: Who it's for

        Returns:
            Dictionary with validation results
        """
        client = self._get_client(self.analysis_model)

        prompt = f"""Validate this startup idea using real-time market research:

**Idea:** {idea_name}
**Problem:** {problem_statement}
**Target Market:** {target_market}

Research and analyze:
1. **Market Validation**: Is this a real problem? Who else is talking about it?
2. **Competitor Analysis**: Who else is solving this? How successful are they?
3. **Market Size**: Rough TAM/SAM/SOM estimates
4. **Timing**: Why now? Any recent trends supporting this?
5. **Risks**: Major risks or concerns
6. **Recommendation**: Build it / Pivot / Skip (with reasoning)

Return as JSON:
{{
    "market_validation": {{
        "score": 1-10,
        "evidence": ["Evidence 1", "Evidence 2"],
        "concerns": ["Concern 1"]
    }},
    "competitors": [
        {{"name": "Competitor", "similarity": "high|medium|low", "funding": "$XM" or null}}
    ],
    "market_size": {{
        "tam": "$XB",
        "sam": "$XM",
        "som": "$XM",
        "sources": ["Source 1"]
    }},
    "timing": {{
        "score": 1-10,
        "reasons": ["Why now 1", "Why now 2"]
    }},
    "risks": [
        {{"risk": "Risk description", "severity": "high|medium|low", "mitigation": "How to address"}}
    ],
    "recommendation": {{
        "action": "build|pivot|skip",
        "confidence": 1-10,
        "reasoning": "Clear explanation"
    }}
}}"""

        try:
            response = client.complete(
                prompt=prompt,
                system_prompt="You are a startup analyst with access to real-time market data. Provide honest, data-backed validation.",
                temperature=0.4,
                json_mode=True
            )

            data = json.loads(response.content)
            logger.info(f"Validated idea '{idea_name}': {data.get('recommendation', {}).get('action', 'unknown')}")
            return data

        except Exception as e:
            logger.error(f"Error validating idea: {e}")
            return {"error": str(e)}

    def research_technology_landscape(
        self,
        technology: str,
        use_case: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Research the technology landscape for building a product.

        Args:
            technology: The technology area (e.g., "AI/ML", "blockchain")
            use_case: Optional specific use case

        Returns:
            Dictionary with technology landscape analysis
        """
        client = self._get_client(self.research_model)

        use_case_str = f" for {use_case}" if use_case else ""

        prompt = f"""Research the current technology landscape for building products using {technology}{use_case_str}.

Provide:
1. **Current State**: Where is this technology today?
2. **Key Players**: Major companies and tools in this space
3. **Open Source Options**: Popular open source frameworks/tools
4. **Build vs Buy**: What should be built vs purchased?
5. **Cost Considerations**: Typical costs and pricing models
6. **Talent Availability**: How easy is it to hire for this?
7. **Best Practices**: Current best practices for implementation
8. **Pitfalls**: Common mistakes to avoid

Return as JSON:
{{
    "current_state": "Description of current state",
    "maturity": "emerging|growing|mature|declining",
    "key_players": [
        {{"name": "Company", "product": "Product", "pricing": "Model"}}
    ],
    "open_source": [
        {{"name": "Project", "url": "GitHub URL", "stars": "Xk", "use_case": "What it's for"}}
    ],
    "build_vs_buy": {{
        "build": ["Component 1", "Component 2"],
        "buy": ["Service 1", "Service 2"],
        "reasoning": "Explanation"
    }},
    "costs": {{
        "development": "Estimate",
        "infrastructure": "Monthly estimate",
        "apis": "Per-unit costs"
    }},
    "talent": {{
        "availability": "scarce|moderate|abundant",
        "salary_range": "$X-Y",
        "key_skills": ["Skill 1", "Skill 2"]
    }},
    "best_practices": ["Practice 1", "Practice 2"],
    "pitfalls": ["Pitfall 1", "Pitfall 2"]
}}"""

        try:
            response = client.complete(
                prompt=prompt,
                system_prompt="You are a technical architect with deep knowledge of modern technology stacks. Provide practical, current guidance.",
                temperature=0.3,
                json_mode=True
            )

            data = json.loads(response.content)
            logger.info(f"Researched technology landscape for '{technology}'")
            return data

        except Exception as e:
            logger.error(f"Error researching technology: {e}")
            return {"error": str(e)}


# Convenience function for quick access
def get_perplexity_research() -> Optional[PerplexityMarketResearch]:
    """
    Get a PerplexityMarketResearch instance if Perplexity is configured.

    Returns:
        PerplexityMarketResearch instance or None if not configured
    """
    if os.getenv("PERPLEXITY_API_KEY"):
        return PerplexityMarketResearch()
    return None
