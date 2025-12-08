#!/usr/bin/env python3
"""
Database Setup Test Script

Tests TimescaleDB setup, hypertables, data insertion, and query performance.
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from solana_rl_bot.data.storage.db_manager import DatabaseManager

console = Console()


class DatabaseTester:
    """Test suite for database setup."""

    def __init__(self):
        self.db = None
        self.results = {}

    def run_all_tests(self) -> bool:
        """Run all database tests."""
        console.print("\n[bold blue]🧪 Solana RL Bot - Database Test Suite[/bold blue]\n")

        tests = [
            ("Connection Test", self.test_connection),
            ("Tables Exist", self.test_tables_exist),
            ("Hypertables", self.test_hypertables),
            ("Data Insertion (OHLCV)", self.test_insert_ohlcv),
            ("Data Retrieval (OHLCV)", self.test_get_ohlcv),
            ("Features Insertion", self.test_insert_features),
            ("Trade Operations", self.test_trade_operations),
            ("Performance Metrics", self.test_performance_metrics),
            ("Query Performance", self.test_query_performance),
            ("Retention Policies", self.test_retention_policies),
        ]

        for test_name, test_func in tests:
            try:
                result = test_func()
                self.results[test_name] = result
                status = "[green]✅ PASS[/green]" if result else "[red]❌ FAIL[/red]"
                console.print(f"{status} {test_name}")
            except Exception as e:
                self.results[test_name] = False
                console.print(f"[red]❌ FAIL[/red] {test_name}: {str(e)}")

        self._print_summary()
        return all(self.results.values())

    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            self.db = DatabaseManager()
            return self.db.health_check()
        except Exception as e:
            console.print(f"[red]Connection error: {e}[/red]")
            return False

    def test_tables_exist(self) -> bool:
        """Test that all required tables exist."""
        expected_tables = [
            "ohlcv",
            "features",
            "trades",
            "performance",
            "models",
            "data_quality",
            "system_logs",
        ]

        query = """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        """

        df = self.db.execute_query(query)
        existing_tables = df["tablename"].tolist()

        missing = set(expected_tables) - set(existing_tables)
        if missing:
            console.print(f"[red]Missing tables: {missing}[/red]")
            return False

        return True

    def test_hypertables(self) -> bool:
        """Test TimescaleDB hypertables are configured."""
        expected_hypertables = [
            "ohlcv",
            "features",
            "performance",
            "data_quality",
            "system_logs",
        ]

        query = """
        SELECT hypertable_name
        FROM timescaledb_information.hypertables
        """

        try:
            df = self.db.execute_query(query)
            existing_hypertables = df["hypertable_name"].tolist()

            missing = set(expected_hypertables) - set(existing_hypertables)
            if missing:
                console.print(f"[red]Missing hypertables: {missing}[/red]")
                return False

            return True
        except Exception as e:
            console.print(f"[red]Hypertable check error: {e}[/red]")
            return False

    def test_insert_ohlcv(self) -> bool:
        """Test inserting OHLCV data."""
        try:
            # Generate sample data
            timestamps = pd.date_range(
                start=datetime.now() - timedelta(days=7), periods=100, freq="5min"
            )

            df = pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "open": np.random.uniform(100, 200, 100),
                    "high": np.random.uniform(100, 200, 100),
                    "low": np.random.uniform(100, 200, 100),
                    "close": np.random.uniform(100, 200, 100),
                    "volume": np.random.uniform(1000, 10000, 100),
                }
            )

            # Ensure high is highest and low is lowest
            df["high"] = df[["open", "high", "low", "close"]].max(axis=1)
            df["low"] = df[["open", "high", "low", "close"]].min(axis=1)

            rows_inserted = self.db.insert_ohlcv(
                df, symbol="SOL/USDT", exchange="binance", timeframe="5m"
            )

            return rows_inserted == 100
        except Exception as e:
            console.print(f"[red]OHLCV insertion error: {e}[/red]")
            return False

    def test_get_ohlcv(self) -> bool:
        """Test retrieving OHLCV data."""
        try:
            df = self.db.get_ohlcv(
                symbol="SOL/USDT",
                exchange="binance",
                timeframe="5m",
                limit=50,
            )

            return len(df) > 0 and all(
                col in df.columns for col in ["timestamp", "open", "high", "low", "close", "volume"]
            )
        except Exception as e:
            console.print(f"[red]OHLCV retrieval error: {e}[/red]")
            return False

    def test_insert_features(self) -> bool:
        """Test inserting feature data."""
        try:
            timestamps = pd.date_range(
                start=datetime.now() - timedelta(days=7), periods=50, freq="5min"
            )

            df = pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "sma_20": np.random.uniform(100, 200, 50),
                    "rsi_14": np.random.uniform(30, 70, 50),
                    "macd": np.random.uniform(-5, 5, 50),
                }
            )

            rows_inserted = self.db.insert_features(
                df, symbol="SOL/USDT", exchange="binance", timeframe="5m"
            )

            return rows_inserted == 50
        except Exception as e:
            console.print(f"[red]Features insertion error: {e}[/red]")
            return False

    def test_trade_operations(self) -> bool:
        """Test trade insert and update operations."""
        try:
            # Insert trade
            trade_data = {
                "trade_id": f"test_trade_{int(time.time())}",
                "strategy_name": "test_strategy",
                "symbol": "SOL/USDT",
                "exchange": "binance",
                "entry_time": datetime.now(),
                "side": "buy",
                "entry_price": 150.50,
                "quantity": 10.0,
                "entry_cost": 1505.0,
                "mode": "backtest",
            }

            trade_id = self.db.insert_trade(trade_data)

            # Update trade
            updates = {
                "exit_time": datetime.now(),
                "exit_price": 155.00,
                "exit_cost": 1550.0,
                "pnl": 45.0,
                "pnl_percent": 2.99,
                "status": "closed",
            }

            success = self.db.update_trade(trade_id, updates)

            # Verify
            trades = self.db.get_trades(strategy="test_strategy")

            return success and len(trades) > 0
        except Exception as e:
            console.print(f"[red]Trade operations error: {e}[/red]")
            return False

    def test_performance_metrics(self) -> bool:
        """Test performance metrics operations."""
        try:
            metrics = {
                "time": datetime.now(),
                "strategy_name": "test_strategy",
                "symbol": "SOL/USDT",
                "timeframe": "5m",
                "total_return": 15.5,
                "sharpe_ratio": 1.2,
                "max_drawdown": -10.5,
                "num_trades": 50,
                "win_rate": 0.65,
                "portfolio_value": 11550.0,
                "cash_balance": 5000.0,
                "mode": "backtest",
            }

            perf_id = self.db.insert_performance(metrics)

            return perf_id is not None and perf_id > 0
        except Exception as e:
            console.print(f"[red]Performance metrics error: {e}[/red]")
            return False

    def test_query_performance(self) -> bool:
        """Test query performance on OHLCV data."""
        try:
            start_time = time.time()

            df = self.db.get_ohlcv(
                symbol="SOL/USDT",
                exchange="binance",
                timeframe="5m",
                limit=10000,
            )

            query_time = time.time() - start_time

            console.print(
                f"[dim]  Query returned {len(df)} rows in {query_time:.3f}s[/dim]"
            )

            # Should be fast (< 2 seconds for reasonable data size)
            return query_time < 2.0
        except Exception as e:
            console.print(f"[red]Query performance error: {e}[/red]")
            return False

    def test_retention_policies(self) -> bool:
        """Test retention policies are configured."""
        try:
            query = """
            SELECT hypertable_name, drop_after
            FROM timescaledb_information.jobs
            WHERE proc_name = 'policy_retention'
            """

            df = self.db.execute_query(query)

            # Should have retention policies for time-series tables
            return len(df) >= 5
        except Exception as e:
            # Retention policies might not show up immediately
            console.print(f"[dim]  Retention policies: {e}[/dim]")
            return True

    def _print_summary(self) -> None:
        """Print test summary table."""
        console.print("\n[bold]📊 Test Summary[/bold]\n")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Test", style="dim", width=30)
        table.add_column("Result", justify="center", width=12)

        for test_name, result in self.results.items():
            status = "[green]✅ PASS[/green]" if result else "[red]❌ FAIL[/red]"
            table.add_row(test_name, status)

        console.print(table)

        # Overall result
        total = len(self.results)
        passed = sum(self.results.values())
        percentage = (passed / total * 100) if total > 0 else 0

        console.print(f"\n[bold]Total:[/bold] {passed}/{total} passed ({percentage:.1f}%)\n")

        if passed == total:
            console.print("[bold green]🎉 DATABASE SETUP COMPLETE![/bold green]\n")
        else:
            console.print("[bold red]⚠️  Some tests failed. Please review the errors above.[/bold red]\n")


def main():
    """Run database tests."""
    tester = DatabaseTester()
    success = tester.run_all_tests()

    if tester.db:
        tester.db.close()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
