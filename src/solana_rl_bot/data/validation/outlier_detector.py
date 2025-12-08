"""
Outlier Detection für OHLCV Marktdaten.

Erkennt Ausreißer mit verschiedenen Methoden:
- Z-Score
- IQR (Interquartile Range)
- Moving Average Deviation
"""

from typing import List, Dict, Tuple
import pandas as pd
import numpy as np

from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


class OutlierDetector:
    """
    Erkennt Ausreißer in OHLCV Marktdaten.
    """

    def __init__(
        self,
        z_score_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        ma_window: int = 20,
        ma_std_multiplier: float = 3.0,
    ):
        """
        Initialisiere OutlierDetector.

        Args:
            z_score_threshold: Z-Score Schwellwert (Standard: 3.0)
            iqr_multiplier: IQR Multiplikator (Standard: 1.5)
            ma_window: Moving Average Fenster (Standard: 20)
            ma_std_multiplier: MA Standardabweichungs-Multiplikator (Standard: 3.0)
        """
        self.z_score_threshold = z_score_threshold
        self.iqr_multiplier = iqr_multiplier
        self.ma_window = ma_window
        self.ma_std_multiplier = ma_std_multiplier

        logger.info(
            "OutlierDetector initialisiert",
            extra={
                "z_threshold": z_score_threshold,
                "iqr_multiplier": iqr_multiplier,
                "ma_window": ma_window,
            },
        )

    def detect_outliers(
        self, df: pd.DataFrame, method: str = "all"
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        Erkenne Ausreißer mit gewählter Methode.

        Args:
            df: DataFrame mit OHLCV Daten
            method: Methode ('z_score', 'iqr', 'ma_deviation', 'all')

        Returns:
            Tuple[DataFrame, Dict]: (DataFrame mit Outlier-Flags, Statistiken)
        """
        if df.empty:
            return df, {"total_outliers": 0}

        df_result = df.copy()

        # Initialisiere Outlier-Spalten
        df_result["is_outlier_zscore"] = False
        df_result["is_outlier_iqr"] = False
        df_result["is_outlier_ma"] = False
        df_result["is_outlier"] = False

        stats = {
            "total_rows": len(df),
            "outliers_zscore": 0,
            "outliers_iqr": 0,
            "outliers_ma": 0,
            "total_outliers": 0,
        }

        # Z-Score Methode
        if method in ["z_score", "all"]:
            df_result, z_count = self._detect_zscore_outliers(df_result)
            stats["outliers_zscore"] = z_count

        # IQR Methode
        if method in ["iqr", "all"]:
            df_result, iqr_count = self._detect_iqr_outliers(df_result)
            stats["outliers_iqr"] = iqr_count

        # Moving Average Deviation
        if method in ["ma_deviation", "all"]:
            df_result, ma_count = self._detect_ma_outliers(df_result)
            stats["outliers_ma"] = ma_count

        # Kombiniere alle Methoden
        df_result["is_outlier"] = (
            df_result["is_outlier_zscore"]
            | df_result["is_outlier_iqr"]
            | df_result["is_outlier_ma"]
        )

        stats["total_outliers"] = df_result["is_outlier"].sum()
        stats["outlier_percentage"] = (
            stats["total_outliers"] / stats["total_rows"] * 100
            if stats["total_rows"] > 0
            else 0
        )

        if stats["total_outliers"] > 0:
            logger.warning(
                f"⚠️  {stats['total_outliers']} Ausreißer erkannt "
                f"({stats['outlier_percentage']:.1f}%)",
                extra=stats,
            )
        else:
            logger.info("✅ Keine Ausreißer gefunden")

        return df_result, stats

    def _detect_zscore_outliers(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, int]:
        """
        Erkenne Ausreißer mit Z-Score Methode.

        Z-Score = (x - mean) / std
        Ausreißer: |Z-Score| > threshold
        """
        if len(df) < 3:
            return df, 0

        # Berechne Z-Scores für Close-Preise
        close_mean = df["close"].mean()
        close_std = df["close"].std()

        if close_std > 0:
            df["z_score"] = (df["close"] - close_mean) / close_std
            df["is_outlier_zscore"] = (
                abs(df["z_score"]) > self.z_score_threshold
            )
        else:
            df["z_score"] = 0
            df["is_outlier_zscore"] = False

        outlier_count = df["is_outlier_zscore"].sum()
        return df, outlier_count

    def _detect_iqr_outliers(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, int]:
        """
        Erkenne Ausreißer mit IQR (Interquartile Range) Methode.

        IQR = Q3 - Q1
        Ausreißer: x < Q1 - 1.5*IQR oder x > Q3 + 1.5*IQR
        """
        if len(df) < 4:
            return df, 0

        # Berechne Quartile
        q1 = df["close"].quantile(0.25)
        q3 = df["close"].quantile(0.75)
        iqr = q3 - q1

        # Berechne Grenzen
        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr

        # Markiere Ausreißer
        df["is_outlier_iqr"] = (df["close"] < lower_bound) | (
            df["close"] > upper_bound
        )

        outlier_count = df["is_outlier_iqr"].sum()
        return df, outlier_count

    def _detect_ma_outliers(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, int]:
        """
        Erkenne Ausreißer basierend auf Moving Average Deviation.

        Ausreißer: |price - MA| > std_multiplier * rolling_std
        """
        if len(df) < self.ma_window:
            return df, 0

        # Sortiere nach Timestamp
        df_sorted = df.sort_values("timestamp")

        # Berechne Moving Average und Std
        df_sorted["ma"] = (
            df_sorted["close"].rolling(window=self.ma_window).mean()
        )
        df_sorted["ma_std"] = (
            df_sorted["close"].rolling(window=self.ma_window).std()
        )

        # Berechne Abweichung
        df_sorted["ma_deviation"] = abs(df_sorted["close"] - df_sorted["ma"])

        # Markiere Ausreißer
        df_sorted["is_outlier_ma"] = (
            df_sorted["ma_deviation"]
            > self.ma_std_multiplier * df_sorted["ma_std"]
        )

        # Handle NaN values vom Rolling Window
        df_sorted["is_outlier_ma"] = df_sorted["is_outlier_ma"].fillna(False)

        # Kopiere zurück zu Original-Index
        df["is_outlier_ma"] = df_sorted["is_outlier_ma"]
        df["ma"] = df_sorted["ma"]
        df["ma_deviation"] = df_sorted["ma_deviation"]

        outlier_count = df["is_outlier_ma"].sum()
        return df, outlier_count

    def get_outlier_summary(
        self, df: pd.DataFrame, symbol: str, timeframe: str
    ) -> Dict:
        """
        Erstelle detaillierte Ausreißer-Zusammenfassung.

        Args:
            df: DataFrame mit Outlier-Flags
            symbol: Trading Symbol
            timeframe: Timeframe

        Returns:
            Dictionary mit Ausreißer-Statistiken
        """
        if "is_outlier" not in df.columns:
            return {"error": "Keine Outlier-Detection durchgeführt"}

        outliers = df[df["is_outlier"]]

        summary = {
            "symbol": symbol,
            "timeframe": timeframe,
            "total_rows": len(df),
            "total_outliers": len(outliers),
            "outlier_percentage": (
                len(outliers) / len(df) * 100 if len(df) > 0 else 0
            ),
            "methods": {
                "z_score": df["is_outlier_zscore"].sum()
                if "is_outlier_zscore" in df.columns
                else 0,
                "iqr": df["is_outlier_iqr"].sum()
                if "is_outlier_iqr" in df.columns
                else 0,
                "ma_deviation": df["is_outlier_ma"].sum()
                if "is_outlier_ma" in df.columns
                else 0,
            },
        }

        # Ausreißer-Details
        if not outliers.empty:
            summary["outlier_details"] = {
                "timestamps": outliers["timestamp"].tolist(),
                "prices": outliers["close"].tolist(),
                "min_price": outliers["close"].min(),
                "max_price": outliers["close"].max(),
            }

        return summary

    def clean_outliers(
        self,
        df: pd.DataFrame,
        method: str = "remove",
        interpolate_method: str = "linear",
    ) -> pd.DataFrame:
        """
        Bereinige Ausreißer aus Daten.

        Args:
            df: DataFrame mit Outlier-Flags
            method: Methode ('remove', 'interpolate', 'clip')
            interpolate_method: Interpolations-Methode ('linear', 'ffill', 'bfill')

        Returns:
            Bereinigtes DataFrame
        """
        if "is_outlier" not in df.columns:
            logger.warning("Keine Outlier-Flags gefunden, gebe Original zurück")
            return df

        outlier_count = df["is_outlier"].sum()

        if outlier_count == 0:
            logger.info("Keine Ausreißer zum Bereinigen")
            return df

        df_clean = df.copy()

        if method == "remove":
            # Entferne Ausreißer
            df_clean = df_clean[~df_clean["is_outlier"]]
            logger.info(f"🧹 {outlier_count} Ausreißer entfernt")

        elif method == "interpolate":
            # Ersetze Ausreißer durch interpolierte Werte
            df_clean.loc[df_clean["is_outlier"], "close"] = np.nan
            df_clean["close"] = df_clean["close"].interpolate(
                method=interpolate_method
            )
            logger.info(f"🔧 {outlier_count} Ausreißer interpoliert")

        elif method == "clip":
            # Clip Ausreißer zu IQR-Grenzen
            q1 = df["close"].quantile(0.25)
            q3 = df["close"].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - self.iqr_multiplier * iqr
            upper_bound = q3 + self.iqr_multiplier * iqr

            df_clean.loc[df_clean["is_outlier"], "close"] = df_clean.loc[
                df_clean["is_outlier"], "close"
            ].clip(lower_bound, upper_bound)
            logger.info(f"✂️  {outlier_count} Ausreißer geclippt")

        else:
            logger.warning(f"Unbekannte Methode: {method}")

        return df_clean
