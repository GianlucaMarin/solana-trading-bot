"""
Database logger for storing critical events in TimescaleDB.
"""

from typing import Optional, Dict, Any
from datetime import datetime
import json
from loguru import logger

from solana_rl_bot.data.storage.db_manager import DatabaseManager


class DatabaseLogger:
    """Logger that stores critical events in the database."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize database logger.

        Args:
            db_manager: Database manager instance (creates new one if None)
        """
        self.db_manager = db_manager or DatabaseManager()
        self._enabled = True

    def log(
        self,
        level: str,
        message: str,
        module: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log message to database.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            module: Module name
            context: Additional context as dictionary

        Returns:
            True if logged successfully, False otherwise
        """
        if not self._enabled:
            return False

        try:
            with self.db_manager.get_session() as session:
                session.execute(
                    """
                    INSERT INTO system_logs (timestamp, level, module, message, context)
                    VALUES (:timestamp, :level, :module, :message, :context)
                    """,
                    {
                        "timestamp": datetime.utcnow(),
                        "level": level.upper(),
                        "module": module or "unknown",
                        "message": message,
                        "context": json.dumps(context) if context else None,
                    },
                )
                session.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to log to database: {e}")
            return False

    def log_error(
        self,
        error: Exception,
        module: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Log an error to database.

        Args:
            error: Exception that occurred
            module: Module where error occurred
            context: Additional context

        Returns:
            True if logged successfully
        """
        error_context = context or {}
        error_context["error_type"] = type(error).__name__
        error_context["error_message"] = str(error)

        return self.log(
            level="ERROR",
            message=f"{type(error).__name__}: {error}",
            module=module,
            context=error_context,
        )

    def log_trade(
        self,
        action: str,
        symbol: str,
        quantity: float,
        price: float,
        **extra_info,
    ) -> bool:
        """Log a trade event to database.

        Args:
            action: Trade action (BUY, SELL)
            symbol: Trading symbol
            quantity: Trade quantity
            price: Trade price
            **extra_info: Additional trade information

        Returns:
            True if logged successfully
        """
        context = {
            "action": action,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            **extra_info,
        }

        return self.log(
            level="INFO",
            message=f"TRADE: {action} {quantity} {symbol} @ ${price:,.2f}",
            module="trading",
            context=context,
        )

    def log_performance_metric(
        self,
        metric_name: str,
        value: float,
        **extra_info,
    ) -> bool:
        """Log a performance metric to database.

        Args:
            metric_name: Name of the metric
            value: Metric value
            **extra_info: Additional information

        Returns:
            True if logged successfully
        """
        context = {
            "metric_name": metric_name,
            "value": value,
            **extra_info,
        }

        return self.log(
            level="INFO",
            message=f"METRIC: {metric_name} = {value:.4f}",
            module="performance",
            context=context,
        )

    def enable(self) -> None:
        """Enable database logging."""
        self._enabled = True
        logger.info("Database logging enabled")

    def disable(self) -> None:
        """Disable database logging."""
        self._enabled = False
        logger.info("Database logging disabled")

    def is_enabled(self) -> bool:
        """Check if database logging is enabled.

        Returns:
            True if enabled
        """
        return self._enabled

    def close(self) -> None:
        """Close database connection."""
        if self.db_manager:
            self.db_manager.close()


# Global database logger instance
_db_logger: Optional[DatabaseLogger] = None


def get_db_logger() -> DatabaseLogger:
    """Get global database logger instance.

    Returns:
        DatabaseLogger instance
    """
    global _db_logger
    if _db_logger is None:
        _db_logger = DatabaseLogger()
    return _db_logger


def log_to_database(
    level: str,
    message: str,
    module: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> bool:
    """Log message to database using global logger.

    Args:
        level: Log level
        message: Log message
        module: Module name
        context: Additional context

    Returns:
        True if logged successfully
    """
    db_logger = get_db_logger()
    return db_logger.log(level, message, module, context)
