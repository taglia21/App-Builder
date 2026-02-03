"""
RSS Feed data source for market intelligence (NO API KEY REQUIRED).
Uses feedparser to aggregate content from various RSS feeds.
"""

from datetime import datetime
from typing import Any, Dict, List

try:
    import feedparser
except ImportError:
    feedparser = None

from loguru import logger

from ..base import DataSource


class RSSFeedSource(DataSource):
    """Collect articles from RSS feeds."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize RSS feed source."""
        super().__init__(config)

        # Default high-quality RSS feeds for startup/tech/business intelligence
        self.feeds = config.get("feeds", [
            # Tech & Startup News
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://news.ycombinator.com/rss",
            "http://feeds.feedburner.com/TechCrunch/startups",

            # Business & SaaS
            "https://www.saastr.com/feed/",
            "https://www.forbes.com/innovation/feed/",
            "https://hbr.org/feed",

            # Developer & Tech
            "https://stackoverflow.blog/feed/",
            "https://github.blog/feed/",
            "https://dev.to/feed",

            # Product & Design
            "https://www.producthunt.com/feed",
            "https://uxdesign.cc/feed",

            # Industry specific
            "https://www.indiehackers.com/feed.xml",
            "https://news.ycombinator.com/rss",
        ])

        self.max_entries_per_feed = config.get("max_entries_per_feed", 20)
        self.keywords = config.get("keywords", [
            "startup", "SaaS", "automation", "API", "integration",
            "productivity", "workflow", "problem", "challenge", "pain point",
            "developer tools", "business tools", "enterprise",
        ])

        if feedparser is None:
            logger.warning("feedparser package not installed. Install with: pip install feedparser")
            self.enabled = False

    async def collect(self) -> List[Dict[str, Any]]:
        """Collect articles from RSS feeds."""
        if not self.enabled or feedparser is None:
            logger.info("RSS feed source is disabled or not configured")
            return []

        results = []
        logger.info(f"Collecting from {len(self.feeds)} RSS feeds...")

        for feed_url in self.feeds:
            try:
                feed = feedparser.parse(feed_url)

                if not feed.entries:
                    logger.warning(f"No entries found in feed: {feed_url}")
                    continue

                feed_title = feed.feed.get('title', feed_url)

                for entry in feed.entries[:self.max_entries_per_feed]:
                    title = entry.get('title', '')
                    description = entry.get('summary', entry.get('description', ''))

                    # Check if article is relevant based on keywords
                    text = f"{title} {description}".lower()
                    relevance_score = sum(1 for keyword in self.keywords if keyword.lower() in text)

                    if relevance_score > 0:  # At least one keyword match
                        results.append({
                            "source": "rss_feed",
                            "feed_name": feed_title,
                            "feed_url": feed_url,
                            "title": title,
                            "description": description,
                            "url": entry.get('link', ''),
                            "published": entry.get('published', entry.get('updated', '')),
                            "author": entry.get('author', ''),
                            "tags": [tag.get('term', '') for tag in entry.get('tags', [])],
                            "relevance_score": relevance_score,
                            "timestamp": datetime.now().isoformat(),
                        })

            except Exception as e:
                logger.warning(f"Failed to parse feed {feed_url}: {e}")

        logger.info(f"Collected {len(results)} relevant articles from RSS feeds")
        return results
