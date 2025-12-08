#!/usr/bin/env python3
"""
Test script for logging system.

Usage:
    python scripts/test_logging.py
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from rich.console import Console
from rich.panel import Panel

from solana_rl_bot.utils.logging import (
    LoggerSetup,
    get_logger,
    log_function_call,
    log_performance,
    PerformanceLogger,
    log_trade,
    log_performance_metric,
    log_error,
    bot_logger,
)

console = Console()


def test_basic_logging():
    """Test basic logging functionality."""
    console.print("\n[bold cyan]Testing Basic Logging...[/bold cyan]")

    logger = get_logger(__name__)

    # Test different log levels
    logger.debug("🔍 This is a DEBUG message")
    logger.info("ℹ️  This is an INFO message")
    logger.warning("⚠️  This is a WARNING message")
    logger.error("❌ This is an ERROR message")

    console.print("[green]✅ Basic logging test completed[/green]")


def test_trade_logging():
    """Test trade event logging."""
    console.print("\n[bold cyan]Testing Trade Logging...[/bold cyan]")

    # Simulate some trades
    log_trade("BUY", "SOL/USDT", 0.5, 125.34, strategy="ppo_agent", session_id="test123")
    time.sleep(0.5)
    log_trade(
        "SELL", "SOL/USDT", 0.5, 127.89, strategy="ppo_agent", pnl=1.27, pnl_percent=2.03
    )

    console.print("[green]✅ Trade logging test completed[/green]")


def test_performance_metrics():
    """Test performance metric logging."""
    console.print("\n[bold cyan]Testing Performance Metrics...[/bold cyan]")

    # Log some metrics
    log_performance_metric("sharpe_ratio", 1.85, strategy="ppo_agent")
    log_performance_metric("total_return", 0.0523, strategy="ppo_agent")
    log_performance_metric("max_drawdown", -0.0823, strategy="ppo_agent")
    log_performance_metric("win_rate", 0.65, strategy="ppo_agent")

    console.print("[green]✅ Performance metrics test completed[/green]")


@log_function_call(log_args=True, log_result=True)
def example_function(x: int, y: int) -> int:
    """Example function with logging decorator."""
    return x + y


@log_performance
def slow_operation():
    """Simulate a slow operation."""
    time.sleep(0.5)
    return "Done"


def test_decorators():
    """Test logging decorators."""
    console.print("\n[bold cyan]Testing Decorators...[/bold cyan]")

    # Test function call decorator
    result = example_function(5, 3)
    console.print(f"Function result: {result}")

    # Test performance decorator
    result = slow_operation()
    console.print(f"Slow operation result: {result}")

    console.print("[green]✅ Decorator tests completed[/green]")


def test_performance_logger():
    """Test performance logger context manager."""
    console.print("\n[bold cyan]Testing Performance Logger...[/bold cyan]")

    with PerformanceLogger("Database Query"):
        time.sleep(0.3)
        # Simulate database work

    with PerformanceLogger("API Request"):
        time.sleep(0.2)
        # Simulate API call

    console.print("[green]✅ Performance logger test completed[/green]")


def test_error_logging():
    """Test error logging."""
    console.print("\n[bold cyan]Testing Error Logging...[/bold cyan]")

    try:
        # Simulate an error
        result = 1 / 0
    except ZeroDivisionError as e:
        log_error(e, context={"operation": "division", "numerator": 1, "denominator": 0})

    try:
        # Another error
        raise ValueError("Invalid configuration parameter")
    except ValueError as e:
        log_error(e, context={"parameter": "max_risk", "value": -0.5})

    console.print("[green]✅ Error logging test completed[/green]")


def test_structured_logging():
    """Test structured logging with extra fields."""
    console.print("\n[bold cyan]Testing Structured Logging...[/bold cyan]")

    logger = get_logger(__name__)

    # Log with extra context
    logger.info(
        "Trading session started",
        extra={
            "session_id": "test_session_123",
            "strategy": "ppo_agent",
            "initial_capital": 10000.0,
            "symbols": ["SOL/USDT", "BTC/USDT"],
        },
    )

    logger.info(
        "Market data fetched",
        extra={"symbol": "SOL/USDT", "candles": 1000, "timeframe": "5m", "elapsed_ms": 245},
    )

    console.print("[green]✅ Structured logging test completed[/green]")


def test_log_levels():
    """Test different log levels."""
    console.print("\n[bold cyan]Testing Log Levels...[/bold cyan]")

    # Test that DEBUG messages appear when log level is DEBUG
    LoggerSetup.setup(log_level="DEBUG", log_to_file=False)

    logger = get_logger(__name__)
    logger.debug("This DEBUG message should appear")
    logger.info("This INFO message should appear")

    # Change to INFO level
    console.print("\n[yellow]Changing log level to INFO...[/yellow]")
    LoggerSetup._initialized = False  # Reset to allow re-initialization
    LoggerSetup.setup(log_level="INFO", log_to_file=False)

    logger.debug("This DEBUG message should NOT appear")
    logger.info("This INFO message should appear")

    console.print("[green]✅ Log level tests completed[/green]")


def main():
    """Run all logging tests."""
    console.print(
        Panel.fit(
            "[bold cyan]Solana RL Bot - Logging System Test Suite[/bold cyan]",
            border_style="cyan",
        )
    )

    # Setup logging
    log_dir = Path("logs/test")
    LoggerSetup.setup(log_level="DEBUG", log_to_file=True, log_dir=log_dir)

    bot_logger.info("🚀 Starting logging tests...")

    tests = [
        ("Basic Logging", test_basic_logging),
        ("Trade Logging", test_trade_logging),
        ("Performance Metrics", test_performance_metrics),
        ("Decorators", test_decorators),
        ("Performance Logger", test_performance_logger),
        ("Error Logging", test_error_logging),
        ("Structured Logging", test_structured_logging),
        ("Log Levels", test_log_levels),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            console.print(f"[red]❌ {name} failed: {e}[/red]")
            failed += 1

    # Summary
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]Test Summary[/bold cyan]")
    console.print("=" * 60)
    console.print(f"✅ Passed: {passed}")
    console.print(f"❌ Failed: {failed}")
    console.print(f"Total: {passed + failed}")

    # Check log files
    console.print("\n[bold cyan]Log Files Created:[/bold cyan]")
    if log_dir.exists():
        for log_file in log_dir.glob("*.log"):
            size = log_file.stat().st_size
            console.print(f"  📄 {log_file.name} ({size} bytes)")
    else:
        console.print("  [yellow]⚠️  Log directory not found[/yellow]")

    if failed == 0:
        console.print("\n[bold green]🎉 ALL LOGGING TESTS PASSED![/bold green]")
        bot_logger.success("✅ Logging system test suite completed successfully!")
        return 0
    else:
        console.print("\n[bold red]❌ SOME TESTS FAILED[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
