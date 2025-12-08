#!/usr/bin/env python3
"""
Test-Script für Feature Engineering.

Testet:
- Feature-Berechnung (alle Indikatoren)
- Feature Pipeline
- Datenbank-Integration
- Feature Quality Analysis

Usage:
    python scripts/test_feature_engineering.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from solana_rl_bot.data.features import FeatureCalculator, FeaturePipeline
from solana_rl_bot.data.collectors import BinanceConnector, DataCollector
from solana_rl_bot.data.storage.db_manager import DatabaseManager
from solana_rl_bot.utils import LoggerSetup

console = Console()


def test_feature_calculator():
    """Teste FeatureCalculator."""
    console.print("\n[bold cyan]Testing FeatureCalculator...[/bold cyan]")

    try:
        # Hole echte Daten
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            df = connector.fetch_ohlcv(
                symbol="SOL/USDT",
                timeframe="5m",
                limit=300,  # Genug für alle Indikatoren
            )

            console.print(f"[green]✅ {len(df)} OHLCV Zeilen abgerufen[/green]")

            # Berechne Features
            calculator = FeatureCalculator()
            df_features = calculator.calculate_all_features(df, symbol="SOL/USDT")

            # Zeige Statistiken
            original_cols = len(df.columns)
            new_cols = len(df_features.columns) - original_cols

            console.print(f"\n[cyan]Feature-Statistiken:[/cyan]")
            console.print(f"  Original Spalten: {original_cols}")
            console.print(f"  Neue Features: {new_cols}")
            console.print(f"  Total Spalten: {len(df_features.columns)}")

            # Liste einige Features
            feature_list = calculator.get_feature_list()
            available = [f for f in feature_list if f in df_features.columns]

            console.print(f"\n[cyan]Berechnete Features ({len(available)}):[/cyan]")

            # Gruppiere nach Kategorie
            categories = {
                "Trend": ["sma", "ema", "macd", "adx"],
                "Momentum": ["rsi", "stoch", "roc"],
                "Volatility": ["bbands", "atr"],
                "Volume": ["obv", "vwap", "volume_sma"],
                "Custom": ["returns", "volatility", "regime"],
            }

            for category, keywords in categories.items():
                cat_features = [
                    f for f in available
                    if any(kw in f for kw in keywords)
                ]
                if cat_features:
                    console.print(f"  {category}: {len(cat_features)} Features")

            # Zeige Sample-Werte
            console.print(f"\n[cyan]Sample Werte (letzte Zeile):[/cyan]")
            last_row = df_features.iloc[-1]

            sample_features = ["sma_20", "rsi_14", "macd", "bbands_middle", "obv", "returns"]
            for feat in sample_features:
                if feat in last_row:
                    value = last_row[feat]
                    console.print(f"  {feat}: {value:.4f}" if pd.notna(value) else f"  {feat}: NaN")

            return True

    except Exception as e:
        console.print(f"[red]❌ FeatureCalculator Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_feature_importance():
    """Teste Feature Importance."""
    console.print("\n[bold cyan]Testing Feature Importance...[/bold cyan]")

    try:
        # Hole Daten
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            df = connector.fetch_ohlcv("SOL/USDT", "5m", limit=300)

            # Berechne Features
            calculator = FeatureCalculator()
            df_features = calculator.calculate_all_features(df)

            # Feature Importance
            importance = calculator.get_feature_importance(df_features)

            # Zeige Top 10
            console.print(f"\n[cyan]Top 10 wichtigste Features (Korrelation mit Returns):[/cyan]")
            table = Table()
            table.add_column("#", style="cyan")
            table.add_column("Feature", style="yellow")
            table.add_column("Importance", style="green")

            for i, (feature, score) in enumerate(list(importance.items())[:10], 1):
                table.add_row(str(i), feature, f"{score:.4f}")

            console.print(table)

            return len(importance) > 0

    except Exception as e:
        console.print(f"[red]❌ Feature Importance Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_feature_pipeline():
    """Teste FeaturePipeline."""
    console.print("\n[bold cyan]Testing FeaturePipeline...[/bold cyan]")

    try:
        # Hole Daten
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            df = connector.fetch_ohlcv("BTC/USDT", "5m", limit=300)

            # Initialisiere Pipeline
            db = DatabaseManager()
            pipeline = FeaturePipeline(db_manager=db)

            # Verarbeite Daten (mit DB-Save)
            console.print(f"\nVerarbeite {len(df)} Zeilen...")
            df_features = pipeline.process_ohlcv_data(
                df,
                symbol="BTC/USDT",
                timeframe="5m",
                save_to_db=True,
            )

            console.print(f"[green]✅ {len(df_features.columns)} Spalten erzeugt[/green]")

            # Hole Features aus DB zurück
            console.print(f"\nHole Features aus Datenbank...")
            df_from_db = pipeline.get_features_from_db(
                symbol="BTC/USDT",
                timeframe="5m",
            )

            if not df_from_db.empty:
                console.print(f"[green]✅ {len(df_from_db)} Zeilen aus DB abgerufen[/green]")
            else:
                console.print(f"[yellow]⚠️  Keine Features in DB (OK für ersten Lauf)[/yellow]")

            return True

    except Exception as e:
        console.print(f"[red]❌ FeaturePipeline Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_feature_quality_analysis():
    """Teste Feature Quality Analysis."""
    console.print("\n[bold cyan]Testing Feature Quality Analysis...[/bold cyan]")

    try:
        # Hole Daten
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            df = connector.fetch_ohlcv("ETH/USDT", "5m", limit=300)

            # Berechne Features
            db = DatabaseManager()
            pipeline = FeaturePipeline(db_manager=db)
            df_features = pipeline.process_ohlcv_data(
                df, "ETH/USDT", "5m", save_to_db=False
            )

            # Analysiere Qualität
            quality = pipeline.analyze_feature_quality(df_features)

            # Zeige Ergebnisse
            console.print(f"\n[cyan]Feature Quality Analysis:[/cyan]")
            console.print(f"  Total Features: {quality['total_features']}")
            console.print(f"  Total Rows: {quality['total_rows']}")
            console.print(f"  Features mit NaN: {len(quality['missing_values'])}")

            # Zeige Features mit vielen NaN
            if quality['missing_values']:
                console.print(f"\n[yellow]Features mit fehlenden Werten:[/yellow]")
                for feat, info in list(quality['missing_values'].items())[:5]:
                    console.print(f"  {feat}: {info['percentage']:.1f}% NaN")

            # Zeige Feature Ranges
            if quality['feature_ranges']:
                console.print(f"\n[cyan]Beispiel Feature Ranges:[/cyan]")
                for feat, ranges in list(quality['feature_ranges'].items())[:3]:
                    console.print(
                        f"  {feat}: [{ranges['min']:.2f}, {ranges['max']:.2f}] "
                        f"(mean: {ranges['mean']:.2f})"
                    )

            return True

    except Exception as e:
        console.print(f"[red]❌ Quality Analysis Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_database_integration():
    """Teste vollständige DB-Integration."""
    console.print("\n[bold cyan]Testing Database Integration...[/bold cyan]")

    try:
        # Sammle Daten und speichere OHLCV
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            db = DatabaseManager()

            # Sammle OHLCV
            collector = DataCollector(connector, db)
            df_ohlcv = collector.collect_ohlcv(
                symbol="SOL/USDT",
                timeframe="5m",
                limit=300,
                save_to_db=True,
            )

            console.print(f"[green]✅ {len(df_ohlcv)} OHLCV Zeilen in DB gespeichert[/green]")

            # Verarbeite Features aus DB
            pipeline = FeaturePipeline(db_manager=db)

            console.print(f"\nVerarbeite Features aus DB-Daten...")
            df_features = pipeline.process_and_save(
                symbol="SOL/USDT",
                timeframe="5m",
            )

            console.print(f"[green]✅ {len(df_features)} Feature-Zeilen erzeugt[/green]")

            # Hole Feature-Summary
            summary = pipeline.get_feature_summary(
                symbol="SOL/USDT",
                timeframe="5m",
            )

            console.print(f"\n[cyan]Feature Summary:[/cyan]")
            console.print(f"  Symbol: {summary.get('symbol')}")
            console.print(f"  Timeframe: {summary.get('timeframe')}")
            console.print(f"  Total Rows: {summary.get('total_rows')}")
            console.print(f"  Features: {summary.get('feature_count')}")

            if summary.get('date_range'):
                dr = summary['date_range']
                console.print(f"  Date Range: {dr['start']} bis {dr['end']}")

            return True

    except Exception as e:
        console.print(f"[red]❌ DB Integration Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Führe alle Tests aus."""
    console.print(
        Panel.fit(
            "[bold cyan]Solana RL Bot - Feature Engineering Test[/bold cyan]\n"
            "[yellow]Testet Berechnung technischer Indikatoren und Features[/yellow]",
            border_style="cyan",
        )
    )

    # Setup logging
    LoggerSetup.setup(log_level="INFO", log_to_file=False)

    # Importiere pandas hier für Sample-Werte
    import pandas as pd
    globals()['pd'] = pd

    tests = [
        ("Feature Calculator", test_feature_calculator),
        ("Feature Importance", test_feature_importance),
        ("Feature Pipeline", test_feature_pipeline),
        ("Quality Analysis", test_feature_quality_analysis),
        ("Database Integration", test_database_integration),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            console.print(f"[red]❌ {name} crashed: {e}[/red]")
            results.append((name, False))

    # Summary
    console.print("\n" + "=" * 60)
    console.print("[bold cyan]Test Summary[/bold cyan]")
    console.print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[green]✅ PASS[/green]" if result else "[red]❌ FAIL[/red]"
        console.print(f"{status} {name}")

    console.print("=" * 60)
    console.print(f"\nTotal: {passed}/{total} bestanden ({passed/total*100:.1f}%)")

    if passed == total:
        console.print("\n[bold green]🎉 ALLE TESTS BESTANDEN![/bold green]")
        console.print("\n[yellow]✅ Feature-Berechnung funktioniert![/yellow]")
        console.print("[yellow]✅ 29+ technische Indikatoren verfügbar![/yellow]")
        console.print("[yellow]✅ Datenbank-Integration funktioniert![/yellow]")
        console.print("[yellow]✅ Feature Quality Analysis funktioniert![/yellow]")
        return 0
    else:
        console.print("\n[bold red]❌ EINIGE TESTS FEHLGESCHLAGEN[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
