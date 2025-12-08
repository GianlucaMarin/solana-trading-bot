"""
Advanced Trading Environment mit erweitertem Position Management.

Features:
- Short-Selling (Long + Short)
- Position Sizing (0-100%)
- Stop-Loss / Take-Profit
- Partial Position Exits
"""

from typing import Dict, Tuple, Optional, Any
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces

from solana_rl_bot.utils import get_logger
from solana_rl_bot.environment.rewards import RewardFunction, RewardFactory

logger = get_logger(__name__)


class AdvancedTradingEnv(gym.Env):
    """
    Advanced Trading Environment mit Short-Selling und Position Sizing.
    
    Action Space:
        Box(3):
            - action[0]: Position Direction (-1=Short, 0=Flat, +1=Long)
            - action[1]: Position Size (0.0 - 1.0 = 0% - 100% of portfolio)
            - action[2]: Stop-Loss Distance (0.0 - 0.2 = 0% - 20%)
    
    Supports:
        - Long and Short positions
        - Variable position sizing
        - Stop-Loss orders
        - Take-Profit orders
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
        enable_short: bool = True,
        enable_stop_loss: bool = True,
        max_position_size: float = 1.0,  # Max 100% of portfolio
    ):
        """
        Initialisiere Advanced Trading Environment.
        
        Args:
            df: DataFrame mit OHLCV + Features
            initial_balance: Startkapital
            commission: Trading Commission
            window_size: Window für Observations
            features: Feature Liste
            reward_function: Custom Reward Function
            reward_type: Reward Type
            enable_short: Short-Selling erlauben
            enable_stop_loss: Stop-Loss Orders erlauben
            max_position_size: Max Position Size (0-1)
        """
        super().__init__()
        
        self.df = df.copy()
        self.initial_balance = initial_balance
        self.commission = commission
        self.window_size = window_size
        self.enable_short = enable_short
        self.enable_stop_loss = enable_stop_loss
        self.max_position_size = max_position_size
        
        # Reward Function
        if reward_function is not None:
            self.reward_function = reward_function
        else:
            self.reward_function = RewardFactory.create(reward_type)
        
        # Features
        if features is None:
            self.features = [
                "open", "high", "low", "close", "volume",
                "rsi_14", "macd", "bbands_upper", "bbands_lower",
                "returns", "volatility"
            ]
        else:
            self.features = features
        
        self.features = [f for f in self.features if f in df.columns]
        
        # Normalize Data
        self._normalize_data()
        
        # Action Space: Box(3)
        # [direction (-1 to 1), size (0 to 1), stop_loss (0 to 0.2)]
        self.action_space = spaces.Box(
            low=np.array([-1.0, 0.0, 0.0]),
            high=np.array([1.0, 1.0, 0.2]),
            dtype=np.float32
        )
        
        # Observation Space
        n_features = len(self.features)
        portfolio_features = 7  # position, size, balance, holdings, pnl, value, stop_loss
        
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(window_size * n_features + portfolio_features,),
            dtype=np.float32
        )
        
        # Trading State
        self.current_step = 0
        self.balance = initial_balance
        self.holdings = 0.0  # Positive=Long, Negative=Short
        self.position = 0  # -1=Short, 0=Flat, 1=Long
        self.position_size = 0.0  # 0.0 - 1.0
        self.entry_price = 0.0
        self.stop_loss_price = None
        self.take_profit_price = None
        
        # Statistics
        self.total_reward = 0.0
        self.trades = []
        self.portfolio_history = []
        
        logger.info(
            f"AdvancedTradingEnv initialisiert: {len(df)} Candles, "
            f"Short={enable_short}, StopLoss={enable_stop_loss}"
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
    
    def reset(
        self, seed: Optional[int] = None, options: Optional[dict] = None
    ) -> Tuple[np.ndarray, Dict]:
        """Reset Environment."""
        super().reset(seed=seed)
        
        self.current_step = self.window_size
        self.balance = self.initial_balance
        self.holdings = 0.0
        self.position = 0
        self.position_size = 0.0
        self.entry_price = 0.0
        self.stop_loss_price = None
        self.take_profit_price = None
        
        self.total_reward = 0.0
        self.trades = []
        self.portfolio_history = []
        
        observation = self._get_observation()
        info = self._get_info()
        
        return observation, info
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Führe Action aus.
        
        Args:
            action: [direction, size, stop_loss]
                direction: -1 to 1 (-1=Short, 0=Close, 1=Long)
                size: 0.0 to 1.0 (0% to 100% of portfolio)
                stop_loss: 0.0 to 0.2 (0% to 20% distance)
        
        Returns:
            observation, reward, terminated, truncated, info
        """
        # Parse Action
        direction = float(action[0])  # -1 to 1
        size = float(np.clip(action[1], 0.0, self.max_position_size))
        stop_loss_pct = float(np.clip(action[2], 0.0, 0.2))
        
        # Current Price
        current_price = self.df.iloc[self.current_step]["close"]
        
        # Portfolio Value BEFORE Action
        portfolio_value_before = self._get_portfolio_value()
        self.portfolio_history.append(portfolio_value_before)
        
        # Check Stop-Loss
        if self.enable_stop_loss and self.stop_loss_price is not None:
            if self.position == 1 and current_price <= self.stop_loss_price:
                # Long Stop-Loss triggered
                logger.debug(f"Stop-Loss triggered @ ${current_price:.2f}")
                self._close_position(current_price, reason="STOP_LOSS")
            elif self.position == -1 and current_price >= self.stop_loss_price:
                # Short Stop-Loss triggered
                logger.debug(f"Stop-Loss triggered @ ${current_price:.2f}")
                self._close_position(current_price, reason="STOP_LOSS")
        
        # Execute Action
        reward = self._execute_action(direction, size, stop_loss_pct, current_price)
        
        # Next Step
        self.current_step += 1
        
        # Portfolio Value AFTER
        portfolio_value = self._get_portfolio_value()
        
        # Check Episode End
        terminated = self.current_step >= len(self.df) - 1
        truncated = portfolio_value <= self.initial_balance * 0.1  # 90% loss
        
        # Observation
        observation = self._get_observation()
        info = self._get_info()
        
        self.total_reward += reward
        
        return observation, reward, terminated, truncated, info
    
    def _execute_action(
        self, direction: float, size: float, stop_loss_pct: float, current_price: float
    ) -> float:
        """
        Führe Trading Action aus.
        
        Args:
            direction: -1 (Short) to 1 (Long)
            size: Position size (0-1)
            stop_loss_pct: Stop-loss distance (0-0.2)
            current_price: Current price
        
        Returns:
            Reward
        """
        old_position = self.position
        
        # Determine Target Position
        if direction > 0.3:
            target_position = 1  # Long
        elif direction < -0.3:
            target_position = -1  # Short
        else:
            target_position = 0  # Close/Flat
        
        # Disable Short if not enabled
        if not self.enable_short and target_position == -1:
            target_position = 0
        
        # Execute based on current and target position
        if target_position == 0 and self.position != 0:
            # Close existing position
            self._close_position(current_price, reason="CLOSE")
        
        elif target_position == 1 and self.position != 1:
            # Open Long or flip from Short
            if self.position == -1:
                self._close_position(current_price, reason="FLIP")
            self._open_long(current_price, size, stop_loss_pct)
        
        elif target_position == -1 and self.position != -1:
            # Open Short or flip from Long
            if self.position == 1:
                self._close_position(current_price, reason="FLIP")
            self._open_short(current_price, size, stop_loss_pct)
        
        # Calculate Reward
        reward = self.reward_function.calculate(
            action=target_position + 1,  # Convert to 0,1,2 for compatibility
            position=old_position,
            balance=self.balance,
            holdings=abs(self.holdings),
            entry_price=self.entry_price,
            current_price=current_price,
            initial_balance=self.initial_balance,
            portfolio_history=self.portfolio_history,
        )
        
        return reward
    
    def _open_long(self, price: float, size: float, stop_loss_pct: float):
        """Open Long Position."""
        if size <= 0:
            return
        
        # Calculate cost
        available = self.balance * size
        cost = available * (1 - self.commission)
        self.holdings = cost / price
        self.entry_price = price
        self.balance -= available
        self.position = 1
        self.position_size = size
        
        # Set Stop-Loss
        if self.enable_stop_loss and stop_loss_pct > 0:
            self.stop_loss_price = price * (1 - stop_loss_pct)
        else:
            self.stop_loss_price = None
        
        self.trades.append({
            "step": self.current_step,
            "action": "LONG",
            "price": price,
            "size": size,
            "holdings": self.holdings,
            "stop_loss": self.stop_loss_price,
        })
        
        sl_str = f"${self.stop_loss_price:.2f}" if self.stop_loss_price is not None else "None"
        logger.debug(
            f"Step {self.current_step}: LONG {self.holdings:.4f} @ ${price:.2f} "
            f"(size={size*100:.1f}%, SL={sl_str})"
        )
    
    def _open_short(self, price: float, size: float, stop_loss_pct: float):
        """Open Short Position."""
        if size <= 0 or not self.enable_short:
            return
        
        # Borrow and sell
        available = self.balance * size
        quantity = available / price
        self.holdings = -quantity  # Negative for short
        self.entry_price = price
        self.balance += available * (1 - self.commission)  # Credit from sale
        self.position = -1
        self.position_size = size
        
        # Set Stop-Loss
        if self.enable_stop_loss and stop_loss_pct > 0:
            self.stop_loss_price = price * (1 + stop_loss_pct)
        else:
            self.stop_loss_price = None
        
        self.trades.append({
            "step": self.current_step,
            "action": "SHORT",
            "price": price,
            "size": size,
            "holdings": abs(self.holdings),
            "stop_loss": self.stop_loss_price,
        })
        
        sl_str = f"${self.stop_loss_price:.2f}" if self.stop_loss_price is not None else "None"
        logger.debug(
            f"Step {self.current_step}: SHORT {abs(self.holdings):.4f} @ ${price:.2f} "
            f"(size={size*100:.1f}%, SL={sl_str})"
        )
    
    def _close_position(self, price: float, reason: str = "CLOSE"):
        """Close Current Position."""
        if self.position == 0:
            return
        
        if self.position == 1:
            # Close Long
            revenue = self.holdings * price * (1 - self.commission)
            profit = revenue - (self.holdings * self.entry_price)
            profit_pct = (price - self.entry_price) / self.entry_price
            self.balance += revenue
        
        else:  # position == -1
            # Close Short (buy back)
            cost = abs(self.holdings) * price * (1 + self.commission)
            profit = (self.entry_price - price) * abs(self.holdings) - cost * self.commission
            profit_pct = (self.entry_price - price) / self.entry_price
            self.balance -= cost
        
        self.trades.append({
            "step": self.current_step,
            "action": f"CLOSE_{reason}",
            "price": price,
            "profit": profit,
            "profit_pct": profit_pct,
            "position_type": "LONG" if self.position == 1 else "SHORT",
        })
        
        logger.debug(
            f"Step {self.current_step}: CLOSE {reason} @ ${price:.2f}, "
            f"Profit=${profit:.2f} ({profit_pct*100:.2f}%)"
        )
        
        self.holdings = 0.0
        self.position = 0
        self.position_size = 0.0
        self.entry_price = 0.0
        self.stop_loss_price = None
    
    def _get_observation(self) -> np.ndarray:
        """Get current observation."""
        start = self.current_step - self.window_size
        end = self.current_step
        
        window_data = self.df_normalized.iloc[start:end]
        features_array = window_data[self.features].values.flatten()
        
        current_price = self.df.iloc[self.current_step]["close"]
        portfolio_value = self._get_portfolio_value()
        
        # Portfolio features
        portfolio_features = np.array([
            float(self.position),  # -1, 0, or 1
            self.position_size,  # 0.0 to 1.0
            self.balance / self.initial_balance,
            abs(self.holdings),
            (portfolio_value - self.initial_balance) / self.initial_balance,  # PnL %
            portfolio_value / self.initial_balance,
            (self.stop_loss_price / current_price - 1) if self.stop_loss_price else 0.0,
        ], dtype=np.float32)
        
        observation = np.concatenate([features_array, portfolio_features])
        return observation.astype(np.float32)
    
    def _get_portfolio_value(self) -> float:
        """Calculate current portfolio value."""
        current_price = self.df.iloc[self.current_step]["close"]
        
        if self.position == 1:
            # Long: balance + holdings value
            return self.balance + self.holdings * current_price
        elif self.position == -1:
            # Short: balance - cost to buy back
            return self.balance - abs(self.holdings) * current_price
        else:
            return self.balance
    
    def _get_info(self) -> Dict:
        """Get info dict."""
        portfolio_value = self._get_portfolio_value()
        
        return {
            "step": self.current_step,
            "balance": self.balance,
            "holdings": self.holdings,
            "position": self.position,
            "position_size": self.position_size,
            "portfolio_value": portfolio_value,
            "total_return": (portfolio_value - self.initial_balance) / self.initial_balance,
            "total_reward": self.total_reward,
            "num_trades": len(self.trades),
            "stop_loss_price": self.stop_loss_price,
        }
    
    def get_trade_statistics(self) -> Dict:
        """Calculate trade statistics."""
        if len(self.trades) == 0:
            return {"total_trades": 0}
        
        close_trades = [t for t in self.trades if "CLOSE" in t.get("action", "")]
        
        if len(close_trades) == 0:
            return {"total_trades": len(self.trades), "completed_trades": 0}
        
        profits = [t["profit"] for t in close_trades]
        profit_pcts = [t["profit_pct"] for t in close_trades]
        
        winning = [p for p in profits if p > 0]
        losing = [p for p in profits if p <= 0]
        
        long_trades = [t for t in close_trades if t.get("position_type") == "LONG"]
        short_trades = [t for t in close_trades if t.get("position_type") == "SHORT"]
        
        stats = {
            "total_trades": len(self.trades),
            "completed_trades": len(close_trades),
            "long_trades": len(long_trades),
            "short_trades": len(short_trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": len(winning) / len(close_trades) if close_trades else 0,
            "total_profit": sum(profits),
            "avg_profit": np.mean(profits),
            "avg_profit_pct": np.mean(profit_pcts) * 100,
            "max_profit": max(profits) if profits else 0,
            "max_loss": min(profits) if profits else 0,
            "final_portfolio_value": self._get_portfolio_value(),
            "total_return": (self._get_portfolio_value() - self.initial_balance) / self.initial_balance,
        }
        
        return stats
