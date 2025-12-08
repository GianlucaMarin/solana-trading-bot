"""
Binance exchange connector for market data collection.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import time
import pandas as pd
import ccxt

from solana_rl_bot.data.collectors.base import BaseExchangeConnector
from solana_rl_bot.utils import get_logger, log_performance, PerformanceLogger

logger = get_logger(__name__)


class BinanceConnector(BaseExchangeConnector):
    """Binance exchange connector using ccxt."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False,
        rate_limit: bool = True,
    ):
        """Initialize Binance connector.

        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Whether to use testnet
            rate_limit: Whether to enable rate limiting
        """
        super().__init__(
            exchange_name="binance",
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
        )
        self.rate_limit = rate_limit

    def connect(self) -> bool:
        """Connect to Binance exchange.

        Returns:
            True if connected successfully
        """
        try:
            # Configure exchange
            config = {
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "enableRateLimit": self.rate_limit,
                "options": {
                    "defaultType": "spot",  # spot trading
                },
            }

            # Use testnet if specified
            if self.testnet:
                config["sandbox"] = True
                config["urls"] = {
                    "api": {
                        "public": "https://testnet.binance.vision/api/v3",
                        "private": "https://testnet.binance.vision/api/v3",
                    }
                }
                logger.info("Using Binance TESTNET")

            # Create exchange instance
            self._exchange = ccxt.binance(config)

            # Load markets
            with PerformanceLogger("Load markets"):
                self._exchange.load_markets()

            logger.info(
                f"Connected to Binance ({'testnet' if self.testnet else 'live'})",
                extra={
                    "exchange": "binance",
                    "testnet": self.testnet,
                    "markets": len(self._exchange.markets),
                },
            )

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            self._exchange = None
            return False

    @log_performance
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "5m",
        since: Optional[datetime] = None,
        limit: Optional[int] = 1000,
    ) -> pd.DataFrame:
        """Fetch OHLCV data from Binance.

        Args:
            symbol: Trading pair (e.g., 'SOL/USDT')
            timeframe: Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            since: Start time
            limit: Max number of candles (default: 1000, max: 1000)

        Returns:
            DataFrame with OHLCV data
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to exchange. Call connect() first.")

        try:
            # Convert datetime to timestamp
            since_ms = None
            if since:
                since_ms = int(since.timestamp() * 1000)

            # Fetch OHLCV data
            logger.debug(
                f"Fetching OHLCV: {symbol} {timeframe} (limit={limit})",
                extra={"symbol": symbol, "timeframe": timeframe, "limit": limit},
            )

            ohlcv = self._exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since_ms,
                limit=limit,
            )

            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )

            # Convert timestamp to datetime
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

            # Add metadata
            df["symbol"] = symbol
            df["timeframe"] = timeframe
            df["exchange"] = "binance"

            logger.info(
                f"Fetched {len(df)} candles for {symbol} {timeframe}",
                extra={"symbol": symbol, "timeframe": timeframe, "candles": len(df)},
            )

            return df

        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            raise

    def fetch_ohlcv_batch(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        batch_size: int = 1000,
    ) -> pd.DataFrame:
        """Fetch OHLCV data in batches for large time ranges.

        Args:
            symbol: Trading pair
            timeframe: Timeframe
            start_time: Start time
            end_time: End time (default: now)
            batch_size: Number of candles per request

        Returns:
            DataFrame with all OHLCV data
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        all_data = []
        current_time = start_time

        logger.info(
            f"Batch fetching {symbol} {timeframe} from {start_time} to {end_time}",
            extra={"symbol": symbol, "timeframe": timeframe},
        )

        while current_time < end_time:
            try:
                df = self.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    since=current_time,
                    limit=batch_size,
                )

                if df.empty:
                    break

                all_data.append(df)

                # Update current_time to last candle + 1 interval
                current_time = df["timestamp"].iloc[-1] + pd.Timedelta(
                    self._get_timeframe_duration(timeframe)
                )

                # Rate limiting pause
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Batch fetch failed at {current_time}: {e}")
                break

        if not all_data:
            return pd.DataFrame()

        # Combine all batches
        result = pd.concat(all_data, ignore_index=True)

        # Remove duplicates
        result = result.drop_duplicates(subset=["timestamp", "symbol"], keep="first")

        # Sort by timestamp
        result = result.sort_values("timestamp").reset_index(drop=True)

        logger.info(
            f"Batch fetch complete: {len(result)} total candles",
            extra={"symbol": symbol, "timeframe": timeframe, "total_candles": len(result)},
        )

        return result

    def _get_timeframe_duration(self, timeframe: str) -> str:
        """Convert timeframe to pandas duration string.

        Args:
            timeframe: Timeframe string (e.g., '5m', '1h')

        Returns:
            Pandas duration string
        """
        mapping = {
            "1m": "1min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "1h": "1H",
            "4h": "4H",
            "1d": "1D",
            "1w": "1W",
        }
        return mapping.get(timeframe, "1min")

    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch current ticker for symbol.

        Args:
            symbol: Trading pair

        Returns:
            Ticker dictionary
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to exchange")

        try:
            ticker = self._exchange.fetch_ticker(symbol)
            logger.debug(f"Fetched ticker for {symbol}: {ticker['last']}")
            return ticker

        except Exception as e:
            logger.error(f"Failed to fetch ticker for {symbol}: {e}")
            raise

    def get_supported_symbols(self) -> List[str]:
        """Get list of supported trading pairs.

        Returns:
            List of symbols
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to exchange")

        return list(self._exchange.markets.keys())

    def get_supported_timeframes(self) -> List[str]:
        """Get list of supported timeframes.

        Returns:
            List of timeframes
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to exchange")

        return list(self._exchange.timeframes.keys())

    def close(self) -> None:
        """Close connection to exchange."""
        if self._exchange:
            # ccxt doesn't need explicit close, but we clean up
            self._exchange = None
            logger.info("Closed Binance connection")

    def __repr__(self) -> str:
        """String representation."""
        return f"BinanceConnector(testnet={self.testnet}, connected={self.is_connected()})"
