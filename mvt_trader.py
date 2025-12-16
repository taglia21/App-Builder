"""
OTREP-X PRIME - MVT Trader Module
Phase III: Multi-Variable Trading System with HybridStrategy

This module provides the main trading interface that integrates
the HybridStrategy with data feeds and execution management.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import yaml
import pandas as pd

from strategy.momentum import HybridStrategy
from api.polygon_client import PolygonClient

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """
    Configuration dataclass for MVTTrader.
    
    Contains all trading, strategy, and data parameters
    loaded from config.yaml.
    """
    # Trading parameters
    symbols: List[str] = field(default_factory=lambda: ['SPY', 'QQQ', 'IWM'])
    capital: float = 100000.0
    max_position_size: float = 0.1
    stop_loss: float = 0.02
    take_profit: float = 0.04
    
    # Strategy parameters
    timeframe: str = '5Min'
    momentum_lookback: int = 20
    signal_threshold: float = 0.15
    neutral_threshold: float = 0.05
    
    # Signal weights
    momentum_weight: float = 0.5
    mean_reversion_weight: float = 0.5  # Replaces trend_weight
    
    # Mean Reversion parameters
    mean_reversion_enabled: bool = True
    mr_lookback: int = 20
    bb_std_dev_multiplier: float = 2.0
    reversion_threshold: float = 0.01
    
    # Adaptive parameters
    adaptive_enabled: bool = True
    volatility_scaling: bool = True
    min_volatility: float = 0.005
    max_volatility: float = 0.05
    regime_detection: bool = True
    regime_lookback: int = 50
    high_vol_threshold: float = 0.03
    low_vol_threshold: float = 0.01
    
    # Data parameters
    data_provider: str = 'polygon'
    cache_enabled: bool = True
    cache_ttl: int = 3600
    
    # Backtest parameters
    backtest_start_date: str = '2024-06-01'
    backtest_end_date: str = '2024-12-01'
    commission: float = 0.001
    slippage: float = 0.0005
    
    # Risk management
    max_drawdown: float = 0.15
    daily_loss_limit: float = 0.03
    
    @classmethod
    def from_yaml(cls, config_path: str = 'config.yaml') -> 'Config':
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to the YAML configuration file
        
        Returns:
            Config instance with loaded parameters
        """
        if not os.path.exists(config_path):
            logger.warning(f"Config file not found: {config_path}. Using defaults.")
            return cls()
        
        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        trading = raw_config.get('TRADING', {})
        strategy = raw_config.get('STRATEGY', {})
        weights = strategy.get('SIGNAL_WEIGHTS', {})
        mr_config = strategy.get('MEAN_REVERSION', {})
        adaptive = strategy.get('ADAPTIVE', {})
        data = raw_config.get('DATA', {})
        backtest = raw_config.get('BACKTEST', {})
        risk = raw_config.get('RISK_MANAGEMENT', {})
        
        return cls(
            # Trading
            symbols=trading.get('SYMBOLS', ['SPY', 'QQQ', 'IWM']),
            capital=trading.get('CAPITAL', 100000.0),
            max_position_size=trading.get('MAX_POSITION_SIZE', 0.1),
            stop_loss=trading.get('STOP_LOSS', 0.02),
            take_profit=trading.get('TAKE_PROFIT', 0.04),
            
            # Strategy
            timeframe=strategy.get('TIMEFRAME', '5Min'),
            momentum_lookback=strategy.get('MOMENTUM_LOOKBACK', 20),
            signal_threshold=strategy.get('SIGNAL_THRESHOLD', 0.15),
            neutral_threshold=strategy.get('NEUTRAL_THRESHOLD', 0.05),
            
            # Weights
            momentum_weight=weights.get('MOMENTUM', 0.5),
            mean_reversion_weight=weights.get('MEAN_REVERSION', 0.5),
            
            # Mean Reversion
            mean_reversion_enabled=mr_config.get('ENABLED', True),
            mr_lookback=mr_config.get('LOOKBACK', 20),
            bb_std_dev_multiplier=mr_config.get('BB_STD_DEV_MULTIPLIER', 2.0),
            reversion_threshold=mr_config.get('REVERSION_THRESHOLD', 0.01),
            
            # Adaptive
            adaptive_enabled=adaptive.get('ENABLED', True),
            volatility_scaling=adaptive.get('VOLATILITY_SCALING', True),
            min_volatility=adaptive.get('MIN_VOLATILITY', 0.005),
            max_volatility=adaptive.get('MAX_VOLATILITY', 0.05),
            regime_detection=adaptive.get('REGIME_DETECTION', True),
            regime_lookback=adaptive.get('REGIME_LOOKBACK', 50),
            high_vol_threshold=adaptive.get('HIGH_VOL_THRESHOLD', 0.03),
            low_vol_threshold=adaptive.get('LOW_VOL_THRESHOLD', 0.01),
            
            # Data
            data_provider=data.get('PROVIDER', 'polygon'),
            cache_enabled=data.get('CACHE_ENABLED', True),
            cache_ttl=data.get('CACHE_TTL', 3600),
            
            # Backtest
            backtest_start_date=backtest.get('START_DATE', '2024-06-01'),
            backtest_end_date=backtest.get('END_DATE', '2024-12-01'),
            commission=backtest.get('COMMISSION', 0.001),
            slippage=backtest.get('SLIPPAGE', 0.0005),
            
            # Risk
            max_drawdown=risk.get('MAX_DRAWDOWN', 0.15),
            daily_loss_limit=risk.get('DAILY_LOSS_LIMIT', 0.03)
        )
    
    def to_dict(self) -> Dict:
        """Convert config to dictionary."""
        return {
            'symbols': self.symbols,
            'capital': self.capital,
            'timeframe': self.timeframe,
            'momentum_lookback': self.momentum_lookback,
            'momentum_weight': self.momentum_weight,
            'mean_reversion_weight': self.mean_reversion_weight,
            'mean_reversion_enabled': self.mean_reversion_enabled,
            'mr_lookback': self.mr_lookback,
            'bb_std_dev_multiplier': self.bb_std_dev_multiplier,
            'adaptive_enabled': self.adaptive_enabled
        }


