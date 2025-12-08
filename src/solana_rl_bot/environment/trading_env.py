"""
Solana RL Trading Environment

Gymnasium-kompatibles Trading Environment für Reinforcement Learning.
"""

from typing import Dict, Tuple, Optional, Any
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces

from solana_rl_bot.utils import get_logger
from solana_rl_bot.environment.rewards import RewardFunction, RewardFactory

logger = get_logger(__name__)


class TradingEnv(gym.Env):
    """
    Trading Environment für Reinforcement Learning.

    Observation Space:
        - OHLCV Daten (normalized)
        - Technische Indikatoren
        - Portfolio Status (Position, PnL, etc.)

    Action Space:
        - 0: Hold (nichts tun)
        - 1: Buy (Long position öffnen)
        - 2: Sell (Position schließen/Short)

    Reward:
        - Portfolio Return
        - Sharpe Ratio berücksichtigt
        - Risk-adjusted Returns
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        df: pd.DataFrame,
        initial_balance: float = 10000.0,
        commission: float = 0.001,  # 0.1%
        window_size: int = 50,
        features: Optional[list] = None,
        reward_function: Optional[RewardFunction] = None,
        reward_type: str = "profit",
    ):
        """
        Initialisiere Trading Environment.

        Args:
            df: DataFrame mit OHLCV + Features
            initial_balance: Startkapital in USDT
            commission: Trading Commission (0.001 = 0.1%)
            window_size: Anzahl vergangener Candles für Observation
            features: Liste von Feature-Namen (None = alle)
            reward_function: Custom RewardFunction (None = nutze reward_type)
            reward_type: Typ der Reward Function ('profit', 'sharpe', 'sortino', 'multi', 'incremental')
        """
        super().__init__()

        self.df = df.copy()
        self.initial_balance = initial_balance
        self.commission = commission
        self.window_size = window_size

        # Reward Function
        if reward_function is not None:
            self.reward_function = reward_function
        else:
            self.reward_function = RewardFactory.create(reward_type)

        logger.info(f"Nutze Reward Function: {self.reward_function}")

        # Bestimme Features
        if features is None:
            # Standard: OHLCV + wichtigste Features
            self.features = [
                "open", "high", "low", "close", "volume",
                "rsi_14", "macd", "bbands_upper", "bbands_lower",
                "returns", "volatility"
            ]
        else:
            self.features = features

        # Filtere verfügbare Features
        self.features = [f for f in self.features if f in df.columns]

        if len(self.features) == 0:
            raise ValueError("Keine gültigen Features gefunden!")

        # Normalize Features
        self._normalize_data()

        # Action Space: 0=Hold, 1=Buy, 2=Sell
        self.action_space = spaces.Discrete(3)

        # Observation Space: Window von Features + Portfolio Status
        n_features = len(self.features)
        portfolio_features = 5  # position, balance, holdings, pnl, total_value

        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(window_size * n_features + portfolio_features,),
            dtype=np.float32,
        )

        # Trading State
        self.current_step = 0
        self.balance = initial_balance
        self.holdings = 0.0  # Anzahl SOL
        self.position = 0  # 0=keine Position, 1=Long
        self.entry_price = 0.0

        # Statistiken
        self.total_reward = 0.0
        self.trades = []
        self.portfolio_history = []

        logger.info(
            f"TradingEnv initialisiert: "
            f"{len(df)} Candles, {len(self.features)} Features, "
            f"Initial Balance: ${initial_balance:.2f}"
        )

    def _normalize_data(self):
        """Normalisiere Features für besseres RL Training."""
        self.df_normalized = self.df.copy()

        for feature in self.features:
            if feature in self.df.columns:
                # Min-Max Normalisierung zu [-1, 1]
                min_val = self.df[feature].min()
                max_val = self.df[feature].max()

                if max_val > min_val:
                    self.df_normalized[feature] = (
                        2 * (self.df[feature] - min_val) / (max_val - min_val) - 1
                    )
                else:
                    self.df_normalized[feature] = 0

    def reset(
        self, seed: Optional[int] = None, options: Optional[dict] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        Resette Environment.

        Returns:
            observation, info
        """
        super().reset(seed=seed)

        # Reset Trading State
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.holdings = 0.0
        self.position = 0
        self.entry_price = 0.0

        # Reset Statistiken
        self.total_reward = 0.0
        self.trades = []
        self.portfolio_history = []

        observation = self._get_observation()
        info = self._get_info()

        return observation, info

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Führe Action aus und gebe nächsten State zurück.

        Args:
            action: 0=Hold, 1=Buy, 2=Sell

        Returns:
            observation, reward, terminated, truncated, info
        """
        # Aktuelle Preis-Daten
        current_price = self.df.iloc[self.current_step]["close"]

        # Portfolio Value VOR Action tracken (für Reward Functions)
        portfolio_value_before = self._get_portfolio_value()
        self.portfolio_history.append(portfolio_value_before)

        # Führe Action aus
        reward = self._execute_action(action, current_price)

        # Nächster Step
        self.current_step += 1

        # Aktueller Portfolio Value (nach Action)
        portfolio_value = self._get_portfolio_value()

        # Check ob Episode endet
        terminated = self.current_step >= len(self.df) - 1
        truncated = portfolio_value <= self.initial_balance * 0.2  # 80% Verlust

        # Nächste Observation
        observation = self._get_observation()
        info = self._get_info()

        self.total_reward += reward

        return observation, reward, terminated, truncated, info

    def _execute_action(self, action: int, current_price: float) -> float:
        """
        Führe Trading Action aus.

        Args:
            action: 0=Hold, 1=Buy, 2=Sell
            current_price: Aktueller Preis

        Returns:
            Reward
        """
        # Speichere alten Position Status für Reward Function
        old_position = self.position
        old_balance = self.balance
        old_holdings = self.holdings

        # ACTION 1: BUY (Long öffnen)
        if action == 1 and self.position == 0:
            # Kaufe mit gesamtem Balance
            cost = self.balance * (1 - self.commission)
            self.holdings = cost / current_price
            self.entry_price = current_price
            self.balance = 0
            self.position = 1

            self.trades.append(
                {
                    "step": self.current_step,
                    "action": "BUY",
                    "price": current_price,
                    "amount": self.holdings,
                    "balance": self.balance,
                }
            )

            logger.debug(
                f"Step {self.current_step}: BUY {self.holdings:.4f} SOL @ ${current_price:.2f}"
            )

        # ACTION 2: SELL (Position schließen)
        elif action == 2 and self.position == 1:
            # Verkaufe alle Holdings
            revenue = self.holdings * current_price * (1 - self.commission)
            profit = revenue - (self.holdings * self.entry_price)
            profit_pct = (current_price - self.entry_price) / self.entry_price

            self.balance = revenue
            self.holdings = 0
            self.position = 0

            self.trades.append(
                {
                    "step": self.current_step,
                    "action": "SELL",
                    "price": current_price,
                    "profit": profit,
                    "profit_pct": profit_pct,
                    "balance": self.balance,
                }
            )

            logger.debug(
                f"Step {self.current_step}: SELL @ ${current_price:.2f}, "
                f"Profit: ${profit:.2f} ({profit_pct*100:.2f}%)"
            )

        # Berechne Reward mit Reward Function
        reward = self.reward_function.calculate(
            action=action,
            position=old_position,  # Position NACH Action
            balance=self.balance,
            holdings=self.holdings,
            entry_price=self.entry_price,
            current_price=current_price,
            initial_balance=self.initial_balance,
            portfolio_history=self.portfolio_history,
        )

        return reward

    def _get_observation(self) -> np.ndarray:
        """
        Erstelle Observation für aktuellen State.

        Returns:
            Observation array
        """
        # Hole letzten `window_size` Candles
        start = self.current_step - self.window_size
        end = self.current_step

        window_data = self.df_normalized.iloc[start:end]

        # Features extrahieren
        features_array = window_data[self.features].values.flatten()

        # Portfolio Status
        current_price = self.df.iloc[self.current_step]["close"]
        portfolio_value = self._get_portfolio_value()

        portfolio_features = np.array(
            [
                float(self.position),  # 0 oder 1
                self.balance / self.initial_balance,  # Normalized
                self.holdings,  # Anzahl SOL
                (portfolio_value - self.initial_balance)
                / self.initial_balance,  # PnL %
                portfolio_value / self.initial_balance,  # Total Value normalized
            ],
            dtype=np.float32,
        )

        # Kombiniere alles
        observation = np.concatenate([features_array, portfolio_features])

        return observation.astype(np.float32)

    def _get_portfolio_value(self) -> float:
        """
        Berechne aktuellen Portfolio Value.

        Returns:
            Total Portfolio Value in USDT
        """
        current_price = self.df.iloc[self.current_step]["close"]
        holdings_value = self.holdings * current_price
        return self.balance + holdings_value

    def _get_info(self) -> Dict:
        """
        Zusätzliche Info für Debugging.

        Returns:
            Info Dictionary
        """
        portfolio_value = self._get_portfolio_value()
        total_return = (portfolio_value - self.initial_balance) / self.initial_balance

        return {
            "step": self.current_step,
            "balance": self.balance,
            "holdings": self.holdings,
            "position": self.position,
            "portfolio_value": portfolio_value,
            "total_return": total_return,
            "total_reward": self.total_reward,
            "num_trades": len(self.trades),
        }

    def render(self, mode="human"):
        """Visualisiere aktuellen State."""
        info = self._get_info()

        print(f"\n=== Step {info['step']} ===")
        print(f"Portfolio Value: ${info['portfolio_value']:.2f}")
        print(f"Balance: ${info['balance']:.2f}")
        print(f"Holdings: {info['holdings']:.4f} SOL")
        print(f"Position: {'LONG' if info['position'] == 1 else 'NONE'}")
        print(f"Total Return: {info['total_return']*100:.2f}%")
        print(f"Trades: {info['num_trades']}")
        print(f"Total Reward: {info['total_reward']:.2f}")

    def get_trade_statistics(self) -> Dict:
        """
        Berechne Trading Statistiken.

        Returns:
            Dictionary mit Statistiken
        """
        if len(self.trades) == 0:
            return {"total_trades": 0}

        # Filtere nur SELL trades (abgeschlossene Trades)
        sell_trades = [t for t in self.trades if t["action"] == "SELL"]

        if len(sell_trades) == 0:
            return {"total_trades": len(self.trades), "completed_trades": 0}

        profits = [t["profit"] for t in sell_trades]
        profit_pcts = [t["profit_pct"] for t in sell_trades]

        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p <= 0]

        stats = {
            "total_trades": len(self.trades),
            "completed_trades": len(sell_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(sell_trades) if sell_trades else 0,
            "total_profit": sum(profits),
            "avg_profit": np.mean(profits),
            "avg_profit_pct": np.mean(profit_pcts) * 100,
            "max_profit": max(profits) if profits else 0,
            "max_loss": min(profits) if profits else 0,
            "final_portfolio_value": self._get_portfolio_value(),
            "total_return": (self._get_portfolio_value() - self.initial_balance)
            / self.initial_balance,
        }

        return stats
