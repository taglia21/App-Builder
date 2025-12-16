"""
OTREP-X PRIME - Polygon.io Data Client
Phase III: Historical Data Provider for Backtesting and Live Trading

This module provides a client for fetching market data from Polygon.io API.
Supports both real-time and historical bar data for backtesting and optimization.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import pandas as pd
import requests
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TimeFrame(Enum):
    """Supported timeframes for bar data."""
    MIN_1 = '1Min'
    MIN_5 = '5Min'
    MIN_15 = '15Min'
    MIN_30 = '30Min'
    HOUR_1 = '1Hour'
    HOUR_4 = '4Hour'
    DAY_1 = '1Day'
    WEEK_1 = '1Week'


@dataclass
class BarData:
    """Container for OHLCV bar data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None
    transactions: Optional[int] = None


class PolygonClient:
    """
    Client for Polygon.io Market Data API.
    
    Provides methods for fetching historical and real-time bar data
    for equities, options, forex, and crypto.
    
    Attributes:
        api_key: Polygon.io API key
        base_url: API base URL
        cache_enabled: Whether to cache responses
        cache_ttl: Cache time-to-live in seconds
    """
    
    BASE_URL = "https://api.polygon.io"
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_enabled: bool = True,
        cache_ttl: int = 3600
    ):
        """
        Initialize the Polygon client.
        
        Args:
            api_key: Polygon.io API key. If None, reads from POLYGON_API_KEY env var.
            cache_enabled: Enable response caching
            cache_ttl: Cache time-to-live in seconds
        """
        self.api_key = api_key or os.getenv('POLYGON_API_KEY')
        if not self.api_key:
            logger.warning(
                "No Polygon API key provided. Set POLYGON_API_KEY environment variable "
                "or pass api_key parameter. Using demo mode with limited data."
            )
            self._demo_mode = True
        else:
            self._demo_mode = False
        
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple] = {}  # {key: (data, timestamp)}
        
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json'
        })
        
        logger.info(
            f"PolygonClient initialized: demo_mode={self._demo_mode}, "
            f"cache_enabled={cache_enabled}"
        )
    
    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate a cache key from endpoint and parameters."""
        param_str = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{endpoint}?{param_str}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Retrieve data from cache if valid."""
        if not self.cache_enabled:
            return None
        
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                logger.debug(f"Cache hit: {cache_key[:50]}...")
                return data.copy()
        
        return None
    
    def _set_cache(self, cache_key: str, data: pd.DataFrame) -> None:
        """Store data in cache."""
        if self.cache_enabled:
            self._cache[cache_key] = (data.copy(), datetime.now())
    
    def _parse_timeframe(self, timeframe: str) -> tuple:
        """
        Parse timeframe string into multiplier and timespan.
        
        Args:
            timeframe: Timeframe string (e.g., '5Min', '1Hour', '1Day')
        
        Returns:
            Tuple of (multiplier, timespan)
        """
        timeframe = timeframe.strip()
        
        # Parse common formats
        timeframe_map = {
            '1Min': (1, 'minute'),
            '5Min': (5, 'minute'),
            '15Min': (15, 'minute'),
            '30Min': (30, 'minute'),
            '1Hour': (1, 'hour'),
            '4Hour': (4, 'hour'),
            '1Day': (1, 'day'),
            '1Week': (1, 'week'),
        }
        
        if timeframe in timeframe_map:
            return timeframe_map[timeframe]
        
        # Try to parse custom format
        import re
        match = re.match(r'(\d+)(\w+)', timeframe)
        if match:
            multiplier = int(match.group(1))
            unit = match.group(2).lower()
            
            unit_map = {
                'min': 'minute',
                'minute': 'minute',
                'h': 'hour',
                'hour': 'hour',
                'd': 'day',
                'day': 'day',
                'w': 'week',
                'week': 'week'
            }
            
            timespan = unit_map.get(unit)
            if timespan:
                return (multiplier, timespan)
        
        raise ValueError(f"Invalid timeframe format: {timeframe}")
    
    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Make an API request to Polygon.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
        
        Returns:
            JSON response as dictionary
        
        Raises:
            requests.HTTPError: On API error
        """
        params = params or {}
        params['apiKey'] = self.api_key
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def _generate_demo_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str
    ) -> pd.DataFrame:
        """
        Generate synthetic demo data for testing without API key.
        
        Args:
            symbol: Stock symbol
            start_date: Start date
            end_date: End date
            timeframe: Timeframe string
        
        Returns:
            DataFrame with synthetic OHLCV data
        """
        import numpy as np
        
        logger.info(f"Generating demo data for {symbol} ({start_date} to {end_date})")
        
        # Determine frequency
        multiplier, timespan = self._parse_timeframe(timeframe)
        
        freq_map = {
            'minute': f'{multiplier}min',
            'hour': f'{multiplier}h',
            'day': f'{multiplier}D',
            'week': f'{multiplier}W'
        }
        freq = freq_map.get(timespan, '5min')
        
        # Generate date range (market hours only for intraday)
        if timespan in ['minute', 'hour']:
            # Generate business days
            dates = pd.date_range(
                start=start_date,
                end=end_date,
                freq='B'  # Business days
            )
            
            # Generate intraday timestamps
            all_timestamps = []
            for date in dates:
                market_open = date.replace(hour=9, minute=30)
                market_close = date.replace(hour=16, minute=0)
                day_timestamps = pd.date_range(
                    start=market_open,
                    end=market_close,
                    freq=freq
                )
                all_timestamps.extend(day_timestamps)
            
            index = pd.DatetimeIndex(all_timestamps)
        else:
            index = pd.date_range(start=start_date, end=end_date, freq=freq)
        
        if len(index) == 0:
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        # Generate synthetic price data using geometric Brownian motion
        np.random.seed(hash(symbol) % (2**32))
        
        # Starting price based on symbol (for reproducibility)
        symbol_prices = {
            'SPY': 450.0,
            'QQQ': 380.0,
            'IWM': 200.0,
            'AAPL': 175.0,
            'MSFT': 380.0,
            'GOOGL': 140.0,
            'AMZN': 180.0,
            'META': 500.0,
        }
        start_price = symbol_prices.get(symbol, 100.0)
        
        # Parameters for GBM
        mu = 0.0001  # drift (small positive)
        sigma = 0.02  # volatility
        
        n = len(index)
        dt = 1  # time step
        
        # Generate returns
        returns = np.random.normal(mu * dt, sigma * np.sqrt(dt), n)
        
        # Add some mean reversion tendency
        mean_reversion_strength = 0.01
        price_series = [start_price]
        for i in range(1, n):
            prev_price = price_series[-1]
            deviation = (prev_price - start_price) / start_price
            reversion = -mean_reversion_strength * deviation
            new_price = prev_price * (1 + returns[i] + reversion)
            price_series.append(max(new_price, 1.0))  # Ensure positive price
        
        close_prices = np.array(price_series)
        
        # Generate OHLV from close
        intraday_vol = 0.005
        open_prices = close_prices * (1 + np.random.normal(0, intraday_vol, n))
        high_prices = np.maximum(open_prices, close_prices) * (1 + abs(np.random.normal(0, intraday_vol, n)))
        low_prices = np.minimum(open_prices, close_prices) * (1 - abs(np.random.normal(0, intraday_vol, n)))
        
        # Generate volume
        base_volume = 1000000
        volume = np.random.poisson(base_volume, n).astype(float)
        volume *= (1 + abs(returns) * 10)  # Higher volume on bigger moves
        
        df = pd.DataFrame({
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volume.astype(int)
        }, index=index)
        
        return df
    
    def get_bars(
        self,
        symbol: str,
        timeframe: str = '5Min',
        start_date: Optional[Union[str, datetime]] = None,
        end_date: Optional[Union[str, datetime]] = None,
        limit: int = 5000
    ) -> pd.DataFrame:
        """
        Fetch historical bar data for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'SPY', 'AAPL')
            timeframe: Bar timeframe ('1Min', '5Min', '1Hour', '1Day', etc.)
            start_date: Start date (string 'YYYY-MM-DD' or datetime)
            end_date: End date (string 'YYYY-MM-DD' or datetime)
            limit: Maximum number of bars to return
        
        Returns:
            DataFrame with columns: open, high, low, close, volume
            Index: DatetimeIndex
        """
        # Parse dates
        if isinstance(start_date, str):
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        elif start_date is None:
            start_dt = datetime.now() - timedelta(days=30)
        else:
            start_dt = start_date
        
        if isinstance(end_date, str):
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        elif end_date is None:
            end_dt = datetime.now()
        else:
            end_dt = end_date
        
        # Check cache
        cache_key = self._get_cache_key(
            f"/v2/aggs/ticker/{symbol}",
            {
                'timeframe': timeframe,
                'from': start_dt.strftime('%Y-%m-%d'),
                'to': end_dt.strftime('%Y-%m-%d'),
                'limit': limit
            }
        )
        
        cached_data = self._get_from_cache(cache_key)
        if cached_data is not None:
            return cached_data
        
        # Use demo data if no API key
        if self._demo_mode:
            df = self._generate_demo_data(symbol, start_dt, end_dt, timeframe)
            self._set_cache(cache_key, df)
            return df
        
        # Parse timeframe
        multiplier, timespan = self._parse_timeframe(timeframe)
        
        # Make API request
        endpoint = f"/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{start_dt.strftime('%Y-%m-%d')}/{end_dt.strftime('%Y-%m-%d')}"
        
        params = {
            'adjusted': 'true',
            'sort': 'asc',
            'limit': limit
        }
        
        try:
            response = self._make_request(endpoint, params)
            
            if response.get('resultsCount', 0) == 0:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            
            results = response.get('results', [])
            
            # Convert to DataFrame
            df = pd.DataFrame(results)
            
            # Rename columns to standard format
            column_map = {
                't': 'timestamp',
                'o': 'open',
                'h': 'high',
                'l': 'low',
                'c': 'close',
                'v': 'volume',
                'vw': 'vwap',
                'n': 'transactions'
            }
            df = df.rename(columns=column_map)
            
            # Convert timestamp to datetime index
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            
            # Select standard columns
            standard_cols = ['open', 'high', 'low', 'close', 'volume']
            df = df[[col for col in standard_cols if col in df.columns]]
            
            # Cache the result
            self._set_cache(cache_key, df)
            
            logger.info(f"Fetched {len(df)} bars for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch bars for {symbol}: {e}")
            raise
    
    def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        Fetch historical bar data for backtesting.
        
        This method is specifically designed for backtesting and optimization.
        It fetches the complete historical data for the specified date range.
        
        Args:
            symbol: Stock symbol (e.g., 'SPY')
            timeframe: Bar timeframe (e.g., '5Min', '1Hour', '1Day')
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
        
        Returns:
            pd.DataFrame with DateTime index and columns:
                - open: Opening price
                - high: High price
                - low: Low price
                - close: Closing price
                - volume: Trading volume
        
        Example:
            >>> client = PolygonClient()
            >>> df = client.get_historical_data('SPY', '5Min', '2024-06-01', '2024-12-01')
            >>> print(df.head())
        """
        logger.info(
            f"Fetching historical data: symbol={symbol}, timeframe={timeframe}, "
            f"start={start_date}, end={end_date}"
        )
        
        # Parse dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # For long date ranges, we may need to paginate
        # Polygon API has limits on the number of results per request
        all_data = []
        current_start = start_dt
        
        # Calculate chunk size based on timeframe
        multiplier, timespan = self._parse_timeframe(timeframe)
        
        if timespan == 'minute':
            # For minute data, fetch in weekly chunks
            chunk_days = 7
        elif timespan == 'hour':
            # For hourly data, fetch in monthly chunks
            chunk_days = 30
        else:
            # For daily/weekly, fetch all at once
            chunk_days = (end_dt - start_dt).days + 1
        
        while current_start < end_dt:
            chunk_end = min(current_start + timedelta(days=chunk_days), end_dt)
            
            chunk_data = self.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                start_date=current_start,
                end_date=chunk_end,
                limit=50000
            )
            
            if not chunk_data.empty:
                all_data.append(chunk_data)
            
            current_start = chunk_end + timedelta(days=1)
        
        if not all_data:
            logger.warning(f"No historical data found for {symbol}")
            return pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        
        # Concatenate all chunks
        df = pd.concat(all_data)
        
        # Remove duplicates and sort
        df = df[~df.index.duplicated(keep='first')]
        df = df.sort_index()
        
        # Ensure proper column types
        df = df.astype({
            'open': float,
            'high': float,
            'low': float,
            'close': float,
            'volume': int
        })
        
        logger.info(
            f"Historical data loaded: {len(df)} bars from "
            f"{df.index.min()} to {df.index.max()}"
        )
        
        return df
    
    def get_latest_bar(self, symbol: str, timeframe: str = '5Min') -> Optional[pd.Series]:
        """
        Get the most recent bar for a symbol.
        
        Args:
            symbol: Stock symbol
            timeframe: Bar timeframe
        
        Returns:
            Series with OHLCV data or None if not available
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)
        
        df = self.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            limit=1
        )
        
        if df.empty:
            return None
        
        return df.iloc[-1]
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get the latest quote for a symbol.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            Dict with bid/ask data or None
        """
        if self._demo_mode:
            # Generate demo quote
            import random
            price = random.uniform(100, 500)
            spread = price * 0.001
            return {
                'symbol': symbol,
                'bid': price - spread / 2,
                'ask': price + spread / 2,
                'bid_size': random.randint(100, 1000),
                'ask_size': random.randint(100, 1000),
                'timestamp': datetime.now()
            }
        
        try:
            endpoint = f"/v2/last/nbbo/{symbol}"
            response = self._make_request(endpoint)
            
            result = response.get('results', {})
            return {
                'symbol': symbol,
                'bid': result.get('P', 0),
                'ask': result.get('p', 0),
                'bid_size': result.get('S', 0),
                'ask_size': result.get('s', 0),
                'timestamp': datetime.now()
            }
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        logger.info("Cache cleared")
