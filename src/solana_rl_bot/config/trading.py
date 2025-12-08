"""
Trading configuration for risk management and execution.
"""

from typing import Optional
from enum import Enum
from pydantic import Field, field_validator
from solana_rl_bot.config.base import BaseConfig


class TradingMode(str, Enum):
    """Trading mode enum."""

    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class PositionSizing(str, Enum):
    """Position sizing method."""

    FIXED = "fixed"
    KELLY = "kelly"
    RISK_PARITY = "risk_parity"
    VOLATILITY = "volatility"


class RiskManagementConfig(BaseConfig):
    """Risk management configuration."""

    # Position sizing
    max_position_size: float = Field(
        default=0.1,
        ge=0.01,
        le=1.0,
        description="Maximum position size as fraction of portfolio (0.1 = 10%)",
    )
    position_sizing_method: PositionSizing = Field(
        default=PositionSizing.FIXED,
        description="Position sizing method",
    )

    # Risk limits
    max_risk_per_trade: float = Field(
        default=0.02,
        ge=0.001,
        le=0.1,
        description="Maximum risk per trade as fraction of portfolio (0.02 = 2%)",
    )
    max_daily_loss: float = Field(
        default=0.05,
        ge=0.01,
        le=0.5,
        description="Maximum daily loss as fraction of portfolio (0.05 = 5%)",
    )
    max_drawdown: float = Field(
        default=0.2,
        ge=0.05,
        le=0.5,
        description="Maximum drawdown before stopping (0.2 = 20%)",
    )

    # Stop loss / Take profit
    use_stop_loss: bool = Field(
        default=True,
        description="Enable stop loss orders",
    )
    stop_loss_pct: float = Field(
        default=0.02,
        ge=0.001,
        le=0.2,
        description="Stop loss percentage (0.02 = 2%)",
    )
    use_take_profit: bool = Field(
        default=True,
        description="Enable take profit orders",
    )
    take_profit_pct: float = Field(
        default=0.04,
        ge=0.001,
        le=1.0,
        description="Take profit percentage (0.04 = 4%)",
    )
    use_trailing_stop: bool = Field(
        default=False,
        description="Use trailing stop loss",
    )
    trailing_stop_pct: float = Field(
        default=0.015,
        ge=0.001,
        le=0.2,
        description="Trailing stop percentage (0.015 = 1.5%)",
    )

    @field_validator("stop_loss_pct", "take_profit_pct")
    @classmethod
    def validate_percentages(cls, v: float) -> float:
        """Validate percentages are positive."""
        if v <= 0:
            raise ValueError("Percentages must be positive")
        return v


class ExecutionConfig(BaseConfig):
    """Order execution configuration."""

    # Order types
    default_order_type: str = Field(
        default="market",
        description="Default order type (market, limit)",
    )
    limit_order_offset_pct: float = Field(
        default=0.001,
        ge=0.0001,
        le=0.01,
        description="Offset for limit orders (0.001 = 0.1%)",
    )

    # Slippage
    max_slippage_pct: float = Field(
        default=0.005,
        ge=0.0001,
        le=0.05,
        description="Maximum acceptable slippage (0.005 = 0.5%)",
    )

    # Fees
    maker_fee: float = Field(
        default=0.0001,
        ge=0.0,
        le=0.01,
        description="Maker fee (0.0001 = 0.01%)",
    )
    taker_fee: float = Field(
        default=0.0004,
        ge=0.0,
        le=0.01,
        description="Taker fee (0.0004 = 0.04%)",
    )

    # Execution timing
    order_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Order timeout in seconds",
    )
    cancel_open_orders_on_stop: bool = Field(
        default=True,
        description="Cancel all open orders when stopping",
    )

    @field_validator("default_order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        """Validate order type."""
        valid_types = ["market", "limit", "stop_market", "stop_limit"]
        if v.lower() not in valid_types:
            raise ValueError(f"Order type must be one of {valid_types}")
        return v.lower()


class TradingConfig(BaseConfig):
    """Main trading configuration."""

    # Trading mode
    mode: TradingMode = Field(
        default=TradingMode.BACKTEST,
        description="Trading mode (backtest, paper, live)",
    )

    # Portfolio
    initial_capital: float = Field(
        default=10000.0,
        ge=100.0,
        le=10000000.0,
        description="Initial capital in USDT",
    )
    reserve_capital_pct: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Reserve capital percentage (0.1 = 10%)",
    )

    # Position limits
    max_open_positions: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Maximum number of open positions",
    )
    allow_short_positions: bool = Field(
        default=False,
        description="Allow short positions (not supported in backtest)",
    )

    # Sub-configurations
    risk_management: RiskManagementConfig = Field(
        default_factory=RiskManagementConfig,
        description="Risk management settings",
    )
    execution: ExecutionConfig = Field(
        default_factory=ExecutionConfig,
        description="Order execution settings",
    )

    # Session settings
    session_id: Optional[str] = Field(
        default=None,
        description="Trading session ID (auto-generated if None)",
    )
    log_trades: bool = Field(
        default=True,
        description="Log all trades to database",
    )
    log_performance: bool = Field(
        default=True,
        description="Log performance metrics to database",
    )

    @field_validator("initial_capital")
    @classmethod
    def validate_capital(cls, v: float) -> float:
        """Validate initial capital is positive."""
        if v <= 0:
            raise ValueError("Initial capital must be positive")
        return v

    @field_validator("max_open_positions")
    @classmethod
    def validate_max_positions(cls, v: int) -> int:
        """Validate max open positions."""
        if v < 1:
            raise ValueError("Must allow at least 1 open position")
        return v

    def get_available_capital(self) -> float:
        """Calculate available capital after reserve.

        Returns:
            Available capital for trading
        """
        return self.initial_capital * (1 - self.reserve_capital_pct)

    def is_production_mode(self) -> bool:
        """Check if running in production (live) mode.

        Returns:
            True if in live trading mode
        """
        return self.mode == TradingMode.LIVE
