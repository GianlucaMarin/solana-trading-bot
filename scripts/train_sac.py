# -*- coding: utf-8 -*-
"""
Trainiere SAC Agent auf Trading Environment.

SAC Agent Implementation fuer Phase 4.2.
SAC nutzt kontinuierlichen Action Space mit ContinuousTradingEnv.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import argparse
from solana_rl_bot.environment import ContinuousTradingEnv
from solana_rl_bot.agents import SACAgent
from solana_rl_bot.risk import RiskConfigFactory
from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


def main():
    """Trainiere SAC Agent."""
    parser = argparse.ArgumentParser(description="SAC Training mit Risk Management")
    parser.add_argument("--steps", type=int, default=500_000,
                       help="Training Steps (default: 500000)")
    parser.add_argument("--timeframe", type=str, default="5min",
                       help="Timeframe fuer Risk Config (default: 5min)")
    args = parser.parse_args()

    print("=" * 70)
    print("SAC TRAINING mit Risk Management")
    print("=" * 70)
    print()

    logger.info("=== SAC Training Start ===\n")

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

    # 3. Risk Config
    risk_config = RiskConfigFactory.create(args.timeframe)
    logger.info(f"Risk Management: {args.timeframe} Config aktiviert")
    logger.info(f"  Stop-Loss: {risk_config.stop_loss_pct*100:.1f}%")
    logger.info(f"  Take-Profit: {risk_config.take_profit_pct*100:.1f}%")
    logger.info(f"  Max Position: {risk_config.max_position_pct*100:.0f}%")
    logger.info(f"  Max Daily Loss: {risk_config.max_daily_loss_pct*100:.1f}%")
    logger.info("")

    # 4. Erstelle Environments (Continuous fuer SAC!)
    logger.info("Erstelle Continuous Trading Environments (fuer SAC)...")

    train_env = ContinuousTradingEnv(
        df=train_df,
        initial_balance=10000.0,
        commission=0.001,
        window_size=50,
        reward_type="sortino",  # Winner!
        use_risk_management=True,
        risk_config=risk_config,
    )

    test_env = ContinuousTradingEnv(
        df=test_df,
        initial_balance=10000.0,
        commission=0.001,
        window_size=50,
        reward_type="sortino",
        use_risk_management=True,
        risk_config=risk_config,
    )

    logger.info("Environments erstellt!\n")

    # 5. Erstelle SAC Agent
    logger.info("Initialisiere SAC Agent...")

    agent = SACAgent(
        env=train_env,
        learning_rate=3e-4,
        buffer_size=100_000,
        learning_starts=10_000,
        batch_size=256,
        tau=0.005,
        gamma=0.99,
        train_freq=1,
        gradient_steps=1,
        ent_coef="auto",  # Automatisches Entropy Tuning
        tensorboard_log="./logs/tensorboard/sac/",
        verbose=1,
    )

    logger.info("Agent bereit!\n")

    # 6. Training
    logger.info("Starte Training...")
    logger.info(f"Dies wird 1.5-2 Stunden dauern ({args.steps:,} Steps)...\n")

    agent.train(
        total_timesteps=args.steps,
        eval_env=test_env,
        eval_freq=25_000,
        n_eval_episodes=5,
        save_path="./models/sac_rm/",
        checkpoint_freq=100_000,
    )

    logger.info("\n=== Training Complete! ===\n")

    # 7. Final Evaluation
    logger.info("Finale Evaluation auf Test-Daten...")

    stats = agent.evaluate(
        env=test_env,
        n_episodes=10,
        deterministic=True,
    )

    # 8. Zusammenfassung
    logger.info("\n" + "=" * 50)
    logger.info("TRAINING SUMMARY")
    logger.info("=" * 50)
    logger.info(f"Total Training Steps: {args.steps:,}")
    logger.info(f"Risk Config: {args.timeframe}")
    logger.info(f"\nFinal Test Performance:")
    logger.info(f"  Mean Return: {stats['mean_return']*100:.2f}%")
    logger.info(f"  Best Return: {stats['max_return']*100:.2f}%")
    logger.info(f"  Worst Return: {stats['min_return']*100:.2f}%")
    logger.info(f"  Std Return: {stats['std_return']*100:.2f}%")
    logger.info(f"\nModel gespeichert in: ./models/sac_rm/")
    logger.info("=" * 50)

    return stats


if __name__ == "__main__":
    main()
