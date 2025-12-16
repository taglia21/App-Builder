"""
YouTube data source for gathering market intelligence.
"""

from datetime import datetime
from typing import Any, Dict, List

try:
    from googleapiclient.discovery import build
except ImportError:
    build = None

from loguru import logger

from ...models import SourceType
from ..base import DataSource, register_source


@register_source("youtube")
class YouTubeSource(DataSource):
    """YouTube source for video content analysis."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize YouTube source."""
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.search_queries = config.get("search_queries", [])
        self.max_results_per_query = config.get("max_results_per_query", 50)

        if self.enabled and self.api_key and build is not None:
            self.youtube = build("youtube", "v3", developerKey=self.api_key)
        else:
            self.youtube = None
            if build is None:
                logger.warning("Google API client not installed. Install with: pip install google-api-python-client")
            else:
                logger.warning("YouTube source not properly configured")

    def get_source_type(self) -> SourceType:
        """Get source type."""
        return SourceType.YOUTUBE

    async def gather(self) -> List[Dict[str, Any]]:
        """Gather data from YouTube."""
        if not self.youtube:
            logger.warning("YouTube client not initialized")
            return []

        all_data = []

        for query in self.search_queries:
            try:
                logger.info(f"Gathering YouTube videos for query: {query}")

                # Search for videos
                search_response = (
                    self.youtube.search()
                    .list(
                        q=query,
                        type="video",
                        part="id,snippet",
                        maxResults=min(self.max_results_per_query, 50),
                        order="relevance",
                    )
                    .execute()
                )

                video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]

                if not video_ids:
                    continue

                # Get video statistics
                videos_response = (
                    self.youtube.videos()
                    .list(part="statistics,snippet", id=",".join(video_ids))
                    .execute()
                )

                for video in videos_response.get("items", []):
                    snippet = video.get("snippet", {})
                    statistics = video.get("statistics", {})

                    # Get top comments
                    comments = self._get_top_comments(video["id"])

                    data_point = {
                        "source_type": "youtube",
                        "source_url": f"https://youtube.com/watch?v={video['id']}",
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "channel_title": snippet.get("channelTitle", ""),
                        "views": int(statistics.get("viewCount", 0)),
                        "likes": int(statistics.get("likeCount", 0)),
                        "comments_count": int(statistics.get("commentCount", 0)),
                        "top_comments": comments,
                        "query": query,
                    }

                    all_data.append(data_point)

                logger.info(f"Collected {len(video_ids)} videos for query: {query}")

            except Exception as e:
                logger.error(f"Error gathering YouTube data for query {query}: {e}")
                continue

        logger.info(f"Total YouTube data points collected: {len(all_data)}")
        return all_data

    def _get_top_comments(self, video_id: str, max_comments: int = 10) -> List[str]:
        """Get top comments for a video."""
        try:
            comments_response = (
                self.youtube.commentThreads()
                .list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=max_comments,
                    order="relevance",
                    textFormat="plainText",
                )
                .execute()
            )

            comments = []
            for item in comments_response.get("items", []):
                comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                comments.append(comment)

            return comments

        except Exception as e:
            logger.debug(f"Could not fetch comments for video {video_id}: {e}")
            return []
