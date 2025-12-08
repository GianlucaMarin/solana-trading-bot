"""
Database Manager for Solana RL Trading Bot

Provides connection pooling, CRUD operations, and database utilities
for TimescaleDB integration.
"""

import os
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Generator, List, Optional

import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool


class DatabaseManager:
    """
    Manages database connections with connection pooling and provides
    CRUD operations for all database tables.
    """

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize DatabaseManager with connection pooling.

        Args:
            connection_string: PostgreSQL connection string. If None, builds from environment.
        """
        if connection_string is None:
            connection_string = self._build_connection_string()

        self.connection_string = connection_string
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        logger.info("DatabaseManager initialized with connection pooling")

    def _build_connection_string(self) -> str:
        """Build connection string from environment variables."""
        host = os.getenv("TIMESCALE_HOST", "localhost")
        port = os.getenv("TIMESCALE_PORT", "5432")
        db = os.getenv("TIMESCALE_DB", "trading_bot")
        user = os.getenv("TIMESCALE_USER", "postgres")
        password = os.getenv("TIMESCALE_PASSWORD", "changeme")

        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine with connection pooling."""
        return create_engine(
            self.connection_string,
            poolclass=QueuePool,
            pool_size=10,  # Number of connections to maintain
            max_overflow=20,  # Additional connections allowed
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=False,  # Set to True for SQL logging
        )

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.

        Usage:
            with db_manager.get_session() as session:
                session.query(...)

        Yields:
            Session: SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def health_check(self) -> bool:
        """
        Check if database is accessible.

        Returns:
            bool: True if database is healthy
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            logger.debug("Database health check passed")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    # ==============================================
    # OHLCV Operations
    # ==============================================

    def insert_ohlcv(
        self,
        data: pd.DataFrame,
        symbol: str,
        exchange: str = "binance",
        timeframe: str = "5m",
    ) -> int:
        """
        Insert OHLCV data efficiently (bulk insert).

        Args:
            data: DataFrame with columns: timestamp, open, high, low, close, volume
            symbol: Trading symbol (e.g., 'SOL/USDT')
            exchange: Exchange name
            timeframe: Timeframe (e.g., '5m', '1h')

        Returns:
            Number of rows inserted
        """
        try:
            # Prepare data
            df = data.copy()
            df["symbol"] = symbol
            df["exchange"] = exchange
            df["timeframe"] = timeframe

            # Ensure required columns
            required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"Missing required columns. Need: {required_cols}")

            # Insert using pandas to_sql
            rows_inserted = df.to_sql(
                "ohlcv",
                self.engine,
                if_exists="append",
                index=False,
                method="multi",
            )

            logger.info(
                f"Inserted {rows_inserted} OHLCV rows for {symbol} ({timeframe})"
            )
            return rows_inserted if rows_inserted else 0

        except Exception as e:
            logger.error(f"Failed to insert OHLCV data: {e}")
            raise

    def get_ohlcv(
        self,
        symbol: str,
        exchange: str = "binance",
        timeframe: str = "5m",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data as DataFrame.

        Args:
            symbol: Trading symbol
            exchange: Exchange name
            timeframe: Timeframe
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)
            limit: Maximum number of rows to return

        Returns:
            DataFrame with OHLCV data
        """
        try:
            query = text(
                """
                SELECT timestamp, open, high, low, close, volume, quote_volume, trades
                FROM ohlcv
                WHERE symbol = :symbol
                    AND exchange = :exchange
                    AND timeframe = :timeframe
                    AND (:start_time IS NULL OR timestamp >= :start_time)
                    AND (:end_time IS NULL OR timestamp <= :end_time)
                ORDER BY timestamp ASC
                LIMIT :limit
                """
            )

            with self.engine.connect() as conn:
                df = pd.read_sql(
                    query,
                    conn,
                    params={
                        "symbol": symbol,
                        "exchange": exchange,
                        "timeframe": timeframe,
                        "start_time": start_time,
                        "end_time": end_time,
                        "limit": limit if limit else 1000000,
                    },
                )

            logger.debug(f"Fetched {len(df)} OHLCV rows for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch OHLCV data: {e}")
            raise

    def get_latest_timestamp(
        self, symbol: str, exchange: str = "binance", timeframe: str = "5m"
    ) -> Optional[datetime]:
        """
        Get timestamp of most recent data.

        Args:
            symbol: Trading symbol
            exchange: Exchange name
            timeframe: Timeframe

        Returns:
            Latest timestamp or None if no data
        """
        try:
            query = text(
                """
                SELECT MAX(timestamp) as latest
                FROM ohlcv
                WHERE symbol = :symbol
                    AND exchange = :exchange
                    AND timeframe = :timeframe
                """
            )

            with self.engine.connect() as conn:
                result = conn.execute(
                    query,
                    {"symbol": symbol, "exchange": exchange, "timeframe": timeframe},
                ).fetchone()

            latest = result[0] if result else None
            logger.debug(f"Latest timestamp for {symbol}: {latest}")
            return latest

        except Exception as e:
            logger.error(f"Failed to get latest timestamp: {e}")
            return None

    # ==============================================
    # Features Operations
    # ==============================================

    def insert_features(
        self,
        data: pd.DataFrame,
        symbol: str,
        exchange: str = "binance",
        timeframe: str = "5m",
    ) -> int:
        """
        Insert calculated features.

        Args:
            data: DataFrame with timestamp and feature columns
            symbol: Trading symbol
            exchange: Exchange name
            timeframe: Timeframe

        Returns:
            Number of rows inserted
        """
        try:
            df = data.copy()
            df["symbol"] = symbol
            df["exchange"] = exchange
            df["timeframe"] = timeframe

            if "timestamp" not in df.columns:
                raise ValueError("DataFrame must have 'timestamp' column")

            rows_inserted = df.to_sql(
                "features",
                self.engine,
                if_exists="append",
                index=False,
                method="multi",
            )

            logger.info(
                f"Inserted {rows_inserted} feature rows for {symbol} ({timeframe})"
            )
            return rows_inserted if rows_inserted else 0

        except Exception as e:
            logger.error(f"Failed to insert features: {e}")
            raise

    def get_features(
        self,
        symbol: str,
        exchange: str = "binance",
        timeframe: str = "5m",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        features: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Fetch features (optionally specific columns).

        Args:
            symbol: Trading symbol
            exchange: Exchange name
            timeframe: Timeframe
            start_time: Start timestamp
            end_time: End timestamp
            features: List of feature column names (None = all)

        Returns:
            DataFrame with features
        """
        try:
            cols = ", ".join(features) if features else "*"
            query = text(
                f"""
                SELECT timestamp, {cols}
                FROM features
                WHERE symbol = :symbol
                    AND exchange = :exchange
                    AND timeframe = :timeframe
                    AND (:start_time IS NULL OR timestamp >= :start_time)
                    AND (:end_time IS NULL OR timestamp <= :end_time)
                ORDER BY timestamp ASC
                """
            )

            with self.engine.connect() as conn:
                df = pd.read_sql(
                    query,
                    conn,
                    params={
                        "symbol": symbol,
                        "exchange": exchange,
                        "timeframe": timeframe,
                        "start_time": start_time,
                        "end_time": end_time,
                    },
                )

            logger.debug(f"Fetched {len(df)} feature rows for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch features: {e}")
            raise

    # ==============================================
    # Trade Operations
    # ==============================================

    def insert_trade(self, trade_data: Dict) -> str:
        """
        Insert a new trade.

        Args:
            trade_data: Dictionary with trade information

        Returns:
            trade_id of inserted trade
        """
        try:
            with self.get_session() as session:
                # Convert dict to SQL INSERT
                columns = ", ".join(trade_data.keys())
                placeholders = ", ".join([f":{k}" for k in trade_data.keys()])
                query = text(
                    f"""
                    INSERT INTO trades ({columns})
                    VALUES ({placeholders})
                    RETURNING trade_id
                    """
                )

                result = session.execute(query, trade_data)
                trade_id = result.fetchone()[0]

            logger.info(f"Inserted trade: {trade_id}")
            return trade_id

        except Exception as e:
            logger.error(f"Failed to insert trade: {e}")
            raise

    def update_trade(self, trade_id: str, updates: Dict) -> bool:
        """
        Update trade (e.g., close position).

        Args:
            trade_id: Trade ID to update
            updates: Dictionary of fields to update

        Returns:
            True if successful
        """
        try:
            with self.get_session() as session:
                set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
                query = text(
                    f"""
                    UPDATE trades
                    SET {set_clause}, updated_at = NOW()
                    WHERE trade_id = :trade_id
                    """
                )

                updates["trade_id"] = trade_id
                session.execute(query, updates)

            logger.info(f"Updated trade: {trade_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update trade: {e}")
            return False

    def get_trades(
        self,
        strategy: Optional[str] = None,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Fetch trades with filters.

        Args:
            strategy: Strategy name filter
            symbol: Symbol filter
            status: Status filter (open, closed, cancelled)
            start_date: Start date filter
            end_date: End date filter

        Returns:
            DataFrame with trades
        """
        try:
            query = text(
                """
                SELECT *
                FROM trades
                WHERE (:strategy IS NULL OR strategy_name = :strategy)
                    AND (:symbol IS NULL OR symbol = :symbol)
                    AND (:status IS NULL OR status = :status)
                    AND (:start_date IS NULL OR entry_time >= :start_date)
                    AND (:end_date IS NULL OR entry_time <= :end_date)
                ORDER BY entry_time DESC
                """
            )

            with self.engine.connect() as conn:
                df = pd.read_sql(
                    query,
                    conn,
                    params={
                        "strategy": strategy,
                        "symbol": symbol,
                        "status": status,
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                )

            logger.debug(f"Fetched {len(df)} trades")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch trades: {e}")
            raise

    # ==============================================
    # Performance Operations
    # ==============================================

    def insert_performance(self, metrics: Dict) -> int:
        """
        Record performance metrics.

        Args:
            metrics: Dictionary with performance metrics

        Returns:
            ID of inserted row
        """
        try:
            with self.get_session() as session:
                columns = ", ".join(metrics.keys())
                placeholders = ", ".join([f":{k}" for k in metrics.keys()])
                query = text(
                    f"""
                    INSERT INTO performance ({columns})
                    VALUES ({placeholders})
                    RETURNING id
                    """
                )

                result = session.execute(query, metrics)
                perf_id = result.fetchone()[0]

            logger.info(f"Inserted performance metrics: {perf_id}")
            return perf_id

        except Exception as e:
            logger.error(f"Failed to insert performance metrics: {e}")
            raise

    def get_performance_history(
        self,
        strategy: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Get performance over time.

        Args:
            strategy: Strategy name
            start_date: Start date filter
            end_date: End date filter

        Returns:
            DataFrame with performance history
        """
        try:
            query = text(
                """
                SELECT *
                FROM performance
                WHERE strategy_name = :strategy
                    AND (:start_date IS NULL OR time >= :start_date)
                    AND (:end_date IS NULL OR time <= :end_date)
                ORDER BY time ASC
                """
            )

            with self.engine.connect() as conn:
                df = pd.read_sql(
                    query,
                    conn,
                    params={
                        "strategy": strategy,
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                )

            logger.debug(f"Fetched {len(df)} performance records for {strategy}")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch performance history: {e}")
            raise

    # ==============================================
    # Data Quality Operations
    # ==============================================

    def log_data_quality(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        issues: List[str],
        passed: bool,
        **metrics: int,
    ) -> None:
        """
        Log data quality check results.

        Args:
            symbol: Trading symbol
            exchange: Exchange name
            timeframe: Timeframe
            issues: List of issue descriptions
            passed: Whether all checks passed
            **metrics: Additional quality metrics
        """
        try:
            with self.get_session() as session:
                query = text(
                    """
                    INSERT INTO data_quality
                    (time, symbol, exchange, timeframe, issues, passed_all_checks,
                     missing_bars, outliers_detected, max_gap_minutes)
                    VALUES (NOW(), :symbol, :exchange, :timeframe, :issues, :passed,
                            :missing_bars, :outliers_detected, :max_gap_minutes)
                    """
                )

                session.execute(
                    query,
                    {
                        "symbol": symbol,
                        "exchange": exchange,
                        "timeframe": timeframe,
                        "issues": issues,
                        "passed": passed,
                        "missing_bars": metrics.get("missing_bars", 0),
                        "outliers_detected": metrics.get("outliers_detected", 0),
                        "max_gap_minutes": metrics.get("max_gap_minutes", 0),
                    },
                )

            logger.info(f"Logged data quality check for {symbol}")

        except Exception as e:
            logger.error(f"Failed to log data quality: {e}")

    def get_data_quality_issues(self, days: int = 7) -> pd.DataFrame:
        """
        Get recent data quality issues.

        Args:
            days: Number of days to look back

        Returns:
            DataFrame with data quality issues
        """
        try:
            query = text(
                """
                SELECT *
                FROM data_quality
                WHERE time >= NOW() - INTERVAL ':days days'
                    AND passed_all_checks = FALSE
                ORDER BY time DESC
                """
            )

            with self.engine.connect() as conn:
                df = pd.read_sql(query, conn, params={"days": days})

            logger.debug(f"Fetched {len(df)} data quality issues")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch data quality issues: {e}")
            raise

    # ==============================================
    # Utility Methods
    # ==============================================

    def execute_query(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """
        Execute raw SQL query and return DataFrame.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            DataFrame with query results
        """
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params=params or {})
            return df
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise

    def close(self) -> None:
        """Close all database connections."""
        self.engine.dispose()
        logger.info("Database connections closed")
