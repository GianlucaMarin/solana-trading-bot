"""
Tests for configuration system.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from solana_rl_bot.config import (
    load_config,
    get_config,
    set_config,
    reset_config,
    DatabaseConfig,
    ExchangeConfig,
    TradingConfig,
    DataQualityConfig,
    TradingMode,
    PositionSizing,
)


@pytest.fixture
def clean_config():
    """Reset global config before and after each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def sample_env_vars():
    """Sample environment variables for testing."""
    return {
        "TIMESCALE_HOST": "testdb.example.com",
        "TIMESCALE_PORT": "5433",
        "TIMESCALE_DB": "test_trading",
        "TIMESCALE_USER": "testuser",
        "TIMESCALE_PASSWORD": "testpass123",
        "BINANCE_API_KEY": "test_api_key",
        "BINANCE_API_SECRET": "test_api_secret",
        "BINANCE_TESTNET": "true",
        "ENVIRONMENT": "development",
        "LOG_LEVEL": "DEBUG",
    }


class TestDatabaseConfig:
    """Tests for DatabaseConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "trading_bot"
        assert config.pool_size == 10
        assert config.max_overflow == 20

    def test_from_env(self, sample_env_vars):
        """Test loading from environment variables."""
        with patch.dict(os.environ, sample_env_vars):
            config = DatabaseConfig.from_env()
            assert config.host == "testdb.example.com"
            assert config.port == 5433
            assert config.database == "test_trading"
            assert config.user == "testuser"
            assert config.password == "testpass123"

    def test_connection_string(self):
        """Test connection string generation."""
        config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="trading_bot",
            user="postgres",
            password="secret123",
        )
        conn_str = config.get_connection_string()
        assert "postgresql+psycopg2://" in conn_str
        assert "postgres:secret123@localhost:5432/trading_bot" in conn_str

    def test_connection_string_no_password(self):
        """Test connection string without password."""
        config = DatabaseConfig(password="secret123")
        conn_str = config.get_connection_string(include_password=False)
        assert "***" in conn_str
        assert "secret123" not in conn_str

    def test_invalid_ssl_mode(self):
        """Test validation of SSL mode."""
        with pytest.raises(ValueError, match="ssl_mode must be one of"):
            DatabaseConfig(ssl_mode="invalid_mode")

    def test_invalid_port(self):
        """Test validation of port range."""
        with pytest.raises(ValueError):
            DatabaseConfig(port=99999)

    def test_pool_settings_validation(self):
        """Test pool settings validation."""
        config = DatabaseConfig(pool_size=5, max_overflow=10)
        assert config.pool_size == 5
        assert config.max_overflow == 10


class TestExchangeConfig:
    """Tests for ExchangeConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ExchangeConfig()
        assert config.name == "binance"
        assert config.enabled is True
        assert config.testnet is False
        assert "SOL/USDT" in config.symbols
        assert config.default_symbol == "SOL/USDT"

    def test_from_env(self, sample_env_vars):
        """Test loading from environment variables."""
        with patch.dict(os.environ, sample_env_vars):
            config = ExchangeConfig.from_env({"name": "binance"})
            assert config.api_key == "test_api_key"
            assert config.api_secret == "test_api_secret"
            assert config.testnet is True

    def test_invalid_exchange_name(self):
        """Test validation of exchange name."""
        with pytest.raises(ValueError, match="Exchange must be one of"):
            ExchangeConfig(name="invalid_exchange")

    def test_default_symbol_validation(self):
        """Test default symbol must be in symbols list."""
        with pytest.raises(ValueError, match="must be in symbols list"):
            ExchangeConfig(
                symbols=["BTC/USDT", "ETH/USDT"],
                default_symbol="SOL/USDT",
            )

    def test_default_timeframe_validation(self):
        """Test default timeframe must be in timeframes list."""
        with pytest.raises(ValueError, match="must be in timeframes list"):
            ExchangeConfig(
                timeframes=["1m", "5m", "15m"],
                default_timeframe="1h",
            )

    def test_get_safe_dict(self):
        """Test safe dictionary with masked credentials."""
        config = ExchangeConfig(
            api_key="my_secret_api_key_1234",
            api_secret="my_secret_secret",
        )
        safe_dict = config.get_safe_dict()
        assert "***1234" in safe_dict["api_key"]
        assert safe_dict["api_secret"] == "***"

    def test_rate_limit_config(self):
        """Test rate limit configuration."""
        config = ExchangeConfig()
        assert config.rate_limit.requests_per_minute == 1200
        assert config.rate_limit.orders_per_minute == 100


