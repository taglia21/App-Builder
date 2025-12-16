"""
OTREP-X PRIME - Backtesting Module
Phase III: SimpleBacktester with Optimization Walk-Forward Logic

This module provides backtesting functionality for the HybridStrategy,
including parameter optimization using grid search over historical data.
"""

import itertools
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from strategy.momentum import HybridStrategy
from api.polygon_client import PolygonClient

logger = logging.getLogger(__name__)


@dataclass
class TradeResult:
    """Container for a single trade result."""
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_pct: float
    commission: float


@dataclass
class BacktestResult:
    """Container for backtest results."""
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float
    win_rate: float
    total_trades: int
    profitable_trades: int
    avg_trade_pnl: float
    avg_trade_duration: timedelta
    trades: List[TradeResult]
    equity_curve: pd.Series
    parameters: Dict
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'total_return': self.total_return,
            'total_return_pct': self.total_return_pct,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'win_rate': self.win_rate,
            'total_trades': self.total_trades,
            'profitable_trades': self.profitable_trades,
            'avg_trade_pnl': self.avg_trade_pnl,
            'parameters': self.parameters
        }


class SimpleBacktester:
    """
    Simple vectorized backtester for the HybridStrategy.
    
    This backtester uses vectorized operations for performance and
    supports position-based P&L calculation with transaction costs.
    
    Attributes:
        strategy: HybridStrategy instance
        initial_capital: Starting capital
        commission: Commission rate (as decimal)
        slippage: Slippage rate (as decimal)
    """
    
    def __init__(
        self,
        strategy: HybridStrategy,
        initial_capital: float = 100000.0,
        commission: float = 0.001,
        slippage: float = 0.0005
    ):
        """
        Initialize the backtester.
        
        Args:
            strategy: HybridStrategy instance
            initial_capital: Starting capital
            commission: Commission rate (e.g., 0.001 = 0.1%)
            slippage: Slippage rate (e.g., 0.0005 = 0.05%)
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        
        logger.info(
            f"SimpleBacktester initialized: capital={initial_capital}, "
            f"commission={commission}, slippage={slippage}"
        )
    
    def run(self, bars_df: pd.DataFrame, symbol: str = 'UNKNOWN') -> BacktestResult:
        """
        Run backtest on historical data.
        
        Args:
            bars_df: DataFrame with OHLCV data
            symbol: Symbol being tested
        
        Returns:
            BacktestResult with performance metrics
        """
        if bars_df.empty:
            raise ValueError("Input DataFrame is empty")
        
        # Calculate signals
        signal_result = self.strategy.calculate_signal(bars_df)
        signals = signal_result['signal']
        
        # Generate positions from signals
        positions = self.strategy.generate_positions(bars_df)
        
        # Calculate returns
        returns = bars_df['close'].pct_change()
        
        # Calculate strategy returns (position * next period return)
        # Shift positions by 1 to avoid look-ahead bias
        shifted_positions = positions.shift(1).fillna(0)
        strategy_returns = shifted_positions * returns
        
        # Apply transaction costs
        position_changes = shifted_positions.diff().abs().fillna(0)
        transaction_costs = position_changes * (self.commission + self.slippage)
        net_returns = strategy_returns - transaction_costs
        
        # Calculate equity curve
        equity_curve = self.initial_capital * (1 + net_returns).cumprod()
        equity_curve = equity_curve.fillna(self.initial_capital)
        
        # Calculate performance metrics
        final_capital = equity_curve.iloc[-1]
        total_return = final_capital - self.initial_capital
        total_return_pct = (final_capital / self.initial_capital - 1) * 100
        
        # Sharpe Ratio (annualized)
        # Assume 252 trading days, ~78 5-min bars per day
        periods_per_year = 252 * 78  # For 5-min bars
        if len(net_returns) > 1 and net_returns.std() > 0:
            sharpe_ratio = (
                net_returns.mean() / net_returns.std() * 
                np.sqrt(periods_per_year)
            )
        else:
            sharpe_ratio = 0.0
        
        # Maximum Drawdown
        rolling_max = equity_curve.expanding().max()
        drawdown = equity_curve - rolling_max
        max_drawdown = drawdown.min()
        max_drawdown_pct = (max_drawdown / rolling_max.max()) * 100 if rolling_max.max() > 0 else 0
        
        # Trade statistics (simplified)
        trades = self._extract_trades(bars_df, positions, symbol)
        total_trades = len(trades)
        profitable_trades = sum(1 for t in trades if t.pnl > 0)
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        avg_trade_pnl = sum(t.pnl for t in trades) / total_trades if total_trades > 0 else 0
        
        # Average trade duration
        if trades:
            avg_duration = sum(
                (t.exit_time - t.entry_time).total_seconds() for t in trades
            ) / total_trades
            avg_trade_duration = timedelta(seconds=avg_duration)
        else:
            avg_trade_duration = timedelta(0)
        
        result = BacktestResult(
            start_date=bars_df.index[0],
            end_date=bars_df.index[-1],
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=abs(max_drawdown),
            max_drawdown_pct=abs(max_drawdown_pct),
            win_rate=win_rate,
            total_trades=total_trades,
            profitable_trades=profitable_trades,
            avg_trade_pnl=avg_trade_pnl,
            avg_trade_duration=avg_trade_duration,
            trades=trades,
            equity_curve=equity_curve,
            parameters=self.strategy.get_parameters()
        )
        
        logger.info(
            f"Backtest complete: Return={total_return_pct:.2f}%, "
            f"Sharpe={sharpe_ratio:.2f}, MaxDD={abs(max_drawdown_pct):.2f}%, "
            f"Trades={total_trades}"
        )
        
        return result
    
    def _extract_trades(
        self,
        bars_df: pd.DataFrame,
        positions: pd.Series,
        symbol: str
    ) -> List[TradeResult]:
        """
        Extract individual trades from position series.
        
        Args:
            bars_df: Price data
            positions: Position series
            symbol: Trading symbol
        
        Returns:
            List of TradeResult objects
        """
        trades = []
        
        # Find position changes
        position_changes = positions.diff().fillna(0)
        
        # Track open position
        current_position = 0
        entry_time = None
        entry_price = None
        entry_size = 0
        
        for timestamp, pos_change in position_changes.items():
            if abs(pos_change) < 0.001:
                continue
            
            current_price = bars_df.loc[timestamp, 'close']
            
            # Opening a position
            if current_position == 0 and pos_change != 0:
                current_position = pos_change
                entry_time = timestamp
                entry_price = current_price * (1 + self.slippage * np.sign(pos_change))
                entry_size = abs(pos_change)
            
            # Closing a position
            elif current_position != 0 and (
                np.sign(pos_change) != np.sign(current_position) or
                abs(current_position + pos_change) < 0.001
            ):
                exit_price = current_price * (1 - self.slippage * np.sign(current_position))
                
                # Calculate P&L
                if current_position > 0:  # Long position
                    pnl_pct = (exit_price - entry_price) / entry_price
                    side = 'long'
                else:  # Short position
                    pnl_pct = (entry_price - exit_price) / entry_price
                    side = 'short'
                
                # Calculate quantity (using initial capital as reference)
                quantity = int((self.initial_capital * entry_size) / entry_price)
                pnl = quantity * (exit_price - entry_price) * np.sign(current_position)
                
                # Subtract commission
                commission = (entry_price + exit_price) * quantity * self.commission
                pnl -= commission
                
                if entry_time is not None:
                    trades.append(TradeResult(
                        entry_time=entry_time,
                        exit_time=timestamp,
                        symbol=symbol,
                        side=side,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        quantity=quantity,
                        pnl=pnl,
                        pnl_pct=pnl_pct * 100,
                        commission=commission
                    ))
                
                current_position = 0
                entry_time = None
                entry_price = None
        
        return trades


def run_backtest(
    bars_df: pd.DataFrame,
    strategy: HybridStrategy,
    initial_capital: float = 100000.0,
    commission: float = 0.001,
    slippage: float = 0.0005,
    symbol: str = 'UNKNOWN'
) -> BacktestResult:
    """
    Convenience function to run a backtest.
    
    Args:
        bars_df: DataFrame with OHLCV data
        strategy: HybridStrategy instance
        initial_capital: Starting capital
        commission: Commission rate
        slippage: Slippage rate
        symbol: Trading symbol
    
    Returns:
        BacktestResult with performance metrics
    """
    backtester = SimpleBacktester(
        strategy=strategy,
        initial_capital=initial_capital,
        commission=commission,
        slippage=slippage
    )
    return backtester.run(bars_df, symbol)


def run_optimization(
    optim_params: Dict[str, List],
    symbol: str = 'SPY',
    timeframe: str = '5Min',
    lookback_months: int = 6,
    initial_capital: float = 100000.0,
    commission: float = 0.001,
    slippage: float = 0.0005
) -> Dict[str, Any]:
    """
    Run parameter optimization using grid search.
    
    This function iterates through all combinations of parameters
    and finds the set that yields the highest Sharpe Ratio.
    
    Args:
        optim_params: Dictionary of parameter names to lists of values
            Example: {
                'momentum_lookback': [10, 20, 30],
                'mr_lookback': [15, 20, 25],
                'bb_std_dev_multiplier': [1.5, 2.0, 2.5]
            }
        symbol: Stock symbol to optimize on
        timeframe: Bar timeframe
        lookback_months: Number of months of historical data
        initial_capital: Starting capital for backtests
        commission: Commission rate
        slippage: Slippage rate
    
    Returns:
        Dict containing:
            - best_params: Dictionary of optimal parameters
            - best_sharpe: The highest Sharpe Ratio achieved
            - all_results: List of all parameter combinations and results
            - total_combinations: Number of combinations tested
    """
    logger.info(f"Starting optimization for {symbol} with {len(optim_params)} parameters")
    
    # Initialize Polygon client and fetch historical data
    client = PolygonClient()
    
    # Calculate date range (6 months lookback)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_months * 30)
    
    logger.info(
        f"Fetching historical data: {start_date.strftime('%Y-%m-%d')} to "
        f"{end_date.strftime('%Y-%m-%d')}"
    )
    
    bars_df = client.get_historical_data(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
    
    if bars_df.empty:
        logger.error("No historical data available for optimization")
        return {
            'best_params': {},
            'best_sharpe': 0.0,
            'all_results': [],
            'total_combinations': 0,
            'error': 'No historical data available'
        }
    
    logger.info(f"Loaded {len(bars_df)} bars for optimization")
    
    # Generate all parameter combinations
    param_names = list(optim_params.keys())
    param_values = [optim_params[name] for name in param_names]
    combinations = list(itertools.product(*param_values))
    
    total_combinations = len(combinations)
    logger.info(f"Testing {total_combinations} parameter combinations")
    
    # Store results
    all_results = []
    best_sharpe = float('-inf')
    best_params = {}
    best_result = None
    
    # Iterate through all combinations
    for i, combo in enumerate(combinations):
        # Create parameter dictionary
        params = dict(zip(param_names, combo))
        
        try:
            # Create strategy with current parameters
            strategy = HybridStrategy(
                momentum_lookback=params.get('momentum_lookback', 20),
                momentum_weight=0.5,
                mean_reversion_enabled=True,
                mr_lookback=params.get('mr_lookback', 20),
                bb_std_dev_multiplier=params.get('bb_std_dev_multiplier', 2.0),
                mr_weight=0.5,
                signal_threshold=params.get('signal_threshold', 0.15),
                neutral_threshold=params.get('neutral_threshold', 0.05)
            )
            
            # Run backtest
            backtester = SimpleBacktester(
                strategy=strategy,
                initial_capital=initial_capital,
                commission=commission,
                slippage=slippage
            )
            
            result = backtester.run(bars_df, symbol)
            
            # Record result
            result_entry = {
                'params': params.copy(),
                'sharpe_ratio': result.sharpe_ratio,
                'total_return_pct': result.total_return_pct,
                'max_drawdown_pct': result.max_drawdown_pct,
                'win_rate': result.win_rate,
                'total_trades': result.total_trades
            }
            all_results.append(result_entry)
            
            # Check if this is the best result
            if result.sharpe_ratio > best_sharpe:
                best_sharpe = result.sharpe_ratio
                best_params = params.copy()
                best_result = result
            
            # Log progress every 10 combinations
            if (i + 1) % 10 == 0 or i == total_combinations - 1:
                logger.info(
                    f"Progress: {i + 1}/{total_combinations} combinations tested. "
                    f"Current best Sharpe: {best_sharpe:.4f}"
                )
        
        except Exception as e:
            logger.warning(f"Failed to test combination {params}: {e}")
            all_results.append({
                'params': params.copy(),
                'sharpe_ratio': float('-inf'),
                'error': str(e)
            })
    
    # Sort results by Sharpe Ratio
    all_results.sort(key=lambda x: x.get('sharpe_ratio', float('-inf')), reverse=True)
    
    logger.info(f"Optimization complete. Best Sharpe Ratio: {best_sharpe:.4f}")
    logger.info(f"Optimal Parameters: {best_params}")
    
    return {
        'best_params': best_params,
        'best_sharpe': best_sharpe,
        'best_result': best_result.to_dict() if best_result else None,
        'all_results': all_results[:10],  # Top 10 results
        'total_combinations': total_combinations
    }


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("OTREP-X PRIME - Phase III: Optimization Walk-Forward")
    print("=" * 60)
    
    # Define optimization parameters
    optim_params = {
        'momentum_lookback': [10, 20, 30],
        'mr_lookback': [15, 20, 25],
        'bb_std_dev_multiplier': [1.5, 2.0, 2.5]
    }
    
    print(f"\nOptimization Parameters:")
    for param, values in optim_params.items():
        print(f"  {param}: {values}")
    
    print(f"\nTotal combinations to test: {np.prod([len(v) for v in optim_params.values()])}")
    print("\nStarting optimization...")
    print("-" * 60)
    
    # Run optimization
    results = run_optimization(
        optim_params=optim_params,
        symbol='SPY',
        timeframe='5Min',
        lookback_months=6,
        initial_capital=100000.0,
        commission=0.001,
        slippage=0.0005
    )
    
    # Display results
    print("\n" + "=" * 60)
    print("OPTIMIZATION RESULTS")
    print("=" * 60)
    
    if results.get('best_params'):
        print(f"\n✅ Optimal Parameters Found:")
        for param, value in results['best_params'].items():
            print(f"   {param}: {value}")
        
        print(f"\n📊 Performance Metrics:")
        print(f"   Best Sharpe Ratio: {results['best_sharpe']:.4f}")
        
        if results.get('best_result'):
            best = results['best_result']
            print(f"   Total Return: {best.get('total_return_pct', 0):.2f}%")
            print(f"   Max Drawdown: {best.get('max_drawdown_pct', 0):.2f}%")
            print(f"   Win Rate: {best.get('win_rate', 0):.1f}%")
            print(f"   Total Trades: {best.get('total_trades', 0)}")
        
        print(f"\n📈 Top 5 Parameter Combinations:")
        for i, result in enumerate(results.get('all_results', [])[:5]):
            print(f"   {i+1}. Sharpe: {result.get('sharpe_ratio', 0):.4f} | "
                  f"Return: {result.get('total_return_pct', 0):.2f}% | "
                  f"Params: {result.get('params', {})}")
    else:
        print(f"\n❌ Optimization failed: {results.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print(f"Phase III Complete. Optimal Parameters Found: {results.get('best_params', {})}")
    print("=" * 60)
