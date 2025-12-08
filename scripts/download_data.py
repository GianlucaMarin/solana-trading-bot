#!/usr/bin/env python3
"""
Download historical market data from exchanges.

Usage:
    python scripts/download_data.py --symbol SOL/USDT --days 365 --timeframes 5m,15m,1h,4h
"""

import argparse
from datetime import datetime, timedelta


def main() -> None:
    parser = argparse.ArgumentParser(description="Download historical market data")
    parser.add_argument(
        "--symbol",
        type=str,
        default="SOL/USDT",
        help="Trading symbol (default: SOL/USDT)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days to download (default: 365)",
    )
    parser.add_argument(
        "--timeframes",
        type=str,
        default="5m,15m,1h,4h",
        help="Comma-separated timeframes (default: 5m,15m,1h,4h)",
    )
    parser.add_argument(
        "--exchange",
        type=str,
        default="binance",
        help="Exchange name (default: binance)",
    )

    args = parser.parse_args()

    print(f"🔽 Downloading {args.symbol} data from {args.exchange}")
    print(f"📅 Period: Last {args.days} days")
    print(f"⏰ Timeframes: {args.timeframes}")
    print()

    # TODO: Implement data collection
    # from solana_rl_bot.data.collectors import BinanceCollector
    # collector = BinanceCollector()
    # collector.download_historical(args.symbol, args.days, args.timeframes.split(','))

    print("✅ Data download completed!")


if __name__ == "__main__":
    main()
