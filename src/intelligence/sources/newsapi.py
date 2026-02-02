"""
News API source for gathering market intelligence.
"""

from datetime import timezone, datetime, timedelta
from typing import Any, Dict, List

from loguru import logger

try:
    from newsapi import NewsApiClient
except ImportError:
    NewsApiClient = None

from ...models import SourceType
from ..base import DataSource, register_source


@register_source("newsapi")
class NewsAPISource(DataSource):
    """News API source for industry trends."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize News API source."""
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.categories = config.get("categories", [])
        self.queries = config.get("queries", [])

        if self.enabled and self.api_key and NewsApiClient is not None:
            self.client = NewsApiClient(api_key=self.api_key)
        else:
            self.client = None
            if NewsApiClient is None:
                logger.warning("NewsAPI package not installed. Install with: pip install newsapi-python")
            else:
                logger.warning("NewsAPI source not properly configured")

    def get_source_type(self) -> SourceType:
        """Get source type."""
        return SourceType.NEWS

    async def gather(self) -> List[Dict[str, Any]]:
        """Gather data from News API."""
        if not self.client:
            logger.warning("NewsAPI client not initialized")
            return []

        all_data = []
        from_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        # Gather by categories
        for category in self.categories:
            try:
                logger.info(f"Gathering news for category: {category}")

                articles = self.client.get_top_headlines(
                    category=category, language="en", page_size=100
                )

                for article in articles.get("articles", []):
                    data_point = {
                        "source_type": "news",
                        "source_url": article.get("url", ""),
                        "title": article.get("title", ""),
                        "description": article.get("description", ""),
                        "content": article.get("content", ""),
                        "published_at": article.get("publishedAt", ""),
                        "source_name": article.get("source", {}).get("name", ""),
                        "category": category,
                    }

                    all_data.append(data_point)

                logger.info(f"Collected {len(articles.get('articles', []))} articles for {category}")

            except Exception as e:
                logger.error(f"Error gathering news for category {category}: {e}")
                continue

        # Gather by queries
        for query in self.queries:
            try:
                logger.info(f"Gathering news for query: {query}")

                articles = self.client.get_everything(
                    q=query, from_param=from_date, language="en", sort_by="relevancy", page_size=100
                )

                for article in articles.get("articles", []):
                    data_point = {
                        "source_type": "news",
                        "source_url": article.get("url", ""),
                        "title": article.get("title", ""),
                        "description": article.get("description", ""),
                        "content": article.get("content", ""),
                        "published_at": article.get("publishedAt", ""),
                        "source_name": article.get("source", {}).get("name", ""),
                        "query": query,
                    }

                    all_data.append(data_point)

                logger.info(f"Collected {len(articles.get('articles', []))} articles for query: {query}")

            except Exception as e:
                logger.error(f"Error gathering news for query {query}: {e}")
                continue

        logger.info(f"Total news data points collected: {len(all_data)}")
        return all_data
