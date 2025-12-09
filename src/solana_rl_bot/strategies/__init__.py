# -*- coding: utf-8 -*-
"""Baseline Trading Strategies fuer Benchmark-Vergleich."""

from .base_strategy import BaseStrategy
from .buy_and_hold import BuyAndHoldStrategy
from .sma_crossover import SMACrossoverStrategy
from .rsi_strategy import RSIStrategy

__all__ = [
    "BaseStrategy",
    "BuyAndHoldStrategy",
    "SMACrossoverStrategy",
    "RSIStrategy",
]
