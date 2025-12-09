#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baseline Strategy Comparison.

Vergleicht RL Agent mit einfachen Baseline Strategies:
- Buy & Hold
- SMA Crossover (20/50)
- RSI (30/70)

Das ist KRITISCH um zu wissen ob RL überhaupt Sinn macht!
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import numpy as np

from solana_rl_bot.strategies import (
    BuyAndHoldStrategy,
    SMACrossoverStrategy,
    RSIStrategy,
)
from solana_rl_bot.environment import TradingEnv
from solana_rl_bot.agents import PPOAgent
from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


def evaluate_rl_agent(test_df: pd.DataFrame, model_path: str, reward_type: str = "sortino") -> dict:
    """Evaluiere RL Agent auf Test-Daten."""

    test_env = TradingEnv(
        df=test_df,
        initial_balance=10000.0,
        commission=0.001,
        window_size=50,
        reward_type=reward_type,
    )

    try:
        agent = PPOAgent.load_agent(model_path, test_env)
        stats = agent.evaluate(env=test_env, n_episodes=1, deterministic=True)

        return {
            "strategy": f"RL Agent (PPO {reward_type})",
            "total_return": stats["mean_return"],
            "sharpe_ratio": 0.0,  # Nicht direkt verfügbar
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "num_trades": 0,
            "final_balance": 10000 * (1 + stats["mean_return"]),
        }
    except Exception as e:
        logger.error(f"Fehler beim Laden des RL Agents: {e}")
        return None


def main():
    """Hauptfunktion - Vergleiche alle Strategies."""

    print("=" * 70)
    print("🎯 BASELINE STRATEGY COMPARISON")
    print("=" * 70)
    print()

    # 1. Lade Test-Daten
    logger.info("Lade Test-Daten...")

    try:
        df = pd.read_csv("data/processed/sol_usdt_features.csv", index_col=0, parse_dates=True)
        train_size = int(len(df) * 0.8)
        test_df = df[train_size:].copy()
        logger.info(f"Test-Daten geladen: {len(test_df)} Candles")
        logger.info(f"Zeitraum: {test_df.index[0]} bis {test_df.index[-1]}")
        print()
    except FileNotFoundError:
        logger.error("Keine Daten gefunden!")
        return

    # 2. Initialisiere Strategies
    strategies = [
        BuyAndHoldStrategy(initial_balance=10000.0, commission=0.001),
        SMACrossoverStrategy(initial_balance=10000.0, commission=0.001),
        RSIStrategy(initial_balance=10000.0, commission=0.001),
    ]

    # 3. Backtests durchführen
    results = []

    for strategy in strategies:
        logger.info(f"Backteste: {strategy.name}...")
        result = strategy.backtest(test_df)
        results.append(result)
        logger.info(f"  → Return: {result['total_return']*100:.2f}%")

    # 4. RL Agent evaluieren
    logger.info("Evaluiere RL Agent (PPO Sortino)...")
    rl_result = evaluate_rl_agent(test_df, "models/ppo_sortino/best_model.zip", "sortino")
    if rl_result:
        results.append(rl_result)
        logger.info(f"  → Return: {rl_result['total_return']*100:.2f}%")

    print()

    # 5. Ergebnisse anzeigen
    print("=" * 70)
    print("📊 ERGEBNISSE")
    print("=" * 70)
    print()
    print(f"{'Strategy':<30} {'Return':<12} {'Sharpe':<10} {'Max DD':<12} {'Trades':<8}")
    print("-" * 70)

    for r in results:
        return_str = f"{r['total_return']*100:>+.2f}%"
        sharpe_str = f"{r['sharpe_ratio']:.2f}" if r['sharpe_ratio'] != 0 else "N/A"
        dd_str = f"{r['max_drawdown']*100:.2f}%" if r['max_drawdown'] != 0 else "N/A"
        trades_str = str(r['num_trades']) if r['num_trades'] > 0 else "N/A"

        print(f"{r['strategy']:<30} {return_str:<12} {sharpe_str:<10} {dd_str:<12} {trades_str:<8}")

    print()

    # 6. Winner ermitteln
    sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)
    winner = sorted_results[0]

    print("=" * 70)
    print(f"🏆 WINNER: {winner['strategy']}")
    print(f"   Return: {winner['total_return']*100:+.2f}%")
    print("=" * 70)
    print()

    # 7. RL vs Baselines Vergleich
    rl_strategies = [r for r in results if "RL Agent" in r['strategy']]
    baseline_strategies = [r for r in results if "RL Agent" not in r['strategy']]

    if rl_strategies:
        rl = rl_strategies[0]

        print("📈 RL AGENT vs BASELINES:")
        print("-" * 70)

        baselines_beaten = 0
        for baseline in baseline_strategies:
            diff = rl['total_return'] - baseline['total_return']
            status = "✅ BEAT" if diff > 0 else "❌ LOST"
            print(f"  vs {baseline['strategy']:<25} {status} ({diff*100:+.2f}%)")
            if diff > 0:
                baselines_beaten += 1

        print()
        print(f"📊 Score: {baselines_beaten}/{len(baseline_strategies)} Baselines geschlagen")

        if baselines_beaten == len(baseline_strategies):
            print("🎉 EXCELLENT! RL Agent schlägt ALLE Baselines!")
        elif baselines_beaten >= len(baseline_strategies) / 2:
            print("👍 GOOD! RL Agent schlägt die Mehrheit der Baselines.")
        else:
            print("⚠️  WARNUNG: RL Agent muss verbessert werden!")

    print()
    print("=" * 70)

    return results


if __name__ == "__main__":
    main()
