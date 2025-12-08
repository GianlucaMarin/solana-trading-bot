"""
Reward Functions für Trading Environment.

Verschiedene Reward-Strategien für RL Agent Training:
- Profit-based: Einfacher Gewinn/Verlust
- Sharpe Ratio: Risk-adjusted Returns
- Sortino Ratio: Downside Risk Focus
- Multi-Objective: Kombination mehrerer Ziele
- Incremental: Step-by-step Portfolio Changes
"""

from typing import Dict, List, Optional
import numpy as np
from abc import ABC, abstractmethod

from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


class RewardFunction(ABC):
    """
    Abstrakte Basis-Klasse für Reward Functions.
    """

    def __init__(self, name: str = "base"):
        """
        Initialisiere Reward Function.

        Args:
            name: Name der Reward Function
        """
        self.name = name

    @abstractmethod
    def calculate(
        self,
        action: int,
        position: int,
        balance: float,
        holdings: float,
        entry_price: float,
        current_price: float,
        initial_balance: float,
        portfolio_history: List[float],
    ) -> float:
        """
        Berechne Reward für gegebene Action.

        Args:
            action: Ausgeführte Action (0=Hold, 1=Buy, 2=Sell)
            position: Aktuelle Position (0 oder 1)
            balance: Cash Balance
            holdings: Anzahl Holdings
            entry_price: Einstiegspreis (wenn Position > 0)
            current_price: Aktueller Preis
            initial_balance: Initiales Kapital
            portfolio_history: Historie Portfolio Values

        Returns:
            Reward (float)
        """
        pass

    def __str__(self) -> str:
        return f"RewardFunction({self.name})"


class ProfitReward(RewardFunction):
    """
    Einfache Profit-basierte Reward.

    - BUY/SELL: Realisierter Profit/Loss
    - HOLD: Kleine Penalty
    """

    def __init__(self, hold_penalty: float = 0.01):
        """
        Initialisiere Profit Reward.

        Args:
            hold_penalty: Penalty für HOLD Actions
        """
        super().__init__(name="profit")
        self.hold_penalty = hold_penalty

    def calculate(
        self,
        action: int,
        position: int,
        balance: float,
        holdings: float,
        entry_price: float,
        current_price: float,
        initial_balance: float,
        portfolio_history: List[float],
    ) -> float:
        """Berechne Profit-basierte Reward."""
        # SELL Action mit Position = Profit realisiert
        if action == 2 and position == 0 and len(portfolio_history) >= 2:
            # Profit wurde bereits in balance eingerechnet
            # Vergleiche aktuelles Portfolio mit vorherigem
            current_portfolio = portfolio_history[-1]
            previous_portfolio = portfolio_history[-2]
            profit = current_portfolio - previous_portfolio

            # Normalisiert auf initial balance
            reward = (profit / initial_balance) * 100
            return reward

        # BUY Action
        elif action == 1 and position == 1:
            # Kleine positive Reward für BUY (ermutigt Trading)
            return 0.1

        # HOLD Action
        else:
            # Penalty für Inaktivität
            return -self.hold_penalty


class SharpeReward(RewardFunction):
    """
    Sharpe Ratio basierte Reward.

    Reward = (Mean Return - Risk Free Rate) / Std of Returns

    Fördert risk-adjusted Returns statt rohem Profit.
    """

    def __init__(
        self, risk_free_rate: float = 0.0, window: int = 50, hold_penalty: float = 0.01
    ):
        """
        Initialisiere Sharpe Reward.

        Args:
            risk_free_rate: Risk-free Rate (annualisiert)
            window: Window für Sharpe Berechnung
            hold_penalty: Penalty für HOLD
        """
        super().__init__(name="sharpe")
        self.risk_free_rate = risk_free_rate
        self.window = window
        self.hold_penalty = hold_penalty

    def calculate(
        self,
        action: int,
        position: int,
        balance: float,
        holdings: float,
        entry_price: float,
        current_price: float,
        initial_balance: float,
        portfolio_history: List[float],
    ) -> float:
        """Berechne Sharpe-basierte Reward."""
        # Brauche genug History für Sharpe Ratio
        if len(portfolio_history) < max(2, self.window):
            # Fallback zu Profit Reward
            if action == 2 and position == 0 and len(portfolio_history) >= 2:
                profit = portfolio_history[-1] - portfolio_history[-2]
                return (profit / initial_balance) * 100
            elif action == 1:
                return 0.1
            else:
                return -self.hold_penalty

        # Berechne Returns aus Portfolio History
        returns = self._calculate_returns(portfolio_history)

        if len(returns) < 2:
            return -self.hold_penalty

        # Sharpe Ratio
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            sharpe = 0.0
        else:
            sharpe = (mean_return - self.risk_free_rate) / std_return

        # Skaliere Sharpe auf sinnvolle Reward
        reward = sharpe * 10  # Scale factor

        # Penalty für HOLD
        if action == 0:
            reward -= self.hold_penalty

        return reward

    def _calculate_returns(self, portfolio_history: List[float]) -> np.ndarray:
        """Berechne Returns aus Portfolio History."""
        if len(portfolio_history) < 2:
            return np.array([])

        # Nutze letzten N Werte
        history = portfolio_history[-self.window :]
        returns = np.diff(history) / history[:-1]

        return returns


