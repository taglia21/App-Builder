"""Search Collector - Web search via Serper and Tavily."""

import os
import logging
import httpx
from typing import List, Dict, Any, Optional
import hashlib

logger = logging.getLogger(__name__)


class SearchCollector:
    """Collects market intelligence via web search."""
    
    SEARCH_QUERIES = [
        "biggest pain points for small business owners 2024",
        "what tools do startups need",
        "frustrating business software problems",
        "automation gaps in enterprise",
        "SaaS tools people wish existed"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.serper_key = os.getenv('SERPER_API_KEY')
        self.tavily_key = os.getenv('TAVILY_API_KEY')
    
    def _search_serper(self, query: str) -> List[Dict]:
        """Search via Serper."""
        if not self.serper_key:
            return []
        try:
            response = httpx.post(
                'https://google.serper.dev/search',
                headers={'X-API-KEY': self.serper_key, 'Content-Type': 'application/json'},
                json={'q': query, 'num': 10},
                timeout=30
            )
            response.raise_for_status()
            return response.json().get('organic', [])
        except Exception as e:
            logger.error(f"Serper error: {e}")
            return []
    
    def _search_tavily(self, query: str) -> List[Dict]:
        """Search via Tavily."""
        if not self.tavily_key:
            return []
        try:
            response = httpx.post(
                'https://api.tavily.com/search',
                json={'api_key': self.tavily_key, 'query': query, 'max_results': 10},
                timeout=30
            )
            response.raise_for_status()
            return response.json().get('results', [])
        except Exception as e:
            logger.error(f"Tavily error: {e}")
            return []
    
    def _result_to_pain_point(self, result: Dict, source: str):
        """Convert search result to pain point."""
        from src.models import PainPoint
        from uuid import uuid4
        
        title = result.get('title', '')
        snippet = result.get('snippet', '') or result.get('content', '')
        url = result.get('link', '') or result.get('url', '')
        
        return PainPoint(
            id=uuid4(),
            description=f"{title}. {snippet[:200]}",
            source_type="google",
            source_url=url,
            frequency_count=1,
            urgency_score=0.6,
            sentiment_score=0.0,
            affected_industries=['technology', 'business'],
            affected_user_personas=['business user'],
            keywords=[],
            raw_excerpts=[title, snippet[:200]]
        )
    
    def collect(self):
        """Collect from search engines."""
        logger.info("Collecting from search engines...")
        pain_points = []
        
        for query in self.SEARCH_QUERIES[:3]:
            for result in self._search_serper(query):
                pain_points.append(self._result_to_pain_point(result, 'serper'))
            
            for result in self._search_tavily(query):
                pain_points.append(self._result_to_pain_point(result, 'tavily'))
        
        logger.info(f"✓ Collected {len(pain_points)} from search")
        return pain_points
