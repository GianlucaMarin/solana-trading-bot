"""
Configuration Management for Solana RL Trading Bot.

This package provides a centralized configuration system using:
- Pydantic v2 for validation
- YAML files for settings
- .env files for secrets
- Environment-specific configs (dev/staging/prod)

Example:
    >>> from solana_rl_bot.config import load_config, get_config
    >>>
    >>> # Initialize configuration once at startup
    >>> config = load_config(environment="development")
    >>>
    >>> # Access config anywhere in the application
    >>> from solana_rl_bot.config import get_config
    >>> config = get_config()
    >>> print(config.exchange.name)  # binance
    >>> print(config.trading.mode)  # backtest
"""

from solana_rl_bot.config.loader import (
    load_config,
    get_config,
    set_config,
    reset_config,
    BotConfig,
)
from solana_rl_bot.config.database import DatabaseConfig
from solana_rl_bot.config.exchange import ExchangeConfig, RateLimitConfig
from solana_rl_bot.config.trading import (
    TradingConfig,
    TradingMode,
    RiskManagementConfig,
    ExecutionConfig,
    PositionSizing,
)
from solana_rl_bot.config.data_quality import (
    DataQualityConfig,
    OutlierDetectionConfig,
    MissingDataConfig,
    ValidationConfig,
)

__all__ = [
    # Loader functions
    "load_config",
    "get_config",
    "set_config",
    "reset_config",
    # Main config
    "BotConfig",
    # Database
    "DatabaseConfig",
    # Exchange
    "ExchangeConfig",
    "RateLimitConfig",
    # Trading
    "TradingConfig",
    "TradingMode",
    "RiskManagementConfig",
    "ExecutionConfig",
    "PositionSizing",
    # Data Quality
    "DataQualityConfig",
    "OutlierDetectionConfig",
    "MissingDataConfig",
    "ValidationConfig",
]
