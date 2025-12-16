"""
Hacker News data source for tech intelligence (NO API KEY REQUIRED).
Uses the official Hacker News API to track trending tech discussions and pain points.
"""

from datetime import datetime
from typing import Any, Dict, List

try:
    import requests
except ImportError:
    requests = None

from loguru import logger

from ...models import PainPoint
from ..base import DataSource


class HackerNewsSource(DataSource):
    """Collect trending stories and discussions from Hacker News."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Hacker News source."""
        super().__init__(config)
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.max_stories = config.get("max_stories", 100)
        self.min_score = config.get("min_score", 50)
        self.story_types = config.get("story_types", ["top", "best", "new"])
        self.keywords = config.get("keywords", [
            "startup", "SaaS", "automation", "tool", "problem",
            "pain point", "frustration", "difficult", "challenge",
            "looking for", "need", "wish", "alternative to",
            "better way", "API", "integration", "workflow",
        ])

        if requests is None:
            logger.warning("requests package not installed. Install with: pip install requests")
            self.enabled = False

    async def collect(self) -> List[Dict[str, Any]]:
        """Collect stories and comments from Hacker News."""
        if not self.enabled or requests is None:
            logger.info("Hacker News source is disabled or not configured")
            return []

        results = []
        logger.info(f"Collecting Hacker News stories and discussions...")

        try:
            # Collect stories from different categories
            for story_type in self.story_types:
                try:
                    # Get story IDs
                    response = requests.get(f"{self.base_url}/{story_type}stories.json", timeout=10)
                    response.raise_for_status()
                    story_ids = response.json()[:self.max_stories]
                    
                    for story_id in story_ids[:50]:  # Process top 50 per type
                        try:
                            # Get story details
                            story_response = requests.get(f"{self.base_url}/item/{story_id}.json", timeout=10)
                            story_response.raise_for_status()
                            story = story_response.json()
                            
                            if not story or story.get('dead') or story.get('deleted'):
                                continue
                            
                            score = story.get('score', 0)
                            if score < self.min_score:
                                continue
                            
                            title = story.get('title', '')
                            text = story.get('text', '')
                            url = story.get('url', '')
                            
                            # Check relevance
                            content = f"{title} {text}".lower()
                            relevance = sum(1 for keyword in self.keywords if keyword in content)
                            
                            if relevance > 0 or score > 200:  # High score stories are always interesting
                                results.append({
                                    "source": "hackernews",
                                    "type": "story",
                                    "story_type": story_type,
                                    "story_id": story_id,
                                    "title": title,
                                    "text": text,
                                    "url": url,
                                    "score": score,
                                    "author": story.get('by', ''),
                                    "num_comments": story.get('descendants', 0),
                                    "time": datetime.fromtimestamp(story.get('time', 0)).isoformat(),
                                    "relevance_score": relevance,
                                    "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
                                    "timestamp": datetime.now().isoformat(),
                                })
                            
                            # Get top comments if highly relevant or high engagement
                            if (relevance >= 2 or score > 300) and story.get('kids'):
                                comment_ids = story['kids'][:10]  # Top 10 comments
                                for comment_id in comment_ids:
                                    try:
                                        comment_response = requests.get(
                                            f"{self.base_url}/item/{comment_id}.json", 
                                            timeout=5
                                        )
                                        comment_response.raise_for_status()
                                        comment = comment_response.json()
                                        
                                        if comment and not comment.get('dead') and not comment.get('deleted'):
                                            comment_text = comment.get('text', '')
                                            comment_content = comment_text.lower()
                                            comment_relevance = sum(1 for kw in self.keywords if kw in comment_content)
                                            
                                            if comment_relevance > 0:
                                                results.append({
                                                    "source": "hackernews",
                                                    "type": "comment",
                                                    "story_id": story_id,
                                                    "comment_id": comment_id,
                                                    "parent_title": title,
                                                    "text": comment_text,
                                                    "author": comment.get('by', ''),
                                                    "time": datetime.fromtimestamp(comment.get('time', 0)).isoformat(),
                                                    "relevance_score": comment_relevance,
                                                    "hn_url": f"https://news.ycombinator.com/item?id={comment_id}",
                                                    "timestamp": datetime.now().isoformat(),
                                                })
                                    except Exception as e:
                                        logger.debug(f"Failed to fetch comment {comment_id}: {e}")
                                        
                        except Exception as e:
                            logger.debug(f"Failed to fetch story {story_id}: {e}")
                            
                except Exception as e:
                    logger.warning(f"Failed to fetch {story_type} stories: {e}")

        except Exception as e:
            logger.error(f"Error collecting Hacker News data: {e}")

        logger.info(f"Collected {len(results)} Hacker News items")
        return results
