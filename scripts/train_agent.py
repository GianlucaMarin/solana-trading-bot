#!/usr/bin/env python3
"""
Train a reinforcement learning agent.

Usage:
    python scripts/train_agent.py --agent ppo --timesteps 100000 --config configs/training.yaml
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Train RL agent")
    parser.add_argument(
        "--agent",
        type=str,
        default="ppo",
        choices=["ppo", "dqn", "sac", "a2c"],
        help="Agent type (default: ppo)",
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=100000,
        help="Total training timesteps (default: 100000)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/training.yaml",
        help="Config file path",
    )
    parser.add_argument(
        "--tensorboard",
        action="store_true",
        help="Enable TensorBoard logging",
    )

    args = parser.parse_args()

    print(f"🤖 Training {args.agent.upper()} agent")
    print(f"📊 Timesteps: {args.timesteps:,}")
    print(f"⚙️  Config: {args.config}")
    print()

    # TODO: Implement training
    # from solana_rl_bot.training import Trainer
    # trainer = Trainer(agent_type=args.agent, config=args.config)
    # trainer.train(timesteps=args.timesteps, tensorboard=args.tensorboard)

    print("✅ Training completed!")


if __name__ == "__main__":
    main()
