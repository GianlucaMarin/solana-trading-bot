# -*- coding: utf-8 -*-
"""Base Strategy - Abstract Class für alle Baseline Strategies."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


class BaseStrategy(ABC):
    """
    Abstract Base Class für Trading Strategies.

    Alle Baseline Strategies müssen diese Klasse implementieren.
    """

    def __init__(
        self,
        initial_balance: float = 10000.0,
        commission: float = 0.001,
        name: str = "BaseStrategy",
    ):
        """
        Initialisiere Strategy.

        Args:
            initial_balance: Startkapital
            commission: Trading-Gebühren (0.001 = 0.1%)
            name: Name der Strategy
        """
        self.initial_balance = initial_balance
        self.commission = commission
        self.name = name

        # State
        self.balance = initial_balance
        self.position = 0.0  # SOL Menge
        self.trades: List[Dict] = []

    def reset(self):
        """Reset Strategy State."""
        self.balance = self.initial_balance
        self.position = 0.0
        self.trades = []

    @abstractmethod
    def get_signal(self, df: pd.DataFrame, idx: int) -> int:
        """
        Generiere Trading Signal.

        Args:
            df: DataFrame mit OHLCV + Indicators
            idx: Aktueller Index

        Returns:
            Signal: 0=HOLD, 1=BUY, 2=SELL
        """
        pass

    def execute_trade(self, signal: int, price: float, timestamp) -> Optional[Dict]:
        """
        Führe Trade aus basierend auf Signal.

        Args:
            signal: 0=HOLD, 1=BUY, 2=SELL
            price: Aktueller Preis
            timestamp: Zeitstempel

        Returns:
            Trade Dict oder None
        """
        trade = None

        if signal == 1 and self.balance > 0:  # BUY
            # Kaufe mit gesamtem Balance
            amount_before_fee = self.balance / price
            fee = amount_before_fee * self.commission
            amount = amount_before_fee - fee

            self.position = amount
            self.balance = 0.0

            trade = {
                "type": "BUY",
                "price": price,
                "amount": amount,
                "fee": fee * price,
                "timestamp": timestamp,
                "balance_after": self.balance,
                "position_after": self.position,
            }
            self.trades.append(trade)

        elif signal == 2 and self.position > 0:  # SELL
            # Verkaufe gesamte Position
            value_before_fee = self.position * price
            fee = value_before_fee * self.commission
            value = value_before_fee - fee

            self.balance = value
            self.position = 0.0

            trade = {
                "type": "SELL",
                "price": price,
                "amount": self.position,
                "fee": fee,
                "timestamp": timestamp,
                "balance_after": self.balance,
                "position_after": self.position,
            }
            self.trades.append(trade)

        return trade

    def backtest(self, df: pd.DataFrame) -> Dict:
        """
        Führe Backtest auf DataFrame durch.

        Args:
            df: DataFrame mit OHLCV + Indicators

        Returns:
            Dictionary mit Performance Metriken
        """
        self.reset()

        # Track Portfolio Value
        portfolio_values = []

        for idx in range(len(df)):
            price = df['close'].iloc[idx]
            timestamp = df.index[idx]

            # Get Signal
            signal = self.get_signal(df, idx)

            # Execute Trade
            self.execute_trade(signal, price, timestamp)

            # Calculate Portfolio Value
            portfolio_value = self.balance + (self.position * price)
            portfolio_values.append(portfolio_value)

        # Final Liquidation (falls noch Position offen)
        if self.position > 0:
            final_price = df['close'].iloc[-1]
            self.execute_trade(2, final_price, df.index[-1])

        # Calculate Metrics
        portfolio_values = np.array(portfolio_values)
        returns = np.diff(portfolio_values) / portfolio_values[:-1]

        # Total Return
        total_return = (portfolio_values[-1] / self.initial_balance) - 1

        # Sharpe Ratio (annualized, assuming 5min candles)
        if len(returns) > 0 and np.std(returns) > 0:
            # 288 candles per day (5min), 365 days per year
            sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(288 * 365)
        else:
            sharpe = 0.0

        # Sortino Ratio
        negative_returns = returns[returns < 0]
        if len(negative_returns) > 0 and np.std(negative_returns) > 0:
            sortino = (np.mean(returns) / np.std(negative_returns)) * np.sqrt(288 * 365)
        else:
            sortino = 0.0

        # Max Drawdown
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (portfolio_values - peak) / peak
        max_drawdown = np.min(drawdown)

        # Win Rate
        winning_trades = sum(1 for t in self.trades if t['type'] == 'SELL' and t['balance_after'] > self.initial_balance)
        total_sells = sum(1 for t in self.trades if t['type'] == 'SELL')
        win_rate = winning_trades / total_sells if total_sells > 0 else 0.0

        # Trade Count
        num_trades = len([t for t in self.trades if t['type'] == 'SELL'])

        return {
            "strategy": self.name,
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "num_trades": num_trades,
            "final_balance": self.balance,
            "portfolio_values": portfolio_values,
        }

    def __repr__(self) -> str:
        return f"{self.name}(balance={self.balance:.2f}, position={self.position:.4f})"
