"""
Data Quality Monitor

Überwacht die Qualität von Marktdaten und loggt Probleme in die Datenbank.
"""

from typing import Dict, Optional
from datetime import datetime
import pandas as pd

from solana_rl_bot.data.validation.data_validator import DataValidator
from solana_rl_bot.data.validation.outlier_detector import OutlierDetector
from solana_rl_bot.data.storage.db_manager import DatabaseManager
from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


class DataQualityMonitor:
    """
    Überwacht und loggt Datenqualität.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        validator: Optional[DataValidator] = None,
        outlier_detector: Optional[OutlierDetector] = None,
    ):
        """
        Initialisiere DataQualityMonitor.

        Args:
            db_manager: DatabaseManager für Logging
            validator: DataValidator Instanz
            outlier_detector: OutlierDetector Instanz
        """
        self.db = db_manager or DatabaseManager()
        self.validator = validator or DataValidator()
        self.outlier_detector = outlier_detector or OutlierDetector()

        logger.info("DataQualityMonitor initialisiert")

    def check_quality(
        self, df: pd.DataFrame, symbol: str, timeframe: str, log_to_db: bool = True
    ) -> Dict:
        """
        Führe vollständige Qualitätsprüfung durch.

        Args:
            df: DataFrame mit OHLCV Daten
            symbol: Trading Symbol
            timeframe: Timeframe
            log_to_db: In Datenbank loggen?

        Returns:
            Dictionary mit Qualitäts-Bericht
        """
        logger.info(
            f"🔍 Starte Qualitätsprüfung für {symbol} {timeframe}",
            extra={"symbol": symbol, "timeframe": timeframe, "rows": len(df)},
        )

        report = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.now(),
            "total_rows": len(df),
        }

        # 1. Datenvalidierung
        is_valid, validation_issues = self.validator.validate_ohlcv(
            df, symbol, timeframe
        )

        report["validation"] = {
            "passed": is_valid,
            "issues": validation_issues,
            "issues_count": len(validation_issues),
        }

        # 2. Ausreißererkennung
        df_with_outliers, outlier_stats = self.outlier_detector.detect_outliers(
            df, method="all"
        )

        report["outliers"] = outlier_stats

        # 3. Gesamtbewertung
        report["overall_passed"] = is_valid and outlier_stats["total_outliers"] == 0
        report["quality_score"] = self._calculate_quality_score(report)

        # 4. In Datenbank loggen
        if log_to_db and self.db:
            self._log_to_database(report)

        # 5. Ausgabe
        self._print_report(report)

        return report

    def _calculate_quality_score(self, report: Dict) -> float:
        """
        Berechne Qualitäts-Score (0-100).

        Args:
            report: Qualitäts-Bericht

        Returns:
            Score zwischen 0 und 100
        """
        score = 100.0

        # Abzüge für Validierungs-Issues
        validation_issues = report["validation"]["issues_count"]
        score -= min(validation_issues * 10, 50)  # Max 50 Punkte Abzug

        # Abzüge für Ausreißer
        outlier_percentage = report["outliers"].get("outlier_percentage", 0)
        score -= min(outlier_percentage * 2, 30)  # Max 30 Punkte Abzug

        return max(score, 0)

    def _log_to_database(self, report: Dict) -> None:
        """
        Logge Qualitäts-Bericht in Datenbank.

        Args:
            report: Qualitäts-Bericht
        """
        try:
            issues = report["validation"]["issues"]
            passed = bool(report["overall_passed"])  # Convert numpy.bool to Python bool
            outliers = int(report["outliers"]["total_outliers"])  # Convert numpy.int64 to Python int

            self.db.log_data_quality(
                symbol=report["symbol"],
                exchange="binance",
                timeframe=report["timeframe"],
                issues=issues,
                passed=passed,
                missing_bars=0,  # TODO: Implement gap counting
                outliers_detected=outliers,
                max_gap_minutes=0,  # TODO: Implement max gap calculation
            )

            logger.debug("Qualitäts-Bericht in Datenbank geloggt")

        except Exception as e:
            logger.error(f"Fehler beim Loggen in Datenbank: {e}")

    def _print_report(self, report: Dict) -> None:
        """
        Gebe Qualitäts-Bericht aus.

        Args:
            report: Qualitäts-Bericht
        """
        symbol = report["symbol"]
        timeframe = report["timeframe"]
        score = report["quality_score"]

        if report["overall_passed"]:
            logger.info(
                f"✅ Qualitätsprüfung bestanden für {symbol} {timeframe} "
                f"(Score: {score:.1f}/100)",
                extra={"symbol": symbol, "score": score},
            )
        else:
            logger.warning(
                f"⚠️  Qualitätsprobleme für {symbol} {timeframe} "
                f"(Score: {score:.1f}/100)",
                extra={
                    "symbol": symbol,
                    "score": score,
                    "issues": report["validation"]["issues_count"],
                    "outliers": report["outliers"]["total_outliers"],
                },
            )

    def get_quality_history(
        self, symbol: str, days: int = 7
    ) -> pd.DataFrame:
        """
        Hole Qualitäts-Historie aus Datenbank.

        Args:
            symbol: Trading Symbol
            days: Anzahl Tage

        Returns:
            DataFrame mit Qualitäts-Historie
        """
        try:
            df = self.db.get_data_quality_issues(days=days)

            # Filter nach Symbol
            if not df.empty and "symbol" in df.columns:
                df = df[df["symbol"] == symbol]

            return df

        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Qualitäts-Historie: {e}")
            return pd.DataFrame()

    def analyze_data_gaps(
        self, df: pd.DataFrame, timeframe: str
    ) -> Dict:
        """
        Analysiere Daten-Lücken detailliert.

        Args:
            df: DataFrame mit OHLCV Daten
            timeframe: Timeframe

        Returns:
            Dictionary mit Gap-Analyse
        """
        if len(df) < 2:
            return {"gaps": 0, "max_gap": None}

        # Sortiere nach Timestamp
        df_sorted = df.sort_values("timestamp")

        # Erwarteter Zeitabstand
        expected_delta = self.validator._get_timeframe_delta(timeframe)

        # Berechne tatsächliche Abstände
        time_diffs = df_sorted["timestamp"].diff()

        # Finde Lücken (größer als erwartet)
        gaps = time_diffs[time_diffs > expected_delta * 1.5]

        analysis = {
            "total_candles": len(df),
            "gaps_count": len(gaps),
            "max_gap": gaps.max() if not gaps.empty else None,
            "avg_gap": gaps.mean() if not gaps.empty else None,
            "gap_locations": [],
        }

        # Details zu Lücken
        if not gaps.empty:
            for idx in gaps.index:
                gap_info = {
                    "timestamp": df_sorted.loc[idx, "timestamp"],
                    "gap_duration": time_diffs.loc[idx],
                    "missing_candles": int(
                        time_diffs.loc[idx] / expected_delta
                    )
                    - 1,
                }
                analysis["gap_locations"].append(gap_info)

        return analysis

    def fix_data_issues(
        self,
        df: pd.DataFrame,
        fix_outliers: bool = True,
        outlier_method: str = "interpolate",
    ) -> pd.DataFrame:
        """
        Behebe Datenprobleme automatisch.

        Args:
            df: DataFrame mit OHLCV Daten
            fix_outliers: Ausreißer beheben?
            outlier_method: Methode für Ausreißer ('remove', 'interpolate', 'clip')

        Returns:
            Bereinigtes DataFrame
        """
        df_fixed = df.copy()

        # 1. Sortiere nach Timestamp
        df_fixed = df_fixed.sort_values("timestamp")

        # 2. Entferne Duplikate
        duplicates_before = df_fixed.duplicated(subset=["timestamp"]).sum()
        if duplicates_before > 0:
            df_fixed = df_fixed.drop_duplicates(subset=["timestamp"], keep="first")
            logger.info(f"🧹 {duplicates_before} Duplikate entfernt")

        # 3. Behebe Ausreißer
        if fix_outliers:
            df_fixed, _ = self.outlier_detector.detect_outliers(df_fixed)
            df_fixed = self.outlier_detector.clean_outliers(
                df_fixed, method=outlier_method
            )

        # 4. Reset Index
        df_fixed = df_fixed.reset_index(drop=True)

        return df_fixed

    def create_quality_report(
        self, symbol: str, timeframe: str, df: pd.DataFrame
    ) -> str:
        """
        Erstelle formatierten Qualitäts-Bericht als String.

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            df: DataFrame mit OHLCV Daten

        Returns:
            Formatierter Bericht
        """
        report = self.check_quality(df, symbol, timeframe, log_to_db=False)

        lines = [
            "=" * 60,
            f"DATA QUALITY REPORT",
            f"Symbol: {symbol} | Timeframe: {timeframe}",
            "=" * 60,
            "",
            f"Total Rows: {report['total_rows']}",
            f"Quality Score: {report['quality_score']:.1f}/100",
            "",
            "VALIDATION:",
            f"  Status: {'✅ PASSED' if report['validation']['passed'] else '❌ FAILED'}",
            f"  Issues: {report['validation']['issues_count']}",
        ]

        if report["validation"]["issues"]:
            lines.append("  Details:")
            for issue in report["validation"]["issues"]:
                lines.append(f"    - {issue}")

        lines.extend(
            [
                "",
                "OUTLIERS:",
                f"  Total: {report['outliers']['total_outliers']} ({report['outliers']['outlier_percentage']:.1f}%)",
                f"  Z-Score: {report['outliers'].get('outliers_zscore', 0)}",
                f"  IQR: {report['outliers'].get('outliers_iqr', 0)}",
                f"  MA Deviation: {report['outliers'].get('outliers_ma', 0)}",
                "",
                "=" * 60,
            ]
        )

        return "\n".join(lines)
