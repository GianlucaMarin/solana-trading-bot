"""
Data Collector Service

Integrates exchange connectors with database storage to automatically
collect and persist market data.
"""

from typing import Optional, List
from datetime import datetime, timedelta, timezone
import pandas as pd

from solana_rl_bot.data.collectors.base import BaseExchangeConnector
from solana_rl_bot.data.collectors.binance import BinanceConnector
from solana_rl_bot.data.storage.db_manager import DatabaseManager
from solana_rl_bot.utils import get_logger, log_performance, PerformanceLogger

logger = get_logger(__name__)


class DataCollector:
    """
    Service that orchestrates data collection from exchanges
    and persistence to the database.
    """

    def __init__(
        self,
        connector: BaseExchangeConnector,
        db_manager: DatabaseManager,
    ):
        """
        Initialize DataCollector.

        Args:
            connector: Exchange connector (e.g., BinanceConnector)
            db_manager: Database manager instance
        """
        self.connector = connector
        self.db = db_manager
        self.exchange = connector.exchange_name

        logger.info(
            f"DataCollector initialized for {self.exchange}",
            extra={"exchange": self.exchange},
        )

    @log_performance
    def collect_ohlcv(
        self,
        symbol: str,
        timeframe: str = "5m",
        limit: Optional[int] = 1000,
        save_to_db: bool = True,
    ) -> pd.DataFrame:
        """
        Collect recent OHLCV data.

        Args:
            symbol: Trading pair (e.g., 'SOL/USDT')
            timeframe: Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles to fetch
            save_to_db: Whether to save to database

        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Fetch data from exchange
            logger.info(
                f"Collecting {limit} candles for {symbol} {timeframe}",
                extra={"symbol": symbol, "timeframe": timeframe, "limit": limit},
            )

            df = self.connector.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
            )

            if df.empty:
                logger.warning(f"No data received for {symbol}")
                return df

            # Save to database
            if save_to_db:
                self._save_ohlcv(df, symbol, timeframe)

            return df

        except Exception as e:
            logger.error(f"Failed to collect OHLCV for {symbol}: {e}")
            raise

    @log_performance
    def collect_ohlcv_historical(
        self,
        symbol: str,
        timeframe: str,
        days: int = 7,
        save_to_db: bool = True,
    ) -> pd.DataFrame:
        """
        Collect historical OHLCV data for a time range.

        Args:
            symbol: Trading pair
            timeframe: Timeframe
            days: Number of days of history to collect
            save_to_db: Whether to save to database

        Returns:
            DataFrame with OHLCV data
        """
        try:
            start_time = datetime.now(timezone.utc) - timedelta(days=days)

            logger.info(
                f"Collecting {days} days of history for {symbol} {timeframe}",
                extra={"symbol": symbol, "timeframe": timeframe, "days": days},
            )

            # Fetch batch data
            df = self.connector.fetch_ohlcv_batch(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                batch_size=1000,
            )

            if df.empty:
                logger.warning(f"No historical data received for {symbol}")
                return df

            # Save to database
            if save_to_db:
                self._save_ohlcv(df, symbol, timeframe)

            logger.info(
                f"Collected {len(df)} candles for {symbol}",
                extra={"symbol": symbol, "candles": len(df)},
            )

            return df

        except Exception as e:
            logger.error(f"Failed to collect historical OHLCV for {symbol}: {e}")
            raise

    @log_performance
    def collect_ohlcv_incremental(
        self,
        symbol: str,
        timeframe: str = "5m",
    ) -> pd.DataFrame:
        """
        Collect only new OHLCV data since last database entry.

        This is efficient for continuous data collection as it only
        fetches candles that don't exist in the database yet.

        Args:
            symbol: Trading pair
            timeframe: Timeframe

        Returns:
            DataFrame with new OHLCV data
        """
        try:
            # Get latest timestamp from database
            latest_ts = self.db.get_latest_timestamp(
                symbol=symbol,
                exchange=self.exchange,
                timeframe=timeframe,
            )

            if latest_ts:
                # Fetch data since latest timestamp
                since = latest_ts + timedelta(minutes=self._get_timeframe_minutes(timeframe))
                logger.info(
                    f"Incremental collection for {symbol} since {since}",
                    extra={"symbol": symbol, "since": since},
                )
            else:
                # No data exists, fetch recent data
                since = datetime.now(timezone.utc) - timedelta(days=1)
                logger.info(
                    f"No existing data for {symbol}, fetching last 24 hours",
                    extra={"symbol": symbol},
                )

            # Fetch new data
            df = self.connector.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since,
                limit=1000,
            )

            if df.empty:
                logger.debug(f"No new data for {symbol}")
                return df

            # Save to database
            self._save_ohlcv(df, symbol, timeframe)

            logger.info(
                f"Collected {len(df)} new candles for {symbol}",
                extra={"symbol": symbol, "new_candles": len(df)},
            )

            return df

        except Exception as e:
            logger.error(f"Failed incremental collection for {symbol}: {e}")
            raise

    def collect_multiple_symbols(
        self,
        symbols: List[str],
        timeframe: str = "5m",
        days: Optional[int] = None,
        incremental: bool = True,
    ) -> dict:
        """
        Collect data for multiple symbols.

        Args:
            symbols: List of trading pairs
            timeframe: Timeframe
            days: Days of history (None = incremental only)
            incremental: Use incremental collection

        Returns:
            Dictionary mapping symbol -> DataFrame
        """
        results = {}

        logger.info(
            f"Collecting data for {len(symbols)} symbols",
            extra={"symbols": symbols, "timeframe": timeframe},
        )

        for symbol in symbols:
            try:
                if days:
                    # Historical collection
                    df = self.collect_ohlcv_historical(
                        symbol=symbol,
                        timeframe=timeframe,
                        days=days,
                    )
                elif incremental:
                    # Incremental collection
                    df = self.collect_ohlcv_incremental(
                        symbol=symbol,
                        timeframe=timeframe,
                    )
                else:
                    # Recent data
                    df = self.collect_ohlcv(
                        symbol=symbol,
                        timeframe=timeframe,
                    )

                results[symbol] = df

            except Exception as e:
                logger.error(f"Failed to collect data for {symbol}: {e}")
                results[symbol] = pd.DataFrame()

        successful = sum(1 for df in results.values() if not df.empty)
        logger.info(
            f"Collection complete: {successful}/{len(symbols)} symbols successful",
            extra={"successful": successful, "total": len(symbols)},
        )

        return results

    def _save_ohlcv(self, df: pd.DataFrame, symbol: str, timeframe: str) -> None:
        """
        Save OHLCV data to database.

        Args:
            df: DataFrame with OHLCV data
            symbol: Trading symbol
            timeframe: Timeframe
        """
        try:
            # The DataFrame already has symbol, exchange, timeframe from connector
            # But we ensure they're correct
            df["symbol"] = symbol
            df["exchange"] = self.exchange
            df["timeframe"] = timeframe

            # Insert to database (handles duplicates)
            rows = self.db.insert_ohlcv(
                data=df,
                symbol=symbol,
                exchange=self.exchange,
                timeframe=timeframe,
            )

            logger.info(
                f"Saved {rows} candles to database",
                extra={"symbol": symbol, "timeframe": timeframe, "rows": rows},
            )

        except Exception as e:
            logger.error(f"Failed to save OHLCV data: {e}")
            raise

    def _get_timeframe_minutes(self, timeframe: str) -> int:
        """
        Convert timeframe to minutes.

        Args:
            timeframe: Timeframe string (e.g., '5m', '1h')

        Returns:
            Number of minutes
        """
        mapping = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
            "1w": 10080,
        }
        return mapping.get(timeframe, 5)

    def get_stored_data(
        self,
        symbol: str,
        timeframe: str = "5m",
        days: int = 7,
    ) -> pd.DataFrame:
        """
        Retrieve stored OHLCV data from database.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            days: Number of days to retrieve

        Returns:
            DataFrame with OHLCV data
        """
        try:
            start_time = datetime.now(timezone.utc) - timedelta(days=days)

            df = self.db.get_ohlcv(
                symbol=symbol,
                exchange=self.exchange,
                timeframe=timeframe,
                start_time=start_time,
            )

            logger.debug(
                f"Retrieved {len(df)} candles from database",
                extra={"symbol": symbol, "timeframe": timeframe, "candles": len(df)},
            )

            return df

        except Exception as e:
            logger.error(f"Failed to retrieve stored data: {e}")
            raise

    def close(self) -> None:
        """Close connections."""
        self.connector.close()
        logger.info("DataCollector closed")

    def __enter__(self):
        """Context manager entry."""
        if not self.connector.is_connected():
            self.connector.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False

    def __repr__(self) -> str:
        """String representation."""
        return f"DataCollector(exchange={self.exchange}, connected={self.connector.is_connected()})"
