# -*- coding: utf-8 -*-
"""
Continuous Trading Environment fuer SAC.

Wie TradingEnv, aber mit kontinuierlichem Action Space
fuer Algorithmen wie SAC die Box Actions brauchen.
"""

from typing import Dict, Tuple, Optional, Any
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces

from solana_rl_bot.utils import get_logger
from solana_rl_bot.environment.rewards import RewardFunction, RewardFactory
from solana_rl_bot.risk import RiskManager, RiskConfig

logger = get_logger(__name__)


class ContinuousTradingEnv(gym.Env):
    """
    Trading Environment mit kontinuierlichem Action Space.

    Fuer SAC und andere Algorithmen die Box Actions brauchen.

    Action Space: Box(-1, 1)
        - action < -0.33 -> Sell
        - -0.33 <= action <= 0.33 -> Hold
        - action > 0.33 -> Buy

    Optional: action magnitude bestimmt Position Size
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        df: pd.DataFrame,
        initial_balance: float = 10000.0,
        commission: float = 0.001,
        window_size: int = 50,
        features: Optional[list] = None,
        reward_function: Optional[RewardFunction] = None,
        reward_type: str = "profit",
        use_risk_management: bool = True,
        risk_config: Optional[RiskConfig] = None,
        use_position_sizing: bool = False,
    ):
        """
        Initialisiere Continuous Trading Environment.

        Args:
            df: DataFrame mit OHLCV + Features
            initial_balance: Startkapital in USDT
            commission: Trading Commission (0.001 = 0.1%)
            window_size: Anzahl vergangener Candles fuer Observation
            features: Liste von Feature-Namen (None = alle)
            reward_function: Custom RewardFunction
            reward_type: Typ der Reward Function
            use_risk_management: Aktiviere Risk Management
            risk_config: Custom RiskConfig
            use_position_sizing: Action magnitude bestimmt Position Size
        """
        super().__init__()

        self.df = df.copy()
        self.initial_balance = initial_balance
        self.commission = commission
        self.window_size = window_size
        self.use_position_sizing = use_position_sizing

        # Reward Function
        if reward_function is not None:
            self.reward_function = reward_function
        else:
            self.reward_function = RewardFactory.create(reward_type)

        # Bestimme Features
        if features is None:
            self.features = [
                "open", "high", "low", "close", "volume",
                "rsi_14", "macd", "bbands_upper", "bbands_lower",
                "returns", "volatility"
            ]
        else:
            self.features = features

        # Filtere verfuegbare Features
        self.features = [f for f in self.features if f in df.columns]

        if len(self.features) == 0:
            raise ValueError("Keine gueltigen Features gefunden!")

        # Normalize Features
        self._normalize_data()

        # KONTINUIERLICHER Action Space fuer SAC
        self.action_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(1,),
            dtype=np.float32,
        )

        # Observation Space
        n_features = len(self.features)
        portfolio_features = 5

        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(window_size * n_features + portfolio_features,),
            dtype=np.float32,
        )

        # Trading State
        self.current_step = 0
        self.balance = initial_balance
        self.holdings = 0.0
        self.position = 0
        self.entry_price = 0.0

        # Risk Management
        self.use_risk_management = use_risk_management
        if use_risk_management:
            self.risk_manager = RiskManager(risk_config or RiskConfig())
        else:
            self.risk_manager = None

        # Statistiken
        self.total_reward = 0.0
        self.trades = []
        self.portfolio_history = []
        self.risk_events = []

        logger.info(
            f"ContinuousTradingEnv initialisiert: "
            f"{len(df)} Candles, Box Action Space"
        )

    def _normalize_data(self):
        """Normalisiere Features."""
        self.df_normalized = self.df.copy()

        for feature in self.features:
            if feature in self.df.columns:
                min_val = self.df[feature].min()
                max_val = self.df[feature].max()

                if max_val > min_val:
                    self.df_normalized[feature] = (
                        2 * (self.df[feature] - min_val) / (max_val - min_val) - 1
                    )
                else:
                    self.df_normalized[feature] = 0

    def _continuous_to_discrete(self, action: np.ndarray) -> int:
        """
        Konvertiere kontinuierliche Action zu diskreter Action.

        Args:
            action: Array mit Wert zwischen -1 und 1

        Returns:
            0=Hold, 1=Buy, 2=Sell
        """
        action_value = float(action[0])

        if action_value < -0.33:
            return 2  # Sell
        elif action_value > 0.33:
            return 1  # Buy
        else:
            return 0  # Hold

    def reset(
        self, seed: Optional[int] = None, options: Optional[dict] = None
    ) -> Tuple[np.ndarray, Dict]:
        """Resette Environment."""
        super().reset(seed=seed)

        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.holdings = 0.0
        self.position = 0
        self.entry_price = 0.0

        self.total_reward = 0.0
        self.trades = []
        self.portfolio_history = []
        self.risk_events = []

        if self.risk_manager:
            self.risk_manager.reset(self.initial_balance)

        observation = self._get_observation()
        info = self._get_info()

        return observation, info

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Fuehre Action aus.

        Args:
            action: Kontinuierliche Action [-1, 1]

        Returns:
            observation, reward, terminated, truncated, info
        """
        # Konvertiere zu diskreter Action
        discrete_action = self._continuous_to_discrete(action)

        # Aktuelle Preis-Daten
        current_price = self.df.iloc[self.current_step]["close"]
        timestamp = self.df.index[self.current_step] if hasattr(self.df.index, '__getitem__') else None

        # Portfolio Value VOR Action
        portfolio_value_before = self._get_portfolio_value()
        self.portfolio_history.append(portfolio_value_before)

        # Risk Management
        if self.risk_manager:
            self.risk_manager.update_day(timestamp, self.balance + self.holdings * current_price)
            self.risk_manager.update_peak(portfolio_value_before)

            if self.position == 1:
                risk_signal = self.risk_manager.on_price_update(current_price)
                if risk_signal:
                    discrete_action = 2
                    self.risk_events.append({
                        "step": self.current_step,
                        "type": risk_signal,
                        "price": current_price,
                        "entry_price": self.entry_price,
                        "pnl_pct": (current_price - self.entry_price) / self.entry_price,
                    })

            if discrete_action == 1 and self.position == 0:
                can_trade, reason = self.risk_manager.can_open_trade(
                    portfolio_value_before, self.current_step
                )
                if not can_trade:
                    discrete_action = 0

        # Fuehre Action aus
        reward = self._execute_action(discrete_action, current_price)

        # Naechster Step
        self.current_step += 1

        # Portfolio Value nach Action
        portfolio_value = self._get_portfolio_value()

        # Berechne Reward
        current_price = self.df.iloc[self.current_step - 1]["close"]
        reward = self.reward_function.calculate(
            action=discrete_action,
            position=self.position,
            balance=self.balance,
            holdings=self.holdings,
            entry_price=self.entry_price,
            current_price=current_price,
            initial_balance=self.initial_balance,
            portfolio_history=self.portfolio_history,
        )

        self.total_reward += reward

        # Check Termination
        terminated = self.current_step >= len(self.df) - 1
        truncated = portfolio_value < self.initial_balance * 0.5

        observation = self._get_observation()
        info = self._get_info()

        return observation, reward, terminated, truncated, info

    def _execute_action(self, action: int, price: float) -> float:
        """Fuehre Trading Action aus."""
        reward = 0.0

        if action == 1 and self.position == 0:  # Buy
            # Position sizing
            if self.risk_manager:
                max_position_value = self.balance * self.risk_manager.config.max_position_pct
            else:
                max_position_value = self.balance

            trade_amount = max_position_value * (1 - self.commission)
            self.holdings = trade_amount / price
            self.balance -= trade_amount / (1 - self.commission)
            self.position = 1
            self.entry_price = price

            if self.risk_manager:
                self.risk_manager.on_trade_open(price, self.current_step)

            self.trades.append({
                "step": self.current_step,
                "type": "buy",
                "price": price,
                "amount": self.holdings,
            })

        elif action == 2 and self.position == 1:  # Sell
            sell_value = self.holdings * price * (1 - self.commission)
            pnl = sell_value - (self.holdings * self.entry_price)
            pnl_pct = (price - self.entry_price) / self.entry_price

            self.balance += sell_value
            self.holdings = 0.0
            self.position = 0

            if self.risk_manager:
                self.risk_manager.on_trade_close()

            self.trades.append({
                "step": self.current_step,
                "type": "sell",
                "price": price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
            })

        return reward

    def _get_observation(self) -> np.ndarray:
        """Erstelle Observation."""
        # Feature Window
        start_idx = self.current_step - self.window_size
        end_idx = self.current_step

        features = []
        for feature in self.features:
            feature_data = self.df_normalized[feature].iloc[start_idx:end_idx].values
            features.extend(feature_data)

        # Portfolio Status
        portfolio_value = self._get_portfolio_value()
        current_price = self.df.iloc[self.current_step]["close"]

        portfolio_status = [
            self.position,
            self.balance / self.initial_balance,
            self.holdings * current_price / self.initial_balance,
            (portfolio_value - self.initial_balance) / self.initial_balance,
            portfolio_value / self.initial_balance,
        ]

        observation = np.array(features + portfolio_status, dtype=np.float32)
        return observation

    def _get_portfolio_value(self) -> float:
        """Berechne aktuellen Portfolio Wert."""
        current_price = self.df.iloc[self.current_step]["close"]
        return self.balance + self.holdings * current_price

    def _get_info(self) -> Dict[str, Any]:
        """Erstelle Info Dictionary."""
        portfolio_value = self._get_portfolio_value()
        total_return = (portfolio_value - self.initial_balance) / self.initial_balance

        return {
            "step": self.current_step,
            "portfolio_value": portfolio_value,
            "balance": self.balance,
            "holdings": self.holdings,
            "position": self.position,
            "total_return": total_return,
            "n_trades": len(self.trades),
            "total_reward": self.total_reward,
            "risk_events": len(self.risk_events),
        }
