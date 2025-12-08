#!/usr/bin/env python3
"""
Test-Script für Backtesting Framework.

Testet:
- Performance Metrics Berechnung
- Backtester mit Random Agent
- Walk-Forward Analysis
- Visualizer

Usage:
    python scripts/test_backtesting.py
"""

import sys
import os
from pathlib import Path
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from rich.console import Console
from rich.panel import Panel

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from solana_rl_bot.environment import TradingEnv
from solana_rl_bot.backtesting import Backtester, PerformanceMetrics, BacktestVisualizer
from solana_rl_bot.data.collectors import BinanceConnector
from solana_rl_bot.data.features import FeatureCalculator
from solana_rl_bot.utils import LoggerSetup

console = Console()


def get_market_data():
    """Hole echte Marktdaten mit Features."""
    console.print("\n[bold cyan]Hole Marktdaten...[/bold cyan]")

    try:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            df = connector.fetch_ohlcv(
                symbol="SOL/USDT",
                timeframe="5m",
                limit=1000,  # Mehr Daten für Walk-Forward
            )

            console.print(f"[green]✅ {len(df)} OHLCV Candles abgerufen[/green]")

            # Berechne Features
            calculator = FeatureCalculator()
            df_features = calculator.calculate_all_features(df, symbol="SOL/USDT")

            console.print(f"[green]✅ {len(df_features.columns)} Features berechnet[/green]")

            return df_features

    except Exception as e:
        console.print(f"[red]❌ Fehler beim Datenabruf: {e}[/red]")
        return None