class TestTradingConfig:
    """Tests for TradingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TradingConfig()
        assert config.mode == TradingMode.BACKTEST
        assert config.initial_capital == 10000.0
        assert config.max_open_positions == 3
        assert config.allow_short_positions is False

    def test_risk_management_defaults(self):
        """Test risk management default values."""
        config = TradingConfig()
        rm = config.risk_management
        assert rm.max_risk_per_trade == 0.02
        assert rm.max_daily_loss == 0.05
        assert rm.max_drawdown == 0.2
        assert rm.use_stop_loss is True
        assert rm.stop_loss_pct == 0.02

    def test_execution_defaults(self):
        """Test execution default values."""
        config = TradingConfig()
        ex = config.execution
        assert ex.default_order_type == "market"
        assert ex.maker_fee == 0.0001
        assert ex.taker_fee == 0.0004

    def test_invalid_order_type(self):
        """Test validation of order type."""
        from solana_rl_bot.config.trading import ExecutionConfig

        with pytest.raises(ValueError, match="Order type must be one of"):
            ExecutionConfig(default_order_type="invalid_type")

    def test_get_available_capital(self):
        """Test available capital calculation."""
        config = TradingConfig(
            initial_capital=10000.0,
            reserve_capital_pct=0.1,
        )
        available = config.get_available_capital()
        assert available == 9000.0  # 90% of 10000

    def test_is_production_mode(self):
        """Test production mode detection."""
        config = TradingConfig(mode=TradingMode.BACKTEST)
        assert config.is_production_mode() is False

        config = TradingConfig(mode=TradingMode.LIVE)
        assert config.is_production_mode() is True

    def test_position_sizing_enum(self):
        """Test position sizing enum."""
        config = TradingConfig()
        config.risk_management.position_sizing_method = PositionSizing.KELLY
        assert config.risk_management.position_sizing_method == "kelly"

    def test_invalid_capital(self):
        """Test validation of initial capital."""
        with pytest.raises(ValueError, match="Initial capital must be positive"):
            TradingConfig(initial_capital=-1000.0)

    def test_invalid_max_positions(self):
        """Test validation of max positions."""
        with pytest.raises(ValueError, match="Must allow at least 1 open position"):
            TradingConfig(max_open_positions=0)


class TestDataQualityConfig:
    """Tests for DataQualityConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = DataQualityConfig()
        assert config.enabled is True
        assert config.check_interval_minutes == 15
        assert config.store_results is True
        assert config.alert_on_failure is True

    def test_outlier_detection_defaults(self):
        """Test outlier detection default values."""
        config = DataQualityConfig()
        od = config.outlier_detection
        assert od.enabled is True
        assert od.method == "zscore"
        assert od.zscore_threshold == 3.0
        assert od.handle_outliers == "clip"

    def test_missing_data_defaults(self):
        """Test missing data default values."""
        config = DataQualityConfig()
        md = config.missing_data
        assert md.enabled is True
        assert md.max_missing_pct == 0.05
        assert md.handle_missing == "forward_fill"

    def test_validation_defaults(self):
        """Test validation default values."""
        config = DataQualityConfig()
        val = config.validation
        assert val.validate_price_ranges is True
        assert val.validate_volume is True
        assert val.validate_timestamps is True

    def test_should_alert(self):
        """Test alert severity filtering."""
        config = DataQualityConfig(min_severity_for_alert="warning")

        assert config.should_alert("debug") is False
        assert config.should_alert("info") is False
        assert config.should_alert("warning") is True
        assert config.should_alert("error") is True
        assert config.should_alert("critical") is True

    def test_invalid_alert_method(self):
        """Test validation of alert methods."""
        with pytest.raises(ValueError, match="Alert method must be one of"):
            DataQualityConfig(alert_methods=["invalid_method"])

    def test_invalid_severity(self):
        """Test validation of severity level."""
        with pytest.raises(ValueError, match="Severity must be one of"):
            DataQualityConfig(min_severity_for_alert="invalid_level")


class TestConfigLoader:
    """Tests for configuration loader."""

    def test_load_config_development(self, clean_config, tmp_path):
        """Test loading development configuration."""
        # Create minimal YAML config
        config_file = tmp_path / "test.yaml"
        config_file.write_text(
            """
database:
  pool_size: 5

exchange:
  name: binance
  symbols:
    - SOL/USDT

trading:
  mode: backtest
  initial_capital: 5000

data_quality:
  enabled: true
"""
        )

        config = load_config(config_path=str(config_file))
        assert config.database.pool_size == 5
        assert config.exchange.name == "binance"
        assert config.trading.initial_capital == 5000.0
        assert config.data_quality.enabled is True

    def test_env_vars_override_yaml(self, clean_config, tmp_path, sample_env_vars):
        """Test environment variables override YAML config."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text(
            """
