"""
Configuration loader for the Solana RL Trading Bot.

This module provides centralized configuration loading from:
- Environment variables (.env) for secrets
- YAML files for settings
- Pydantic validation for type safety
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from dotenv import load_dotenv
from loguru import logger

from solana_rl_bot.config.base import BaseConfig
from solana_rl_bot.config.database import DatabaseConfig
from solana_rl_bot.config.exchange import ExchangeConfig
from solana_rl_bot.config.trading import TradingConfig, TradingMode
from solana_rl_bot.config.data_quality import DataQualityConfig


class BotConfig(BaseConfig):
    """Main bot configuration that combines all sub-configs."""

    # Environment
    environment: str = "development"  # development, staging, production

    # Sub-configurations
    database: DatabaseConfig
    exchange: ExchangeConfig
    trading: TradingConfig
    data_quality: DataQualityConfig

    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: Optional[str] = None

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def validate_for_live_trading(self) -> None:
        """Validate configuration is safe for live trading.

        Raises:
            ValueError: If configuration is unsafe for live trading
        """
        if self.trading.mode == TradingMode.LIVE:
            # Check API credentials are set
            if not self.exchange.api_key or not self.exchange.api_secret:
                raise ValueError("API credentials required for live trading")

            # Check not using testnet
            if self.exchange.testnet:
                logger.warning("Using testnet in LIVE mode - this is unusual")

            # Check risk limits are reasonable
            if self.trading.risk_management.max_risk_per_trade > 0.05:
                raise ValueError("Max risk per trade too high for live trading (>5%)")

            if self.trading.risk_management.max_daily_loss > 0.1:
                raise ValueError("Max daily loss too high for live trading (>10%)")

            logger.info("Live trading validation passed")


def _find_project_root() -> Path:
    """Find project root directory (contains .env file).

    Returns:
        Path to project root

    Raises:
        FileNotFoundError: If project root cannot be found
    """
    current = Path.cwd()

    # Try current directory and parents
    for path in [current] + list(current.parents):
        if (path / ".env").exists() or (path / ".env.template").exists():
            return path
        if (path / "pyproject.toml").exists():
            return path

    # Fallback to current directory
    logger.warning(f"Could not find project root, using current directory: {current}")
    return current


def _load_yaml_config(config_path: Path) -> Dict[str, Any]:
    """Load YAML configuration file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file not found
        yaml.YAMLError: If YAML parsing fails
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    if config is None:
        logger.warning(f"Empty config file: {config_path}")
        return {}

    logger.info(f"Loaded config from: {config_path}")
    return config


def _load_env_file(env_path: Optional[Path] = None) -> None:
    """Load environment variables from .env file.

    Args:
        env_path: Optional path to .env file (default: project_root/.env)
    """
    if env_path is None:
        project_root = _find_project_root()
        env_path = project_root / ".env"

    if env_path.exists():
        load_dotenv(env_path, override=True)
        logger.info(f"Loaded environment variables from: {env_path}")
    else:
        logger.warning(f".env file not found: {env_path}")


def load_config(
    config_path: Optional[str] = None,
    environment: Optional[str] = None,
    env_file: Optional[str] = None,
) -> BotConfig:
    """Load complete bot configuration.

    Configuration priority:
    1. Environment variables (highest priority)
    2. YAML config file
    3. Defaults (lowest priority)

    Args:
        config_path: Path to YAML config file (default: config/{environment}.yaml)
        environment: Environment name (development, staging, production)
        env_file: Path to .env file (default: project_root/.env)

    Returns:
        Complete bot configuration

    Example:
        >>> config = load_config()  # Uses config/development.yaml
        >>> config = load_config(environment="production")  # Uses config/production.yaml
        >>> config = load_config(config_path="my_config.yaml")  # Custom config
    """
    # Load environment variables first
    if env_file:
        _load_env_file(Path(env_file))
    else:
        _load_env_file()

    # Determine environment
    if environment is None:
        environment = os.getenv("ENVIRONMENT", "development")

    # Determine config path
    if config_path is None:
        project_root = _find_project_root()
        config_dir = project_root / "config"
        config_path = str(config_dir / f"{environment}.yaml")

    # Load YAML config
    try:
        yaml_config = _load_yaml_config(Path(config_path))
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}, using defaults")
        yaml_config = {}

    # Create sub-configs with env override
    database_config = DatabaseConfig.from_env(yaml_config.get("database", {}))
    exchange_config = ExchangeConfig.from_env(yaml_config.get("exchange", {}))

    # Trading and data quality configs (no env override needed)
    trading_config = TradingConfig(**yaml_config.get("trading", {}))
    data_quality_config = DataQualityConfig(**yaml_config.get("data_quality", {}))

    # Logging settings
    log_level = os.getenv("LOG_LEVEL", yaml_config.get("log_level", "INFO"))
    log_to_file = yaml_config.get("log_to_file", True)
    log_file_path = yaml_config.get("log_file_path")

    # Create main config
    config = BotConfig(
        environment=environment,
        database=database_config,
        exchange=exchange_config,
        trading=trading_config,
        data_quality=data_quality_config,
        log_level=log_level,
        log_to_file=log_to_file,
        log_file_path=log_file_path,
    )

    logger.info(f"Configuration loaded for environment: {environment}")
    logger.debug(f"Trading mode: {config.trading.mode}")
    logger.debug(f"Exchange: {config.exchange.name}")
    logger.debug(f"Database: {config.database.database}@{config.database.host}")

    return config


# Global config instance (can be set once and accessed everywhere)
_global_config: Optional[BotConfig] = None


def get_config() -> BotConfig:
    """Get global configuration instance.

    Returns:
        Global bot configuration

    Raises:
        RuntimeError: If config not initialized (call load_config first)

    Example:
        >>> from solana_rl_bot.config import load_config, get_config
        >>> load_config()  # Initialize once
        >>> config = get_config()  # Access anywhere
    """
    global _global_config
    if _global_config is None:
        raise RuntimeError(
            "Configuration not initialized. Call load_config() first."
        )
    return _global_config


def set_config(config: BotConfig) -> None:
    """Set global configuration instance.

    Args:
        config: Bot configuration to set as global

    Example:
        >>> config = load_config()
        >>> set_config(config)  # Now accessible via get_config()
    """
    global _global_config
    _global_config = config
    logger.info("Global configuration set")


def reset_config() -> None:
    """Reset global configuration (useful for testing)."""
    global _global_config
    _global_config = None
    logger.debug("Global configuration reset")
