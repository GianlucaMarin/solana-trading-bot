# -*- coding: utf-8 -*-
"""
Systematische PPO Optimization mit verschiedenen Reward Functions.

Testet 4 verschiedene Reward Functions:
- profit (Baseline)
- sharpe (Risiko-adjustiert)
- sortino (Downside-Risiko)
- multi_objective (Balance)

Jedes Training: 500k Steps
Gesamt: 6-8 Stunden
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
from solana_rl_bot.environment import TradingEnv
from solana_rl_bot.agents import PPOAgent
from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


def train_with_reward(reward_type: str, train_df: pd.DataFrame, test_df: pd.DataFrame):
    """Trainiere PPO mit spezifischer Reward Function."""

    logger.info("=" * 70)
    logger.info(f"TRAINING MIT REWARD TYPE: {reward_type.upper()}")
    logger.info("=" * 70)

    # Erstelle Environments
    train_env = TradingEnv(
        df=train_df,
        initial_balance=10000.0,
        commission=0.001,
        window_size=50,
        reward_type=reward_type,
    )

    test_env = TradingEnv(
        df=test_df,
        initial_balance=10000.0,
        commission=0.001,
        window_size=50,
        reward_type=reward_type,
    )

    # Erstelle PPO Agent
    agent = PPOAgent(
        env=train_env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        ent_coef=0.01,
        tensorboard_log=f"./logs/tensorboard/{reward_type}/",
        verbose=1,
    )

    # Training
    logger.info(f"\nStarte Training mit {reward_type} reward...")
    logger.info("Dies wird 1.5-2 Stunden dauern...\n")

    save_path = f"./models/ppo_{reward_type}/"

    agent.train(
        total_timesteps=500_000,
        eval_env=test_env,
        eval_freq=25_000,
        n_eval_episodes=5,
        save_path=save_path,
        checkpoint_freq=100_000,
    )

    # Final Evaluation
    logger.info(f"\nFinale Evaluation für {reward_type}...")

    stats = agent.evaluate(
        env=test_env,
        n_episodes=10,
        deterministic=True,
    )

    logger.info(f"\n{'=' * 70}")
    logger.info(f"ERGEBNISSE FÜR {reward_type.upper()}")
    logger.info("=" * 70)
    logger.info(f"Mean Return: {stats['mean_return']*100:.2f}%")
    logger.info(f"Best Return: {stats['max_return']*100:.2f}%")
    logger.info(f"Worst Return: {stats['min_return']*100:.2f}%")
    logger.info(f"Std Return: {stats['std_return']*100:.2f}%")
    logger.info(f"Model: {save_path}")
    logger.info("=" * 70)
    logger.info("")

    return {
        "reward_type": reward_type,
        "stats": stats,
        "model_path": save_path,
    }


def main():
    """Hauptfunktion für systematische Optimization."""

    logger.info("=" * 70)
    logger.info("PPO SYSTEMATIC OPTIMIZATION")
    logger.info("=" * 70)
    logger.info("Testet 4 Reward Functions:")
    logger.info("  1. profit      - Maximiere einfach Gewinn")
    logger.info("  2. sharpe      - Maximiere Risiko-adjustierten Gewinn")
    logger.info("  3. sortino     - Minimiere Downside-Risiko")
    logger.info("  4. multi_objective - Balance aus allen")
    logger.info("")
    logger.info("Jedes Training: 500k Steps (~1.5-2h)")
    logger.info("Gesamt: ~6-8 Stunden")
    logger.info("=" * 70)
    logger.info("")

    # 1. Lade Daten
    logger.info("Lade Training-Daten...")

    try:
        df = pd.read_csv("data/processed/sol_usdt_features.csv", index_col=0, parse_dates=True)
        logger.info(f"Daten geladen: {len(df)} Candles\n")
    except FileNotFoundError:
        logger.error("Keine Daten gefunden! Bitte zuerst download_real_data.py ausführen.")
        return

    # 2. Split Train/Test
    train_size = int(len(df) * 0.8)
    train_df = df[:train_size].copy()
    test_df = df[train_size:].copy()

    logger.info(f"Train: {len(train_df)} Candles")
    logger.info(f"Test: {len(test_df)} Candles\n")

    # 3. Trainiere mit allen Reward Functions
    reward_types = ["profit", "sharpe", "sortino", "multi_objective"]
    results = []

    for i, reward_type in enumerate(reward_types, 1):
        logger.info(f"\n{'#' * 70}")
        logger.info(f"EXPERIMENT {i}/4: {reward_type.upper()}")
        logger.info(f"{'#' * 70}\n")

        result = train_with_reward(reward_type, train_df, test_df)
        results.append(result)

        logger.info(f"\n✅ {reward_type} Training komplett!\n")

    # 4. Vergleiche Ergebnisse
    logger.info("\n" + "=" * 70)
    logger.info("FINAL COMPARISON")
    logger.info("=" * 70)
    logger.info(f"{'Reward Type':<20} {'Mean Return':<15} {'Best Return':<15} {'Std Return':<15}")
    logger.info("-" * 70)

    best_result = None
    best_return = -float('inf')

    for result in results:
        reward_type = result["reward_type"]
        stats = result["stats"]
        mean_return = stats["mean_return"] * 100
        max_return = stats["max_return"] * 100
        std_return = stats["std_return"] * 100

        logger.info(f"{reward_type:<20} {mean_return:>13.2f}%  {max_return:>13.2f}%  {std_return:>13.2f}%")

        if mean_return > best_return:
            best_return = mean_return
            best_result = result

    logger.info("=" * 70)
    logger.info(f"\n🏆 WINNER: {best_result['reward_type'].upper()}")
    logger.info(f"Mean Return: {best_result['stats']['mean_return']*100:.2f}%")
    logger.info(f"Best Return: {best_result['stats']['max_return']*100:.2f}%")
    logger.info(f"Model Path: {best_result['model_path']}")
    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ OPTIMIZATION COMPLETE!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
