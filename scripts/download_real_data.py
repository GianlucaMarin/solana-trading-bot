#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download REAL historical SOL/USDT data from Binance.

Ersetzt die synthetischen Daten mit echten Marktdaten.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
from solana_rl_bot.data.collectors.binance import BinanceConnector
from solana_rl_bot.data.features.feature_calculator import FeatureCalculator
from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


def main():
    """Download real Binance data and calculate features."""
    logger.info("=== Real Data Download Start ===\n")

    # 1. Setup Binance Connector
    logger.info("Verbinde mit Binance...")
    connector = BinanceConnector(testnet=False, rate_limit=True)

    if not connector.connect():
        logger.error("Verbindung zu Binance fehlgeschlagen!")
        return

    logger.info("✅ Mit Binance verbunden!\n")

    # 2. Download Parameters
    symbol = "SOL/USDT"
    timeframe = "5m"
    days = 365  # 12 Monate echte Daten

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)

    logger.info(f"Download Parameters:")
    logger.info(f"  Symbol: {symbol}")
    logger.info(f"  Timeframe: {timeframe}")
    logger.info(f"  Period: {start_time.date()} bis {end_time.date()} ({days} Tage)")
    logger.info(f"  Expected Candles: ~{days * 24 * 12:,}\n")

    # 3. Download Data
    logger.info("📥 Starte Download von Binance...")
    logger.info("Dies kann 2-3 Minuten dauern...\n")

    try:
        df = connector.fetch_ohlcv_batch(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            batch_size=1000,
        )

        logger.info(f"✅ Download komplett: {len(df):,} Candles\n")

    except Exception as e:
        logger.error(f"Download fehlgeschlagen: {e}")
        return

    # 4. Basic Data Info
    logger.info("=" * 60)
    logger.info("RAW DATA SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Candles: {len(df):,}")
    logger.info(f"Zeitraum: {df['timestamp'].min()} bis {df['timestamp'].max()}")
    logger.info(f"SOL Preis Range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    logger.info(f"Ø Volume: {df['volume'].mean():,.0f}")
    logger.info("=" * 60)
    logger.info("")

    # 5. Calculate Features
    logger.info("📊 Berechne Technical Indicators...")

    feature_calc = FeatureCalculator()

    # Prepare data
    df_features = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    df_features = df_features.set_index("timestamp")

    # Calculate all features
    df_features = feature_calc.calculate_all_features(df_features, symbol="SOL/USDT")

    logger.info(f"✅ Features berechnet: {len(df_features.columns)} Features\n")

    # Clean NaN values (first rows from indicators warmup)
    logger.info("🧹 Entferne NaN Werte...")
    rows_before = len(df_features)
    df_features = df_features.dropna()
    rows_after = len(df_features)
    logger.info(f"✅ {rows_before - rows_after} Zeilen mit NaN entfernt ({rows_after:,} Zeilen übrig)\n")

    # 6. Save Data
    logger.info("💾 Speichere Daten...")

    # Create directory
    data_dir = Path("data/processed")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Save processed data
    output_path = data_dir / "sol_usdt_features.csv"
    df_features.to_csv(output_path)

    logger.info(f"✅ Daten gespeichert: {output_path}\n")

    # 7. Summary
    logger.info("=" * 60)
    logger.info("✅ DOWNLOAD COMPLETE!")
    logger.info("=" * 60)
    logger.info(f"📁 File: {output_path}")
    logger.info(f"📊 Candles: {len(df_features):,}")
    logger.info(f"🔢 Features: {len(df_features.columns)}")
    logger.info(f"💾 File Size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
    logger.info("")
    logger.info("Feature Columns:")
    for col in df_features.columns:
        logger.info(f"  - {col}")
    logger.info("=" * 60)

    # 8. Close connection
    connector.close()

    logger.info("\n🎉 Bereit für Training mit ECHTEN Daten!")


if __name__ == "__main__":
    main()