@dataclass
class Position:
    """Container for an open position."""
    symbol: str
    side: str  # 'long' or 'short'
    quantity: int
    entry_price: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0
    
    def update_pnl(self, current_price: float) -> None:
        """Update unrealized P&L."""
        if self.side == 'long':
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity


@dataclass
class TradeSignal:
    """Container for a trade signal."""
    symbol: str
    timestamp: datetime
    signal_value: float
    direction: str  # 'long', 'short', or 'flat'
    strength: float
    momentum_component: float
    mean_reversion_component: Optional[float]
    metadata: Dict = field(default_factory=dict)


class MVTTrader:
    """
    Multi-Variable Trader using HybridStrategy.
    
    This class integrates:
    - HybridStrategy for signal generation
    - PolygonClient for market data
    - Position and risk management
    
    Attributes:
        config: Trading configuration
        strategy: HybridStrategy instance
        data_client: PolygonClient instance
        positions: Currently open positions
    """
    
    def __init__(self, config: Optional[Config] = None, config_path: str = 'config.yaml'):
        """
        Initialize the MVTTrader.
        
        Args:
            config: Config instance (optional)
            config_path: Path to config YAML if config not provided
        """
        # Load configuration
        if config is None:
            self.config = Config.from_yaml(config_path)
        else:
            self.config = config
        
        # Initialize HybridStrategy with configuration
        self.strategy = HybridStrategy(
            # Momentum parameters
            momentum_lookback=self.config.momentum_lookback,
            momentum_weight=self.config.momentum_weight,
            signal_threshold=self.config.signal_threshold,
            neutral_threshold=self.config.neutral_threshold,
            
            # Mean Reversion parameters
            mean_reversion_enabled=self.config.mean_reversion_enabled,
            mr_lookback=self.config.mr_lookback,
            bb_std_dev_multiplier=self.config.bb_std_dev_multiplier,
            mr_weight=self.config.mean_reversion_weight,
            reversion_threshold=self.config.reversion_threshold,
            
            # Adaptive parameters
            adaptive_enabled=self.config.adaptive_enabled,
            volatility_scaling=self.config.volatility_scaling,
            min_volatility=self.config.min_volatility,
            max_volatility=self.config.max_volatility,
            regime_detection=self.config.regime_detection,
            regime_lookback=self.config.regime_lookback,
            high_vol_threshold=self.config.high_vol_threshold,
            low_vol_threshold=self.config.low_vol_threshold
        )
        
        # Initialize data client
        self.data_client = PolygonClient(
            cache_enabled=self.config.cache_enabled,
            cache_ttl=self.config.cache_ttl
        )
        
        # Initialize position tracking
        self.positions: Dict[str, Position] = {}
        self.daily_pnl: float = 0.0
        self.trade_history: List[Dict] = []
        
        logger.info(
            f"MVTTrader initialized: symbols={self.config.symbols}, "
            f"capital={self.config.capital}, timeframe={self.config.timeframe}"
        )
        logger.info(
            f"Strategy config: momentum_weight={self.config.momentum_weight}, "
            f"mean_reversion_weight={self.config.mean_reversion_weight}, "
            f"mean_reversion_enabled={self.config.mean_reversion_enabled}"
        )
    
    def process_symbol(self, symbol: str) -> Optional[TradeSignal]:
        """
        Process a symbol and generate trade signal.
        
        Fetches latest bar data, runs the HybridStrategy,
        and returns the resulting signal.
        
        Args:
            symbol: Stock symbol to process
        
        Returns:
            TradeSignal or None if no signal generated
        """
        logger.debug(f"Processing symbol: {symbol}")
        
        # Calculate lookback period needed
        lookback_bars = max(
            self.config.momentum_lookback,
            self.config.mr_lookback,
            self.config.regime_lookback
        ) + 10  # Add buffer
        
        # Estimate days needed based on timeframe
        if 'Min' in self.config.timeframe:
            bars_per_day = 78  # 5-min bars in trading day
            lookback_days = (lookback_bars // bars_per_day) + 5
        elif 'Hour' in self.config.timeframe:
            bars_per_day = 7  # 1-hour bars in trading day
            lookback_days = (lookback_bars // bars_per_day) + 5
        else:
            lookback_days = lookback_bars + 10
        
        # Fetch recent bars
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days)
        
        try:
            bars_df = self.data_client.get_bars(
                symbol=symbol,
                timeframe=self.config.timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if bars_df.empty or len(bars_df) < lookback_bars:
                logger.warning(
                    f"Insufficient data for {symbol}: "
                    f"got {len(bars_df)}, need {lookback_bars}"
                )
                return None
            
            # Calculate signal
            signal_result = self.strategy.calculate_signal(bars_df)
            
            # Get latest signal value
            latest_signal = signal_result['signal'].iloc[-1]
            momentum_signal = signal_result['momentum_signal'].iloc[-1]
            mr_signal = (
                signal_result['mean_reversion_signal'].iloc[-1]
                if signal_result['mean_reversion_signal'] is not None
                else None
            )
            
            # Determine direction
            if latest_signal >= self.config.signal_threshold:
                direction = 'long'
            elif latest_signal <= -self.config.signal_threshold:
                direction = 'short'
            else:
                direction = 'flat'
            
            trade_signal = TradeSignal(
                symbol=symbol,
                timestamp=bars_df.index[-1],
                signal_value=latest_signal,
                direction=direction,
                strength=abs(latest_signal),
                momentum_component=momentum_signal,
                mean_reversion_component=mr_signal,
                metadata={
                    'momentum_weight': self.config.momentum_weight,
                    'mean_reversion_weight': self.config.mean_reversion_weight,
                    'close_price': bars_df['close'].iloc[-1],
                    'bars_analyzed': len(bars_df)
                }
            )
            
            logger.info(
                f"Signal for {symbol}: direction={direction}, "
                f"value={latest_signal:.4f}, strength={abs(latest_signal):.4f}"
            )
            
            return trade_signal
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            return None
    
    def process_all_symbols(self) -> List[TradeSignal]:
        """
        Process all configured symbols and generate signals.
        
        Returns:
            List of TradeSignal objects
        """
        signals = []
        
        for symbol in self.config.symbols:
            signal = self.process_symbol(symbol)
            if signal is not None:
                signals.append(signal)
        
        # Sort by signal strength (strongest first)
        signals.sort(key=lambda x: x.strength, reverse=True)
        
        return signals
    
    def calculate_position_size(
        self,
        signal: TradeSignal,
        current_price: float
    ) -> int:
        """
        Calculate position size based on signal and risk parameters.
        
        Args:
            signal: TradeSignal object
            current_price: Current price of the symbol
        
        Returns:
            Number of shares to trade
        """
        # Base position size (fraction of capital)
        base_allocation = self.config.capital * self.config.max_position_size
        
        # Scale by signal strength
        scaled_allocation = base_allocation * signal.strength
        
        # Calculate shares
        shares = int(scaled_allocation / current_price)
        
        # Apply minimum and maximum constraints
        max_shares = int(self.config.capital * 0.25 / current_price)
        shares = min(shares, max_shares)
        shares = max(shares, 1)
        
        return shares
    
    def open_position(self, signal: TradeSignal) -> Optional[Position]:
        """
        Open a new position based on signal.
        
        Args:
            signal: TradeSignal object
        
        Returns:
            Position object or None if position couldn't be opened
        """
        if signal.direction == 'flat':
            return None
        
        if signal.symbol in self.positions:
            logger.warning(f"Position already exists for {signal.symbol}")
            return None
        
        current_price = signal.metadata.get('close_price', 0)
        if current_price <= 0:
            logger.error(f"Invalid price for {signal.symbol}")
            return None
        
        # Calculate position size
        quantity = self.calculate_position_size(signal, current_price)
        
        # Calculate stop loss and take profit
        if signal.direction == 'long':
            stop_loss = current_price * (1 - self.config.stop_loss)
            take_profit = current_price * (1 + self.config.take_profit)
        else:
            stop_loss = current_price * (1 + self.config.stop_loss)
            take_profit = current_price * (1 - self.config.take_profit)
        
        position = Position(
            symbol=signal.symbol,
            side=signal.direction,
            quantity=quantity,
            entry_price=current_price,
            entry_time=signal.timestamp,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        self.positions[signal.symbol] = position
        
        logger.info(
            f"Opened {signal.direction} position: {signal.symbol} "
            f"@ {current_price:.2f} x {quantity} shares"
        )
        
        return position
    
    def close_position(
        self,
        symbol: str,
        exit_price: float,
        reason: str = 'signal'
    ) -> Optional[Dict]:
        """
        Close an existing position.
        
        Args:
            symbol: Symbol to close
            exit_price: Exit price
            reason: Reason for closing
        
        Returns:
            Trade result dictionary or None
        """
        if symbol not in self.positions:
            logger.warning(f"No position to close for {symbol}")
            return None
        
        position = self.positions.pop(symbol)
        
        # Calculate P&L
        if position.side == 'long':
            pnl = (exit_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - exit_price) * position.quantity
        
        # Apply commission
        commission = (position.entry_price + exit_price) * position.quantity * self.config.commission
        net_pnl = pnl - commission
        
        self.daily_pnl += net_pnl
        
        trade_result = {
            'symbol': symbol,
            'side': position.side,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'quantity': position.quantity,
            'pnl': net_pnl,
            'commission': commission,
            'entry_time': position.entry_time,
            'exit_time': datetime.now(),
            'reason': reason
        }
        
        self.trade_history.append(trade_result)
        
        logger.info(
            f"Closed {position.side} position: {symbol} "
            f"@ {exit_price:.2f}, P&L: ${net_pnl:.2f}"
        )
        
        return trade_result
    
    def check_risk_limits(self) -> bool:
        """
        Check if risk limits have been breached.
        
        Returns:
            True if limits are OK, False if breached
        """
        # Check daily loss limit
        if self.daily_pnl < -self.config.capital * self.config.daily_loss_limit:
            logger.warning(
                f"Daily loss limit breached: ${self.daily_pnl:.2f} "
                f"(limit: ${-self.config.capital * self.config.daily_loss_limit:.2f})"
            )
            return False
        
        return True
    
    def get_portfolio_status(self) -> Dict:
        """
        Get current portfolio status.
        
        Returns:
            Dictionary with portfolio metrics
        """
        total_exposure = sum(
            p.entry_price * p.quantity
            for p in self.positions.values()
        )
        
        total_unrealized_pnl = sum(
            p.unrealized_pnl for p in self.positions.values()
        )
        
        return {
            'capital': self.config.capital,
            'open_positions': len(self.positions),
            'total_exposure': total_exposure,
            'exposure_pct': (total_exposure / self.config.capital) * 100,
            'unrealized_pnl': total_unrealized_pnl,
            'daily_pnl': self.daily_pnl,
            'total_trades': len(self.trade_history),
            'positions': {
                symbol: {
                    'side': pos.side,
                    'quantity': pos.quantity,
                    'entry_price': pos.entry_price,
                    'unrealized_pnl': pos.unrealized_pnl
                }
                for symbol, pos in self.positions.items()
            }
        }
    
    def run_once(self) -> Dict[str, Any]:
        """
        Run a single iteration of the trading loop.
        
        Returns:
            Dictionary with results
        """
        logger.info("Running trading iteration...")
        
        # Check risk limits
        if not self.check_risk_limits():
            logger.warning("Risk limits breached, skipping iteration")
            return {'status': 'risk_limit_breached'}
        
        # Process all symbols
        signals = self.process_all_symbols()
        
        # Generate trading actions
        actions = []
        for signal in signals:
            if signal.direction != 'flat':
                if signal.symbol not in self.positions:
                    # Open new position
                    position = self.open_position(signal)
                    if position:
                        actions.append({
                            'action': 'open',
                            'symbol': signal.symbol,
                            'direction': signal.direction
                        })
                else:
                    # Check if signal direction matches position
                    existing = self.positions[signal.symbol]
                    if existing.side != signal.direction:
                        # Close existing and open new
                        self.close_position(
                            signal.symbol,
                            signal.metadata.get('close_price', existing.entry_price),
                            'signal_reversal'
                        )
                        position = self.open_position(signal)
                        if position:
                            actions.append({
                                'action': 'reverse',
                                'symbol': signal.symbol,
                                'direction': signal.direction
                            })
        
        return {
            'status': 'ok',
            'signals': len(signals),
            'actions': actions,
            'portfolio': self.get_portfolio_status()
        }


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("OTREP-X PRIME - MVT Trader")
    print("=" * 60)
    
    # Initialize trader
    trader = MVTTrader(config_path='config.yaml')
    
    print(f"\nConfiguration:")
    print(f"  Symbols: {trader.config.symbols}")
    print(f"  Capital: ${trader.config.capital:,.2f}")
    print(f"  Timeframe: {trader.config.timeframe}")
    print(f"  Momentum Weight: {trader.config.momentum_weight}")
    print(f"  Mean Reversion Weight: {trader.config.mean_reversion_weight}")
    print(f"  Mean Reversion Enabled: {trader.config.mean_reversion_enabled}")
    
    print("\nRunning single iteration...")
    print("-" * 60)
    
    result = trader.run_once()
    
    print("\nResults:")
    print(f"  Status: {result['status']}")
    print(f"  Signals Generated: {result.get('signals', 0)}")
    print(f"  Actions Taken: {len(result.get('actions', []))}")
    
    if result.get('actions'):
        print("\n  Actions:")
        for action in result['actions']:
            print(f"    - {action['action'].upper()}: {action['symbol']} ({action['direction']})")
    
    portfolio = result.get('portfolio', {})
    print(f"\n  Portfolio Status:")
    print(f"    Open Positions: {portfolio.get('open_positions', 0)}")
    print(f"    Total Exposure: ${portfolio.get('total_exposure', 0):,.2f}")
    print(f"    Exposure %: {portfolio.get('exposure_pct', 0):.1f}%")
    
    print("\n" + "=" * 60)
