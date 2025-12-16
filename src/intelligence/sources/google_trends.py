"""
Google Trends data source for market intelligence (NO API KEY REQUIRED).
Uses pytrends to discover trending searches and rising topics.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

try:
    from pytrends.request import TrendReq
except ImportError:
    TrendReq = None

from loguru import logger

from ...models import PainPoint
from ..base import DataSource


class GoogleTrendsSource(DataSource):
    """Collect trending search data from Google Trends."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Google Trends source."""
        super().__init__(config)
        self.regions = config.get("regions", ["US", "GB", "CA", "AU"])
        self.categories = config.get("categories", [
            "Business & Industrial",
            "Computers & Electronics",
            "Internet & Telecom",
            "Jobs & Education",
        ])
        self.timeframe = config.get("timeframe", "today 3-m")
        self.keywords = config.get("keywords", [
            "SaaS",
            "automation",
            "productivity",
            "workflow",
            "business tools",
            "remote work",
            "team collaboration",
            "API integration",
        ])

        if self.enabled and TrendReq is not None:
            self.pytrends = TrendReq(hl='en-US', tz=360)
        else:
            self.pytrends = None
            if TrendReq is None:
                logger.warning("pytrends package not installed. Install with: pip install pytrends")
            else:
                logger.warning("Google Trends source not enabled")

    async def collect(self) -> List[Dict[str, Any]]:
        """Collect trending search data from Google Trends."""
        if not self.enabled or self.pytrends is None:
            logger.info("Google Trends source is disabled or not configured")
            return []

        results = []
        logger.info(f"Collecting Google Trends data for {len(self.keywords)} keyword groups...")

        try:
            # Get trending searches
            for region in self.regions:
                try:
                    trending = self.pytrends.trending_searches(pn=region.lower())
                    if not trending.empty:
                        for idx, trend in trending.head(20).iterrows():
                            results.append({
                                "source": "google_trends",
                                "type": "trending_search",
                                "region": region,
                                "keyword": str(trend[0]),
                                "timestamp": datetime.now().isoformat(),
                                "rank": idx + 1,
                            })
                except Exception as e:
                    logger.warning(f"Failed to fetch trending searches for {region}: {e}")

            # Get interest over time for keywords
            for keyword in self.keywords:
                try:
                    self.pytrends.build_payload([keyword], timeframe=self.timeframe)
                    
                    # Interest over time
                    interest = self.pytrends.interest_over_time()
                    if not interest.empty and keyword in interest.columns:
                        avg_interest = interest[keyword].mean()
                        trend_direction = "rising" if interest[keyword].iloc[-1] > interest[keyword].iloc[0] else "falling"
                        
                        results.append({
                            "source": "google_trends",
                            "type": "keyword_interest",
                            "keyword": keyword,
                            "average_interest": float(avg_interest),
                            "trend_direction": trend_direction,
                            "current_interest": float(interest[keyword].iloc[-1]),
                            "timestamp": datetime.now().isoformat(),
                        })
                    
                    # Related queries
                    related = self.pytrends.related_queries()
                    if keyword in related and related[keyword]['rising'] is not None:
                        rising_queries = related[keyword]['rising']
                        if not rising_queries.empty:
                            for _, query in rising_queries.head(10).iterrows():
                                results.append({
                                    "source": "google_trends",
                                    "type": "rising_query",
                                    "main_keyword": keyword,
                                    "query": query['query'],
                                    "value": int(query['value']) if 'value' in query else 0,
                                    "timestamp": datetime.now().isoformat(),
                                })
                
                except Exception as e:
                    logger.warning(f"Failed to fetch interest data for '{keyword}': {e}")

        except Exception as e:
            logger.error(f"Error collecting Google Trends data: {e}")

        logger.info(f"Collected {len(results)} Google Trends data points")
        return results
