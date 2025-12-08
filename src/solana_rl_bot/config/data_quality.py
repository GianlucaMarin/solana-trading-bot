"""
Data quality monitoring and validation configuration.
"""

from typing import List, Optional
from pydantic import Field, field_validator
from solana_rl_bot.config.base import BaseConfig


class OutlierDetectionConfig(BaseConfig):
    """Outlier detection configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable outlier detection",
    )
    method: str = Field(
        default="zscore",
        description="Outlier detection method (zscore, iqr, isolation_forest)",
    )
    zscore_threshold: float = Field(
        default=3.0,
        ge=1.0,
        le=10.0,
        description="Z-score threshold for outlier detection",
    )
    iqr_multiplier: float = Field(
        default=1.5,
        ge=1.0,
        le=5.0,
        description="IQR multiplier for outlier detection",
    )
    handle_outliers: str = Field(
        default="clip",
        description="How to handle outliers (clip, remove, flag)",
    )

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        """Validate outlier detection method."""
        valid_methods = ["zscore", "iqr", "isolation_forest"]
        if v.lower() not in valid_methods:
            raise ValueError(f"Method must be one of {valid_methods}")
        return v.lower()

    @field_validator("handle_outliers")
    @classmethod
    def validate_handle_outliers(cls, v: str) -> str:
        """Validate outlier handling method."""
        valid_methods = ["clip", "remove", "flag"]
        if v.lower() not in valid_methods:
            raise ValueError(f"Handle method must be one of {valid_methods}")
        return v.lower()


class MissingDataConfig(BaseConfig):
    """Missing data handling configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable missing data checks",
    )
    max_missing_pct: float = Field(
        default=0.05,
        ge=0.0,
        le=0.5,
        description="Maximum percentage of missing data allowed (0.05 = 5%)",
    )
    handle_missing: str = Field(
        default="forward_fill",
        description="How to handle missing data (forward_fill, interpolate, drop)",
    )
    max_gap_minutes: int = Field(
        default=60,
        ge=1,
        le=1440,
        description="Maximum gap in minutes before flagging as issue",
    )

    @field_validator("handle_missing")
    @classmethod
    def validate_handle_missing(cls, v: str) -> str:
        """Validate missing data handling method."""
        valid_methods = ["forward_fill", "backward_fill", "interpolate", "drop", "zero"]
        if v.lower() not in valid_methods:
            raise ValueError(f"Handle method must be one of {valid_methods}")
        return v.lower()


class ValidationConfig(BaseConfig):
    """Data validation rules configuration."""

    # Price validation
    validate_price_ranges: bool = Field(
        default=True,
        description="Validate OHLCV price ranges (high >= low, etc.)",
    )
    validate_volume: bool = Field(
        default=True,
        description="Validate volume is positive",
    )
    max_price_change_pct: float = Field(
        default=0.5,
        ge=0.1,
        le=2.0,
        description="Maximum price change between candles (0.5 = 50%)",
    )

    # Timestamp validation
    validate_timestamps: bool = Field(
        default=True,
        description="Validate timestamps are sequential and complete",
    )
    allow_duplicates: bool = Field(
        default=False,
        description="Allow duplicate timestamps",
    )

    # Feature validation
    validate_features: bool = Field(
        default=True,
        description="Validate technical indicators are within expected ranges",
    )
    feature_bounds: dict = Field(
        default_factory=lambda: {
            "rsi_14": (0, 100),
            "stoch_k": (0, 100),
            "stoch_d": (0, 100),
            "cci": (-500, 500),
            "adx": (0, 100),
        },
        description="Expected bounds for features {feature_name: (min, max)}",
    )


class DataQualityConfig(BaseConfig):
    """Data quality monitoring configuration."""

    # Enable/disable monitoring
    enabled: bool = Field(
        default=True,
        description="Enable data quality monitoring",
    )

    # Monitoring frequency
    check_interval_minutes: int = Field(
        default=15,
        ge=1,
        le=1440,
        description="How often to run quality checks (in minutes)",
    )
    store_results: bool = Field(
        default=True,
        description="Store quality check results in database",
    )

    # Alert settings
    alert_on_failure: bool = Field(
        default=True,
        description="Send alerts when quality checks fail",
    )
    alert_methods: List[str] = Field(
        default=["log", "database"],
        description="Alert methods (log, database, email, slack)",
    )
    min_severity_for_alert: str = Field(
        default="warning",
        description="Minimum severity level for alerts (info, warning, error, critical)",
    )

    # Sub-configurations
    outlier_detection: OutlierDetectionConfig = Field(
        default_factory=OutlierDetectionConfig,
        description="Outlier detection settings",
    )
    missing_data: MissingDataConfig = Field(
        default_factory=MissingDataConfig,
        description="Missing data handling settings",
    )
    validation: ValidationConfig = Field(
        default_factory=ValidationConfig,
        description="Data validation rules",
    )

    # Retention
    keep_results_days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="How long to keep quality check results (in days)",
    )

    @field_validator("alert_methods")
    @classmethod
    def validate_alert_methods(cls, v: List[str]) -> List[str]:
        """Validate alert methods."""
        valid_methods = ["log", "database", "email", "slack", "webhook"]
        for method in v:
            if method.lower() not in valid_methods:
                raise ValueError(f"Alert method must be one of {valid_methods}")
        return [m.lower() for m in v]

    @field_validator("min_severity_for_alert")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity level."""
        valid_levels = ["debug", "info", "warning", "error", "critical"]
        if v.lower() not in valid_levels:
            raise ValueError(f"Severity must be one of {valid_levels}")
        return v.lower()

    def should_alert(self, severity: str) -> bool:
        """Check if alert should be sent for given severity.

        Args:
            severity: Severity level of the issue

        Returns:
            True if alert should be sent
        """
        severity_order = ["debug", "info", "warning", "error", "critical"]
        min_index = severity_order.index(self.min_severity_for_alert)
        severity_index = severity_order.index(severity.lower())
        return severity_index >= min_index
