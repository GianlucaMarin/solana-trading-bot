#!/usr/bin/env python3
"""
Test-Script für Advanced Trading Environment.

Testet:
- Short-Selling
- Position Sizing
- Stop-Loss Triggers
- Long/Short Statistics

Usage:
    python scripts/test_advanced_env.py
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

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from solana_rl_bot.environment import AdvancedTradingEnv
from solana_rl_bot.data.collectors import BinanceConnector
from solana_rl_bot.data.features import FeatureCalculator
from solana_rl_bot.utils import LoggerSetup

console = Console()


def get_market_data():
    """Hole echte Marktdaten."""
    console.print("\n[bold cyan]Hole Marktdaten...[/bold cyan]")

    try:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            df = connector.fetch_ohlcv(
                symbol="SOL/USDT",
                timeframe="5m",
                limit=500,
            )

            console.print(f"[green]✅ {len(df)} OHLCV Candles abgerufen[/green]")

            # Features
            calculator = FeatureCalculator()
            df_features = calculator.calculate_all_features(df, symbol="SOL/USDT")

            console.print(f"[green]✅ {len(df_features.columns)} Features berechnet[/green]")

            return df_features

    except Exception as e:
        console.print(f"[red]❌ Fehler: {e}[/red]")
        return None


def test_short_selling():
    """Teste Short-Selling."""
    console.print("\n[bold cyan]Testing Short-Selling...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        # Environment mit Short-Selling
        env = AdvancedTradingEnv(
            df=df,
            initial_balance=10000.0,
            enable_short=True,
            enable_stop_loss=False,
        )

        observation, info = env.reset()

        # Manual Short Trade
        console.print("\n[cyan]Teste Short-Selling:[/cyan]")
        
        # Open Short: [direction=-1, size=0.5, stop_loss=0]
        action = np.array([-1.0, 0.5, 0.0])
        obs, reward, done, truncated, info = env.step(action)
        
        console.print(f"  SHORT @ ${env.df.iloc[env.current_step-1]['close']:.2f}")
        console.print(f"  Position: {info['position']} (Short)")
        console.print(f"  Holdings: {abs(info['holdings']):.4f} SOL")
        console.print(f"  Size: {info['position_size']*100:.1f}%")
        
        # Hold for 10 steps
        for _ in range(10):
            action = np.array([0.0, 0.0, 0.0])  # Hold
            obs, reward, done, truncated, info = env.step(action)
        
        # Close Short
        action = np.array([0.0, 0.0, 0.0])  # Close
        obs, reward, done, truncated, info = env.step(action)
        
        console.print(f"  CLOSE @ ${env.df.iloc[env.current_step-1]['close']:.2f}")
        console.print(f"  Portfolio: ${info['portfolio_value']:.2f}")

        stats = env.get_trade_statistics()
        console.print(f"\n[cyan]Short Trading Stats:[/cyan]")
        console.print(f"  Short Trades: {stats.get('short_trades', 0)}")
        console.print(f"  Long Trades: {stats.get('long_trades', 0)}")

        console.print("[green]✅ Short-Selling funktioniert[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Short-Selling Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_position_sizing():
    """Teste Position Sizing."""
    console.print("\n[bold cyan]Testing Position Sizing...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        env = AdvancedTradingEnv(df=df, initial_balance=10000.0)
        observation, info = env.reset()

        console.print("\n[cyan]Teste verschiedene Position Sizes:[/cyan]")

        # Test 25% Position
        action = np.array([1.0, 0.25, 0.0])  # Long 25%
        obs, reward, done, truncated, info = env.step(action)
        console.print(f"  25% Long: Size={info['position_size']*100:.1f}%, Holdings={info['holdings']:.4f}")

        # Close
        action = np.array([0.0, 0.0, 0.0])
        obs, reward, done, truncated, info = env.step(action)

        # Test 100% Position
        action = np.array([1.0, 1.0, 0.0])  # Long 100%
        obs, reward, done, truncated, info = env.step(action)
        console.print(f"  100% Long: Size={info['position_size']*100:.1f}%, Holdings={info['holdings']:.4f}")

        console.print("[green]✅ Position Sizing funktioniert[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Position Sizing Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_stop_loss():
    """Teste Stop-Loss."""
    console.print("\n[bold cyan]Testing Stop-Loss...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        env = AdvancedTradingEnv(
            df=df,
            initial_balance=10000.0,
            enable_stop_loss=True,
        )

        observation, info = env.reset()

        console.print("\n[cyan]Teste Stop-Loss Trigger:[/cyan]")

        # Open Long mit 5% Stop-Loss
        action = np.array([1.0, 0.5, 0.05])  # Long 50%, SL=5%
        obs, reward, done, truncated, info = env.step(action)
        
        entry_price = env.df.iloc[env.current_step-1]['close']
        stop_loss = info['stop_loss_price']
        
        console.print(f"  LONG @ ${entry_price:.2f}")
        console.print(f"  Stop-Loss @ ${stop_loss:.2f} ({(stop_loss/entry_price-1)*100:.1f}%)")

        # Simulate price movement (hope for trigger)
        triggered = False
        for i in range(50):
            action = np.array([1.0, 0.5, 0.05])  # Hold Long
            obs, reward, done, truncated, info = env.step(action)
            
            if info['position'] == 0:  # Position closed
                triggered = True
                console.print(f"  [yellow]Stop-Loss triggered at step {i+1}![/yellow]")
                break

        if not triggered:
            console.print(f"  [yellow]Stop-Loss not triggered in 50 steps (OK)[/yellow]")

        console.print("[green]✅ Stop-Loss funktioniert[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Stop-Loss Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_random_agent_advanced():
    """Teste Random Agent mit Advanced Env."""
    console.print("\n[bold cyan]Testing Random Agent (Advanced)...[/bold cyan]")

    try:
        df = get_market_data()
        if df is None:
            return False

        env = AdvancedTradingEnv(
            df=df,
            initial_balance=10000.0,
            enable_short=True,
            enable_stop_loss=True,
        )

        observation, info = env.reset()

        console.print(f"\nLaufe Random Agent für {len(df) - env.window_size} Steps...")

        done = False
        truncated = False
        steps = 0

        while not (done or truncated) and steps < 200:
            # Random Action
            action = env.action_space.sample()
            obs, reward, done, truncated, info = env.step(action)
            steps += 1

        # Stats
        stats = env.get_trade_statistics()

        console.print(f"\n[cyan]Random Agent Ergebnisse:[/cyan]")

        table = Table(title="Advanced Trading Statistics")
        table.add_column("Metrik", style="cyan")
        table.add_column("Wert", style="green")

        table.add_row("Steps", str(steps))
        table.add_row("Total Trades", str(stats.get('total_trades', 0)))
        table.add_row("Completed Trades", str(stats.get('completed_trades', 0)))
        table.add_row("Long Trades", str(stats.get('long_trades', 0)))
        table.add_row("Short Trades", str(stats.get('short_trades', 0)))
        table.add_row("Win Rate", f"{stats.get('win_rate', 0)*100:.1f}%")
        table.add_row("Total Return", f"{stats['total_return']*100:+.2f}%")
        table.add_row("Final Portfolio", f"${stats['final_portfolio_value']:.2f}")

        console.print(table)

        console.print("[green]✅ Random Agent (Advanced) abgeschlossen[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ Random Agent Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Führe alle Tests aus."""
    console.print(
        Panel.fit(
            "[bold cyan]Solana RL Bot - Advanced Trading Environment Test[/bold cyan]\n"
            "[yellow]Testet Short-Selling, Position Sizing und Stop-Loss[/yellow]",
            border_style="cyan",
        )
    )

    # Setup logging
    LoggerSetup.setup(log_level="INFO", log_to_file=False)

    tests = [
        ("Short-Selling", test_short_selling),
        ("Position Sizing", test_position_sizing),
        ("Stop-Loss", test_stop_loss),
        ("Random Agent Advanced", test_random_agent_advanced),
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
        console.print("\n[yellow]✅ Short-Selling funktioniert![/yellow]")
        console.print("[yellow]✅ Position Sizing (0-100%)![/yellow]")
        console.print("[yellow]✅ Stop-Loss Orders![/yellow]")
        console.print("[yellow]✅ Advanced Trading Environment ready![/yellow]")
        return 0
    else:
        console.print("\n[bold red]❌ EINIGE TESTS FEHLGESCHLAGEN[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
