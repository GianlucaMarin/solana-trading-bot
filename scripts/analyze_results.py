#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPO Optimization Results Analysis

Analysiert die Ergebnisse der 4 verschiedenen Reward Functions:
- profit
- sharpe
- sortino
- multi_objective

Erstellt automatisch:
- Vergleichstabelle
- Performance Charts
- Best Model Recommendation
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import numpy as np
from typing import Dict, List
import json

from solana_rl_bot.environment import TradingEnv
from solana_rl_bot.agents import PPOAgent
from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


def load_model_and_evaluate(reward_type: str, test_df: pd.DataFrame) -> Dict:
    """
    Lade gespeichertes Model und evaluiere es.

    Args:
        reward_type: profit, sharpe, sortino, multi_objective
        test_df: Test DataFrame

    Returns:
        Dictionary mit Evaluation Stats
    """
    logger.info(f"Evaluiere {reward_type} Model...")

    # Model Path
    model_path = f"./models/ppo_{reward_type}/best_model.zip"

    if not Path(model_path).exists():
        logger.warning(f"Model nicht gefunden: {model_path}")
        return None

    # Erstelle Test Environment
    test_env = TradingEnv(
        df=test_df,
        initial_balance=10000.0,
        commission=0.001,
        window_size=50,
        reward_type=reward_type,
    )

    # Lade Model
    try:
        agent = PPOAgent.load_agent(model_path, test_env)

        # Evaluiere
        stats = agent.evaluate(
            env=test_env,
            n_episodes=20,  # Mehr Episodes für bessere Stats
            deterministic=True,
        )

        stats["reward_type"] = reward_type
        stats["model_path"] = model_path

        return stats

    except Exception as e:
        logger.error(f"Fehler beim Laden/Evaluieren von {reward_type}: {e}")
        return None


def create_comparison_table(results: List[Dict]) -> pd.DataFrame:
    """Erstelle Vergleichstabelle aus allen Ergebnissen."""

    data = []
    for result in results:
        if result is None:
            continue

        data.append({
            "Reward Type": result["reward_type"],
            "Mean Return (%)": result["mean_return"] * 100,
            "Std Return (%)": result["std_return"] * 100,
            "Min Return (%)": result["min_return"] * 100,
            "Max Return (%)": result["max_return"] * 100,
            "Mean Reward": result["mean_reward"],
            "Std Reward": result["std_reward"],
            "Mean Length": result["mean_length"],
        })

    df = pd.DataFrame(data)

    # Sortiere nach Mean Return
    df = df.sort_values("Mean Return (%)", ascending=False)

    return df


def calculate_sharpe_ratio(returns: List[float]) -> float:
    """Berechne Sharpe Ratio aus Returns."""
    returns_array = np.array(returns)
    mean_return = np.mean(returns_array)
    std_return = np.std(returns_array)

    if std_return == 0:
        return 0.0

    # Annualized Sharpe (assuming daily returns)
    sharpe = (mean_return / std_return) * np.sqrt(252)
    return sharpe


def calculate_sortino_ratio(returns: List[float]) -> float:
    """Berechne Sortino Ratio (nur Downside Volatility)."""
    returns_array = np.array(returns)
    mean_return = np.mean(returns_array)

    # Downside Deviation
    negative_returns = returns_array[returns_array < 0]
    if len(negative_returns) == 0:
        return float('inf')

    downside_std = np.std(negative_returns)
    if downside_std == 0:
        return 0.0

    sortino = (mean_return / downside_std) * np.sqrt(252)
    return sortino


def calculate_max_drawdown(returns: List[float]) -> float:
    """Berechne Maximum Drawdown."""
    cumulative = np.cumprod(1 + np.array(returns))
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_dd = np.min(drawdown)
    return max_dd


