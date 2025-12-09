# -*- coding: utf-8 -*-
"""RSI Mean Reversion Strategy."""

import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    """
    RSI Mean Reversion Strategy.

    - BUY Signal: RSI < 30 (oversold)
    - SELL Signal: RSI > 70 (overbought)

    Counter-Trend Strategy basierend auf Relative Strength Index.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        commission: float = 0.001,
        rsi_period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ):
        super().__init__(
            initial_balance=initial_balance,
            commission=commission,
            name=f"RSI ({oversold}/{overbought})",
        )
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought

    def _calculate_rsi(self, prices: pd.Series) -> float:
        """Berechne RSI manuell."""
        if len(prices) < self.rsi_period + 1:
            return 50.0  # Neutral

        # Price changes
        delta = prices.diff()

        # Gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = -delta.where(delta < 0, 0.0)

        # Average gains/losses
        avg_gain = gains.iloc[-self.rsi_period:].mean()
        avg_loss = losses.iloc[-self.rsi_period:].mean()

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def get_signal(self, df: pd.DataFrame, idx: int) -> int:
        """
        RSI Signal.

        Returns:
            1 (BUY) bei oversold, 2 (SELL) bei overbought, 0 (HOLD) sonst
        """
        # Brauchen mindestens rsi_period Candles
        if idx < self.rsi_period:
            return 0

        # Nutze vorberechneten RSI wenn vorhanden
        if 'rsi_14' in df.columns:
            rsi = df['rsi_14'].iloc[idx]
        else:
            # Berechne manuell
            prices = df['close'].iloc[:idx + 1]
            rsi = self._calculate_rsi(prices)

        # Check for NaN
        if pd.isna(rsi):
            return 0

        # Oversold -> BUY (nur wenn keine Position)
        if rsi < self.oversold and self.position == 0:
            return 1  # BUY

        # Overbought -> SELL (nur wenn Position vorhanden)
        elif rsi > self.overbought and self.position > 0:
            return 2  # SELL

        return 0  # HOLD
