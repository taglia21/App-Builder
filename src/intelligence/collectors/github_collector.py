"""GitHub Collector - Trending repos and issue mining for pain points."""

import os
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GitHubCollector:
    """Collects trending repos and issues from GitHub."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.token = self.config.get('token') or os.getenv('GITHUB_TOKEN')
        self.headers = {'Accept': 'application/vnd.github.v3+json'}
        if self.token:
            self.headers['Authorization'] = f'token {self.token}'
    
    def _search_repos(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for repositories."""
        try:
            url = f"https://api.github.com/search/repositories?q={query}&sort=stars&per_page={limit}"
            response = httpx.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json().get('items', [])
        except Exception as e:
            logger.error(f"GitHub search error: {e}")
            return []
    
    def _get_trending_topics(self) -> List[Dict]:
        """Get trending topics based on recent stars."""
        queries = [
            'automation created:>2024-01-01',
            'saas tool created:>2024-01-01',
            'ai assistant created:>2024-01-01',
            'workflow automation stars:>100',
            'developer tools stars:>500'
        ]
        repos = []
        for q in queries:
            repos.extend(self._search_repos(q, 5))
        return repos
    
    def _repo_to_pain_point(self, repo: Dict):
        """Convert repo to pain point."""
        from src.models import PainPoint
        from uuid import uuid4
        
        desc = repo.get('description', '') or ''
        name = repo.get('name', '')
        
        return PainPoint(
            id=uuid4(),
            description=f"GitHub trending: {name} - {desc[:200]}",
            source_type="github",
            source_url=repo.get('html_url', ''),
            frequency_count=repo.get('stargazers_count', 0),
            urgency_score=min(repo.get('stargazers_count', 0) / 10000, 1.0),
            sentiment_score=0.5,
            affected_industries=['technology', 'software'],
            affected_user_personas=['developer'],
            keywords=[t for t in (repo.get('topics') or [])[:5]],
            raw_excerpts=[desc[:300]]
        )
    
    def collect(self):
        """Collect pain points from GitHub."""
        logger.info("Collecting from GitHub...")
        repos = self._get_trending_topics()
        pain_points = [self._repo_to_pain_point(r) for r in repos[:20]]
        logger.info(f"✓ Collected {len(pain_points)} from GitHub")
        return pain_points
