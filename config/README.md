# Configuration Directory

This directory contains environment-specific YAML configuration files for the Solana RL Trading Bot.

## Files

- [development.yaml](development.yaml) - Development environment config
- [paper.yaml](paper.yaml) - Paper trading config (simulated trades with real data)
- [production.yaml](production.yaml) - Production config for live trading
- `README.md` - This file

## Configuration Philosophy

**Secrets in `.env`, Settings in YAML**

- **Secrets** (API keys, passwords, tokens) → `.env` file (never commit!)
- **Settings** (timeframes, risk limits, etc.) → YAML files (safe to commit)

## Environment Selection

The bot automatically loads the correct config based on the `ENVIRONMENT` variable:

```bash
# Development (default)
ENVIRONMENT=development python main.py

# Paper trading
ENVIRONMENT=paper python main.py

# Production (live trading)
ENVIRONMENT=production python main.py
```

Or specify a custom config file:

```python
from solana_rl_bot.config import load_config

config = load_config(config_path="config/my_custom.yaml")
```

## Configuration Structure

Each YAML file contains these sections:

### 1. Database Configuration
```yaml
database:
  host: localhost  # From .env: TIMESCALE_HOST
  port: 5432       # From .env: TIMESCALE_PORT
  pool_size: 10
  max_overflow: 20
```

Credentials (`user`, `password`) come from `.env` file automatically.

### 2. Exchange Configuration
```yaml
exchange:
  name: binance
  testnet: false
  symbols:
    - SOL/USDT
  timeframes:
    - 5m
    - 1h
```

API credentials (`api_key`, `api_secret`) come from `.env` file automatically.

### 3. Trading Configuration
```yaml
trading:
  mode: backtest  # backtest, paper, live
  initial_capital: 10000.0
  max_open_positions: 3

  risk_management:
    max_risk_per_trade: 0.02
    stop_loss_pct: 0.02
    take_profit_pct: 0.04
```

### 4. Data Quality Configuration
```yaml
data_quality:
  enabled: true
  check_interval_minutes: 15
  outlier_detection:
    enabled: true
    method: zscore
```

## Usage Example

```python
from solana_rl_bot.config import load_config, get_config

# Load config once at startup
config = load_config(environment="development")

# Access anywhere in your code
from solana_rl_bot.config import get_config
config = get_config()

print(f"Trading mode: {config.trading.mode}")
print(f"Exchange: {config.exchange.name}")
print(f"Max risk: {config.trading.risk_management.max_risk_per_trade}")
```

## Environment-Specific Settings

### Development
- Uses testnet
- DEBUG logging
- Relaxed risk limits for testing
- Small capital for experimentation

### Paper Trading
- Real market data
- Simulated trades
- Production-like risk management
- Realistic fees and slippage

### Production
- **LIVE TRADING** - Real money!
- Conservative risk limits
- Strict data quality checks
- Higher logging level (INFO)
- SSL required for database

## Creating Custom Configs

You can create your own config file:

```bash
cp config/development.yaml config/my_strategy.yaml
# Edit my_strategy.yaml
```

Load it:

```python
config = load_config(config_path="config/my_strategy.yaml")
```

## Important Notes

1. **Never commit `.env` file** - It contains secrets!
2. **YAML files are safe to commit** - No secrets here
3. **Production config uses conservative defaults** - Review before live trading
4. **All Pydantic validation applies** - Invalid configs will raise errors
5. **Environment variables override YAML** - For flexibility in deployment

## Validation

All configs are validated using Pydantic v2:

- Type checking (int, float, str, bool, enums)
- Range validation (min/max values)
- Custom validators (e.g., SSL mode, exchange name)
- Required fields check

Invalid configs will raise clear error messages at startup.

## Adding New Config Options

1. Add field to appropriate config class in `src/solana_rl_bot/config/`
2. Add default value and validation
3. Update YAML files with new option
4. Update this README

Example:

```python
# In src/solana_rl_bot/config/trading.py
class TradingConfig(BaseConfig):
    new_option: int = Field(
        default=42,
        ge=1,
        le=100,
        description="My new option"
    )
```

```yaml
# In config/development.yaml
trading:
  new_option: 50
```

## See Also

- [Main Config Documentation](../docs/configuration.md) (coming in Phase 5)
- [Environment Setup Guide](../SETUP_VALIDATION.md)
- [Database Configuration](../docker/README.md)
