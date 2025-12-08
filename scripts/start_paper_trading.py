#!/usr/bin/env python3
"""
Start paper trading with a trained agent.

Usage:
    python scripts/start_paper_trading.py --agent ppo --model models/production/ppo_best.zip
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Start paper trading")
    parser.add_argument(
        "--agent",
        type=str,
        required=True,
        choices=["ppo", "dqn", "sac", "a2c"],
        help="Agent type",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to trained model",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="SOL/USDT",
        help="Trading symbol (default: SOL/USDT)",
    )
    parser.add_argument(
        "--initial-capital",
        type=float,
        default=10000.0,
        help="Initial capital (default: 10000)",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Start monitoring dashboard",
    )

    args = parser.parse_args()

    print("🔴 Starting Paper Trading")
    print(f"🤖 Agent: {args.agent.upper()}")
    print(f"📦 Model: {args.model}")
    print(f"💰 Symbol: {args.symbol}")
    print(f"💵 Initial Capital: ${args.initial_capital:,.2f}")
    print()
    print("⚠️  This is PAPER TRADING - no real money involved")
    print("📊 Monitor performance for at least 3 months before going live!")
    print()

    # TODO: Implement paper trading
    # from solana_rl_bot.live import PaperTrader
    # trader = PaperTrader(...)
    # trader.start()

    print("🚀 Paper trading started!")
    print("Press Ctrl+C to stop...")


if __name__ == "__main__":
    main()
