"""
Logging utilities for Solana RL Trading Bot.

Provides structured logging with:
- Console output (colored)
- File output (rotated)
- Database logging (critical events)
- Performance logging
"""

import sys
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime
from loguru import logger
from functools import wraps
import time

from solana_rl_bot.config import get_config


class LoggerSetup:
    """Setup and configure logging for the application."""

    _initialized = False

    @classmethod
    def setup(
        cls,
        log_level: str = "INFO",
        log_to_file: bool = True,
        log_dir: Optional[Path] = None,
        enable_console: bool = True,
    ) -> None:
        """Setup logging configuration.

        Args:
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Enable file logging
            log_dir: Directory for log files (default: project_root/logs)
            enable_console: Enable console logging
        """
        if cls._initialized:
            logger.debug("Logger already initialized, skipping setup")
            return

        # Remove default logger
        logger.remove()

        # Setup console logging
        if enable_console:
            cls._setup_console_logger(log_level)

        # Setup file logging
        if log_to_file:
            if log_dir is None:
                log_dir = Path.cwd() / "logs"
            cls._setup_file_loggers(log_level, log_dir)

        cls._initialized = True
        logger.info("Logging system initialized")

    @classmethod
    def _setup_console_logger(cls, log_level: str) -> None:
        """Setup colored console logger.

        Args:
            log_level: Minimum log level
        """
        logger.add(
            sys.stdout,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            level=log_level,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
        logger.debug(f"Console logger configured with level: {log_level}")

    @classmethod
    def _setup_file_loggers(cls, log_level: str, log_dir: Path) -> None:
        """Setup file loggers with rotation.

        Args:
            log_level: Minimum log level
            log_dir: Directory for log files
        """
        log_dir.mkdir(parents=True, exist_ok=True)

        # Main log file (all messages)
        logger.add(
            log_dir / "bot.log",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            ),
            level=log_level,
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            backtrace=True,
            diagnose=True,
        )

        # Error log file (errors and critical only)
        logger.add(
            log_dir / "errors.log",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}\n{exception}"
            ),
            level="ERROR",
            rotation="5 MB",
            retention="60 days",
            compression="zip",
            backtrace=True,
            diagnose=True,
        )

        # Trade log file (INFO and above, for trade events)
        logger.add(
            log_dir / "trades.log",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{message}"
            ),
            level="INFO",
            rotation="10 MB",
            retention="90 days",
            compression="zip",
            filter=lambda record: "TRADE" in record["message"]
            or "trade" in record["extra"].get("category", ""),
        )

        logger.debug(f"File loggers configured in: {log_dir}")

    @classmethod
    def setup_from_config(cls) -> None:
        """Setup logging from application config.

        Raises:
            RuntimeError: If config not initialized
        """
        try:
            config = get_config()
            log_level = config.log_level
            log_to_file = config.log_to_file
            log_dir = Path(config.log_file_path).parent if config.log_file_path else None

            cls.setup(
                log_level=log_level,
                log_to_file=log_to_file,
                log_dir=log_dir,
            )
        except RuntimeError:
            # Config not initialized, use defaults
            logger.warning("Config not initialized, using default logging settings")
            cls.setup()


def get_logger(name: str) -> Any:
    """Get a logger instance with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logger.bind(name=name)


def log_function_call(log_args: bool = True, log_result: bool = False):
    """Decorator to log function calls.

    Args:
        log_args: Log function arguments
        log_result: Log function result

    Example:
        >>> @log_function_call(log_args=True, log_result=True)
        >>> def my_function(x, y):
        >>>     return x + y
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"

            if log_args:
                logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")
            else:
                logger.debug(f"Calling {func_name}")

            try:
                result = func(*args, **kwargs)

                if log_result:
                    logger.debug(f"{func_name} returned: {result}")

                return result

            except Exception as e:
                logger.exception(f"Error in {func_name}: {e}")
                raise

        return wrapper

    return decorator


def log_performance(func):
    """Decorator to log function execution time.

    Example:
        >>> @log_performance
        >>> def slow_function():
        >>>     time.sleep(1)
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = f"{func.__module__}.{func.__name__}"
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time

            logger.info(
                f"⏱️  {func_name} completed in {elapsed:.3f}s",
                extra={"category": "performance", "elapsed_time": elapsed},
            )

            return result

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(
                f"❌ {func_name} failed after {elapsed:.3f}s: {e}",
                extra={"category": "performance", "elapsed_time": elapsed},
            )
            raise

    return wrapper


class PerformanceLogger:
    """Context manager for logging performance of code blocks."""

    def __init__(self, operation_name: str):
        """Initialize performance logger.

        Args:
            operation_name: Name of the operation to measure
        """
        self.operation_name = operation_name
        self.start_time = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        logger.debug(f"Starting: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and log result."""
        elapsed = time.time() - self.start_time

        if exc_type is None:
            logger.info(
                f"⏱️  {self.operation_name} completed in {elapsed:.3f}s",
                extra={"category": "performance", "elapsed_time": elapsed},
            )
        else:
            logger.error(
                f"❌ {self.operation_name} failed after {elapsed:.3f}s",
                extra={"category": "performance", "elapsed_time": elapsed},
            )

        return False  # Don't suppress exceptions


def log_trade(
    action: str,
    symbol: str,
    quantity: float,
    price: float,
    **extra_info,
) -> None:
    """Log a trade event.

    Args:
        action: Trade action (BUY, SELL, etc.)
        symbol: Trading symbol
        quantity: Trade quantity
        price: Trade price
        **extra_info: Additional information to log
    """
    emoji = "💰" if action.upper() == "BUY" else "💵"

    message = f"{emoji} TRADE | {action} {quantity} {symbol} @ ${price:,.2f}"

    # Add extra info to message
    if extra_info:
        info_str = ", ".join(f"{k}={v}" for k, v in extra_info.items())
        message += f" | {info_str}"

    logger.bind(category="trade").info(message)


def log_performance_metric(
    metric_name: str,
    value: float,
    **extra_info,
) -> None:
    """Log a performance metric.

    Args:
        metric_name: Name of the metric
        value: Metric value
        **extra_info: Additional information
    """
    # Create extra dict safely
    extra_dict = {"category": "metric", "metric_name": metric_name, "value": value}
    extra_dict.update(extra_info)

    logger.info(
        f"📊 METRIC | {metric_name}: {value:.4f}",
        extra=extra_dict,
    )


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an error with context.

    Args:
        error: The exception that occurred
        context: Additional context information
    """
    context_str = f" | Context: {context}" if context else ""
    logger.error(f"❌ ERROR | {type(error).__name__}: {error}{context_str}")
    logger.exception(error)


# Initialize logger on module import (will use defaults if config not ready)
def initialize_logging():
    """Initialize logging system."""
    try:
        LoggerSetup.setup_from_config()
    except Exception:
        # If config fails, use basic setup
        LoggerSetup.setup(log_level="INFO")


# Export commonly used logger
bot_logger = logger
