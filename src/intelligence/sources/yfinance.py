"""
Yahoo Finance data source for market intelligence (NO API KEY REQUIRED).
Uses yfinance to track market trends, sector performance, and emerging industries.
"""

from datetime import datetime
from typing import Any, Dict, List

try:
    import yfinance as yf
except ImportError:
    yf = None

from loguru import logger

from ..base import DataSource


class YFinanceSource(DataSource):
    """Collect market trend data from Yahoo Finance."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Yahoo Finance source."""
        super().__init__(config)

        # Track technology and SaaS-related companies
        self.tickers = config.get("tickers", [
            # Major tech/cloud
            "MSFT", "GOOGL", "AMZN", "META", "AAPL",
            # SaaS companies
            "CRM", "NOW", "WDAY", "TEAM", "ZM", "DDOG", "SNOW",
            # Developer tools
            "GTLB", "MDB", "NET", "CFLT",
            # Productivity
            "MNDY", "ASNA", "ZI",
            # ETFs for sectors
            "XLK",  # Technology sector
            "WCLD", # Cloud computing
            "SKYY", # Cloud computing
        ])

        self.period = config.get("period", "3mo")  # Last 3 months
        self.analyze_news = config.get("analyze_news", True)

        if yf is None:
            logger.warning("yfinance package not installed. Install with: pip install yfinance")
            self.enabled = False

    async def collect(self) -> List[Dict[str, Any]]:
        """Collect market data from Yahoo Finance."""
        if not self.enabled or yf is None:
            logger.info("Yahoo Finance source is disabled or not configured")
            return []

        results = []
        logger.info(f"Collecting Yahoo Finance data for {len(self.tickers)} tickers...")

        for ticker_symbol in self.tickers:
            try:
                ticker = yf.Ticker(ticker_symbol)

                # Get company info
                info = ticker.info

                # Get historical data
                hist = ticker.history(period=self.period)

                if not hist.empty:
                    # Calculate trend
                    start_price = hist['Close'].iloc[0]
                    end_price = hist['Close'].iloc[-1]
                    price_change_pct = ((end_price - start_price) / start_price) * 100

                    # Get average volume
                    avg_volume = hist['Volume'].mean()

                    results.append({
                        "source": "yfinance",
                        "type": "stock_trend",
                        "ticker": ticker_symbol,
                        "company_name": info.get('longName', ticker_symbol),
                        "sector": info.get('sector', ''),
                        "industry": info.get('industry', ''),
                        "price_change_pct": float(price_change_pct),
                        "current_price": float(end_price),
                        "market_cap": info.get('marketCap', 0),
                        "avg_volume": float(avg_volume),
                        "trend": "rising" if price_change_pct > 0 else "falling",
                        "description": info.get('longBusinessSummary', ''),
                        "timestamp": datetime.now().isoformat(),
                    })

                # Get recent news
                if self.analyze_news:
                    try:
                        news = ticker.news
                        for article in news[:5]:  # Top 5 news items
                            results.append({
                                "source": "yfinance",
                                "type": "company_news",
                                "ticker": ticker_symbol,
                                "company_name": info.get('longName', ticker_symbol),
                                "title": article.get('title', ''),
                                "publisher": article.get('publisher', ''),
                                "url": article.get('link', ''),
                                "published": datetime.fromtimestamp(article.get('providerPublishTime', 0)).isoformat(),
                                "timestamp": datetime.now().isoformat(),
                            })
                    except Exception as e:
                        logger.debug(f"No news available for {ticker_symbol}: {e}")

            except Exception as e:
                logger.warning(f"Failed to fetch data for {ticker_symbol}: {e}")

        logger.info(f"Collected {len(results)} Yahoo Finance data points")
        return results
