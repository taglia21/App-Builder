"""
Google News data source for market intelligence (NO API KEY REQUIRED).
Uses pygooglenews to scrape recent news articles and headlines.
"""

from datetime import datetime
from typing import Any, Dict, List

try:
    from pygooglenews import GoogleNews
except ImportError:
    GoogleNews = None

from loguru import logger

from ...models import PainPoint
from ..base import DataSource


class GoogleNewsSource(DataSource):
    """Collect news articles from Google News."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Google News source."""
        super().__init__(config)
        self.language = config.get("language", "en")
        self.country = config.get("country", "US")
        self.topics = config.get("topics", [
            "BUSINESS",
            "TECHNOLOGY",
            "SCIENCE",
        ])
        self.search_queries = config.get("search_queries", [
            "startup problems",
            "business automation",
            "SaaS tools",
            "productivity software",
            "enterprise software",
            "developer tools",
            "API integration",
            "workflow automation",
            "remote work challenges",
            "business efficiency",
        ])
        self.max_articles_per_query = config.get("max_articles_per_query", 20)

        if self.enabled and GoogleNews is not None:
            self.gn = GoogleNews(lang=self.language, country=self.country)
        else:
            self.gn = None
            if GoogleNews is None:
                logger.warning("pygooglenews package not installed. Install with: pip install pygooglenews")
            else:
                logger.warning("Google News source not enabled")

    async def collect(self) -> List[Dict[str, Any]]:
        """Collect news articles from Google News."""
        if not self.enabled or self.gn is None:
            logger.info("Google News source is disabled or not configured")
            return []

        results = []
        logger.info(f"Collecting Google News articles for {len(self.search_queries)} queries...")

        try:
            # Collect articles by topic
            for topic in self.topics:
                try:
                    news = self.gn.topic_headlines(topic)
                    if news and 'entries' in news:
                        for entry in news['entries'][:10]:  # Top 10 per topic
                            results.append({
                                "source": "google_news",
                                "type": "topic_headline",
                                "topic": topic,
                                "title": entry.get('title', ''),
                                "description": entry.get('summary', ''),
                                "url": entry.get('link', ''),
                                "published": entry.get('published', ''),
                                "source_name": entry.get('source', {}).get('title', ''),
                                "timestamp": datetime.now().isoformat(),
                            })
                except Exception as e:
                    logger.warning(f"Failed to fetch topic '{topic}': {e}")

            # Collect articles by search query
            for query in self.search_queries:
                try:
                    search = self.gn.search(query, when='7d')  # Last 7 days
                    if search and 'entries' in search:
                        for entry in search['entries'][:self.max_articles_per_query]:
                            results.append({
                                "source": "google_news",
                                "type": "search_result",
                                "query": query,
                                "title": entry.get('title', ''),
                                "description": entry.get('summary', ''),
                                "url": entry.get('link', ''),
                                "published": entry.get('published', ''),
                                "source_name": entry.get('source', {}).get('title', ''),
                                "timestamp": datetime.now().isoformat(),
                            })
                except Exception as e:
                    logger.warning(f"Failed to search query '{query}': {e}")

        except Exception as e:
            logger.error(f"Error collecting Google News data: {e}")

        logger.info(f"Collected {len(results)} Google News articles")
        return results
