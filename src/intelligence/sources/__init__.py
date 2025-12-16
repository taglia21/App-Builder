"""
Sources package initialization.
"""

# Paid/API-key required sources
from .github import GitHubSource
from .google_search import GoogleSearchSource
from .newsapi import NewsAPISource
from .reddit import RedditSource
from .twitter import TwitterSource
from .youtube import YouTubeSource

# Free sources (NO API KEY REQUIRED)
from .google_news import GoogleNewsSource
from .google_trends import GoogleTrendsSource
from .hackernews import HackerNewsSource
from .rss_feeds import RSSFeedSource
from .yfinance import YFinanceSource

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
