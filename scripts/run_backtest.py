#!/usr/bin/env python3
"""
Run backtesting for strategies or trained agents.

Usage:
    # Baseline strategy
    python scripts/run_backtest.py --strategy sma_crossover --start 2023-01-01 --end 2024-01-01

    # RL Agent
    python scripts/run_backtest.py --agent ppo --model models/production/ppo_best.zip
"""

import argparse
from datetime import datetime


def main() -> None:
    parser = argparse.ArgumentParser(description="Run backtesting")
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["buy_hold", "sma_crossover", "rsi_mean_reversion", "vwap_bounce", "bollinger_bands"],
        help="Baseline strategy to backtest",
    )
    parser.add_argument(
        "--agent",
        type=str,
        choices=["ppo", "dqn", "sac", "a2c"],
        help="RL agent type to backtest",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Path to trained model (required if --agent is set)",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="SOL/USDT",
        help="Trading symbol (default: SOL/USDT)",
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2023-01-01",
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default="2024-01-01",
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--initial-capital",
        type=float,
        default=10000.0,
        help="Initial capital (default: 10000)",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed report",
    )

    args = parser.parse_args()

    if not args.strategy and not args.agent:
        parser.error("Either --strategy or --agent must be specified")

    if args.agent and not args.model:
        parser.error("--model is required when --agent is specified")

    print("📊 Starting Backtest")
    print(f"💰 Symbol: {args.symbol}")
    print(f"📅 Period: {args.start} to {args.end}")
    print(f"💵 Initial Capital: ${args.initial_capital:,.2f}")
    print()

    if args.strategy:
        print(f"📈 Strategy: {args.strategy}")
    else:
        print(f"🤖 Agent: {args.agent}")
        print(f"📦 Model: {args.model}")

    print()

    # TODO: Implement backtesting
    # from solana_rl_bot.backtesting import Backtester
    # backtester = Backtester(...)
    # results = backtester.run(...)
    # if args.report:
    #     backtester.generate_report(results)

    print("✅ Backtest completed!")


if __name__ == "__main__":
    main()
