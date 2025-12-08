"""
Database configuration for TimescaleDB.
"""

import os
from typing import Optional
from pydantic import Field, field_validator
from solana_rl_bot.config.base import BaseConfig


class DatabaseConfig(BaseConfig):
    """TimescaleDB database configuration.

    Secrets (credentials) come from environment variables.
    Settings (pool sizes, timeouts) come from YAML config.
    """

    # Connection settings (from .env)
    host: str = Field(
        default="localhost",
        description="Database host",
    )
    port: int = Field(
        default=5432,
        ge=1,
        le=65535,
        description="Database port",
    )
    database: str = Field(
        default="trading_bot",
        description="Database name",
    )
    user: str = Field(
        default="postgres",
        description="Database user",
    )
    password: str = Field(
        default="changeme",
        description="Database password (should come from .env)",
    )

    # Connection pool settings (from YAML)
    pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Base connection pool size",
    )
    max_overflow: int = Field(
        default=20,
        ge=0,
        le=100,
        description="Maximum overflow connections",
    )
    pool_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Connection pool timeout in seconds",
    )
    pool_recycle: int = Field(
        default=3600,
        ge=300,
        le=86400,
        description="Connection recycle time in seconds",
    )

    # Query settings
    query_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Query timeout in seconds",
    )
    statement_timeout: int = Field(
        default=60000,
        ge=1000,
        le=300000,
        description="Statement timeout in milliseconds",
    )

    # SSL settings
    ssl_mode: str = Field(
        default="prefer",
        description="SSL mode (disable, allow, prefer, require, verify-ca, verify-full)",
    )

    @field_validator("ssl_mode")
    @classmethod
    def validate_ssl_mode(cls, v: str) -> str:
        """Validate SSL mode."""
        valid_modes = ["disable", "allow", "prefer", "require", "verify-ca", "verify-full"]
        if v not in valid_modes:
            raise ValueError(f"ssl_mode must be one of {valid_modes}")
        return v

    @field_validator("pool_size", "max_overflow")
    @classmethod
    def validate_pool_settings(cls, v: int) -> int:
        """Validate pool settings are reasonable."""
        if v < 0:
            raise ValueError("Pool settings must be positive")
        return v

    def get_connection_string(self, include_password: bool = True) -> str:
        """Build SQLAlchemy connection string.

        Args:
            include_password: Whether to include password in connection string

        Returns:
            Connection string for SQLAlchemy
        """
        password = self.password if include_password else "***"
        return (
            f"postgresql+psycopg2://{self.user}:{password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    @classmethod
    def from_env(cls, yaml_config: Optional[dict] = None) -> "DatabaseConfig":
        """Create config from environment variables and optional YAML config.

        Priority: Environment variables > YAML config > defaults

        Args:
            yaml_config: Optional YAML configuration dictionary

        Returns:
            DatabaseConfig instance
        """
        config_dict = yaml_config or {}

        # Override with environment variables (secrets)
        env_overrides = {
            "host": os.getenv("TIMESCALE_HOST"),
            "port": os.getenv("TIMESCALE_PORT"),
            "database": os.getenv("TIMESCALE_DB"),
            "user": os.getenv("TIMESCALE_USER"),
            "password": os.getenv("TIMESCALE_PASSWORD"),
        }

        # Merge: Start with YAML, override with env vars
        for key, value in env_overrides.items():
            if value is not None:
                config_dict[key] = value

        return cls(**config_dict)
