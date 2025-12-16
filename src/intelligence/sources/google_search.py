"""
Google Search data source for gathering market intelligence.
"""

from typing import Any, Dict, List

try:
    from googleapiclient.discovery import build
except ImportError:
    build = None

from loguru import logger

from ...models import SourceType
from ..base import DataSource, register_source


@register_source("google_search")
class GoogleSearchSource(DataSource):
    """Google Custom Search source for market trends."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Google Search source."""
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.cse_id = config.get("cse_id")
        self.queries_per_run = config.get("queries_per_run", 50)

        # Default search queries
        self.search_queries = [
            "B2B SaaS trends 2024",
            "enterprise software pain points",
            "startup automation tools",
            "business process automation",
            "SaaS market opportunities",
            "developer tools trends",
            "workflow automation software",
            "team collaboration problems",
        ]

        if self.enabled and self.api_key and self.cse_id and build is not None:
            self.service = build("customsearch", "v1", developerKey=self.api_key)
        else:
            self.service = None
            if build is None:
                logger.warning("Google API client not installed. Install with: pip install google-api-python-client")
            else:
                logger.warning("Google Search source not properly configured")

    def get_source_type(self) -> SourceType:
        """Get source type."""
        return SourceType.GOOGLE

    async def gather(self) -> List[Dict[str, Any]]:
        """Gather data from Google Search."""
        if not self.service:
            logger.warning("Google Search client not initialized")
            return []

        all_data = []

        for query in self.search_queries[: self.queries_per_run]:
            try:
                logger.info(f"Searching Google for: {query}")

                result = (
                    self.service.cse()
                    .list(
                        q=query,
                        cx=self.cse_id,
                        num=10,  # Max results per query
                    )
                    .execute()
                )

                for item in result.get("items", []):
                    data_point = {
                        "source_type": "google",
                        "source_url": item.get("link", ""),
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "query": query,
                    }

                    all_data.append(data_point)

                logger.info(f"Collected {len(result.get('items', []))} results for: {query}")

            except Exception as e:
                logger.error(f"Error searching Google for '{query}': {e}")
                continue

        logger.info(f"Total Google Search data points collected: {len(all_data)}")
        return all_data
