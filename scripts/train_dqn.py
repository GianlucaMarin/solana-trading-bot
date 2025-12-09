# -*- coding: utf-8 -*-
"""
Trainiere DQN Agent auf Trading Environment.

DQN Agent Implementation fuer Phase 4.2.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
from solana_rl_bot.environment import TradingEnv
from solana_rl_bot.agents import DQNAgent
from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


def main():
    """Trainiere DQN Agent."""
    logger.info("=== DQN Training Start ===\n")

    # 1. Lade Daten
    logger.info("Lade Training-Daten...")

    try:
        df = pd.read_csv("data/processed/sol_usdt_features.csv", index_col=0, parse_dates=True)
        logger.info(f"Daten geladen: {len(df)} Candles\n")
    except FileNotFoundError:
        logger.error("Keine Daten gefunden! Bitte zuerst download_real_data.py ausfuehren.")
        logger.error("Erwartet: data/processed/sol_usdt_features.csv")
        return
    except Exception as e:
        logger.error(f"Fehler beim Laden der Daten: {e}")
        return

    # 2. Split Train/Test
    train_size = int(len(df) * 0.8)
    train_df = df[:train_size].copy()
    test_df = df[train_size:].copy()

    logger.info(f"Train: {len(train_df)} Candles")
    logger.info(f"Test: {len(test_df)} Candles\n")

    # 3. Erstelle Environments
    logger.info("Erstelle Trading Environments...")

    train_env = TradingEnv(
        df=train_df,
        initial_balance=10000.0,
        commission=0.001,
        window_size=50,
        reward_type="sortino",  # DQN mit Sortino Reward (Winner!)
    )

    test_env = TradingEnv(
        df=test_df,
        initial_balance=10000.0,
        commission=0.001,
        window_size=50,
        reward_type="sortino",
    )

    logger.info("Environments erstellt!\n")

    # 4. Erstelle DQN Agent
    logger.info("Initialisiere DQN Agent...")

    agent = DQNAgent(
        env=train_env,
        learning_rate=1e-4,
        buffer_size=100_000,
        learning_starts=10_000,
        batch_size=128,
        gamma=0.99,
        target_update_interval=10_000,
        exploration_fraction=0.1,
        exploration_initial_eps=1.0,
        exploration_final_eps=0.05,
        tensorboard_log="./logs/tensorboard/dqn/",
        verbose=1,
    )

    logger.info("Agent bereit!\n")

    # 5. Training
    logger.info("Starte Training...")
    logger.info("Dies wird 1.5-2 Stunden dauern (500k Steps)...\n")

    agent.train(
        total_timesteps=500_000,  # 500k Steps wie PPO
        eval_env=test_env,
        eval_freq=25_000,
        n_eval_episodes=5,
        save_path="./models/dqn/",
        checkpoint_freq=100_000,
    )

    logger.info("\n=== Training Complete! ===\n")

    # 6. Final Evaluation
    logger.info("Finale Evaluation auf Test-Daten...")

    stats = agent.evaluate(
        env=test_env,
        n_episodes=10,
        deterministic=True,
    )

    # 7. Zusammenfassung
    logger.info("\n" + "=" * 50)
    logger.info("TRAINING SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total Training Steps: 500,000")
    logger.info(f"Training Episodes: {len(train_df) // train_env.window_size}")
    logger.info(f"\nFinal Test Performance:")
    logger.info(f"  Mean Return: {stats['mean_return']*100:.2f}%")
    logger.info(f"  Best Return: {stats['max_return']*100:.2f}%")
    logger.info(f"  Worst Return: {stats['min_return']*100:.2f}%")
    logger.info(f"  Std Return: {stats['std_return']*100:.2f}%")
    logger.info(f"\nModel gespeichert in: ./models/dqn/")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
