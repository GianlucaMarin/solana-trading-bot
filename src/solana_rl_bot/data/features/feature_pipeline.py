"""
Feature Engineering Pipeline

Orchestriert Feature-Berechnung und Speicherung in Datenbank.
"""

from typing import Optional, List
from datetime import datetime
import pandas as pd

from solana_rl_bot.data.features.feature_calculator import FeatureCalculator
from solana_rl_bot.data.storage.db_manager import DatabaseManager
from solana_rl_bot.utils import get_logger, log_performance

logger = get_logger(__name__)


class FeaturePipeline:
    """
    Pipeline für Feature Engineering mit Datenbank-Integration.
    """

    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        calculator: Optional[FeatureCalculator] = None,
    ):
        """
        Initialisiere FeaturePipeline.

        Args:
            db_manager: DatabaseManager für Speicherung
            calculator: FeatureCalculator für Berechnungen
        """
        self.db = db_manager or DatabaseManager()
        self.calculator = calculator or FeatureCalculator()

        logger.info("FeaturePipeline initialisiert")

    @log_performance
    def process_ohlcv_data(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        exchange: str = "binance",
        save_to_db: bool = True,
    ) -> pd.DataFrame:
        """
        Verarbeite OHLCV Daten und berechne Features.

        Args:
            df: DataFrame mit OHLCV Daten
            symbol: Trading Symbol
            timeframe: Timeframe
            exchange: Exchange Name
            save_to_db: In Datenbank speichern?

        Returns:
            DataFrame mit Features
        """
        if df.empty:
            logger.warning("Leeres DataFrame übergeben")
            return df

        logger.info(
            f"Verarbeite {len(df)} OHLCV Zeilen für {symbol} {timeframe}",
            extra={"symbol": symbol, "timeframe": timeframe, "rows": len(df)},
        )

        # Berechne Features
        df_features = self.calculator.calculate_all_features(df, symbol=symbol)

        # Speichere in Datenbank
        if save_to_db:
            self._save_features_to_db(df_features, symbol, timeframe, exchange)

        return df_features

    def _save_features_to_db(
        self, df: pd.DataFrame, symbol: str, timeframe: str, exchange: str
    ) -> None:
        """
        Speichere Features in Datenbank.

        Args:
            df: DataFrame mit Features
            symbol: Trading Symbol
            timeframe: Timeframe
            exchange: Exchange Name
        """
        try:
            # Wähle nur Feature-Spalten aus
            feature_cols = self.calculator.get_feature_list()
            available_features = ["timestamp"] + [
                f for f in feature_cols if f in df.columns
            ]

            # DataFrame für DB vorbereiten
            df_db = df[available_features].copy()

            # Füge Metadaten hinzu
            df_db["symbol"] = symbol
            df_db["timeframe"] = timeframe
            df_db["exchange"] = exchange

            # Entferne NaN Zeilen (erste Zeilen haben oft NaN wegen Indikatoren)
            df_db = df_db.dropna()

            if df_db.empty:
                logger.warning("Keine Features zum Speichern (alle NaN)")
                return

            # Speichere in DB
            rows = self.db.insert_features(
                data=df_db,
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
            )

            logger.info(
                f"✅ {rows} Feature-Zeilen in Datenbank gespeichert",
                extra={"symbol": symbol, "timeframe": timeframe, "rows": rows},
            )

        except Exception as e:
            logger.error(f"Fehler beim Speichern von Features: {e}")
            raise

    def get_features_from_db(
        self,
        symbol: str,
        timeframe: str,
        exchange: str = "binance",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        features: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Hole Features aus Datenbank.

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            exchange: Exchange Name
            start_time: Start-Zeit
            end_time: End-Zeit
            features: Liste spezifischer Features (None = alle)

        Returns:
            DataFrame mit Features
        """
        try:
            df = self.db.get_features(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
                features=features,
            )

            logger.info(
                f"📊 {len(df)} Feature-Zeilen aus DB abgerufen",
                extra={"symbol": symbol, "timeframe": timeframe, "rows": len(df)},
            )

            return df

        except Exception as e:
            logger.error(f"Fehler beim Abrufen von Features: {e}")
            return pd.DataFrame()

    def process_and_save(
        self,
        symbol: str,
        timeframe: str,
        exchange: str = "binance",
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Hole OHLCV aus DB, berechne Features und speichere zurück.

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            exchange: Exchange Name
            limit: Max Anzahl Zeilen

        Returns:
            DataFrame mit Features
        """
        # Hole OHLCV aus DB
        df_ohlcv = self.db.get_ohlcv(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            limit=limit,
        )

        if df_ohlcv.empty:
            logger.warning(f"Keine OHLCV Daten in DB für {symbol}")
            return pd.DataFrame()

        # Verarbeite und speichere Features
        df_features = self.process_ohlcv_data(
            df_ohlcv,
            symbol=symbol,
            timeframe=timeframe,
            exchange=exchange,
            save_to_db=True,
        )

        return df_features

    def update_features_incremental(
        self, symbol: str, timeframe: str, exchange: str = "binance"
    ) -> pd.DataFrame:
        """
        Update nur neue Features (inkrementell).

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            exchange: Exchange Name

        Returns:
            DataFrame mit neuen Features
        """
        try:
            # Hole neueste OHLCV Daten
            df_ohlcv = self.db.get_ohlcv(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                limit=1000,  # Genug für alle Indikatoren
            )

            if df_ohlcv.empty:
                logger.warning(f"Keine OHLCV Daten für {symbol}")
                return pd.DataFrame()

            # Hole letzten Feature-Timestamp
            latest_feature = self.db.execute_query(
                """
                SELECT MAX(timestamp) as latest
                FROM features
                WHERE symbol = :symbol
                    AND exchange = :exchange
                    AND timeframe = :timeframe
                """,
                params={
                    "symbol": symbol,
                    "exchange": exchange,
                    "timeframe": timeframe,
                },
            )

            if not latest_feature.empty and latest_feature["latest"].iloc[0]:
                latest_ts = latest_feature["latest"].iloc[0]
                # Filtere nur neue OHLCV Daten
                df_ohlcv = df_ohlcv[df_ohlcv["timestamp"] > latest_ts]

            if df_ohlcv.empty:
                logger.info(f"Keine neuen OHLCV Daten für Feature-Update")
                return pd.DataFrame()

            # Berechne Features für neue Daten
            df_features = self.process_ohlcv_data(
                df_ohlcv,
                symbol=symbol,
                timeframe=timeframe,
                exchange=exchange,
                save_to_db=True,
            )

            logger.info(
                f"✅ {len(df_features)} neue Features berechnet",
                extra={"symbol": symbol, "new_rows": len(df_features)},
            )

            return df_features

        except Exception as e:
            logger.error(f"Fehler beim inkrementellen Feature-Update: {e}")
            return pd.DataFrame()

    def analyze_feature_quality(
        self, df: pd.DataFrame
    ) -> dict:
        """
        Analysiere Feature-Qualität.

        Args:
            df: DataFrame mit Features

        Returns:
            Dictionary mit Qualitäts-Statistiken
        """
        if df.empty:
            return {"error": "Leeres DataFrame"}

        feature_cols = self.calculator.get_feature_list()
        available_features = [f for f in feature_cols if f in df.columns]

        stats = {
            "total_features": len(available_features),
            "total_rows": len(df),
            "missing_values": {},
            "feature_ranges": {},
            "correlations": {},
        }

        # Fehlende Werte
        for feature in available_features:
            nan_count = df[feature].isna().sum()
            if nan_count > 0:
                stats["missing_values"][feature] = {
                    "count": int(nan_count),
                    "percentage": float(nan_count / len(df) * 100),
                }

        # Feature Ranges
        for feature in available_features:
            if df[feature].dtype in ["float64", "float32", "int64", "int32"]:
                stats["feature_ranges"][feature] = {
                    "min": float(df[feature].min()),
                    "max": float(df[feature].max()),
                    "mean": float(df[feature].mean()),
                    "std": float(df[feature].std()),
                }

        # Feature Importance (Korrelation mit Returns)
        if "returns" in df.columns:
            importance = self.calculator.get_feature_importance(df)
            stats["feature_importance"] = importance

        return stats

    def get_feature_summary(
        self, symbol: str, timeframe: str, exchange: str = "binance"
    ) -> dict:
        """
        Erstelle Zusammenfassung der Features in DB.

        Args:
            symbol: Trading Symbol
            timeframe: Timeframe
            exchange: Exchange Name

        Returns:
            Dictionary mit Feature-Zusammenfassung
        """
        try:
            # Hole Features aus DB
            df = self.get_features_from_db(
                symbol=symbol,
                timeframe=timeframe,
                exchange=exchange,
            )

            if df.empty:
                return {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "total_rows": 0,
                    "features_available": [],
                }

            feature_cols = [
                col
                for col in df.columns
                if col not in ["timestamp", "symbol", "exchange", "timeframe"]
            ]

            summary = {
                "symbol": symbol,
                "timeframe": timeframe,
                "total_rows": len(df),
                "features_available": feature_cols,
                "feature_count": len(feature_cols),
                "date_range": {
                    "start": df["timestamp"].min(),
                    "end": df["timestamp"].max(),
                },
                "quality": self.analyze_feature_quality(df),
            }

            return summary

        except Exception as e:
            logger.error(f"Fehler bei Feature-Zusammenfassung: {e}")
            return {"error": str(e)}
