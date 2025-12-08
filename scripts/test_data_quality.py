#!/usr/bin/env python3
"""
Test-Script für Data Quality & Validation.

Testet:
- Datenvalidierung
- Ausreißererkennung
- Data Quality Monitoring
- Datenbereinigung

Usage:
    python scripts/test_data_quality.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from solana_rl_bot.data.validation import (
    DataValidator,
    OutlierDetector,
    DataQualityMonitor,
)
from solana_rl_bot.data.collectors import BinanceConnector, DataCollector
from solana_rl_bot.data.storage.db_manager import DatabaseManager
from solana_rl_bot.utils import LoggerSetup

console = Console()


def create_test_data() -> pd.DataFrame:
    """Erstelle Test-Daten mit bekannten Problemen."""
    console.print("\n[bold cyan]Erstelle Test-Daten...[/bold cyan]")

    # Basis-Daten
    timestamps = pd.date_range(
        start="2025-12-01 00:00:00",
        end="2025-12-01 23:55:00",
        freq="5min",
        tz="UTC",
    )

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": 100 + np.random.randn(len(timestamps)) * 2,
            "high": 102 + np.random.randn(len(timestamps)) * 2,
            "low": 98 + np.random.randn(len(timestamps)) * 2,
            "close": 100 + np.random.randn(len(timestamps)) * 2,
            "volume": 1000 + np.random.randn(len(timestamps)) * 100,
        }
    )

    # Füge bekannte Probleme hinzu

    # 1. Invalide OHLC Beziehungen
    df.loc[10, "high"] = df.loc[10, "low"] - 1  # High < Low

    # 2. Negative Preise
    df.loc[20, "close"] = -50

    # 3. Ausreißer
    df.loc[30, "close"] = 500  # Extrem hoher Preis
    df.loc[40, "close"] = 10  # Extrem niedriger Preis

    # 4. Extremes Volume
    df.loc[50, "volume"] = 50000  # 50x normal

    # 5. Duplikat Timestamp
    df.loc[60, "timestamp"] = df.loc[59, "timestamp"]

    # 6. Daten-Lücke (entferne einige Zeilen)
    df = df.drop([70, 71, 72, 73, 74])

    console.print(f"[green]✅ {len(df)} Test-Zeilen erstellt mit bekannten Problemen[/green]")

    return df


def test_data_validator():
    """Teste DataValidator."""
    console.print("\n[bold cyan]Testing DataValidator...[/bold cyan]")

    try:
        # Erstelle Test-Daten
        df = create_test_data()

        # Initialisiere Validator
        validator = DataValidator(
            min_price=0.01,
            max_price=10000,
            max_price_change_percent=50.0,
        )

        # Validiere
        is_valid, issues = validator.validate_ohlcv(df, "TEST/USDT", "5m")

        # Zeige Ergebnisse
        console.print(f"\n[yellow]Validierung: {'✅ BESTANDEN' if is_valid else '❌ FEHLER'}[/yellow]")
        console.print(f"[yellow]Issues gefunden: {len(issues)}[/yellow]")

        if issues:
            table = Table(title="Validierungs-Probleme")
            table.add_column("#", style="cyan")
            table.add_column("Problem", style="yellow")

            for i, issue in enumerate(issues, 1):
                table.add_row(str(i), issue)

            console.print(table)

        # Detaillierte Zusammenfassung
        summary = validator.get_validation_summary(df, "TEST/USDT", "5m")
        console.print(f"\n[cyan]Validierungs-Zusammenfassung:[/cyan]")
        console.print(f"  Total Rows: {summary['total_rows']}")
        console.print(f"  Valid: {summary['is_valid']}")
        console.print(f"  Issues: {summary['issues_count']}")

        return len(issues) > 0  # Test besteht wenn Issues gefunden werden

    except Exception as e:
        console.print(f"[red]❌ DataValidator Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_outlier_detector():
    """Teste OutlierDetector."""
    console.print("\n[bold cyan]Testing OutlierDetector...[/bold cyan]")

    try:
        # Erstelle Test-Daten
        df = create_test_data()

        # Initialisiere Detector
        detector = OutlierDetector(
            z_score_threshold=3.0,
            iqr_multiplier=1.5,
            ma_window=20,
        )

        # Erkenne Ausreißer
        df_with_outliers, stats = detector.detect_outliers(df, method="all")

        # Zeige Ergebnisse
        table = Table(title="Ausreißer-Statistiken")
        table.add_column("Methode", style="cyan")
        table.add_column("Anzahl", style="yellow")

        table.add_row("Z-Score", str(stats["outliers_zscore"]))
        table.add_row("IQR", str(stats["outliers_iqr"]))
        table.add_row("MA Deviation", str(stats["outliers_ma"]))
        table.add_row(
            "Gesamt",
            f"{stats['total_outliers']} ({stats['outlier_percentage']:.1f}%)",
        )

        console.print(table)

        # Teste verschiedene Bereinigungsmethoden
        console.print("\n[cyan]Teste Bereinigungsmethoden:[/cyan]")

        for method in ["remove", "interpolate", "clip"]:
            df_cleaned = detector.clean_outliers(df_with_outliers, method=method)
            console.print(f"  {method}: {len(df_cleaned)} Zeilen verbleiben")

        return stats["total_outliers"] > 0  # Test besteht wenn Ausreißer gefunden

    except Exception as e:
        console.print(f"[red]❌ OutlierDetector Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_quality_monitor():
    """Teste DataQualityMonitor."""
    console.print("\n[bold cyan]Testing DataQualityMonitor...[/bold cyan]")

    try:
        # Erstelle Test-Daten
        df = create_test_data()

        # Initialisiere Monitor (ohne DB für Test)
        monitor = DataQualityMonitor(db_manager=None)

        # Führe Qualitätsprüfung durch
        report = monitor.check_quality(
            df, "TEST/USDT", "5m", log_to_db=False
        )

        # Zeige Bericht
        console.print("\n[cyan]Quality Report:[/cyan]")
        console.print(f"  Symbol: {report['symbol']}")
        console.print(f"  Timeframe: {report['timeframe']}")
        console.print(f"  Total Rows: {report['total_rows']}")
        console.print(f"  Quality Score: {report['quality_score']:.1f}/100")
        console.print(f"  Overall Passed: {report['overall_passed']}")

        # Teste Daten-Gap Analyse
        gap_analysis = monitor.analyze_data_gaps(df, "5m")
        console.print(f"\n[cyan]Gap Analysis:[/cyan]")
        console.print(f"  Gaps Found: {gap_analysis['gaps_count']}")
        if gap_analysis['max_gap']:
            console.print(f"  Max Gap: {gap_analysis['max_gap']}")

        # Teste automatische Bereinigung
        console.print(f"\n[cyan]Teste automatische Bereinigung...[/cyan]")
        df_fixed = monitor.fix_data_issues(df, fix_outliers=True)
        console.print(f"  Vor Bereinigung: {len(df)} Zeilen")
        console.print(f"  Nach Bereinigung: {len(df_fixed)} Zeilen")

        # Erstelle formatierten Bericht
        console.print("\n[cyan]Formatierter Bericht:[/cyan]")
        report_str = monitor.create_quality_report("TEST/USDT", "5m", df)
        console.print(report_str)

        return report["quality_score"] < 100  # Test besteht wenn Probleme gefunden

    except Exception as e:
        console.print(f"[red]❌ QualityMonitor Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_real_data_quality():
    """Teste mit echten Binance-Daten."""
    console.print("\n[bold cyan]Testing mit echten Binance-Daten...[/bold cyan]")

    try:
        api_key = os.getenv("BINANCE_API_KEY")
        api_secret = os.getenv("BINANCE_API_SECRET")
        testnet = os.getenv("BINANCE_TESTNET", "false").lower() == "true"

        with BinanceConnector(api_key, api_secret, testnet) as connector:
            # Hole echte Daten
            df = connector.fetch_ohlcv(
                symbol="SOL/USDT",
                timeframe="5m",
                limit=100,
            )

            console.print(f"[green]✅ {len(df)} echte Candles abgerufen[/green]")

            # Initialisiere Monitor
            db = DatabaseManager()
            monitor = DataQualityMonitor(db_manager=db)

            # Prüfe Qualität
            report = monitor.check_quality(
                df, "SOL/USDT", "5m", log_to_db=True
            )

            # Zeige Ergebnisse
            table = Table(title="Echte Daten - Qualitäts-Bericht")
            table.add_column("Metrik", style="cyan")
            table.add_column("Wert", style="green")

            table.add_row("Total Rows", str(report["total_rows"]))
            table.add_row("Quality Score", f"{report['quality_score']:.1f}/100")
            table.add_row(
                "Validation",
                "✅ PASS" if report["validation"]["passed"] else "❌ FAIL",
            )
            table.add_row("Issues", str(report["validation"]["issues_count"]))
            table.add_row("Outliers", str(report["outliers"]["total_outliers"]))
            table.add_row(
                "Overall",
                "✅ PASS" if report["overall_passed"] else "⚠️  WARN",
            )

            console.print(table)

            return True

    except Exception as e:
        console.print(f"[red]❌ Real data test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_quality_monitoring_integration():
    """Teste Integration mit DatabaseManager."""
    console.print("\n[bold cyan]Testing Quality Monitoring Integration...[/bold cyan]")

    try:
        db = DatabaseManager()

        # Erstelle Test-Daten
        df = create_test_data()

        # Initialisiere Monitor mit DB
        monitor = DataQualityMonitor(db_manager=db)

        # Führe Qualitätsprüfung durch (mit DB-Logging)
        report = monitor.check_quality(
            df, "TEST/USDT", "5m", log_to_db=True
        )

        console.print("[green]✅ Quality Report in Datenbank geloggt[/green]")

        # Hole Historie aus DB
        history = monitor.get_quality_history("TEST/USDT", days=7)

        if not history.empty:
            console.print(f"[green]✅ {len(history)} Quality-Einträge in DB gefunden[/green]")
        else:
            console.print("[yellow]⚠️  Keine Quality-Historie gefunden (OK für ersten Lauf)[/yellow]")

        return True

    except Exception as e:
        console.print(f"[red]❌ Integration Test fehlgeschlagen: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Führe alle Tests aus."""
    console.print(
        Panel.fit(
            "[bold cyan]Solana RL Bot - Data Quality & Validation Test[/bold cyan]\n"
            "[yellow]Testet Datenvalidierung, Ausreißererkennung und Quality Monitoring[/yellow]",
            border_style="cyan",
        )
    )

    # Setup logging
    LoggerSetup.setup(log_level="INFO", log_to_file=False)

    tests = [
        ("DataValidator", test_data_validator),
        ("OutlierDetector", test_outlier_detector),
        ("QualityMonitor", test_quality_monitor),
        ("Real Data Quality", test_real_data_quality),
        ("DB Integration", test_quality_monitoring_integration),
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
        console.print("\n[yellow]✅ Datenvalidierung funktioniert![/yellow]")
        console.print("[yellow]✅ Ausreißererkennung funktioniert![/yellow]")
        console.print("[yellow]✅ Quality Monitoring funktioniert![/yellow]")
        return 0
    else:
        console.print("\n[bold red]❌ EINIGE TESTS FEHLGESCHLAGEN[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
