"""Intelligence collectors for all data sources."""

try:
    from src.intelligence.collectors.reddit_playwright import RedditPlaywrightCollector
except ImportError:
    RedditPlaywrightCollector = None

try:
    from src.intelligence.collectors.github_collector import GitHubCollector
except ImportError:
    GitHubCollector = None

try:
    from src.intelligence.collectors.news_collector import NewsCollector
except ImportError:
    NewsCollector = None

try:
    from src.intelligence.collectors.search_collector import SearchCollector
except ImportError:
    SearchCollector = None

__all__ = ['RedditPlaywrightCollector', 'GitHubCollector', 'NewsCollector', 'SearchCollector']