class SortinoReward(RewardFunction):
    """
    Sortino Ratio basierte Reward.

    Reward = (Mean Return - Risk Free Rate) / Downside Std

    Fokus auf Downside Risk (nur negative Returns).
    """

    def __init__(
        self, risk_free_rate: float = 0.0, window: int = 50, hold_penalty: float = 0.01
    ):
        """
        Initialisiere Sortino Reward.

        Args:
            risk_free_rate: Risk-free Rate
            window: Window für Berechnung
            hold_penalty: Penalty für HOLD
        """
        super().__init__(name="sortino")
        self.risk_free_rate = risk_free_rate
        self.window = window
        self.hold_penalty = hold_penalty

    def calculate(
        self,
        action: int,
        position: int,
        balance: float,
        holdings: float,
        entry_price: float,
        current_price: float,
        initial_balance: float,
        portfolio_history: List[float],
    ) -> float:
        """Berechne Sortino-basierte Reward."""
        # Brauche genug History
        if len(portfolio_history) < max(2, self.window):
            # Fallback
            if action == 2 and position == 0 and len(portfolio_history) >= 2:
                profit = portfolio_history[-1] - portfolio_history[-2]
                return (profit / initial_balance) * 100
            elif action == 1:
                return 0.1
            else:
                return -self.hold_penalty

        # Berechne Returns
        returns = self._calculate_returns(portfolio_history)

        if len(returns) < 2:
            return -self.hold_penalty

        # Sortino Ratio
        mean_return = np.mean(returns)

        # Nur negative Returns für Downside Risk
        downside_returns = returns[returns < 0]

        if len(downside_returns) == 0:
            # Keine Losses = perfekt
            sortino = mean_return * 10
        else:
            downside_std = np.std(downside_returns)
            if downside_std == 0:
                sortino = 0.0
            else:
                sortino = (mean_return - self.risk_free_rate) / downside_std

        # Skaliere
        reward = sortino * 10

        # Penalty für HOLD
        if action == 0:
            reward -= self.hold_penalty

        return reward

    def _calculate_returns(self, portfolio_history: List[float]) -> np.ndarray:
        """Berechne Returns aus Portfolio History."""
        if len(portfolio_history) < 2:
            return np.array([])

        history = portfolio_history[-self.window :]
        returns = np.diff(history) / history[:-1]

        return returns


