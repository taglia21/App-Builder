"""News Collector - Aggregates from NewsAPI, GNews, and Currents."""

import os
import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class NewsCollector:
    """Collects tech/business news from multiple sources."""
    
    TECH_KEYWORDS = ['startup', 'saas', 'automation', 'AI', 'software', 'productivity']
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.newsapi_key = os.getenv('NEWSAPI_KEY')
        self.gnews_key = os.getenv('GNEWS_API_KEY')
        self.currents_key = os.getenv('CURRENTS_API_KEY')
    
    def _fetch_newsapi(self) -> List[Dict]:
        """Fetch from NewsAPI."""
        if not self.newsapi_key:
            return []
        try:
            url = f"https://newsapi.org/v2/everything?q=startup+OR+saas+OR+automation&sortBy=publishedAt&pageSize=20&apiKey={self.newsapi_key}"
            response = httpx.get(url, timeout=30)
            response.raise_for_status()
            return response.json().get('articles', [])
        except Exception as e:
            logger.error(f"NewsAPI error: {e}")
            return []
    
    def _fetch_gnews(self) -> List[Dict]:
        """Fetch from GNews."""
        if not self.gnews_key:
            return []
        try:
            url = f"https://gnews.io/api/v4/search?q=technology+startup&lang=en&max=10&apikey={self.gnews_key}"
            response = httpx.get(url, timeout=30)
            response.raise_for_status()
            return response.json().get('articles', [])
        except Exception as e:
            logger.error(f"GNews error: {e}")
            return []
    
    def _fetch_currents(self) -> List[Dict]:
        """Fetch from Currents API."""
        if not self.currents_key:
            return []
        try:
            url = f"https://api.currentsapi.services/v1/search?keywords=startup,saas&language=en&apiKey={self.currents_key}"
            response = httpx.get(url, timeout=30)
            response.raise_for_status()
            return response.json().get('news', [])
        except Exception as e:
            logger.error(f"Currents error: {e}")
            return []
    
    def _article_to_pain_point(self, article: Dict, source: str):
        """Convert article to pain point."""
        from src.models import PainPoint
        from uuid import uuid4
        
        title = article.get('title', '') or ''
        desc = article.get('description', '') or article.get('content', '') or ''
        url = article.get('url', '') or article.get('link', '')
        
        return PainPoint(
            id=uuid4(),
            description=f"{title}. {desc[:200]}",
            source_type="news",
            source_url=url,
            frequency_count=1,
            urgency_score=0.5,
            sentiment_score=0.0,
            affected_industries=['technology'],
            affected_user_personas=['business user'],
            keywords=[kw for kw in self.TECH_KEYWORDS if kw.lower() in (title + desc).lower()][:5],
            raw_excerpts=[title, desc[:200]]
        )
    
    def collect(self):
        """Collect from all news sources."""
        logger.info("Collecting from news sources...")
        pain_points = []
        
        for article in self._fetch_newsapi():
            pain_points.append(self._article_to_pain_point(article, 'newsapi'))
        
        for article in self._fetch_gnews():
            pain_points.append(self._article_to_pain_point(article, 'gnews'))
        
        for article in self._fetch_currents():
            pain_points.append(self._article_to_pain_point(article, 'currents'))
        
        logger.info(f"✓ Collected {len(pain_points)} from news sources")
        return pain_points
