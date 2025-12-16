"""
Reddit Playwright Collector - Browser-based scraping for comprehensive pain point discovery.
"""

import os
import re
import json
import time
import logging
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RedditPost:
    id: str
    title: str
    body: str
    url: str
    subreddit: str
    score: int
    num_comments: int
    author: str = ""
    comments: List[Dict[str, Any]] = field(default_factory=list)


class RedditPlaywrightCollector:
    """Collects Reddit data using Playwright browser automation."""
    
    PAIN_POINT_QUERIES = [
        "I wish there was",
        "why doesn't anyone make",
        "frustrated with",
        "hate using",
        "waste of time",
        "looking for a tool",
        "anyone know of",
        "is there a way to",
        "so annoying",
        "biggest challenge"
    ]
    
    TARGET_SUBREDDITS = [
        "SaaS", "startups", "Entrepreneur", "smallbusiness",
        "webdev", "programming", "sysadmin", "devops",
        "digital_marketing", "ecommerce"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.username = self.config.get('username') or os.getenv('REDDIT_USERNAME')
        self.password = self.config.get('password') or os.getenv('REDDIT_PASSWORD')
        self.headless = self.config.get('headless', True)
        self.delay = self.config.get('rate_limit_delay', 3)
        self.max_posts = self.config.get('posts_per_subreddit', 15)
        self.subreddits = self.config.get('subreddits', self.TARGET_SUBREDDITS)
        self.search_queries = self.config.get('search_queries', self.PAIN_POINT_QUERIES)
        
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
    
    def _start_browser(self):
        from playwright.sync_api import sync_playwright
        try:
            from playwright_stealth import stealth_sync
        except ImportError:
            stealth_sync = None
        
        logger.info("Starting browser...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36'
        )
        self.page = self.context.new_page()
        if stealth_sync:
            stealth_sync(self.page)
        logger.info("✓ Browser started")
    
    def _stop_browser(self):
        try:
            if self.page: self.page.close()
            if self.context: self.context.close()
            if self.browser: self.browser.close()
            if self.playwright: self.playwright.stop()
        except: pass
    
    def _login(self) -> bool:
        """Try to login if credentials provided, but continue without login if it fails."""
        if not self.username or not self.password:
            logger.info("No credentials provided, continuing without login (public access)")
            return False
        try:
            logger.info(f"Attempting login as {self.username}...")
            self.page.goto('https://www.reddit.com/login', wait_until='domcontentloaded', timeout=15000)
            time.sleep(2)
            self.page.fill('input[name="username"]', self.username, timeout=10000)
            self.page.fill('input[name="password"]', self.password, timeout=10000)
            self.page.click('button[type="submit"]', timeout=10000)
            time.sleep(5)
            if 'login' not in self.page.url.lower():
                logger.info("✓ Login successful")
                return True
            logger.info("Login didn't complete, continuing with public access")
            return False
        except Exception as e:
            logger.info(f"Login failed ({e}), continuing with public access")
            return False
    
    def _scroll_page(self, n: int = 3):
        for _ in range(n):
            self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1.5)
    
    def _extract_posts_from_subreddit(self, subreddit: str) -> List[RedditPost]:
        posts = []
        try:
            # Try old.reddit.com which works better without login
            url = f'https://old.reddit.com/r/{subreddit}/hot/'
            logger.info(f"Fetching r/{subreddit}...")
            self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            time.sleep(self.delay)
            self._scroll_page(2)
            
            post_urls = set()
            # old.reddit.com uses different selectors
            for link in self.page.query_selector_all('a.title'):
                href = link.get_attribute('href')
                if href:
                    if href.startswith('/r/'):
                        href = f"https://old.reddit.com{href}"
                    elif not href.startswith('http'):
                        continue
                    if '/comments/' in href:
                        post_urls.add(href.replace('old.reddit.com', 'www.reddit.com'))
            
            # Fallback to new reddit if old didn't work
            if not post_urls:
                url = f'https://www.reddit.com/r/{subreddit}/hot/'
                self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
                time.sleep(self.delay)
                self._scroll_page(2)
                
                for sel in ['a[data-click-id="body"]', 'a[href*="/comments/"]']:
                    for link in self.page.query_selector_all(sel):
                        href = link.get_attribute('href')
                        if href and '/comments/' in href:
                            if not href.startswith('http'):
                                href = f"https://www.reddit.com{href}"
                            post_urls.add(href)
            
            logger.info(f"Found {len(post_urls)} posts in r/{subreddit}")
            
            for url in list(post_urls)[:self.max_posts]:
                try:
                    post = self._extract_post(url, subreddit)
                    if post and len(post.title) > 10:
                        posts.append(post)
                    time.sleep(self.delay)
                except Exception as e:
                    logger.debug(f"Error extracting post {url}: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error with r/{subreddit}: {e}")
        
        logger.info(f"r/{subreddit}: {len(posts)} posts collected")
        return posts
    
    def _extract_post(self, url: str, subreddit: str) -> Optional[RedditPost]:
        try:
            self.page.goto(url, wait_until='domcontentloaded')
            time.sleep(2)
            
            title = ""
            for sel in ['h1', '[data-testid="post-title"]']:
                elem = self.page.query_selector(sel)
                if elem:
                    title = elem.inner_text()
                    break
            
            body = ""
            for sel in ['[data-click-id="text"]', '[slot="text-body"]']:
                elem = self.page.query_selector(sel)
                if elem:
                    body = elem.inner_text()
                    break
            
            comments = []
            for elem in self.page.query_selector_all('[data-testid="comment"]')[:20]:
                try:
                    p = elem.query_selector('p')
                    if p:
                        text = p.inner_text()
                        if len(text) > 20:
                            comments.append({'text': text[:500]})
                except: pass
            
            return RedditPost(
                id=hashlib.md5(url.encode()).hexdigest()[:12],
                title=title.strip(),
                body=body.strip()[:1000],
                url=url,
                subreddit=subreddit,
                score=0,
                num_comments=len(comments),
                comments=comments
            )
        except Exception as e:
            logger.warning(f"Extract error: {e}")
            return None
    
    def _search_pain_points(self) -> List[RedditPost]:
        posts = []
        for query in self.search_queries[:5]:
            try:
                encoded = query.replace(' ', '%20')
                self.page.goto(f'https://www.reddit.com/search/?q={encoded}&sort=relevance&t=year')
                time.sleep(self.delay)
                self._scroll_page(2)
                
                urls = set()
                for link in self.page.query_selector_all('a[href*="/comments/"]')[:10]:
                    href = link.get_attribute('href')
                    if href:
                        if not href.startswith('http'):
                            href = f"https://www.reddit.com{href}"
                        urls.add(href)
                
                for url in list(urls)[:3]:
                    post = self._extract_post(url, "search")
                    if post:
                        posts.append(post)
                    time.sleep(self.delay)
            except: continue
        return posts
    
    def _to_pain_point(self, post: RedditPost):
        from src.models import PainPoint
        from uuid import uuid4
        
        text = f"{post.title} {post.body} " + " ".join([c['text'] for c in post.comments[:5]])
        
        keywords = [kw for kw in ['automation', 'manual', 'time-consuming', 'expensive', 
            'integration', 'api', 'crm', 'workflow', 'productivity', 'billing', 'onboarding']
            if kw in text.lower()]
        
        urgency = 0.5
        for word in ['hate', 'frustrated', 'terrible', 'urgent', 'desperate']:
            if word in text.lower():
                urgency += 0.1
        urgency = min(urgency, 1.0)
        
        industries = []
        for ind, kws in {'SaaS': ['saas', 'software'], 'e-commerce': ['ecommerce', 'shopify'],
            'fintech': ['payment', 'invoice'], 'marketing': ['marketing', 'seo']}.items():
            if any(k in text.lower() for k in kws):
                industries.append(ind)
        
        return PainPoint(
            id=uuid4(),
            description=f"{post.title}. {post.body[:300]}" if post.body else post.title,
            source_type="reddit",
            source_url=post.url,
            frequency_count=post.num_comments + 1,
            urgency_score=urgency,
            sentiment_score=-0.3,
            affected_industries=industries or ['technology'],
            affected_user_personas=['business user'],
            keywords=keywords[:10],
            raw_excerpts=[post.title] + [c['text'][:100] for c in post.comments[:2]]
        )
    
    def collect(self):
        pain_points = []
        try:
            self._start_browser()
            self._login()
            
            logger.info("=== Scraping Subreddits ===")
            for sub in self.subreddits[:3]:
                posts = self._extract_posts_from_subreddit(sub)
                pain_points.extend([self._to_pain_point(p) for p in posts])
                logger.info(f"r/{sub}: {len(posts)} posts")
            
            logger.info("=== Searching Pain Points ===")
            search_posts = self._search_pain_points()
            pain_points.extend([self._to_pain_point(p) for p in search_posts])
            
            # Dedupe
            seen = set()
            unique = []
            for pp in pain_points:
                if pp.source_url not in seen:
                    seen.add(pp.source_url)
                    unique.append(pp)
            
            logger.info(f"✓ Collected {len(unique)} pain points")
            return unique
        finally:
            self._stop_browser()