class MultiObjectiveReward(RewardFunction):
    """
    Multi-Objective Reward Function.

    Kombiniert mehrere Ziele:
    - Profit (Gewinn maximieren)
    - Risk (Volatilität minimieren)
    - Drawdown (Max Drawdown minimieren)
    """

    def __init__(
        self,
        profit_weight: float = 0.5,
        risk_weight: float = 0.3,
        drawdown_weight: float = 0.2,
        window: int = 50,
        hold_penalty: float = 0.01,
    ):
        """
        Initialisiere Multi-Objective Reward.

        Args:
            profit_weight: Gewicht für Profit
            risk_weight: Gewicht für Risk (negative)
            drawdown_weight: Gewicht für Drawdown (negative)
            window: Window für Berechnungen
            hold_penalty: Penalty für HOLD
        """
        super().__init__(name="multi_objective")
        self.profit_weight = profit_weight
        self.risk_weight = risk_weight
        self.drawdown_weight = drawdown_weight
        self.window = window
        self.hold_penalty = hold_penalty

        # Normalisiere Weights
        total = profit_weight + risk_weight + drawdown_weight
        self.profit_weight /= total
        self.risk_weight /= total
        self.drawdown_weight /= total

    def calculate(
        self,
        action: int,
        position: int,
        balance: float,
        holdings: float,
        entry_price: float,
        current_price: float,
        initial_balance: float,
        portfolio_history: List[float],
    ) -> float:
        """Berechne Multi-Objective Reward."""
        if len(portfolio_history) < 2:
            return -self.hold_penalty if action == 0 else 0.1

        # 1. Profit Component
        profit_reward = self._calculate_profit(portfolio_history, initial_balance)

        # 2. Risk Component (Volatilität)
        risk_penalty = self._calculate_risk(portfolio_history)

        # 3. Drawdown Component
        drawdown_penalty = self._calculate_drawdown(portfolio_history)

        # Kombiniere
        reward = (
            self.profit_weight * profit_reward
            - self.risk_weight * risk_penalty
            - self.drawdown_weight * drawdown_penalty
        )

        # Hold Penalty
        if action == 0:
            reward -= self.hold_penalty

        return reward

    def _calculate_profit(
        self, portfolio_history: List[float], initial_balance: float
    ) -> float:
        """Berechne Profit Component."""
        current = portfolio_history[-1]
        previous = portfolio_history[-2]

        profit = current - previous
        return (profit / initial_balance) * 100

    def _calculate_risk(self, portfolio_history: List[float]) -> float:
        """Berechne Risk Component (Volatilität)."""
        if len(portfolio_history) < max(2, self.window):
            return 0.0

        history = portfolio_history[-self.window :]
        returns = np.diff(history) / history[:-1]

        volatility = np.std(returns)
        return volatility * 100  # Skaliert

    def _calculate_drawdown(self, portfolio_history: List[float]) -> float:
        """Berechne Drawdown Component."""
        if len(portfolio_history) < max(2, self.window):
            return 0.0

        history = np.array(portfolio_history[-self.window :])

        # Running Maximum
        running_max = np.maximum.accumulate(history)

        # Drawdown
        drawdown = (running_max - history) / running_max

        # Max Drawdown
        max_drawdown = np.max(drawdown)

        return max_drawdown * 100  # Skaliert


class IncrementalReward(RewardFunction):
    """
    Incremental Reward Function.

    Gibt Feedback bei jedem Step basierend auf Portfolio-Änderung.
    Gut für schnelleres Learning.
    """

    def __init__(self, hold_penalty: float = 0.001):
        """
        Initialisiere Incremental Reward.

        Args:
            hold_penalty: Kleine Penalty für HOLD
        """
        super().__init__(name="incremental")
        self.hold_penalty = hold_penalty

    def calculate(
        self,
        action: int,
        position: int,
        balance: float,
        holdings: float,
        entry_price: float,
        current_price: float,
        initial_balance: float,
        portfolio_history: List[float],
    ) -> float:
        """Berechne Incremental Reward."""
        if len(portfolio_history) < 2:
            return 0.0

        # Portfolio Change
        current_value = portfolio_history[-1]
        previous_value = portfolio_history[-2]

        portfolio_change = current_value - previous_value

        # Normalisiert
        reward = (portfolio_change / initial_balance) * 100

        # Hold Penalty
        if action == 0:
            reward -= self.hold_penalty

        return reward


class RewardFactory:
    """
    Factory für Reward Functions.
    """

    @staticmethod
    def create(reward_type: str, **kwargs) -> RewardFunction:
        """
        Erstelle Reward Function.

        Args:
            reward_type: Typ der Reward Function
                - "profit": Profit-basiert
                - "sharpe": Sharpe Ratio
                - "sortino": Sortino Ratio
                - "multi": Multi-Objective
                - "incremental": Incremental
            **kwargs: Argumente für Reward Function

        Returns:
            RewardFunction Instanz
        """
        if reward_type == "profit":
            return ProfitReward(**kwargs)
        elif reward_type == "sharpe":
            return SharpeReward(**kwargs)
        elif reward_type == "sortino":
            return SortinoReward(**kwargs)
        elif reward_type == "multi":
            return MultiObjectiveReward(**kwargs)
        elif reward_type == "incremental":
            return IncrementalReward(**kwargs)
        else:
            logger.warning(f"Unbekannter Reward Type: {reward_type}, nutze 'profit'")
            return ProfitReward()

    @staticmethod
    def available_rewards() -> List[str]:
        """Liste verfügbare Reward Types."""
        return ["profit", "sharpe", "sortino", "multi", "incremental"]
