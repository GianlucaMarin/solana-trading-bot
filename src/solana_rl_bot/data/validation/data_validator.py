"""
Data Validator für OHLCV Marktdaten.

Validiert OHLCV Daten auf:
- Preisplausibilität (OHLC Beziehungen)
- Volume Plausibilität
- Timestamp Konsistenz
- Daten-Lücken
- Duplikate
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


class DataValidator:
    """
    Validiert OHLCV Marktdaten auf Qualität und Konsistenz.
    """

    def __init__(
        self,
        min_price: float = 0.0001,
        max_price: float = 1_000_000,
        max_price_change_percent: float = 50.0,
        min_volume: float = 0.0,
        max_volume_multiplier: float = 100.0,
    ):
        """
        Initialisiere DataValidator.

        Args:
            min_price: Minimaler akzeptabler Preis
            max_price: Maximaler akzeptabler Preis
            max_price_change_percent: Maximale Preisänderung zwischen Candles (%)
            min_volume: Minimales Volume
            max_volume_multiplier: Maximaler Volume-Multiplikator vs. Durchschnitt
        """
        self.min_price = min_price
        self.max_price = max_price
        self.max_price_change_percent = max_price_change_percent
        self.min_volume = min_volume
        self.max_volume_multiplier = max_volume_multiplier

        logger.info(
            "DataValidator initialisiert",
            extra={
                "min_price": min_price,
                "max_price": max_price,
                "max_price_change": max_price_change_percent,
            },
        )

    def validate_ohlcv(
        self, df: pd.DataFrame, symbol: str, timeframe: str
    ) -> Tuple[bool, List[str]]:
        """
        Vollständige Validierung von OHLCV Daten.

        Args:
            df: DataFrame mit OHLCV Daten
            symbol: Trading Symbol
            timeframe: Timeframe

        Returns:
            Tuple[bool, List[str]]: (ist_valide, Liste von Issues)
        """
        if df.empty:
            return False, ["DataFrame ist leer"]

        issues = []

        # 1. Spalten-Validierung
        issues.extend(self._validate_columns(df))

        # 2. OHLC Beziehungen validieren
        issues.extend(self._validate_ohlc_relationships(df))

        # 3. Preisbereiche validieren
        issues.extend(self._validate_price_ranges(df))

        # 4. Volume validieren
        issues.extend(self._validate_volume(df))

        # 5. Timestamp validieren
        issues.extend(self._validate_timestamps(df, timeframe))

        # 6. Daten-Lücken finden
        issues.extend(self._find_gaps(df, timeframe))

        # 7. Duplikate finden
        issues.extend(self._find_duplicates(df))

        # 8. Extreme Preisänderungen
        issues.extend(self._validate_price_changes(df))

        is_valid = len(issues) == 0

        if is_valid:
            logger.info(
                f"✅ Datenvalidierung erfolgreich für {symbol} {timeframe}",
                extra={"symbol": symbol, "timeframe": timeframe, "rows": len(df)},
            )
        else:
            logger.warning(
                f"⚠️  {len(issues)} Validierungsprobleme für {symbol} {timeframe}",
                extra={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "issues": len(issues),
                },
            )

        return is_valid, issues

    def _validate_columns(self, df: pd.DataFrame) -> List[str]:
        """Prüfe ob alle erforderlichen Spalten vorhanden sind."""
        required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            return [f"Fehlende Spalten: {', '.join(missing_cols)}"]
        return []

    def _validate_ohlc_relationships(self, df: pd.DataFrame) -> List[str]:
        """
        Validiere OHLC Beziehungen:
        - high >= max(open, close)
        - low <= min(open, close)
        - high >= low
        """
        issues = []

        # High muss größer/gleich open und close sein
        invalid_high = df[(df["high"] < df["open"]) | (df["high"] < df["close"])]
        if not invalid_high.empty:
            issues.append(
                f"{len(invalid_high)} Zeilen: High < Open oder Close"
            )

        # Low muss kleiner/gleich open und close sein
        invalid_low = df[(df["low"] > df["open"]) | (df["low"] > df["close"])]
        if not invalid_low.empty:
            issues.append(
                f"{len(invalid_low)} Zeilen: Low > Open oder Close"
            )

        # High muss >= Low sein
        invalid_range = df[df["high"] < df["low"]]
        if not invalid_range.empty:
            issues.append(f"{len(invalid_range)} Zeilen: High < Low")

        return issues

    def _validate_price_ranges(self, df: pd.DataFrame) -> List[str]:
        """Validiere Preisbereiche."""
        issues = []

        # Prüfe auf negative oder Null-Preise
        for col in ["open", "high", "low", "close"]:
            invalid = df[df[col] <= 0]
            if not invalid.empty:
                issues.append(f"{len(invalid)} Zeilen: {col} <= 0")

        # Prüfe auf unrealistische Preise
        for col in ["open", "high", "low", "close"]:
            too_low = df[df[col] < self.min_price]
            too_high = df[df[col] > self.max_price]

            if not too_low.empty:
                issues.append(
                    f"{len(too_low)} Zeilen: {col} < {self.min_price}"
                )
            if not too_high.empty:
                issues.append(
                    f"{len(too_high)} Zeilen: {col} > {self.max_price}"
                )

        return issues

    def _validate_volume(self, df: pd.DataFrame) -> List[str]:
        """Validiere Volume."""
        issues = []

        # Prüfe auf negative Volumes
        negative_volume = df[df["volume"] < 0]
        if not negative_volume.empty:
            issues.append(f"{len(negative_volume)} Zeilen: Negatives Volume")

        # Prüfe auf zu niedriges Volume
        too_low_volume = df[df["volume"] < self.min_volume]
        if not too_low_volume.empty:
            issues.append(
                f"{len(too_low_volume)} Zeilen: Volume < {self.min_volume}"
            )

        # Prüfe auf extrem hohes Volume (Anomalie)
        if len(df) > 1:
            avg_volume = df["volume"].mean()
            max_volume = avg_volume * self.max_volume_multiplier
            extreme_volume = df[df["volume"] > max_volume]

            if not extreme_volume.empty:
                issues.append(
                    f"{len(extreme_volume)} Zeilen: Extremes Volume "
                    f"(>{self.max_volume_multiplier}x Durchschnitt)"
                )

        return issues

    def _validate_timestamps(self, df: pd.DataFrame, timeframe: str) -> List[str]:
        """Validiere Timestamps."""
        issues = []

        # Prüfe auf NULL timestamps
        null_timestamps = df[df["timestamp"].isna()]
        if not null_timestamps.empty:
            issues.append(f"{len(null_timestamps)} Zeilen: NULL Timestamp")

        # Prüfe auf nicht-monoton steigende Timestamps
        if not df["timestamp"].is_monotonic_increasing:
            issues.append("Timestamps sind nicht chronologisch sortiert")

        # Prüfe auf Zukunfts-Timestamps
        now = pd.Timestamp.now(tz="UTC")
        future_timestamps = df[df["timestamp"] > now]
        if not future_timestamps.empty:
            issues.append(
                f"{len(future_timestamps)} Zeilen: Timestamp in der Zukunft"
            )

        return issues

    def _find_gaps(self, df: pd.DataFrame, timeframe: str) -> List[str]:
        """Finde Lücken in den Daten."""
        issues = []

        if len(df) < 2:
            return issues

        # Erwarteter Zeitabstand basierend auf Timeframe
        expected_delta = self._get_timeframe_delta(timeframe)

        # Sortiere nach Timestamp
        df_sorted = df.sort_values("timestamp")

        # Berechne Zeitabstände
        time_diffs = df_sorted["timestamp"].diff()

        # Finde Lücken (größer als erwarteter Abstand)
        gaps = time_diffs[time_diffs > expected_delta * 1.5]  # 50% Toleranz

        if not gaps.empty:
            max_gap = gaps.max()
            issues.append(
                f"{len(gaps)} Daten-Lücken gefunden "
                f"(größte Lücke: {max_gap})"
            )

        return issues

    def _find_duplicates(self, df: pd.DataFrame) -> List[str]:
        """Finde Duplikate."""
        issues = []

        # Prüfe auf doppelte Timestamps
        duplicates = df[df.duplicated(subset=["timestamp"], keep=False)]
        if not duplicates.empty:
            issues.append(
                f"{len(duplicates)} doppelte Timestamps gefunden"
            )

        return issues

    def _validate_price_changes(self, df: pd.DataFrame) -> List[str]:
        """Validiere extreme Preisänderungen zwischen Candles."""
        issues = []

        if len(df) < 2:
            return issues

        # Sortiere nach Timestamp
        df_sorted = df.sort_values("timestamp").copy()

        # Berechne prozentuale Änderung
        df_sorted["price_change"] = df_sorted["close"].pct_change() * 100

        # Finde extreme Änderungen
        extreme_changes = df_sorted[
            abs(df_sorted["price_change"]) > self.max_price_change_percent
        ]

        if not extreme_changes.empty:
            max_change = extreme_changes["price_change"].abs().max()
            issues.append(
                f"{len(extreme_changes)} extreme Preisänderungen "
                f"(max: {max_change:.1f}%)"
            )

        return issues

    def _get_timeframe_delta(self, timeframe: str) -> pd.Timedelta:
        """Konvertiere Timeframe zu Timedelta."""
        mapping = {
            "1m": pd.Timedelta(minutes=1),
            "5m": pd.Timedelta(minutes=5),
            "15m": pd.Timedelta(minutes=15),
            "30m": pd.Timedelta(minutes=30),
            "1h": pd.Timedelta(hours=1),
            "4h": pd.Timedelta(hours=4),
            "1d": pd.Timedelta(days=1),
            "1w": pd.Timedelta(weeks=1),
        }
        return mapping.get(timeframe, pd.Timedelta(minutes=5))

    def get_validation_summary(
        self, df: pd.DataFrame, symbol: str, timeframe: str
    ) -> Dict:
        """
        Erstelle detaillierte Validierungs-Zusammenfassung.

        Args:
            df: DataFrame mit OHLCV Daten
            symbol: Trading Symbol
            timeframe: Timeframe

        Returns:
            Dictionary mit Validierungs-Statistiken
        """
        is_valid, issues = self.validate_ohlcv(df, symbol, timeframe)

        summary = {
            "symbol": symbol,
            "timeframe": timeframe,
            "total_rows": len(df),
            "is_valid": is_valid,
            "issues_count": len(issues),
            "issues": issues,
            "date_range": {
                "start": df["timestamp"].min() if not df.empty else None,
                "end": df["timestamp"].max() if not df.empty else None,
            },
            "price_stats": {
                "min_price": df[["open", "high", "low", "close"]].min().min()
                if not df.empty
                else None,
                "max_price": df[["open", "high", "low", "close"]].max().max()
                if not df.empty
                else None,
                "avg_close": df["close"].mean() if not df.empty else None,
            },
            "volume_stats": {
                "total_volume": df["volume"].sum() if not df.empty else 0,
                "avg_volume": df["volume"].mean() if not df.empty else 0,
                "max_volume": df["volume"].max() if not df.empty else 0,
            },
        }

        return summary
