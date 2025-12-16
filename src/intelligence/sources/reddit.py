"""
Reddit data source for gathering market intelligence.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

try:
    import praw
except ImportError:
    praw = None

from loguru import logger

from ...models import SourceType
from ..base import DataSource, register_source


@register_source("reddit")
class RedditSource(DataSource):
    """Reddit data source for pain point discovery."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Reddit source."""
        super().__init__(config)
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.subreddits = config.get("subreddits", [])
        self.posts_per_subreddit = config.get("posts_per_subreddit", 100)
        self.min_score = config.get("min_score", 50)
        self.min_comments = config.get("min_comments", 20)
        self.max_age_days = config.get("max_age_days", 90)

        if self.enabled and self.client_id and self.client_secret and praw is not None:
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
        if not self.reddit:
            logger.warning("Reddit client not initialized")
            return []

        all_data = []
        cutoff_date = datetime.utcnow() - timedelta(days=self.max_age_days)

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
                        # Extract pain point patterns
                        pain_point_indicators = [
                            "i wish there was",
                            "why isn't there",
                            "frustrated with",
                            "problem with",
                            "hate that",
                            "annoying that",
                            "need a tool",
                            "looking for a solution",
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

                logger.info(f"Collected {len(all_data)} posts from r/{subreddit_name}")

            except Exception as e:
                logger.error(f"Error gathering from r/{subreddit_name}: {e}")
                continue

        logger.info(f"Total Reddit data points collected: {len(all_data)}")
        return all_data
