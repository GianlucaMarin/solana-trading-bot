# -*- coding: utf-8 -*-
"""SMA Crossover Strategy - Classic Trend Following."""

import pandas as pd
from .base_strategy import BaseStrategy


class SMACrossoverStrategy(BaseStrategy):
    """
    SMA Crossover Strategy (20/50).

    - BUY Signal: SMA20 kreuzt über SMA50 (Golden Cross)
    - SELL Signal: SMA20 kreuzt unter SMA50 (Death Cross)

    Classic Trend-Following Strategy.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        commission: float = 0.001,
        fast_period: int = 20,
        slow_period: int = 50,
    ):
        super().__init__(
            initial_balance=initial_balance,
            commission=commission,
            name=f"SMA Crossover ({fast_period}/{slow_period})",
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self._prev_fast_above_slow = None

    def reset(self):
        super().reset()
        self._prev_fast_above_slow = None

    def get_signal(self, df: pd.DataFrame, idx: int) -> int:
        """
        SMA Crossover Signal.

        Returns:
            1 (BUY) bei Golden Cross, 2 (SELL) bei Death Cross, 0 (HOLD) sonst
        """
        # Brauchen mindestens slow_period Candles
        if idx < self.slow_period:
            return 0

        # Berechne SMAs wenn nicht vorhanden
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            fast_sma = df['sma_20'].iloc[idx]
            slow_sma = df['sma_50'].iloc[idx]
        else:
            # Berechne manuell
            fast_sma = df['close'].iloc[max(0, idx - self.fast_period + 1):idx + 1].mean()
            slow_sma = df['close'].iloc[max(0, idx - self.slow_period + 1):idx + 1].mean()

        # Check for NaN
        if pd.isna(fast_sma) or pd.isna(slow_sma):
            return 0

        # Current state
        fast_above_slow = fast_sma > slow_sma

        # First candle - set state
        if self._prev_fast_above_slow is None:
            self._prev_fast_above_slow = fast_above_slow
            return 0

        signal = 0

        # Golden Cross: Fast SMA crosses ABOVE Slow SMA
        if fast_above_slow and not self._prev_fast_above_slow:
            signal = 1  # BUY

        # Death Cross: Fast SMA crosses BELOW Slow SMA
        elif not fast_above_slow and self._prev_fast_above_slow:
            signal = 2  # SELL

        # Update state
        self._prev_fast_above_slow = fast_above_slow

        return signal
