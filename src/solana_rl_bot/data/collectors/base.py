"""
Base exchange connector for market data collection.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd

from solana_rl_bot.utils import get_logger

logger = get_logger(__name__)


class BaseExchangeConnector(ABC):
    """Abstract base class for exchange connectors."""

    def __init__(
        self,
        exchange_name: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False,
    ):
        """Initialize exchange connector.

        Args:
            exchange_name: Name of the exchange
            api_key: API key (optional for public data)
            api_secret: API secret (optional for public data)
            testnet: Whether to use testnet
        """
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self._exchange = None

        logger.info(
            f"Initializing {exchange_name} connector (testnet={testnet})",
            extra={"exchange": exchange_name, "testnet": testnet},
        )

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the exchange.

        Returns:
            True if connected successfully
        """
        pass

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """Fetch OHLCV (candlestick) data.

        Args:
            symbol: Trading pair symbol (e.g., 'SOL/USDT')
            timeframe: Timeframe (e.g., '5m', '1h', '1d')
            since: Start time for data
            limit: Maximum number of candles to fetch

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        pass

    @abstractmethod
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch current ticker data.

        Args:
            symbol: Trading pair symbol

        Returns:
            Dictionary with ticker data
        """
        pass

    @abstractmethod
    def get_supported_symbols(self) -> List[str]:
        """Get list of supported trading pairs.

        Returns:
            List of symbol strings
        """
        pass

    @abstractmethod
    def get_supported_timeframes(self) -> List[str]:
        """Get list of supported timeframes.

        Returns:
            List of timeframe strings
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close connection to exchange."""
        pass

    def is_connected(self) -> bool:
        """Check if connected to exchange.

        Returns:
            True if connected
        """
        return self._exchange is not None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
