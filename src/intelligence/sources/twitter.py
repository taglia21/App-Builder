"""
Twitter/X data source for gathering market intelligence.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

try:
    import tweepy
except ImportError:
    tweepy = None

from loguru import logger

from ...models import SourceType
from ..base import DataSource, register_source


@register_source("twitter")
class TwitterSource(DataSource):
    """Twitter/X data source for trend discovery."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Twitter source."""
        super().__init__(config)
        self.bearer_token = config.get("bearer_token")
        self.hashtags = config.get("hashtags", [])
        self.tweets_per_hashtag = config.get("tweets_per_hashtag", 200)

        if self.enabled and self.bearer_token and tweepy is not None:
            self.client = tweepy.Client(bearer_token=self.bearer_token)
        else:
            self.client = None
            if tweepy is None:
                logger.warning("Tweepy package not installed. Install with: pip install tweepy")
            else:
                logger.warning("Twitter source not properly configured")

    def get_source_type(self) -> SourceType:
        """Get source type."""
        return SourceType.TWITTER

    async def gather(self) -> List[Dict[str, Any]]:
        """Gather data from Twitter."""
        if not self.client:
            logger.warning("Twitter client not initialized")
            return []

        all_data = []

        for hashtag in self.hashtags:
            try:
                logger.info(f"Gathering tweets for #{hashtag}")

                # Search recent tweets
                query = f"#{hashtag} -is:retweet lang:en"
                tweets = self.client.search_recent_tweets(
                    query=query,
                    max_results=min(self.tweets_per_hashtag, 100),
                    tweet_fields=["created_at", "public_metrics", "author_id"],
                    expansions=["author_id"],
                )

                if not tweets.data:
                    continue

                for tweet in tweets.data:
                    metrics = tweet.public_metrics

                    data_point = {
                        "source_type": "twitter",
                        "source_url": f"https://twitter.com/i/web/status/{tweet.id}",
                        "content": tweet.text,
                        "created_at": tweet.created_at.isoformat(),
                        "likes": metrics.get("like_count", 0),
                        "retweets": metrics.get("retweet_count", 0),
                        "replies": metrics.get("reply_count", 0),
                        "hashtag": hashtag,
                        "engagement_score": (
                            metrics.get("like_count", 0) * 1
                            + metrics.get("retweet_count", 0) * 2
                            + metrics.get("reply_count", 0) * 3
                        ),
                    }

                    all_data.append(data_point)

                logger.info(f"Collected {len(tweets.data)} tweets for #{hashtag}")

            except Exception as e:
                logger.error(f"Error gathering tweets for #{hashtag}: {e}")
                continue

        logger.info(f"Total Twitter data points collected: {len(all_data)}")
        return all_data
