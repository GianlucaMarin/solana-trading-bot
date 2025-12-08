#!/usr/bin/env python3
"""
Test-Script für Reward Functions.

Testet:
- Alle 5 Reward Functions
- Vergleich mit Random Agent
- Performance Metriken

Usage:
    python scripts/test_reward_functions.py
"""

import sys
import os
from pathlib import Path
import numpy as np
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import track

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from solana_rl_bot.environment import TradingEnv, RewardFactory
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
            # Hole OHLCV Daten
            df = connector.fetch_ohlcv(
                symbol="SOL/USDT",
                timeframe="5m",
                limit=500,
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


def test_reward_function(reward_type: str, df: pd.DataFrame, n_episodes: int = 3):
    """
    Teste eine Reward Function mit Random Agent.

    Args:
        reward_type: Typ der Reward Function
        df: DataFrame mit Marktdaten
        n_episodes: Anzahl Test-Episodes

    Returns:
        Dictionary mit Ergebnissen
    """
    console.print(f"\n[bold cyan]Testing {reward_type.upper()} Reward...[/bold cyan]")

    try:
        # Erstelle Environment mit Reward Function
        env = TradingEnv(
            df=df,
            initial_balance=10000.0,
            reward_type=reward_type,
        )

        returns = []
        total_rewards = []
        win_rates = []
        num_trades = []

        for episode in range(n_episodes):
            observation, info = env.reset()

            done = False
            truncated = False
            episode_reward = 0

            while not (done or truncated):
                action = env.action_space.sample()
                obs, reward, done, truncated, info = env.step(action)
                episode_reward += reward

            stats = env.get_trade_statistics()
            returns.append(stats['total_return'])
            total_rewards.append(episode_reward)
            win_rates.append(stats.get('win_rate', 0))
            num_trades.append(stats.get('completed_trades', 0))

        # Aggregiere Ergebnisse
        results = {
            "reward_type": reward_type,
            "avg_return": np.mean(returns),
            "std_return": np.std(returns),
            "avg_reward": np.mean(total_rewards),
            "std_reward": np.std(total_rewards),
            "avg_win_rate": np.mean(win_rates),
            "avg_trades": np.mean(num_trades),
            "best_return": max(returns),
            "worst_return": min(returns),
        }

        console.print(f"[green]✅ {reward_type.upper()} getestet[/green]")

        return results

    except Exception as e:
        console.print(f"[red]❌ Test für {reward_type} fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def compare_reward_functions():
    """Vergleiche alle Reward Functions."""
    console.print("\n[bold cyan]Comparing All Reward Functions...[/bold cyan]")

    # Hole Marktdaten
    df = get_market_data()
    if df is None:
        return False

    # Teste alle Reward Functions
    reward_types = ["profit", "sharpe", "sortino", "multi", "incremental"]
    results = []

    for reward_type in reward_types:
        result = test_reward_function(reward_type, df, n_episodes=5)
        if result:
            results.append(result)

    # Zeige Vergleich
    console.print("\n[bold cyan]Reward Function Comparison[/bold cyan]")

    table = Table(title="Random Agent Performance by Reward Function")
    table.add_column("Reward Type", style="cyan")
    table.add_column("Avg Return", style="yellow")
    table.add_column("Avg Reward", style="green")
    table.add_column("Win Rate", style="magenta")
    table.add_column("Avg Trades", style="blue")
    table.add_column("Best Return", style="green")

    for result in results:
        table.add_row(
            result["reward_type"].upper(),
            f"{result['avg_return']*100:+.2f}%",
            f"{result['avg_reward']:.2f}",
            f"{result['avg_win_rate']*100:.1f}%",
            f"{result['avg_trades']:.0f}",
            f"{result['best_return']*100:+.2f}%",
        )

    console.print(table)

    # Analyse
    console.print("\n[cyan]Key Insights:[/cyan]")

    # Beste Return
    best_return = max(results, key=lambda x: x["avg_return"])
    console.print(
        f"  🏆 Beste Return: {best_return['reward_type'].upper()} "
        f"({best_return['avg_return']*100:+.2f}%)"
    )

    # Höchste Reward
    best_reward = max(results, key=lambda x: x["avg_reward"])
    console.print(
        f"  🎯 Höchste Reward: {best_reward['reward_type'].upper()} "
        f"({best_reward['avg_reward']:.2f})"
    )

    # Beste Win Rate
    best_winrate = max(results, key=lambda x: x["avg_win_rate"])
    console.print(
        f"  ⚡ Beste Win Rate: {best_winrate['reward_type'].upper()} "
        f"({best_winrate['avg_win_rate']*100:.1f}%)"
    )

    return len(results) > 0


def test_single_reward():
    """Teste einzelne Reward Function im Detail."""
    console.print("\n[bold cyan]Testing Single Reward Function (Multi-Objective)...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        # Multi-Objective Reward
        env = TradingEnv(
            df=df,
            initial_balance=10000.0,
            reward_type="multi",
        )

        # Einzelne Episode
        observation, info = env.reset()
        console.print(f"\n[cyan]Running Episode...[/cyan]")

        done = False
        truncated = False
        step_count = 0
        rewards_log = []

        for i in track(range(len(df) - env.window_size - 1), description="Steps"):
            action = env.action_space.sample()
            obs, reward, done, truncated, info = env.step(action)

            rewards_log.append({
                "step": step_count,
                "action": ["HOLD", "BUY", "SELL"][action],
                "reward": reward,
                "portfolio_value": info["portfolio_value"],
            })

            step_count += 1

            if done or truncated:
                break

        # Statistiken
        stats = env.get_trade_statistics()

        console.print(f"\n[cyan]Episode Results:[/cyan]")
        console.print(f"  Steps: {step_count}")
        console.print(f"  Total Trades: {stats['total_trades']}")
        console.print(f"  Completed Trades: {stats.get('completed_trades', 0)}")
        console.print(f"  Win Rate: {stats.get('win_rate', 0)*100:.1f}%")
        console.print(f"  Total Return: {stats['total_return']*100:+.2f}%")
        console.print(f"  Final Portfolio: ${stats['final_portfolio_value']:.2f}")

        # Reward Statistics
        rewards_array = np.array([r["reward"] for r in rewards_log])
        console.print(f"\n[cyan]Reward Statistics:[/cyan]")
        console.print(f"  Total Reward: {np.sum(rewards_array):.2f}")
        console.print(f"  Mean Reward: {np.mean(rewards_array):.4f}")
        console.print(f"  Std Reward: {np.std(rewards_array):.4f}")
        console.print(f"  Max Reward: {np.max(rewards_array):.4f}")
        console.print(f"  Min Reward: {np.min(rewards_array):.4f}")

        return True

    except Exception as e:
        console.print(f"[red]❌ Single Reward Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Führe alle Tests aus."""
    console.print(
        Panel.fit(
            "[bold cyan]Solana RL Bot - Reward Functions Test[/bold cyan]\n"
            "[yellow]Testet 5 verschiedene Reward Functions[/yellow]",
            border_style="cyan",
        )
    )

    # Setup logging
    LoggerSetup.setup(log_level="INFO", log_to_file=False)

    tests = [
        ("Single Reward Function", test_single_reward),
        ("Compare All Reward Functions", compare_reward_functions),
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
        console.print("\n[yellow]✅ 5 Reward Functions verfügbar![/yellow]")
        console.print("[yellow]✅ Profit, Sharpe, Sortino, Multi, Incremental![/yellow]")
        console.print("[yellow]✅ Bereit für RL Training![/yellow]")
        return 0
    else:
        console.print("\n[bold red]❌ EINIGE TESTS FEHLGESCHLAGEN[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
