# -*- coding: utf-8 -*-
"""
Fairer Vergleich: PPO vs DQN mit Risk Management.

Trainiert beide Agents unter identischen Bedingungen:
- Sortino Reward Function
- 5min RiskConfig aktiviert
- Gleiche Daten (80/20 Split)
- 500k Training Steps
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
import argparse
from solana_rl_bot.environment import TradingEnv
from solana_rl_bot.agents import PPOAgent, DQNAgent
from solana_rl_bot.risk import RiskConfigFactory
from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


def train_agent(agent_type: str, train_df: pd.DataFrame, test_df: pd.DataFrame,
                risk_config, total_timesteps: int = 500_000):
    """Trainiere einen Agent mit Risk Management."""

    logger.info(f"\n{'='*60}")
    logger.info(f"Training {agent_type.upper()} mit Risk Management")
    logger.info(f"{'='*60}\n")

    # Erstelle Environments mit Risk Management
    train_env = TradingEnv(
        df=train_df,
        initial_balance=10000.0,
        commission=0.001,
        window_size=50,
        reward_type="sortino",  # Winner!
        use_risk_management=True,
        risk_config=risk_config,
    )

    test_env = TradingEnv(
        df=test_df,
        initial_balance=10000.0,
        commission=0.001,
        window_size=50,
        reward_type="sortino",
        use_risk_management=True,
        risk_config=risk_config,
    )

    logger.info(f"Risk Config: {risk_config.timeframe}")
    logger.info(f"  Stop-Loss: {risk_config.stop_loss_pct*100:.1f}%")
    logger.info(f"  Take-Profit: {risk_config.take_profit_pct*100:.1f}%")
    logger.info(f"  Max Position: {risk_config.max_position_pct*100:.0f}%")
    logger.info(f"  Max Daily Loss: {risk_config.max_daily_loss_pct*100:.1f}%")
    logger.info("")

    # Erstelle Agent
    if agent_type.lower() == "ppo":
        agent = PPOAgent(
            env=train_env,
            learning_rate=3e-4,
            n_steps=2048,
            batch_size=64,
            n_epochs=10,
            gamma=0.99,
            ent_coef=0.01,
            tensorboard_log="./logs/tensorboard/",
            verbose=1,
        )
        save_path = "./models/ppo_rm/"

    elif agent_type.lower() == "dqn":
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
            tensorboard_log="./logs/tensorboard/",
            verbose=1,
        )
        save_path = "./models/dqn_rm/"
    else:
        raise ValueError(f"Unbekannter Agent-Typ: {agent_type}")

    logger.info(f"Agent {agent_type.upper()} initialisiert")
    logger.info(f"Starte Training ({total_timesteps:,} Steps)...\n")

    # Training
    agent.train(
        total_timesteps=total_timesteps,
        eval_env=test_env,
        eval_freq=25_000,
        n_eval_episodes=5,
        save_path=save_path,
        checkpoint_freq=100_000,
    )

    # Evaluation
    logger.info(f"\nFinale Evaluation {agent_type.upper()}...")
    stats = agent.evaluate(
        env=test_env,
        n_episodes=10,
        deterministic=True,
    )

    logger.info(f"\n{agent_type.upper()} Ergebnis:")
    logger.info(f"  Mean Return: {stats['mean_return']*100:.2f}%")
    logger.info(f"  Best Return: {stats['max_return']*100:.2f}%")
    logger.info(f"  Worst Return: {stats['min_return']*100:.2f}%")
    logger.info(f"  Model: {save_path}")

    return stats


def main():
    """Hauptfunktion - Trainiere PPO und DQN fair."""

    parser = argparse.ArgumentParser(description="Fair PPO vs DQN Comparison")
    parser.add_argument("--agent", type=str, default="both",
                       choices=["ppo", "dqn", "both"],
                       help="Welchen Agent trainieren (default: both)")
    parser.add_argument("--steps", type=int, default=500_000,
                       help="Training Steps (default: 500000)")
    parser.add_argument("--timeframe", type=str, default="5min",
                       help="Timeframe fuer Risk Config (default: 5min)")
    args = parser.parse_args()

    print("=" * 70)
    print("FAIRER VERGLEICH: PPO vs DQN mit Risk Management")
    print("=" * 70)
    print()

    # 1. Lade Daten
    logger.info("Lade Training-Daten...")

    try:
        df = pd.read_csv("data/processed/sol_usdt_features.csv", index_col=0, parse_dates=True)
        logger.info(f"Daten geladen: {len(df)} Candles")
    except FileNotFoundError:
        logger.error("Keine Daten gefunden!")
        return

    # 2. Split Train/Test
    train_size = int(len(df) * 0.8)
    train_df = df[:train_size].copy()
    test_df = df[train_size:].copy()

    logger.info(f"Train: {len(train_df)} Candles ({train_df.index[0]} bis {train_df.index[-1]})")
    logger.info(f"Test: {len(test_df)} Candles ({test_df.index[0]} bis {test_df.index[-1]})")

    # 3. Risk Config
    risk_config = RiskConfigFactory.create(args.timeframe)
    logger.info(f"\nRisk Management: {args.timeframe} Config aktiviert")

    results = {}

    # 4. Training
    if args.agent in ["ppo", "both"]:
        results["PPO"] = train_agent("ppo", train_df, test_df, risk_config, args.steps)

    if args.agent in ["dqn", "both"]:
        results["DQN"] = train_agent("dqn", train_df, test_df, risk_config, args.steps)

    # 5. Vergleich
    if len(results) == 2:
        print("\n" + "=" * 70)
        print("VERGLEICH: PPO vs DQN (beide mit Risk Management)")
        print("=" * 70)
        print()
        print(f"{'Agent':<10} {'Mean Return':<15} {'Best':<12} {'Worst':<12}")
        print("-" * 50)

        for name, stats in results.items():
            print(f"{name:<10} {stats['mean_return']*100:>+.2f}%{'':>8} "
                  f"{stats['max_return']*100:>+.2f}%{'':>5} "
                  f"{stats['min_return']*100:>+.2f}%")

        print()

        # Winner
        winner = max(results.keys(), key=lambda k: results[k]['mean_return'])
        diff = abs(results['PPO']['mean_return'] - results['DQN']['mean_return']) * 100

        print(f"WINNER: {winner} (um {diff:.2f}% besser)")
        print()
        print("=" * 70)

    return results


if __name__ == "__main__":
    main()