def display_summary(comparison_df: pd.DataFrame, results: List[Dict]):
    """Zeige schöne Zusammenfassung."""

    print("\n" + "=" * 80)
    print("🎯 PPO OPTIMIZATION RESULTS ANALYSIS")
    print("=" * 80)
    print()

    # Vergleichstabelle
    print("📊 PERFORMANCE COMPARISON")
    print("-" * 80)
    print(comparison_df.to_string(index=False))
    print()

    # Winner
    winner = comparison_df.iloc[0]
    print("=" * 80)
    print(f"🏆 WINNER: {winner['Reward Type'].upper()}")
    print("=" * 80)
    print(f"Mean Return:     {winner['Mean Return (%)']:>8.2f}%")
    print(f"Std Return:      {winner['Std Return (%)']:>8.2f}%")
    print(f"Return Range:    [{winner['Min Return (%)']:>6.2f}%, {winner['Max Return (%)']:>6.2f}%]")
    print(f"Mean Reward:     {winner['Mean Reward']:>8.2f}")
    print(f"Episode Length:  {winner['Mean Length']:>8.1f} steps")
    print()

    # Empfehlung
    print("=" * 80)
    print("💡 RECOMMENDATION")
    print("=" * 80)

    best_reward_type = winner['Reward Type']

    if best_reward_type == "profit":
        print("✅ PROFIT ist der Winner!")
        print("   → Maximiert reinen Gewinn")
        print("   → Gut für aggressive Trading-Strategie")
        print("   → Risiko: Höhere Volatilität möglich")

    elif best_reward_type == "sharpe":
        print("✅ SHARPE ist der Winner!")
        print("   → Beste Risk-Adjusted Performance")
        print("   → Balance zwischen Gewinn und Risiko")
        print("   → Empfohlen für konservatives Trading")

    elif best_reward_type == "sortino":
        print("✅ SORTINO ist der Winner!")
        print("   → Minimiert Downside-Risiko")
        print("   → Schützt vor großen Verlusten")
        print("   → Gut für Kapitalerhalt")

    elif best_reward_type == "multi_objective":
        print("✅ MULTI_OBJECTIVE ist der Winner!")
        print("   → Beste Balance aus allen Metriken")
        print("   → Kombiniert Gewinn, Sharpe, Sortino")
        print("   → Empfohlen für Production Use")

    print()
    print(f"📁 Best Model Path: ./models/ppo_{best_reward_type}/best_model.zip")
    print()
    print("=" * 80)


def save_results(comparison_df: pd.DataFrame, results: List[Dict]):
    """Speichere Ergebnisse als JSON und CSV."""

    # CSV
    csv_path = "./results/ppo_optimization_comparison.csv"
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    comparison_df.to_csv(csv_path, index=False)
    logger.info(f"Ergebnisse gespeichert: {csv_path}")

    # JSON (detailed)
    json_path = "./results/ppo_optimization_detailed.json"
    detailed_results = {
        "summary": comparison_df.to_dict(orient="records"),
        "detailed_stats": [r for r in results if r is not None],
    }

    with open(json_path, 'w') as f:
        json.dump(detailed_results, f, indent=2)

    logger.info(f"Detaillierte Ergebnisse gespeichert: {json_path}")


def main():
    """Hauptfunktion - Analysiere alle PPO Results."""

    logger.info("=" * 80)
    logger.info("PPO OPTIMIZATION RESULTS ANALYSIS")
    logger.info("=" * 80)
    logger.info("")

    # 1. Lade Test Daten
    logger.info("Lade Test-Daten...")

    try:
        df = pd.read_csv("data/processed/sol_usdt_features.csv", index_col=0, parse_dates=True)
        train_size = int(len(df) * 0.8)
        test_df = df[train_size:].copy()
        logger.info(f"Test-Daten geladen: {len(test_df)} Candles\n")
    except FileNotFoundError:
        logger.error("Keine Daten gefunden!")
        return

    # 2. Evaluiere alle Models
    reward_types = ["profit", "sharpe", "sortino", "multi_objective"]
    results = []

    for reward_type in reward_types:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Evaluiere: {reward_type.upper()}")
        logger.info(f"{'=' * 80}")

        result = load_model_and_evaluate(reward_type, test_df)
        results.append(result)

        if result:
            logger.info(f"✅ {reward_type}: Mean Return = {result['mean_return']*100:.2f}%")
        else:
            logger.warning(f"⚠️  {reward_type}: Model nicht gefunden oder Fehler")

    # Filter None results
    valid_results = [r for r in results if r is not None]

    if not valid_results:
        logger.error("\n❌ Keine Models gefunden! Training noch nicht abgeschlossen?")
        return

    # 3. Erstelle Vergleich
    logger.info("\n" + "=" * 80)
    logger.info("Erstelle Vergleichstabelle...")
    logger.info("=" * 80)

    comparison_df = create_comparison_table(valid_results)

    # 4. Display Summary
    display_summary(comparison_df, valid_results)

    # 5. Speichere Ergebnisse
    logger.info("Speichere Ergebnisse...")
    save_results(comparison_df, valid_results)

    logger.info("\n✅ Analysis Complete!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