database:
  host: yaml_host
  port: 9999

exchange:
  name: binance
"""
        )

        with patch.dict(os.environ, sample_env_vars):
            config = load_config(config_path=str(config_file))
            # Env vars should override YAML
            assert config.database.host == "testdb.example.com"
            assert config.database.port == 5433
            # YAML value used where no env var
            assert config.exchange.name == "binance"

    def test_global_config(self, clean_config):
        """Test global config get/set."""
        # Should raise before initialization
        with pytest.raises(RuntimeError, match="Configuration not initialized"):
            get_config()

        # Create and set config
        config = TradingConfig()
        from solana_rl_bot.config.loader import BotConfig

        bot_config = BotConfig(
            environment="test",
            database=DatabaseConfig(),
            exchange=ExchangeConfig(),
            trading=config,
            data_quality=DataQualityConfig(),
            log_level="INFO",
        )
        set_config(bot_config)

        # Should work now
        retrieved = get_config()
        assert retrieved.trading.mode == TradingMode.BACKTEST

        # Reset works
        reset_config()
        with pytest.raises(RuntimeError):
            get_config()

    def test_validate_for_live_trading(self):
        """Test live trading validation."""
        from solana_rl_bot.config.loader import BotConfig

        # Missing API credentials should fail
        config = BotConfig(
            environment="production",
            database=DatabaseConfig(),
            exchange=ExchangeConfig(api_key=None, api_secret=None),
            trading=TradingConfig(mode=TradingMode.LIVE),
            data_quality=DataQualityConfig(),
            log_level="INFO",
        )

        with pytest.raises(ValueError, match="API credentials required"):
            config.validate_for_live_trading()

        # Too high risk should fail
        config = BotConfig(
            environment="production",
            database=DatabaseConfig(),
            exchange=ExchangeConfig(api_key="key", api_secret="secret"),
            trading=TradingConfig(
                mode=TradingMode.LIVE,
                risk_management={"max_risk_per_trade": 0.1},  # 10% too high
            ),
            data_quality=DataQualityConfig(),
            log_level="INFO",
        )

        with pytest.raises(ValueError, match="Max risk per trade too high"):
            config.validate_for_live_trading()

    def test_to_dict_to_json(self):
        """Test config serialization."""
        config = TradingConfig(
            mode=TradingMode.BACKTEST,
            initial_capital=10000.0,
        )

        # to_dict
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["mode"] == "backtest"
        assert config_dict["initial_capital"] == 10000.0

        # to_json
        config_json = config.to_json()
        assert isinstance(config_json, str)
        assert "backtest" in config_json
        assert "10000" in config_json


class TestConfigIntegration:
    """Integration tests for complete config system."""

    def test_full_config_lifecycle(self, clean_config, tmp_path):
        """Test complete config loading and usage lifecycle."""
        # Create test config file
        config_file = tmp_path / "integration.yaml"
        config_file.write_text(
            """
log_level: DEBUG

database:
  pool_size: 8
  max_overflow: 15

exchange:
  name: binance
  testnet: true
  symbols:
    - SOL/USDT
    - BTC/USDT
  default_symbol: SOL/USDT
  timeframes:
    - 5m
    - 1h
  default_timeframe: 5m

trading:
  mode: paper
  initial_capital: 5000
  max_open_positions: 2

  risk_management:
    max_risk_per_trade: 0.015
    stop_loss_pct: 0.02
    take_profit_pct: 0.04

data_quality:
  enabled: true
  check_interval_minutes: 10
"""
        )

        # Load config
        config = load_config(config_path=str(config_file), environment="test")

        # Verify all sections loaded correctly
        assert config.log_level == "DEBUG"
        assert config.database.pool_size == 8
        assert config.exchange.name == "binance"
        assert config.exchange.testnet is True
        assert config.trading.mode == TradingMode.PAPER
        assert config.trading.initial_capital == 5000.0
        assert config.trading.risk_management.max_risk_per_trade == 0.015
        assert config.data_quality.check_interval_minutes == 10

        # Set as global
        set_config(config)

        # Access from anywhere
        global_config = get_config()
        assert global_config.exchange.default_symbol == "SOL/USDT"
        assert global_config.trading.max_open_positions == 2
