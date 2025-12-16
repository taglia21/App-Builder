"""
OTREP-X PRIME - Hybrid Strategy Module
Phase III: Vectorized Momentum + Mean Reversion Strategy

This module implements a HybridStrategy that combines:
1. Momentum signals (trend-following)
2. Mean Reversion signals (Bollinger Band based)

The signals are weighted and combined to produce a final trading signal.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class StrategyResult:
    """Container for strategy calculation results."""
    signal: pd.Series
    momentum_signal: pd.Series
    mean_reversion_signal: Optional[pd.Series]
    combined_signal: pd.Series
    metadata: Dict


class HybridStrategy:
    """
    Hybrid Strategy combining Momentum and Mean Reversion signals.
    
    The strategy uses:
    - Momentum: Rate of change over lookback period
    - Mean Reversion: Bollinger Band distance (standardized)
    
    Signals are combined using configurable weights to produce
    a final signal in the range [-1.0, 1.0].
    """
    
    def __init__(
        self,
        # Momentum Parameters
        momentum_lookback: int = 20,
        momentum_weight: float = 0.5,
        signal_threshold: float = 0.15,
        neutral_threshold: float = 0.05,
        
        # Mean Reversion Parameters
        mean_reversion_enabled: bool = False,
        mr_lookback: int = 20,
        bb_std_dev_multiplier: float = 2.0,
        mr_weight: float = 0.5,
        reversion_threshold: float = 0.01,
        
        # Adaptive Parameters
        adaptive_enabled: bool = False,
        volatility_scaling: bool = True,
        min_volatility: float = 0.005,
        max_volatility: float = 0.05,
        regime_detection: bool = False,
        regime_lookback: int = 50,
        high_vol_threshold: float = 0.03,
        low_vol_threshold: float = 0.01
    ):
        """
        Initialize the HybridStrategy.
        
        Args:
            momentum_lookback: Lookback period for momentum calculation
            momentum_weight: Weight for momentum signal in final combination
            signal_threshold: Threshold for generating strong signals
            neutral_threshold: Threshold below which signal is considered neutral
            mean_reversion_enabled: Enable mean reversion component
            mr_lookback: Lookback period for mean reversion (Bollinger Band)
            bb_std_dev_multiplier: Standard deviation multiplier for Bollinger Bands
            mr_weight: Weight for mean reversion signal in final combination
            reversion_threshold: Threshold for mean reversion signals
            adaptive_enabled: Enable adaptive parameter adjustment
            volatility_scaling: Scale signals by volatility
            min_volatility: Minimum volatility threshold
            max_volatility: Maximum volatility threshold
            regime_detection: Enable market regime detection
            regime_lookback: Lookback for regime detection
            high_vol_threshold: High volatility regime threshold
            low_vol_threshold: Low volatility regime threshold
        """
        # Momentum parameters
        self.momentum_lookback = momentum_lookback
        self.momentum_weight = momentum_weight
        self.signal_threshold = signal_threshold
        self.neutral_threshold = neutral_threshold
        
        # Mean Reversion parameters
        self.mean_reversion_enabled = mean_reversion_enabled
        self.mr_lookback = mr_lookback
        self.bb_std_dev_multiplier = bb_std_dev_multiplier
        self.mr_weight = mr_weight
        self.reversion_threshold = reversion_threshold
        
        # Adaptive parameters
        self.adaptive_enabled = adaptive_enabled
        self.volatility_scaling = volatility_scaling
        self.min_volatility = min_volatility
        self.max_volatility = max_volatility
        self.regime_detection = regime_detection
        self.regime_lookback = regime_lookback
        self.high_vol_threshold = high_vol_threshold
        self.low_vol_threshold = low_vol_threshold
        
        # Validate weights sum
        total_weight = self.momentum_weight + self.mr_weight
        if abs(total_weight - 1.0) > 0.01 and self.mean_reversion_enabled:
            logger.warning(
                f"Signal weights sum to {total_weight}, expected 1.0. "
                "Signals will be normalized."
            )
        
        logger.info(
            f"HybridStrategy initialized: "
            f"momentum_lookback={momentum_lookback}, mr_lookback={mr_lookback}, "
            f"momentum_weight={momentum_weight}, mr_weight={mr_weight}, "
            f"mean_reversion_enabled={mean_reversion_enabled}"
        )
    
    def calculate_momentum_signal(self, bars_df: pd.DataFrame) -> pd.Series:
        """
        Calculate the momentum signal using rate of change.
        
        The momentum signal is the percentage change over the lookback period,
        normalized to fit within [-1.0, 1.0].
        
        Args:
            bars_df: DataFrame with OHLCV data (must have 'close' column)
        
        Returns:
            pd.Series: Momentum signal in range [-1.0, 1.0]
        """
        if 'close' not in bars_df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        close = bars_df['close']
        
        # Calculate rate of change (momentum)
        roc = close.pct_change(periods=self.momentum_lookback)
        
        # Calculate rolling volatility for normalization
        volatility = close.pct_change().rolling(
            window=self.momentum_lookback
        ).std()
        
        # Normalize momentum by volatility to get standardized signal
        # Avoid division by zero
        volatility = volatility.replace(0, np.nan)
        normalized_momentum = roc / (volatility * np.sqrt(self.momentum_lookback))
        
        # Scale to [-1.0, 1.0] using tanh for smooth clipping
        momentum_signal = np.tanh(normalized_momentum / 2.0)
        
        # Fill NaN values with 0 (neutral)
        momentum_signal = momentum_signal.fillna(0.0)
        
        return momentum_signal
    
    def calculate_mean_reversion_signal(self, bars_df: pd.DataFrame) -> pd.Series:
        """
        Calculate the Mean Reversion signal using Bollinger Band distance.
        
        Signal = - (Close - SMA) / (STD * BB_STD_DEV_MULTIPLIER)
        
        The signal is the NEGATIVE normalized distance from the closing price
        to the center SMA. This means:
        - Price far ABOVE the mean (overbought) → NEGATIVE signal (SELL/SHORT)
        - Price far BELOW the mean (oversold) → POSITIVE signal (BUY/LONG)
        
        Args:
            bars_df: DataFrame with OHLCV data (must have 'close' column)
        
        Returns:
            pd.Series: Mean reversion signal in range [-1.0, 1.0]
        """
        if 'close' not in bars_df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        close = bars_df['close']
        
        # Calculate Simple Moving Average (SMA)
        sma = close.rolling(window=self.mr_lookback).mean()
        
        # Calculate Standard Deviation (STD)
        std = close.rolling(window=self.mr_lookback).std()
        
        # Avoid division by zero
        std = std.replace(0, np.nan)
        
        # Calculate standardized distance from SMA
        # Signal_MR = - (Close - SMA) / (STD * BB_STD_DEV_MULTIPLIER)
        distance = close - sma
        normalized_distance = distance / (std * self.bb_std_dev_multiplier)
        
        # The signal is the NEGATIVE of the normalized distance
        # Overbought (above SMA) → negative signal (sell)
        # Oversold (below SMA) → positive signal (buy)
        mr_signal = -normalized_distance
        
        # Scale to strictly fit within [-1.0, 1.0] using tanh
        mr_signal = np.tanh(mr_signal)
        
        # Fill NaN values with 0 (neutral)
        mr_signal = mr_signal.fillna(0.0)
        
        return mr_signal
    
    def calculate_volatility(self, bars_df: pd.DataFrame) -> pd.Series:
        """
        Calculate rolling volatility for adaptive scaling.
        
        Args:
            bars_df: DataFrame with OHLCV data
        
        Returns:
            pd.Series: Rolling volatility
        """
        close = bars_df['close']
        returns = close.pct_change()
        volatility = returns.rolling(window=self.regime_lookback).std()
        return volatility.fillna(self.min_volatility)
    
    def detect_regime(self, volatility: pd.Series) -> pd.Series:
        """
        Detect market regime based on volatility.
        
        Args:
            volatility: Rolling volatility series
        
        Returns:
            pd.Series: Regime indicator (-1=low vol, 0=normal, 1=high vol)
        """
        regime = pd.Series(0, index=volatility.index)
        regime[volatility > self.high_vol_threshold] = 1
        regime[volatility < self.low_vol_threshold] = -1
        return regime
    
    def apply_adaptive_scaling(
        self,
        signal: pd.Series,
        volatility: pd.Series,
        regime: pd.Series
    ) -> pd.Series:
        """
        Apply adaptive scaling to signals based on volatility and regime.
        
        Args:
            signal: Raw signal series
            volatility: Rolling volatility
            regime: Market regime indicator
        
        Returns:
            pd.Series: Scaled signal
        """
        if not self.volatility_scaling:
            return signal
        
        # Scale factor: reduce signal in high volatility, increase in low
        vol_scale = (self.max_volatility - volatility) / (
            self.max_volatility - self.min_volatility
        )
        vol_scale = vol_scale.clip(0.5, 1.5)
        
        # Adjust for regime
        if self.regime_detection:
            # Reduce signals in high volatility regime
            regime_scale = 1.0 - (regime * 0.2)
            vol_scale = vol_scale * regime_scale
        
        scaled_signal = signal * vol_scale
        
        # Ensure signal stays within bounds
        return scaled_signal.clip(-1.0, 1.0)
    
    def calculate_signal(self, bars_df: pd.DataFrame) -> Dict:
        """
        Calculate the combined hybrid signal.
        
        This method:
        1. Calculates the momentum signal
        2. Calculates the mean reversion signal (if enabled)
        3. Combines signals using configured weights
        4. Applies adaptive scaling (if enabled)
        
        Final Signal = (Momentum * Momentum_Weight) + (MR * MR_Weight)
        
        Args:
            bars_df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        
        Returns:
            Dict containing:
                - signal: Final combined signal series [-1.0, 1.0]
                - momentum_signal: Raw momentum signal
                - mean_reversion_signal: Raw mean reversion signal (if enabled)
                - metadata: Additional calculation metadata
        """
        if bars_df.empty:
            raise ValueError("Input DataFrame is empty")
        
        # Ensure column names are lowercase
        bars_df = bars_df.copy()
        bars_df.columns = bars_df.columns.str.lower()
        
        # Calculate momentum signal
        momentum_signal = self.calculate_momentum_signal(bars_df)
        
        # Initialize result
        result = {
            'momentum_signal': momentum_signal,
            'mean_reversion_signal': None,
            'metadata': {
                'momentum_lookback': self.momentum_lookback,
                'momentum_weight': self.momentum_weight,
                'mean_reversion_enabled': self.mean_reversion_enabled
            }
        }
        
        # Calculate combined signal
        if self.mean_reversion_enabled:
            # Calculate mean reversion signal
            mr_signal = self.calculate_mean_reversion_signal(bars_df)
            result['mean_reversion_signal'] = mr_signal
            result['metadata']['mr_lookback'] = self.mr_lookback
            result['metadata']['mr_weight'] = self.mr_weight
            result['metadata']['bb_std_dev_multiplier'] = self.bb_std_dev_multiplier
            
            # Combine signals using weights
            # FinalSignal = (MomentumSignal * Momentum_Weight) + (ReversionSignal * MR_Weight)
            combined_signal = (
                momentum_signal * self.momentum_weight +
                mr_signal * self.mr_weight
            )
        else:
            # Use momentum signal only
            combined_signal = momentum_signal
        
        # Apply adaptive scaling if enabled
        if self.adaptive_enabled:
            volatility = self.calculate_volatility(bars_df)
            regime = self.detect_regime(volatility)
            combined_signal = self.apply_adaptive_scaling(
                combined_signal, volatility, regime
            )
            result['metadata']['adaptive_applied'] = True
            result['metadata']['avg_volatility'] = volatility.mean()
        
        # Ensure final signal is within bounds
        final_signal = combined_signal.clip(-1.0, 1.0)
        
        # Apply thresholds for signal clarity
        # Signals below neutral_threshold are set to 0
        final_signal = final_signal.where(
            abs(final_signal) >= self.neutral_threshold, 0.0
        )
        
        result['signal'] = final_signal
        result['combined_signal'] = combined_signal
        
        logger.debug(
            f"Signal calculated: mean={final_signal.mean():.4f}, "
            f"std={final_signal.std():.4f}, "
            f"non_zero_pct={((final_signal != 0).sum() / len(final_signal) * 100):.1f}%"
        )
        
        return result
    
    def generate_positions(
        self,
        bars_df: pd.DataFrame,
        signal_threshold: Optional[float] = None
    ) -> pd.Series:
        """
        Generate position sizing based on signals.
        
        Args:
            bars_df: DataFrame with OHLCV data
            signal_threshold: Override threshold for position generation
        
        Returns:
            pd.Series: Position sizes in range [-1.0, 1.0]
                - Positive: Long position
                - Negative: Short position
                - Zero: No position
        """
        threshold = signal_threshold or self.signal_threshold
        
        # Calculate signals
        result = self.calculate_signal(bars_df)
        signal = result['signal']
        
        # Generate positions based on threshold
        positions = pd.Series(0.0, index=signal.index)
        
        # Long positions for strong positive signals
        positions[signal >= threshold] = signal[signal >= threshold]
        
        # Short positions for strong negative signals
        positions[signal <= -threshold] = signal[signal <= -threshold]
        
        return positions
    
    def get_parameters(self) -> Dict:
        """
        Get current strategy parameters.
        
        Returns:
            Dict: All strategy parameters
        """
        return {
            'momentum_lookback': self.momentum_lookback,
            'momentum_weight': self.momentum_weight,
            'signal_threshold': self.signal_threshold,
            'neutral_threshold': self.neutral_threshold,
            'mean_reversion_enabled': self.mean_reversion_enabled,
            'mr_lookback': self.mr_lookback,
            'bb_std_dev_multiplier': self.bb_std_dev_multiplier,
            'mr_weight': self.mr_weight,
            'reversion_threshold': self.reversion_threshold,
            'adaptive_enabled': self.adaptive_enabled,
            'volatility_scaling': self.volatility_scaling
        }
    
    @classmethod
    def from_config(cls, config: Dict) -> 'HybridStrategy':
        """
        Create a HybridStrategy from a configuration dictionary.
        
        Args:
            config: Configuration dictionary (from config.yaml STRATEGY section)
        
        Returns:
            HybridStrategy: Configured strategy instance
        """
        strategy_config = config.get('STRATEGY', config)
        weights = strategy_config.get('SIGNAL_WEIGHTS', {})
        mr_config = strategy_config.get('MEAN_REVERSION', {})
        adaptive_config = strategy_config.get('ADAPTIVE', {})
        
        return cls(
            # Momentum parameters
            momentum_lookback=strategy_config.get('MOMENTUM_LOOKBACK', 20),
            momentum_weight=weights.get('MOMENTUM', 0.5),
            signal_threshold=strategy_config.get('SIGNAL_THRESHOLD', 0.15),
            neutral_threshold=strategy_config.get('NEUTRAL_THRESHOLD', 0.05),
            
            # Mean Reversion parameters
            mean_reversion_enabled=mr_config.get('ENABLED', False),
            mr_lookback=mr_config.get('LOOKBACK', 20),
            bb_std_dev_multiplier=mr_config.get('BB_STD_DEV_MULTIPLIER', 2.0),
            mr_weight=weights.get('MEAN_REVERSION', 0.5),
            reversion_threshold=mr_config.get('REVERSION_THRESHOLD', 0.01),
            
            # Adaptive parameters
            adaptive_enabled=adaptive_config.get('ENABLED', False),
            volatility_scaling=adaptive_config.get('VOLATILITY_SCALING', True),
            min_volatility=adaptive_config.get('MIN_VOLATILITY', 0.005),
            max_volatility=adaptive_config.get('MAX_VOLATILITY', 0.05),
            regime_detection=adaptive_config.get('REGIME_DETECTION', False),
            regime_lookback=adaptive_config.get('REGIME_LOOKBACK', 50),
            high_vol_threshold=adaptive_config.get('HIGH_VOL_THRESHOLD', 0.03),
            low_vol_threshold=adaptive_config.get('LOW_VOL_THRESHOLD', 0.01)
        )