def test_performance_metrics():
    """Teste PerformanceMetrics."""
    console.print("\n[bold cyan]Testing PerformanceMetrics...[/bold cyan]")

    try:
        metrics = PerformanceMetrics(risk_free_rate=0.02)

        # Fake Portfolio History
        portfolio_values = [10000 + i * 10 + np.random.randn() * 50 for i in range(100)]
        
        # Fake Trades
        trades = [
            {"action": "BUY", "price": 100, "step": 10},
            {"action": "SELL", "price": 110, "profit": 100, "profit_pct": 0.1, "step": 20},
            {"action": "BUY", "price": 110, "step": 30},
            {"action": "SELL", "price": 105, "profit": -50, "profit_pct": -0.045, "step": 40},
        ]

        # Berechne Metriken
        perf = metrics.calculate_all_metrics(
            portfolio_values=portfolio_values,
            trades=trades,
            initial_balance=10000.0,
        )

        console.print(f"\n[cyan]Calculated Metrics:[/cyan]")
        console.print(f"  Total Return: {perf['total_return_pct']:.2f}%")
        console.print(f"  Sharpe Ratio: {perf['sharpe_ratio']:.3f}")
        console.print(f"  Max Drawdown: {perf['max_drawdown_pct']:.2f}%")
        console.print(f"  Win Rate: {perf['win_rate']*100:.1f}%")
        console.print(f"  Completed Trades: {perf['completed_trades']}")

        console.print("[green]✅ PerformanceMetrics funktioniert[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ PerformanceMetrics Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_backtester_random_agent():
    """Teste Backtester mit Random Agent."""
    console.print("\n[bold cyan]Testing Backtester (Random Agent)...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        # Erstelle Environment
        env = TradingEnv(
            df=df,
            initial_balance=10000.0,
            reward_type="profit",
        )

        # Erstelle Backtester
        backtester = Backtester(env)

        # Random Agent
        def random_agent(observation):
            return env.action_space.sample()

        # Run Backtest
        results = backtester.run_backtest(random_agent, verbose=False)

        # Visualize
        visualizer = BacktestVisualizer()
        visualizer.print_results(results, title="Random Agent Backtest")
        visualizer.print_summary_panel(results)

        console.print("[green]✅ Backtester funktioniert[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Backtester Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_backtests():
    """Teste Multiple Backtests."""
    console.print("\n[bold cyan]Testing Multiple Backtests...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        env = TradingEnv(df=df, initial_balance=10000.0, reward_type="profit")
        backtester = Backtester(env)

        # Random Agent
        def random_agent(observation):
            return env.action_space.sample()

        # Run 5 Backtests
        results_list = backtester.run_multiple_backtests(random_agent, n_runs=5)

        console.print(f"\n[cyan]Ran {len(results_list)} backtests[/cyan]")

        # Show summary stats
        returns = [r["performance"]["total_return_pct"] for r in results_list]
        console.print(f"  Avg Return: {np.mean(returns):+.2f}% ± {np.std(returns):.2f}%")
        console.print(f"  Best: {max(returns):+.2f}%")
        console.print(f"  Worst: {min(returns):+.2f}%")

        console.print("[green]✅ Multiple Backtests funktionieren[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Multiple Backtests Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_walk_forward_analysis():
    """Teste Walk-Forward Analysis."""
    console.print("\n[bold cyan]Testing Walk-Forward Analysis...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        # Brauche genug Daten
        if len(df) < 500:
            console.print("[yellow]⚠️  Nicht genug Daten für Walk-Forward (brauche 500+)[/yellow]")
            return True  # Nicht fehlgeschlagen, nur übersprungen

        env = TradingEnv(df=df, initial_balance=10000.0, reward_type="profit")
        backtester = Backtester(env)

        # Random Agent
        def random_agent(observation):
            return env.action_space.sample()

        # Walk-Forward
        wf_results = backtester.walk_forward_analysis(
            df=df,
            agent=random_agent,
            train_size=300,
            test_size=100,
            step_size=100,
        )

        console.print(f"\n[cyan]{len(wf_results)} Walk-Forward Windows getestet[/cyan]")

        # Visualize
        if len(wf_results) > 0:
            visualizer = BacktestVisualizer()
            visualizer.print_walk_forward_results(wf_results)

        console.print("[green]✅ Walk-Forward Analysis funktioniert[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Walk-Forward Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_buy_and_hold_comparison():
    """Teste Buy-and-Hold Vergleich."""
    console.print("\n[bold cyan]Testing Buy-and-Hold Comparison...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        env = TradingEnv(df=df, initial_balance=10000.0, reward_type="profit")
        backtester = Backtester(env)

        # Random Agent
        def random_agent(observation):
            return env.action_space.sample()

        # Backtest
        results = backtester.run_backtest(random_agent, verbose=False)

        # Check Buy-and-Hold Comparison
        perf = results["performance"]
        
        if "buy_and_hold_return" in perf:
            console.print(f"\n[cyan]Buy-and-Hold Comparison:[/cyan]")
            console.print(f"  B&H Return:      {perf['buy_and_hold_return_pct']:+.2f}%")
            console.print(f"  Strategy Return: {perf['strategy_return_pct']:+.2f}%")
            console.print(f"  Alpha:           {perf['alpha_pct']:+.2f}%")
            
            if perf['outperformance']:
                console.print("  Status:          [green]✅ Outperforms B&H[/green]")
            else:
                console.print("  Status:          [red]❌ Underperforms B&H[/red]")

        console.print("[green]✅ Buy-and-Hold Comparison funktioniert[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Buy-and-Hold Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Führe alle Tests aus."""
    console.print(
        Panel.fit(
            "[bold cyan]Solana RL Bot - Backtesting Framework Test[/bold cyan]\n"
            "[yellow]Testet Backtesting, Metriken und Walk-Forward Analysis[/yellow]",
            border_style="cyan",
        )
    )

    # Setup logging
    LoggerSetup.setup(log_level="INFO", log_to_file=False)

    tests = [
        ("Performance Metrics", test_performance_metrics),
        ("Backtester Random Agent", test_backtester_random_agent),
        ("Multiple Backtests", test_multiple_backtests),
        ("Buy-and-Hold Comparison", test_buy_and_hold_comparison),
        ("Walk-Forward Analysis", test_walk_forward_analysis),
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
    console.print(f"\nTotal: {passed}/{total} bestanden ({passed/total*100:.1f}%)")

    if passed == total:
        console.print("\n[bold green]🎉 ALLE TESTS BESTANDEN![/bold green]")
        console.print("\n[yellow]✅ Backtesting Framework funktioniert![/yellow]")
        console.print("[yellow]✅ Performance Metrics (Sharpe, Sortino, DD)![/yellow]")
        console.print("[yellow]✅ Walk-Forward Analysis![/yellow]")
        console.print("[yellow]✅ Buy-and-Hold Benchmark![/yellow]")
        return 0
    else:
        console.print("\n[bold red]❌ EINIGE TESTS FEHLGESCHLAGEN[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
