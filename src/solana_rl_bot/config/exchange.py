"""
Exchange configuration for cryptocurrency exchanges.
"""

import os
from typing import Dict, List, Optional
from pydantic import Field, field_validator
from solana_rl_bot.config.base import BaseConfig


class RateLimitConfig(BaseConfig):
    """Rate limiting configuration for exchange API."""

    requests_per_minute: int = Field(
        default=1200,
        ge=1,
        le=10000,
        description="Maximum requests per minute",
    )
    orders_per_minute: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum orders per minute",
    )
    burst_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Burst size for rate limiter",
    )


class ExchangeConfig(BaseConfig):
    """Exchange configuration.

    API keys come from environment variables (.env).
    Exchange settings come from YAML config.
    """

    # Exchange identification
    name: str = Field(
        default="binance",
        description="Exchange name (binance, coinbase, kraken, etc.)",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this exchange is enabled",
    )

    # API credentials (from .env)
    api_key: Optional[str] = Field(
        default=None,
        description="API key (should come from .env)",
    )
    api_secret: Optional[str] = Field(
        default=None,
        description="API secret (should come from .env)",
    )
    testnet: bool = Field(
        default=False,
        description="Use testnet/sandbox mode",
    )

    # Trading pairs
    symbols: List[str] = Field(
        default=["SOL/USDT", "BTC/USDT", "ETH/USDT"],
        description="Trading symbols to monitor",
    )
    default_symbol: str = Field(
        default="SOL/USDT",
        description="Default trading symbol",
    )

    # Timeframes
    timeframes: List[str] = Field(
        default=["1m", "5m", "15m", "1h", "4h", "1d"],
        description="Timeframes to collect data for",
    )
    default_timeframe: str = Field(
        default="5m",
        description="Default timeframe for trading",
    )

    # Rate limiting
    rate_limit: RateLimitConfig = Field(
        default_factory=RateLimitConfig,
        description="Rate limiting configuration",
    )

    # Connection settings
    timeout: int = Field(
        default=30,
        ge=1,
        le=120,
        description="Request timeout in seconds",
    )
    retry_attempts: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of retry attempts on failure",
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Delay between retries in seconds",
    )

    # Data collection
    fetch_ohlcv_limit: int = Field(
        default=1000,
        ge=1,
        le=5000,
        description="Maximum candles to fetch per request",
    )
    enable_websocket: bool = Field(
        default=True,
        description="Enable WebSocket for real-time data",
    )

    @field_validator("name")
    @classmethod
    def validate_exchange_name(cls, v: str) -> str:
        """Validate exchange name."""
        supported = ["binance", "coinbase", "kraken", "bybit", "okx"]
        if v.lower() not in supported:
            raise ValueError(f"Exchange must be one of {supported}")
        return v.lower()

    @field_validator("default_timeframe")
    @classmethod
    def validate_default_timeframe(cls, v: str, info) -> str:
        """Validate default timeframe is in timeframes list."""
        # Access other fields via info.data
        timeframes = info.data.get("timeframes", [])
        if timeframes and v not in timeframes:
            raise ValueError(f"default_timeframe '{v}' must be in timeframes list")
        return v

    @field_validator("default_symbol")
    @classmethod
    def validate_default_symbol(cls, v: str, info) -> str:
        """Validate default symbol is in symbols list."""
        symbols = info.data.get("symbols", [])
        if symbols and v not in symbols:
            raise ValueError(f"default_symbol '{v}' must be in symbols list")
        return v

    @classmethod
    def from_env(cls, yaml_config: Optional[dict] = None) -> "ExchangeConfig":
        """Create config from environment variables and optional YAML config.

        Priority: Environment variables > YAML config > defaults

        Args:
            yaml_config: Optional YAML configuration dictionary

        Returns:
            ExchangeConfig instance
        """
        config_dict = yaml_config or {}

        # Get exchange name from YAML or default
        exchange_name = config_dict.get("name", "binance").upper()

        # Override with environment variables (API keys)
        env_overrides = {
            "api_key": os.getenv(f"{exchange_name}_API_KEY"),
            "api_secret": os.getenv(f"{exchange_name}_API_SECRET"),
            "testnet": os.getenv(f"{exchange_name}_TESTNET", "").lower() == "true",
        }

        # Merge: Start with YAML, override with env vars
        for key, value in env_overrides.items():
            if value is not None:
                config_dict[key] = value

        return cls(**config_dict)

    def get_safe_dict(self) -> Dict:
        """Get config dict with sensitive data masked.

        Returns:
            Dictionary with API keys masked
        """
        config = self.to_dict()
        if config.get("api_key"):
            config["api_key"] = "***" + config["api_key"][-4:]
        if config.get("api_secret"):
            config["api_secret"] = "***"
        return config
