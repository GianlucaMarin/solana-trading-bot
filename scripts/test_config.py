#!/usr/bin/env python3
"""
Test script for configuration system.

Usage:
    python scripts/test_config.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from solana_rl_bot.config import (
    load_config,
    DatabaseConfig,
    ExchangeConfig,
    TradingConfig,
    DataQualityConfig,
)

console = Console()


def test_database_config():
    """Test DatabaseConfig."""
    console.print("\n[bold cyan]Testing DatabaseConfig...[/bold cyan]")

    try:
        # Test with defaults
        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.pool_size == 10

        # Test connection string
        conn_str = config.get_connection_string(include_password=False)
        assert "***" in conn_str

        console.print("[green]✅ DatabaseConfig tests passed[/green]")
        return True
    except Exception as e:
        console.print(f"[red]❌ DatabaseConfig tests failed: {e}[/red]")
        return False


def test_exchange_config():
    """Test ExchangeConfig."""
    console.print("\n[bold cyan]Testing ExchangeConfig...[/bold cyan]")

    try:
        # Test with defaults
        config = ExchangeConfig()
        assert config.name == "binance"
        assert "SOL/USDT" in config.symbols
        assert config.default_symbol == "SOL/USDT"

        # Test safe dict
        config_with_keys = ExchangeConfig(
            api_key="my_secret_key_1234",
            api_secret="my_secret_secret",
        )
        safe_dict = config_with_keys.get_safe_dict()
        assert "***1234" in safe_dict["api_key"]
        assert safe_dict["api_secret"] == "***"

        console.print("[green]✅ ExchangeConfig tests passed[/green]")
        return True
    except Exception as e:
        console.print(f"[red]❌ ExchangeConfig tests failed: {e}[/red]")
        return False


def test_trading_config():
    """Test TradingConfig."""
    console.print("\n[bold cyan]Testing TradingConfig...[/bold cyan]")

    try:
        # Test with defaults
        config = TradingConfig()
        assert config.initial_capital == 10000.0
        assert config.max_open_positions == 3

        # Test available capital calculation
        config = TradingConfig(
            initial_capital=10000.0,
            reserve_capital_pct=0.1,
        )
        available = config.get_available_capital()
        assert available == 9000.0

        # Test risk management
        assert config.risk_management.max_risk_per_trade == 0.02
        assert config.risk_management.use_stop_loss is True

        console.print("[green]✅ TradingConfig tests passed[/green]")
        return True
    except Exception as e:
        console.print(f"[red]❌ TradingConfig tests failed: {e}[/red]")
        return False


def test_data_quality_config():
    """Test DataQualityConfig."""
    console.print("\n[bold cyan]Testing DataQualityConfig...[/bold cyan]")

    try:
        # Test with defaults
        config = DataQualityConfig()
        assert config.enabled is True
        assert config.check_interval_minutes == 15

        # Test alert severity
        config = DataQualityConfig(min_severity_for_alert="warning")
        assert config.should_alert("error") is True
        assert config.should_alert("info") is False

        console.print("[green]✅ DataQualityConfig tests passed[/green]")
        return True
    except Exception as e:
        console.print(f"[red]❌ DataQualityConfig tests failed: {e}[/red]")
        return False


def test_load_config():
    """Test loading configuration from YAML."""
    console.print("\n[bold cyan]Testing Config Loading...[/bold cyan]")

    try:
        # Load development config
        config = load_config(environment="development")

        # Verify config loaded
        assert config.environment == "development"
        assert config.database is not None
        assert config.exchange is not None
        assert config.trading is not None
        assert config.data_quality is not None

        console.print(f"[green]✅ Loaded {config.environment} config successfully[/green]")

        # Display config summary
        table = Table(title="Configuration Summary")
        table.add_column("Section", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Environment", config.environment)
        table.add_row("Log Level", config.log_level)
        table.add_row("Database", f"{config.database.host}:{config.database.port}")
        table.add_row("Exchange", config.exchange.name)
        table.add_row("Trading Mode", str(config.trading.mode))
        table.add_row("Initial Capital", f"${config.trading.initial_capital:,.2f}")
        table.add_row("Max Positions", str(config.trading.max_open_positions))
        table.add_row(
            "Max Risk/Trade",
            f"{config.trading.risk_management.max_risk_per_trade * 100}%",
        )
        table.add_row(
            "Data Quality Checks",
            "Enabled" if config.data_quality.enabled else "Disabled",
        )

        console.print(table)
        return True

    except Exception as e:
        console.print(f"[red]❌ Config loading failed: {e}[/red]")
        import traceback

        traceback.print_exc()
        return False


def test_all_environments():
    """Test loading all environment configs."""
    console.print("\n[bold cyan]Testing All Environments...[/bold cyan]")

    environments = ["development", "paper", "production"]
    results = {}

    for env in environments:
        try:
            config = load_config(environment=env)
            results[env] = "✅ Pass"
            console.print(f"[green]✅ {env.capitalize()}: Loaded successfully[/green]")
        except Exception as e:
            results[env] = f"❌ Fail: {e}"
            console.print(f"[red]❌ {env.capitalize()}: {e}[/red]")

    # Summary table
    table = Table(title="Environment Loading Summary")
    table.add_column("Environment", style="cyan")
    table.add_column("Status", style="green")

    for env, status in results.items():
        table.add_row(env.capitalize(), status)

    console.print(table)
    return all("✅" in status for status in results.values())


def main():
    """Run all configuration tests."""
    console.print(
        Panel.fit(
            "[bold cyan]Solana RL Bot - Configuration Test Suite[/bold cyan]",
            border_style="cyan",
        )
    )

    tests = [
        ("DatabaseConfig", test_database_config),
        ("ExchangeConfig", test_exchange_config),
        ("TradingConfig", test_trading_config),
        ("DataQualityConfig", test_data_quality_config),
        ("Config Loading", test_load_config),
        ("All Environments", test_all_environments),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            console.print(f"[red]❌ {name} crashed: {e}[/red]")
            results.append((name, False))

    # Summary
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]Test Summary[/bold cyan]")
    console.print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[green]✅ PASS[/green]" if result else "[red]❌ FAIL[/red]"
        console.print(f"{status} {name}")

    console.print("=" * 60)
    console.print(f"\nTotal: {passed}/{total} passed ({passed/total*100:.1f}%)")

    if passed == total:
        console.print("\n[bold green]🎉 ALL CONFIGURATION TESTS PASSED![/bold green]")
        return 0
    else:
        console.print("\n[bold red]❌ SOME TESTS FAILED[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
