"""
Feature Calculator für technische Indikatoren.

Berechnet technische Indikatoren für OHLCV Daten:
- Trend: SMA, EMA, MACD, ADX
- Momentum: RSI, Stochastic, CCI
- Volatilität: Bollinger Bands, ATR
- Volume: OBV, VWAP
- Custom: Returns, Volatilität, Market Regime
"""

from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from ta.trend import (
    SMAIndicator,
    EMAIndicator,
    MACD,
    ADXIndicator,
)
from ta.momentum import (
    RSIIndicator,
    StochasticOscillator,
    ROCIndicator,
)
from ta.volatility import (
    BollingerBands,
    AverageTrueRange,
)
from ta.volume import (
    OnBalanceVolumeIndicator,
    VolumeWeightedAveragePrice,
)

from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


class FeatureCalculator:
    """
    Berechnet technische Indikatoren und Features für OHLCV Daten.
    """

    def __init__(self):
        """Initialisiere FeatureCalculator."""
        logger.info("FeatureCalculator initialisiert")

    def calculate_all_features(
        self, df: pd.DataFrame, symbol: str = None
    ) -> pd.DataFrame:
        """
        Berechne alle Features für OHLCV Daten.

        Args:
            df: DataFrame mit OHLCV Daten
            symbol: Optional - Trading Symbol für Logging

        Returns:
            DataFrame mit allen berechneten Features
        """
        if df.empty or len(df) < 50:
            logger.warning(
                f"Nicht genug Daten für Feature-Berechnung (min 50, got {len(df)})"
            )
            return df

        logger.info(
            f"Berechne Features für {symbol or 'unknown'} ({len(df)} Zeilen)"
        )

        df_features = df.copy()

        # 1. Trend Indicators
        df_features = self._add_trend_indicators(df_features)

        # 2. Momentum Indicators
        df_features = self._add_momentum_indicators(df_features)

        # 3. Volatility Indicators
        df_features = self._add_volatility_indicators(df_features)

        # 4. Volume Indicators
        df_features = self._add_volume_indicators(df_features)

        # 5. Custom Features
        df_features = self._add_custom_features(df_features)

        # 6. Market Regime
        df_features = self._add_market_regime(df_features)

        logger.info(
            f"✅ {len(df_features.columns) - len(df.columns)} Features berechnet"
        )

        return df_features

    def _add_trend_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Füge Trend-Indikatoren hinzu."""
        try:
            # Simple Moving Averages
            df["sma_20"] = SMAIndicator(df["close"], window=20).sma_indicator()
            df["sma_50"] = SMAIndicator(df["close"], window=50).sma_indicator()
            df["sma_200"] = SMAIndicator(df["close"], window=200).sma_indicator()

            # Exponential Moving Averages
            df["ema_12"] = EMAIndicator(df["close"], window=12).ema_indicator()
            df["ema_26"] = EMAIndicator(df["close"], window=26).ema_indicator()

            # MACD
            macd = MACD(df["close"])
            df["macd"] = macd.macd()
            df["macd_signal"] = macd.macd_signal()
            df["macd_hist"] = macd.macd_diff()

            # ADX (Average Directional Index)
            if len(df) >= 14:
                adx = ADXIndicator(df["high"], df["low"], df["close"], window=14)
                df["adx"] = adx.adx()

            logger.debug("Trend-Indikatoren berechnet")

        except Exception as e:
            logger.error(f"Fehler bei Trend-Indikatoren: {e}")

        return df

    def _add_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Füge Momentum-Indikatoren hinzu."""
        try:
            # RSI (Relative Strength Index)
            df["rsi_14"] = RSIIndicator(df["close"], window=14).rsi()

            # Stochastic Oscillator
            if len(df) >= 14:
                stoch = StochasticOscillator(
                    df["high"], df["low"], df["close"], window=14, smooth_window=3
                )
                df["stoch_k"] = stoch.stoch()
                df["stoch_d"] = stoch.stoch_signal()

            # Rate of Change (ROC)
            df["roc"] = ROCIndicator(df["close"], window=12).roc()

            logger.debug("Momentum-Indikatoren berechnet")

        except Exception as e:
            logger.error(f"Fehler bei Momentum-Indikatoren: {e}")

        return df

    def _add_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Füge Volatilitäts-Indikatoren hinzu."""
        try:
            # Bollinger Bands
            bb = BollingerBands(df["close"], window=20, window_dev=2)
            df["bbands_upper"] = bb.bollinger_hband()
            df["bbands_middle"] = bb.bollinger_mavg()
            df["bbands_lower"] = bb.bollinger_lband()
            df["bbands_bandwidth"] = bb.bollinger_wband()

            # Average True Range (ATR)
            if len(df) >= 14:
                df["atr"] = AverageTrueRange(
                    df["high"], df["low"], df["close"], window=14
                ).average_true_range()

            logger.debug("Volatilitäts-Indikatoren berechnet")

        except Exception as e:
            logger.error(f"Fehler bei Volatilitäts-Indikatoren: {e}")

        return df

    def _add_volume_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Füge Volume-Indikatoren hinzu."""
        try:
            # On-Balance Volume (OBV)
            df["obv"] = OnBalanceVolumeIndicator(
                df["close"], df["volume"]
            ).on_balance_volume()

            # Volume Weighted Average Price (VWAP)
            df["vwap"] = VolumeWeightedAveragePrice(
                df["high"], df["low"], df["close"], df["volume"]
            ).volume_weighted_average_price()

            # Volume SMA
            df["volume_sma"] = SMAIndicator(df["volume"], window=20).sma_indicator()

            logger.debug("Volume-Indikatoren berechnet")

        except Exception as e:
            logger.error(f"Fehler bei Volume-Indikatoren: {e}")

        return df

    def _add_custom_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Füge Custom Features hinzu."""
        try:
            # Returns
            df["returns"] = df["close"].pct_change()
            df["log_returns"] = np.log(df["close"] / df["close"].shift(1))

            # Volatilität (Rolling Standard Deviation)
            df["volatility"] = df["returns"].rolling(window=20).std()

            # High-Low Spread
            df["hl_spread"] = (df["high"] - df["low"]) / df["close"]

            # Price Distance from MA
            if "sma_20" in df.columns:
                df["price_to_sma20"] = (df["close"] - df["sma_20"]) / df["sma_20"]

            # Volume Ratio
            if "volume_sma" in df.columns:
                df["volume_ratio"] = df["volume"] / df["volume_sma"]

            logger.debug("Custom Features berechnet")

        except Exception as e:
            logger.error(f"Fehler bei Custom Features: {e}")

        return df

    def _add_market_regime(self, df: pd.DataFrame) -> pd.DataFrame:
        """Bestimme Market Regime (Bull/Bear/Sideways)."""
        try:
            # Trend Regime basierend auf SMA 20 vs SMA 50
            if "sma_20" in df.columns and "sma_50" in df.columns:
                df["regime"] = "sideways"
                df.loc[df["sma_20"] > df["sma_50"] * 1.02, "regime"] = "bull"
                df.loc[df["sma_20"] < df["sma_50"] * 0.98, "regime"] = "bear"

            # Volatility Regime
            if "volatility" in df.columns:
                vol_median = df["volatility"].median()
                df["volatility_regime"] = "medium"
                df.loc[df["volatility"] < vol_median * 0.7, "volatility_regime"] = (
                    "low"
                )
                df.loc[df["volatility"] > vol_median * 1.3, "volatility_regime"] = (
                    "high"
                )

            logger.debug("Market Regime bestimmt")

        except Exception as e:
            logger.error(f"Fehler bei Market Regime: {e}")

        return df

    def get_feature_list(self) -> List[str]:
        """
        Hole Liste aller berechneten Features.

        Returns:
            Liste von Feature-Namen
        """
        features = [
            # Trend
            "sma_20",
            "sma_50",
            "sma_200",
            "ema_12",
            "ema_26",
            "macd",
            "macd_signal",
            "macd_hist",
            "adx",
            # Momentum
            "rsi_14",
            "stoch_k",
            "stoch_d",
            "roc",
            # Volatility
            "bbands_upper",
            "bbands_middle",
            "bbands_lower",
            "bbands_bandwidth",
            "atr",
            # Volume
            "obv",
            "vwap",
            "volume_sma",
            # Custom
            "returns",
            "log_returns",
            "volatility",
            "hl_spread",
            "price_to_sma20",
            "volume_ratio",
            # Regime
            "regime",
            "volatility_regime",
        ]

        return features

    def calculate_specific_features(
        self, df: pd.DataFrame, features: List[str]
    ) -> pd.DataFrame:
        """
        Berechne nur spezifische Features.

        Args:
            df: DataFrame mit OHLCV Daten
            features: Liste von gewünschten Features

        Returns:
            DataFrame mit gewählten Features
        """
        # Berechne alle Features
        df_all = self.calculate_all_features(df)

        # Wähle nur gewünschte Features
        available_features = [f for f in features if f in df_all.columns]

        if len(available_features) < len(features):
            missing = set(features) - set(available_features)
            logger.warning(f"Fehlende Features: {missing}")

        # Behalte Original-Spalten + gewählte Features
        original_cols = df.columns.tolist()
        result_cols = original_cols + available_features

        return df_all[result_cols]

    def get_feature_importance(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Berechne einfache Feature Importance (Korrelation mit Returns).

        Args:
            df: DataFrame mit Features

        Returns:
            Dictionary mit Feature -> Importance Werten
        """
        if "returns" not in df.columns:
            logger.warning("Keine Returns für Feature Importance")
            return {}

        feature_cols = self.get_feature_list()
        available_features = [f for f in feature_cols if f in df.columns]

        importance = {}
        for feature in available_features:
            try:
                # Berechne absolute Korrelation mit Returns
                corr = abs(df[feature].corr(df["returns"]))
                if not np.isnan(corr):
                    importance[feature] = corr
            except:
                pass

        # Sortiere nach Importance
        importance = dict(
            sorted(importance.items(), key=lambda x: x[1], reverse=True)
        )

        return importance
