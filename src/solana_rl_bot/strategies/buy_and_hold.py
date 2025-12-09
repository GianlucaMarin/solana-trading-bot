# -*- coding: utf-8 -*-
"""Buy and Hold Strategy - Die wichtigste Baseline überhaupt."""

import pandas as pd
from .base_strategy import BaseStrategy


class BuyAndHoldStrategy(BaseStrategy):
    """
    Buy and Hold Strategy.

    Kauft am Anfang und hält bis zum Ende.
    Das ist die WICHTIGSTE Baseline - jede Strategy muss diese schlagen!
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        commission: float = 0.001,
    ):
        super().__init__(
            initial_balance=initial_balance,
            commission=commission,
            name="Buy & Hold",
        )
        self._bought = False

    def reset(self):
        super().reset()
        self._bought = False

    def get_signal(self, df: pd.DataFrame, idx: int) -> int:
        """
        Buy and Hold: Kaufe am ersten Tag, verkaufe nie.

        Returns:
            1 (BUY) am ersten Tag, sonst 0 (HOLD)
        """
        if not self._bought:
            self._bought = True
            return 1  # BUY

        return 0  # HOLD
