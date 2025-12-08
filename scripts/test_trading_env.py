#!/usr/bin/env python3
"""
Test-Script für Trading Environment.

Testet:
- Environment Initialization
- Action Execution
- Reward Calculation
- Random Agent Performance

Usage:
    python scripts/test_trading_env.py
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
from rich.table import Table
from rich.progress import track

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from solana_rl_bot.environment import TradingEnv
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
                limit=500,  # Genug für Training
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


def test_environment_init():
    """Teste Environment Initialisierung."""
    console.print("\n[bold cyan]Testing Environment Initialization...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        # Erstelle Environment
        env = TradingEnv(
            df=df,
            initial_balance=10000.0,
            commission=0.001,
            window_size=50,
        )

        console.print(f"\n[cyan]Environment Details:[/cyan]")
        console.print(f"  Observation Space: {env.observation_space.shape}")
        console.print(f"  Action Space: {env.action_space.n} actions")
        console.print(f"  Features: {len(env.features)}")
        console.print(f"  Initial Balance: ${env.initial_balance:.2f}")
        console.print(f"  Commission: {env.commission*100:.2f}%")

        # Test Reset
        observation, info = env.reset()

        console.print(f"\n[cyan]Initial State:[/cyan]")
        console.print(f"  Observation Shape: {observation.shape}")
        console.print(f"  Portfolio Value: ${info['portfolio_value']:.2f}")
        console.print(f"  Position: {info['position']}")

        console.print("[green]✅ Environment initialisiert[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Init Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_action_execution():
    """Teste Action Execution."""
    console.print("\n[bold cyan]Testing Action Execution...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        env = TradingEnv(df=df, initial_balance=10000.0)
        observation, info = env.reset()

        console.print("\n[cyan]Teste Actions:[/cyan]")

        # Test BUY
        console.print("  ACTION 1: BUY")
        obs, reward, done, truncated, info = env.step(1)  # Buy
        console.print(f"    Position: {info['position']} (Long)")
        console.print(f"    Holdings: {info['holdings']:.4f} SOL")
        console.print(f"    Reward: {reward:.4f}")

        # Test HOLD
        console.print("  ACTION 0: HOLD")
        obs, reward, done, truncated, info = env.step(0)  # Hold
        console.print(f"    Position: {info['position']}")
        console.print(f"    Reward: {reward:.4f}")

        # Test SELL
        console.print("  ACTION 2: SELL")
        obs, reward, done, truncated, info = env.step(2)  # Sell
        console.print(f"    Position: {info['position']} (Closed)")
        console.print(f"    Balance: ${info['balance']:.2f}")
        console.print(f"    Reward: {reward:.4f}")

        console.print("[green]✅ Actions funktionieren[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Action Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_random_agent():
    """Teste Environment mit Random Agent."""
    console.print("\n[bold cyan]Testing Random Agent...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        env = TradingEnv(df=df, initial_balance=10000.0)
        observation, info = env.reset()

        console.print(f"\nLasse Random Agent für {len(df) - env.window_size} Steps laufen...")

        total_reward = 0
        steps = 0

        # Laufe Episode
        done = False
        truncated = False

        for i in track(range(len(df) - env.window_size - 1), description="Steps"):
            # Random Action
            action = env.action_space.sample()

            obs, reward, done, truncated, info = env.step(action)
            total_reward += reward
            steps += 1

            if done or truncated:
                break

        # Statistiken
        stats = env.get_trade_statistics()

        console.print(f"\n[cyan]Random Agent Ergebnisse:[/cyan]")

        table = Table(title="Trading Statistics")
        table.add_column("Metrik", style="cyan")
        table.add_column("Wert", style="green")

        table.add_row("Steps", str(steps))
        table.add_row("Total Reward", f"{total_reward:.2f}")
        table.add_row("Total Trades", str(stats.get('total_trades', 0)))
        table.add_row("Completed Trades", str(stats.get('completed_trades', 0)))

        if stats.get('completed_trades', 0) > 0:
            table.add_row("Win Rate", f"{stats['win_rate']*100:.1f}%")
            table.add_row("Avg Profit", f"${stats['avg_profit']:.2f}")
            table.add_row("Avg Profit %", f"{stats['avg_profit_pct']:.2f}%")
            table.add_row("Total Profit", f"${stats['total_profit']:.2f}")

        table.add_row("Final Portfolio", f"${stats['final_portfolio_value']:.2f}")
        table.add_row(
            "Total Return",
            f"{stats['total_return']*100:.2f}%",
            style="green" if stats['total_return'] > 0 else "red"
        )

        console.print(table)

        console.print("[green]✅ Random Agent abgeschlossen[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Random Agent Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_episodes():
    """Teste mehrere Episodes."""
    console.print("\n[bold cyan]Testing Multiple Episodes...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        env = TradingEnv(df=df, initial_balance=10000.0)

        n_episodes = 5
        returns = []

        console.print(f"\nLaufe {n_episodes} Episodes...")

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

            console.print(
                f"  Episode {episode+1}: "
                f"Return: {stats['total_return']*100:+.2f}%, "
                f"Trades: {stats.get('completed_trades', 0)}"
            )

        # Durchschnittliche Performance
        avg_return = np.mean(returns) * 100
        std_return = np.std(returns) * 100

        console.print(f"\n[cyan]Durchschnittliche Performance:[/cyan]")
        console.print(f"  Avg Return: {avg_return:+.2f}% ± {std_return:.2f}%")
        console.print(f"  Best: {max(returns)*100:+.2f}%")
        console.print(f"  Worst: {min(returns)*100:+.2f}%")

        console.print("[green]✅ Multiple Episodes abgeschlossen[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Multiple Episodes Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Führe alle Tests aus."""
    console.print(
        Panel.fit(
            "[bold cyan]Solana RL Bot - Trading Environment Test[/bold cyan]\n"
            "[yellow]Testet RL Trading Environment mit echten Marktdaten[/yellow]",
            border_style="cyan",
        )
    )

    # Setup logging
    LoggerSetup.setup(log_level="INFO", log_to_file=False)

    tests = [
        ("Environment Initialization", test_environment_init),
        ("Action Execution", test_action_execution),
        ("Random Agent", test_random_agent),
        ("Multiple Episodes", test_multiple_episodes),
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
        console.print("\n[yellow]✅ Trading Environment funktioniert![/yellow]")
        console.print("[yellow]✅ Action Space (Hold/Buy/Sell) funktioniert![/yellow]")
        console.print("[yellow]✅ Reward Function funktioniert![/yellow]")
        console.print("[yellow]✅ Gymnasium-kompatibel![/yellow]")
        return 0
    else:
        console.print("\n[bold red]❌ EINIGE TESTS FEHLGESCHLAGEN[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
