#!/usr/bin/env python3
"""
Test script for Binance connection and API keys.

Usage:
    python scripts/test_binance_connection.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from solana_rl_bot.data.collectors import BinanceConnector
from solana_rl_bot.utils import LoggerSetup

console = Console()


def test_api_keys():
    """Test if API keys are configured."""
    console.print("\n[bold cyan]Testing API Keys Configuration...[/bold cyan]")

    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

    if not api_key:
        console.print("[red]❌ BINANCE_API_KEY not found in .env[/red]")
        return False

    if not api_secret:
        console.print("[red]❌ BINANCE_API_SECRET not found in .env[/red]")
        return False

    # Show masked keys
    masked_key = api_key[:8] + "***" + api_key[-4:]
    masked_secret = api_secret[:8] + "***"

    table = Table(title="API Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("API Key", masked_key)
    table.add_row("Secret Key", masked_secret)
    table.add_row("Testnet", str(testnet))

    console.print(table)
    console.print("[green]✅ API keys are configured[/green]")

    return True


def test_connection():
    """Test connection to Binance."""
    console.print("\n[bold cyan]Testing Binance Connection...[/bold cyan]")

    try:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        # Create connector
        connector = BinanceConnector(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
        )

        # Connect
        if not connector.connect():
            console.print("[red]❌ Failed to connect[/red]")
            return False

        console.print(f"[green]✅ Connected to Binance ({'testnet' if testnet else 'live'})[/green]")

        # Get supported symbols
        symbols = connector.get_supported_symbols()
        console.print(f"[green]✅ {len(symbols)} trading pairs available[/green]")

        # Get supported timeframes
        timeframes = connector.get_supported_timeframes()
        console.print(f"[green]✅ Supported timeframes: {', '.join(timeframes)}[/green]")

        connector.close()
        return True

    except Exception as e:
        console.print(f"[red]❌ Connection failed: {e}[/red]")
        return False


def test_fetch_ohlcv():
    """Test fetching OHLCV data."""
    console.print("\n[bold cyan]Testing OHLCV Data Fetch...[/bold cyan]")

    try:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            # Fetch recent SOL/USDT data
            symbol = "SOL/USDT"
            timeframe = "5m"
            limit = 10

            console.print(f"Fetching {limit} candles for {symbol} ({timeframe})...")

            df = connector.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
            )

            if df.empty:
                console.print("[red]❌ No data received[/red]")
                return False

            console.print(f"[green]✅ Received {len(df)} candles[/green]")

            # Show sample data
            table = Table(title=f"{symbol} {timeframe} - Latest 5 Candles")
            table.add_column("Time", style="cyan")
            table.add_column("Open", style="green")
            table.add_column("High", style="green")
            table.add_column("Low", style="red")
            table.add_column("Close", style="yellow")
            table.add_column("Volume", style="blue")

            for _, row in df.tail(5).iterrows():
                table.add_row(
                    row["timestamp"].strftime("%Y-%m-%d %H:%M"),
                    f"${row['open']:.2f}",
                    f"${row['high']:.2f}",
                    f"${row['low']:.2f}",
                    f"${row['close']:.2f}",
                    f"{row['volume']:.2f}",
                )

            console.print(table)

            return True

    except Exception as e:
        console.print(f"[red]❌ OHLCV fetch failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_batch_fetch():
    """Test batch fetching for large time ranges."""
    console.print("\n[bold cyan]Testing Batch OHLCV Fetch...[/bold cyan]")

    try:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            # Fetch last 7 days of 5m data
            symbol = "SOL/USDT"
            timeframe = "5m"
            start_time = datetime.now(timezone.utc) - timedelta(days=7)

            console.print(f"Fetching 7 days of {symbol} {timeframe} data...")

            df = connector.fetch_ohlcv_batch(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                batch_size=1000,
            )

            if df.empty:
                console.print("[red]❌ No data received[/red]")
                return False

            console.print(f"[green]✅ Received {len(df)} candles[/green]")
            console.print(f"[green]✅ Date range: {df['timestamp'].min()} to {df['timestamp'].max()}[/green]")

            return True

    except Exception as e:
        console.print(f"[red]❌ Batch fetch failed: {e}[/red]")
        return False


def main():
    """Run all tests."""
    console.print(
        Panel.fit(
            "[bold cyan]Solana RL Bot - Binance Connection Test[/bold cyan]",
            border_style="cyan",
        )
    )

    # Setup logging
    LoggerSetup.setup(log_level="INFO", log_to_file=False)

    tests = [
        ("API Keys Configuration", test_api_keys),
        ("Binance Connection", test_connection),
        ("OHLCV Data Fetch", test_fetch_ohlcv),
        ("Batch OHLCV Fetch", test_batch_fetch),
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
        console.print("\n[bold green]🎉 ALL TESTS PASSED![/bold green]")
        console.print("\n[yellow]✅ Your Binance API keys are working![/yellow]")
        console.print("[yellow]✅ You can now collect market data![/yellow]")
        return 0
    else:
        console.print("\n[bold red]❌ SOME TESTS FAILED[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
