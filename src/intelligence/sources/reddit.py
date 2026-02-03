"""
Reddit data source for gathering market intelligence.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

try:
    import praw
except ImportError:
    praw = None

import asyncio
import os
from uuid import uuid4

import httpx
from loguru import logger

from ...models import PainPoint, SourceType
from ..base import DataSource, register_source


@register_source("reddit")
class RedditSource(DataSource):
    """Reddit data source for pain point discovery."""

    def collect(self) -> List[PainPoint]:
        """Synchronous wrapper for gather (for Streamlit compatibility)."""
        try:
            raw_data = asyncio.run(self.gather())
            return [self._to_pain_point(item) for item in raw_data]
        except Exception as e:
            logger.error(f"Error in Reddit collect: {e}")
            return []

    def _to_pain_point(self, item: Dict[str, Any]) -> PainPoint:
        return PainPoint(
            id=uuid4(),
            description=f"{item.get('title', '')}\n\n{item.get('content', '')}",
            source_type=item.get('source_type', 'reddit'),
            source_url=item.get('source_url', ''),
            frequency_count=1,
            urgency_score=0.7,
            sentiment_score=0.0,
            affected_industries=['technology', 'startup'],
            affected_user_personas=['entrepreneur'],
            keywords=[],
            raw_excerpts=[item.get('title', ''), item.get('content', '')[:200]]
        )

    def __init__(self, config: Dict[str, Any]):
        """Initialize Reddit source."""
        super().__init__(config)
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.subreddits = config.get("subreddits", ["startups", "entrepreneur", "smallbusiness", "saas"])
        self.posts_per_subreddit = config.get("posts_per_subreddit", 100)
        self.min_score = config.get("min_score", 50)
        self.min_comments = config.get("min_comments", 20)
        self.max_age_days = config.get("max_age_days", 90)

        self.use_tavily = False
        self.tavily_key = os.getenv("TAVILY_API_KEY")

        # Prioritize Tavily as requested by user
        if self.tavily_key:
            self.use_tavily = True
            self.reddit = None
            logger.info("Using Tavily Search for Reddit data (Default).")
        elif self.enabled and self.client_id and self.client_secret and praw is not None:
            self.use_tavily = False
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent="StartupGenerator/1.0",
            )
        else:
            self.reddit = None
            if praw is None:
                logger.warning("PRAW package not installed. Install with: pip install praw")
            else:
                logger.warning("Reddit source not properly configured")

    def get_source_type(self) -> SourceType:
        """Get source type."""
        return SourceType.REDDIT

    async def gather(self) -> List[Dict[str, Any]]:
        """Gather data from Reddit."""
        if self.use_tavily:
            return await self._gather_via_tavily()

        if not self.reddit:
            logger.warning("Reddit client not initialized")
            return []

        all_data = []
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.max_age_days)

        for subreddit_name in self.subreddits:
            try:
                logger.info(f"Gathering from r/{subreddit_name}")
                subreddit = self.reddit.subreddit(subreddit_name)

                # Get top posts from the time period
                for post in subreddit.top(time_filter="month", limit=self.posts_per_subreddit):
                    post_date = datetime.fromtimestamp(post.created_utc)

                    # Filter by criteria
                    if (
                        post.score >= self.min_score
                        and post.num_comments >= self.min_comments
                        and post_date >= cutoff_date
                    ):
                        self._process_post(post, subreddit_name, post_date, all_data)

                logger.info(f"Collected {len(all_data)} posts from r/{subreddit_name}")

            except Exception as e:
                logger.error(f"Error gathering from r/{subreddit_name}: {e}")
                continue

        logger.info(f"Total Reddit data points collected: {len(all_data)}")
        return all_data

    def _process_post(self, post, subreddit_name, post_date, all_data):
        # Extract pain point patterns
        pain_point_indicators = [
            "i wish there was", "why isn't there", "frustrated with",
            "problem with", "hate that", "annoying that",
            "need a tool", "looking for a solution",
        ]

        title_lower = post.title.lower()
        selftext_lower = post.selftext.lower()

        is_pain_point = any(
            indicator in title_lower or indicator in selftext_lower
            for indicator in pain_point_indicators
        )

        # Collect top comments
        post.comments.replace_more(limit=0)
        top_comments = []
        for comment in post.comments[:10]:
            if hasattr(comment, "body"):
                top_comments.append(comment.body)

        data_point = {
            "source_type": "reddit",
            "source_url": f"https://reddit.com{post.permalink}",
            "title": post.title,
            "content": post.selftext,
            "comments": top_comments,
            "score": post.score,
            "num_comments": post.num_comments,
            "created_at": post_date.isoformat(),
            "subreddit": subreddit_name,
            "is_pain_point": is_pain_point,
        }

        all_data.append(data_point)

    async def _gather_via_tavily(self) -> List[Dict[str, Any]]:
        """Gather Reddit data via Tavily Search."""
        if not self.tavily_key:
            return []

        logger.info("Searching Reddit via Tavily...")
        all_data = []

        queries = [
            f"site:reddit.com/r/{sr} biggest pain points problems complaints"
            for sr in self.subreddits[:3]
        ]

        async with httpx.AsyncClient() as client:
            for query in queries:
                try:
                    response = await client.post(
                        'https://api.tavily.com/search',
                        json={
                            'api_key': self.tavily_key,
                            'query': query,
                            'max_results': 5,
                            'include_domains': ['reddit.com']
                        },
                        timeout=30
                    )

                    if response.status_code == 200:
                        results = response.json().get('results', [])
                        for res in results:
                            data_point = {
                                "source_type": "reddit", # Must match Enum
                                "source_url": res.get('url'),
                                "title": res.get('title'),
                                "content": res.get('content'),
                                "comments": [], # Tavily doesn't return comments usually
                                "score": 100, # Mock score
                                "num_comments": 0,
                                "created_at": datetime.now(timezone.utc).isoformat(),
                                "subreddit": "unknown",
                                "is_pain_point": True, # Assume search result is relevant
                            }
                            all_data.append(data_point)
                except Exception as e:
                    logger.error(f"Tavily search error: {e}")

        logger.info(f"Collected {len(all_data)} Reddit posts via Tavily")
        return all_data
