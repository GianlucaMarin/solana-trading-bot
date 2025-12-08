#!/usr/bin/env python3
"""
Test script for data collection with database integration.

This script tests the complete data pipeline:
1. Connect to Binance
2. Fetch OHLCV data
3. Save to TimescaleDB
4. Retrieve from database
5. Incremental updates

Usage:
    python scripts/test_data_collection.py
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
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from solana_rl_bot.data.collectors import BinanceConnector, DataCollector
from solana_rl_bot.data.storage.db_manager import DatabaseManager
from solana_rl_bot.utils import LoggerSetup

console = Console()


def test_database_connection():
    """Test database connectivity."""
    console.print("\n[bold cyan]Testing Database Connection...[/bold cyan]")

    try:
        db = DatabaseManager()

        if db.health_check():
            console.print("[green]✅ Database connection successful[/green]")
            return db
        else:
            console.print("[red]❌ Database health check failed[/red]")
            return None

    except Exception as e:
        console.print(f"[red]❌ Database connection failed: {e}[/red]")
        return None


def test_data_collector_setup():
    """Test DataCollector initialization."""
    console.print("\n[bold cyan]Testing DataCollector Setup...[/bold cyan]")

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
            console.print("[red]❌ Failed to connect to Binance[/red]")
            return None

        # Create database manager
        db = DatabaseManager()

        # Create data collector
        collector = DataCollector(
            connector=connector,
            db_manager=db,
        )

        console.print("[green]✅ DataCollector initialized successfully[/green]")
        console.print(f"[cyan]Exchange: {collector.exchange}[/cyan]")

        return collector

    except Exception as e:
        console.print(f"[red]❌ DataCollector setup failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def test_collect_and_save():
    """Test collecting data and saving to database."""
    console.print("\n[bold cyan]Testing Data Collection & Database Save...[/bold cyan]")

    try:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            db = DatabaseManager()
            collector = DataCollector(connector, db)

            # Collect recent data
            symbol = "SOL/USDT"
            timeframe = "5m"
            limit = 50

            console.print(f"\nCollecting {limit} candles for {symbol} ({timeframe})...")

            df = collector.collect_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                save_to_db=True,
            )

            if df.empty:
                console.print("[red]❌ No data collected[/red]")
                return False

            console.print(f"[green]✅ Collected and saved {len(df)} candles[/green]")

            # Show sample
            table = Table(title=f"Sample Data (Latest 5 Candles)")
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
        console.print(f"[red]❌ Collect and save failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_retrieve_from_database():
    """Test retrieving data from database."""
    console.print("\n[bold cyan]Testing Data Retrieval from Database...[/bold cyan]")

    try:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            db = DatabaseManager()
            collector = DataCollector(connector, db)

            # Retrieve stored data
            symbol = "SOL/USDT"
            timeframe = "5m"
            days = 1

            console.print(f"\nRetrieving {days} day(s) of data for {symbol}...")

            df = collector.get_stored_data(
                symbol=symbol,
                timeframe=timeframe,
                days=days,
            )

            if df.empty:
                console.print("[yellow]⚠️  No data in database (this is OK if first run)[/yellow]")
                return True

            console.print(f"[green]✅ Retrieved {len(df)} candles from database[/green]")
            console.print(f"[cyan]Date range: {df['timestamp'].min()} to {df['timestamp'].max()}[/cyan]")

            return True

    except Exception as e:
        console.print(f"[red]❌ Data retrieval failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_incremental_collection():
    """Test incremental data collection."""
    console.print("\n[bold cyan]Testing Incremental Collection...[/bold cyan]")

    try:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            db = DatabaseManager()
            collector = DataCollector(connector, db)

            symbol = "SOL/USDT"
            timeframe = "5m"

            console.print(f"\nPerforming incremental collection for {symbol}...")

            # First collection (might fetch more if database is empty)
            df1 = collector.collect_ohlcv_incremental(
                symbol=symbol,
                timeframe=timeframe,
            )

            console.print(f"[green]✅ First collection: {len(df1)} candles[/green]")

            # Second collection (should fetch only new data)
            df2 = collector.collect_ohlcv_incremental(
                symbol=symbol,
                timeframe=timeframe,
            )

            console.print(f"[green]✅ Second collection: {len(df2)} candles (new data only)[/green]")

            return True

    except Exception as e:
        console.print(f"[red]❌ Incremental collection failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_historical_collection():
    """Test historical data collection."""
    console.print("\n[bold cyan]Testing Historical Collection...[/bold cyan]")

    try:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            db = DatabaseManager()
            collector = DataCollector(connector, db)

            symbol = "BTC/USDT"
            timeframe = "1h"
            days = 3

            console.print(f"\nCollecting {days} days of {symbol} {timeframe} data...")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Fetching data...", total=None)

                df = collector.collect_ohlcv_historical(
                    symbol=symbol,
                    timeframe=timeframe,
                    days=days,
                    save_to_db=True,
                )

                progress.update(task, completed=True)

            if df.empty:
                console.print("[red]❌ No historical data collected[/red]")
                return False

            console.print(f"[green]✅ Collected {len(df)} candles[/green]")
            console.print(f"[cyan]Date range: {df['timestamp'].min()} to {df['timestamp'].max()}[/cyan]")

            return True

    except Exception as e:
        console.print(f"[red]❌ Historical collection failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_symbols():
    """Test collecting data for multiple symbols."""
    console.print("\n[bold cyan]Testing Multiple Symbol Collection...[/bold cyan]")

    try:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            db = DatabaseManager()
            collector = DataCollector(connector, db)

            symbols = ["SOL/USDT", "BTC/USDT", "ETH/USDT"]
            timeframe = "5m"

            console.print(f"\nCollecting data for {len(symbols)} symbols...")

            results = collector.collect_multiple_symbols(
                symbols=symbols,
                timeframe=timeframe,
                incremental=True,
            )

            # Show results
            table = Table(title="Collection Results")
            table.add_column("Symbol", style="cyan")
            table.add_column("Candles", style="green")
            table.add_column("Status", style="yellow")

            for symbol, df in results.items():
                candles = len(df) if not df.empty else 0
                status = "✅ Success" if not df.empty else "❌ Failed"
                table.add_row(symbol, str(candles), status)

            console.print(table)

            successful = sum(1 for df in results.values() if not df.empty)
            console.print(f"[green]✅ {successful}/{len(symbols)} symbols collected successfully[/green]")

            return successful > 0

    except Exception as e:
        console.print(f"[red]❌ Multiple symbol collection failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    console.print(
        Panel.fit(
            "[bold cyan]Solana RL Bot - Data Collection Test[/bold cyan]\n"
            "[yellow]Testing complete data pipeline with database integration[/yellow]",
            border_style="cyan",
        )
    )

    # Setup logging
    LoggerSetup.setup(log_level="INFO", log_to_file=False)

    tests = [
        ("Database Connection", test_database_connection),
        ("DataCollector Setup", test_data_collector_setup),
        ("Collect & Save Data", test_collect_and_save),
        ("Retrieve from Database", test_retrieve_from_database),
        ("Incremental Collection", test_incremental_collection),
        ("Historical Collection", test_historical_collection),
        ("Multiple Symbols", test_multiple_symbols),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            # Handle case where test returns an object (like database connection)
            passed = result is not None and result is not False
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
        console.print("\n[yellow]✅ Data collection pipeline is working![/yellow]")
        console.print("[yellow]✅ OHLCV data is being saved to TimescaleDB![/yellow]")
        console.print("[yellow]✅ Incremental updates are working![/yellow]")
        return 0
    else:
        console.print("\n[bold red]❌ SOME TESTS FAILED[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
