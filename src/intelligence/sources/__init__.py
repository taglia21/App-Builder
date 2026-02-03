"""
Sources package initialization.
"""

# Paid/API-key required sources
from .github import GitHubSource

# Free sources (NO API KEY REQUIRED)
from .google_news import GoogleNewsSource
from .google_search import GoogleSearchSource
from .google_trends import GoogleTrendsSource
from .hackernews import HackerNewsSource
from .newsapi import NewsAPISource
from .reddit import RedditSource
from .rss_feeds import RSSFeedSource
from .twitter import TwitterSource
from .yfinance import YFinanceSource
from .youtube import YouTubeSource

__all__ = [
    # Paid/API sources
    "RedditSource",
    "TwitterSource",
    "NewsAPISource",
    "YouTubeSource",
    "GitHubSource",
    "GoogleSearchSource",
    # Free sources
    "GoogleTrendsSource",
    "GoogleNewsSource",
    "RSSFeedSource",
    "YFinanceSource",
    "HackerNewsSource",
]
