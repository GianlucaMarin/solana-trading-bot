-- ==============================================
-- Solana RL Trading Bot - Database Schema
-- TimescaleDB Initialization Script
-- ==============================================

\echo 'Starting database initialization...'

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

\echo 'TimescaleDB extension enabled'

-- ==============================================
-- Table: OHLCV Data (Market Data)
-- ==============================================
CREATE TABLE IF NOT EXISTS ohlcv (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(20) NOT NULL DEFAULT 'binance',
    timeframe VARCHAR(10) NOT NULL,
    open NUMERIC(20, 8) NOT NULL,
    high NUMERIC(20, 8) NOT NULL,
    low NUMERIC(20, 8) NOT NULL,
    close NUMERIC(20, 8) NOT NULL,
    volume NUMERIC(20, 8) NOT NULL,
    quote_volume NUMERIC(20, 8),
    trades INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (timestamp, symbol, exchange, timeframe)
);

\echo 'Creating ohlcv hypertable...'

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('ohlcv', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_time
    ON ohlcv (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ohlcv_timeframe
    ON ohlcv (timeframe, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_exchange_timeframe
    ON ohlcv (symbol, exchange, timeframe, timestamp DESC);

\echo 'OHLCV table created'

-- ==============================================
-- Table: Technical Indicators (Features)
-- ==============================================
CREATE TABLE IF NOT EXISTS features (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(20) NOT NULL DEFAULT 'binance',
    timeframe VARCHAR(10) NOT NULL,

    -- Trend Indicators
    sma_20 NUMERIC(20, 8),
    sma_50 NUMERIC(20, 8),
    sma_200 NUMERIC(20, 8),
    ema_12 NUMERIC(20, 8),
    ema_26 NUMERIC(20, 8),
    macd NUMERIC(20, 8),
    macd_signal NUMERIC(20, 8),
    macd_hist NUMERIC(20, 8),
    adx NUMERIC(10, 4),

    -- Momentum Indicators
    rsi_14 NUMERIC(10, 4),
    stoch_k NUMERIC(10, 4),
    stoch_d NUMERIC(10, 4),
    cci NUMERIC(10, 4),

    -- Volatility Indicators
    bbands_upper NUMERIC(20, 8),
    bbands_middle NUMERIC(20, 8),
    bbands_lower NUMERIC(20, 8),
    bbands_bandwidth NUMERIC(10, 4),
    atr NUMERIC(20, 8),

    -- Volume Indicators
    obv NUMERIC(20, 8),
    vwap NUMERIC(20, 8),
    volume_sma NUMERIC(20, 8),

    -- Custom Features
    returns NUMERIC(10, 6),
    log_returns NUMERIC(10, 6),
    volatility NUMERIC(10, 6),

    -- Market Regime
    regime VARCHAR(20),  -- bull, bear, sideways
    volatility_regime VARCHAR(20),  -- low, medium, high

    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (timestamp, symbol, exchange, timeframe)
);

\echo 'Creating features hypertable...'

-- Convert to hypertable
SELECT create_hypertable('features', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_features_symbol_time
    ON features (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_features_symbol_exchange_timeframe
    ON features (symbol, exchange, timeframe, timestamp DESC);

\echo 'Features table created'

-- ==============================================
-- Table: Trades (Executed Trades)
-- ==============================================
CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    trade_id VARCHAR(100) UNIQUE NOT NULL,
    strategy_name VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(20) NOT NULL DEFAULT 'binance',

    -- Trade Details
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    side VARCHAR(10) NOT NULL,  -- buy, sell
    type VARCHAR(20) NOT NULL DEFAULT 'market',  -- market, limit
    entry_price NUMERIC(20, 8) NOT NULL,
    exit_price NUMERIC(20, 8),
    quantity NUMERIC(20, 8) NOT NULL,

    -- Costs & Fees
    entry_cost NUMERIC(20, 8) NOT NULL,
    exit_cost NUMERIC(20, 8),
    fee NUMERIC(20, 8),
    fee_currency VARCHAR(10) DEFAULT 'USDT',

    -- P&L
    pnl NUMERIC(20, 8),
    pnl_percent NUMERIC(10, 4),

    -- Risk Management
    stop_loss NUMERIC(20, 8),
    take_profit NUMERIC(20, 8),
    max_drawdown NUMERIC(10, 4),

    -- Trade Context
    session_id VARCHAR(100),  -- backtest/paper/live session ID
    mode VARCHAR(20) NOT NULL,  -- backtest, paper, live

    -- Status
    status VARCHAR(20) DEFAULT 'open',  -- open, closed, cancelled
    notes TEXT,

    -- Exchange Info
    order_id VARCHAR(100),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

\echo 'Creating trades indexes...'

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades (entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades (strategy_name, entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades (symbol, entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_session ON trades (session_id, entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades (status, entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_mode ON trades (mode, entry_time DESC);

\echo 'Trades table created'

-- ==============================================
-- Table: Performance Metrics (Time-Series)
-- ==============================================
CREATE TABLE IF NOT EXISTS performance (
    id BIGSERIAL,
    time TIMESTAMPTZ NOT NULL,
    strategy_name VARCHAR(50) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    session_id VARCHAR(100),

    -- Returns
    total_return NUMERIC(10, 4),
    daily_return NUMERIC(10, 4),
    cumulative_return NUMERIC(10, 4),
    annual_return NUMERIC(10, 4),

    -- Risk Metrics
    sharpe_ratio NUMERIC(10, 4),
    sortino_ratio NUMERIC(10, 4),
    max_drawdown NUMERIC(10, 4),
    calmar_ratio NUMERIC(10, 4),
    volatility NUMERIC(10, 4),

    -- Trade Statistics
    num_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate NUMERIC(10, 4),
    profit_factor NUMERIC(10, 4),
    avg_win NUMERIC(20, 8),
    avg_loss NUMERIC(20, 8),

    -- Portfolio Values
    portfolio_value NUMERIC(20, 8),
    cash_balance NUMERIC(20, 8),
    position_value NUMERIC(20, 8),

    -- Trading Metrics
    avg_trade_duration INTERVAL,

    -- Mode
    mode VARCHAR(20) NOT NULL,  -- backtest, paper, live

    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, strategy_name, symbol, timeframe)
);

\echo 'Creating performance hypertable...'

-- Convert to hypertable
SELECT create_hypertable('performance', 'time',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_performance_strategy ON performance (strategy_name, time DESC);
CREATE INDEX IF NOT EXISTS idx_performance_session ON performance (session_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_performance_mode ON performance (mode, time DESC);

\echo 'Performance table created'

-- ==============================================
-- Table: Model Metadata (Saved RL Models)
-- ==============================================
CREATE TABLE IF NOT EXISTS models (
    id BIGSERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    version VARCHAR(50) NOT NULL,
    algorithm VARCHAR(50) NOT NULL,  -- ppo, dqn, sac, a2c, ensemble

    -- Training Info
    training_session_id VARCHAR(100),
    training_start TIMESTAMPTZ NOT NULL,
    training_end TIMESTAMPTZ,
    training_episodes INTEGER,
    training_timesteps BIGINT,

    -- Hyperparameters (JSON)
    hyperparameters JSONB,

    -- Performance Metrics
    final_reward NUMERIC(20, 8),
    best_reward NUMERIC(20, 8),
    validation_sharpe NUMERIC(10, 4),
    validation_return NUMERIC(10, 4),

    -- Artifacts
    model_path TEXT,
    checkpoint_path TEXT,

    -- Status
    status VARCHAR(20) DEFAULT 'training',  -- training, completed, validated, deployed, deprecated
    is_production BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (model_name, version)
);

\echo 'Creating models indexes...'

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_models_algorithm ON models (algorithm, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_models_status ON models (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_models_production ON models (is_production, created_at DESC);

\echo 'Models table created'

-- ==============================================
-- Table: Data Quality Monitoring
-- ==============================================
CREATE TABLE IF NOT EXISTS data_quality (
    id BIGSERIAL,
    time TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,

    -- Quality Metrics
    missing_bars INTEGER DEFAULT 0,
    outliers_detected INTEGER DEFAULT 0,
    max_gap_minutes INTEGER,

    -- Validation Results
    passed_all_checks BOOLEAN DEFAULT TRUE,
    issues TEXT[],

    checked_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (time, symbol, exchange, timeframe)
);

\echo 'Creating data_quality hypertable...'

SELECT create_hypertable('data_quality', 'time',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_data_quality_symbol ON data_quality (symbol, time DESC);
CREATE INDEX IF NOT EXISTS idx_data_quality_passed ON data_quality (passed_all_checks, time DESC);

\echo 'Data quality table created'

-- ==============================================
-- Table: System Logs
-- ==============================================
CREATE TABLE IF NOT EXISTS system_logs (
    id BIGSERIAL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level VARCHAR(10) NOT NULL,  -- DEBUG, INFO, WARNING, ERROR, CRITICAL
    module VARCHAR(100),
    message TEXT,
    context JSONB,
    PRIMARY KEY (timestamp, id)
);

\echo 'Creating system_logs hypertable...'

-- Convert to hypertable
SELECT create_hypertable('system_logs', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs (level, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_system_logs_module ON system_logs (module, timestamp DESC);

\echo 'System logs table created'

-- ==============================================
-- Data Retention Policies
-- ==============================================

\echo 'Setting up retention policies...'

-- Keep raw OHLCV for 2 years
SELECT add_retention_policy('ohlcv', INTERVAL '2 years', if_not_exists => TRUE);

-- Keep features for 2 years
SELECT add_retention_policy('features', INTERVAL '2 years', if_not_exists => TRUE);

-- Keep performance metrics for 3 years
SELECT add_retention_policy('performance', INTERVAL '3 years', if_not_exists => TRUE);

-- Keep data quality checks for 6 months
SELECT add_retention_policy('data_quality', INTERVAL '6 months', if_not_exists => TRUE);

-- Keep system logs for 90 days
SELECT add_retention_policy('system_logs', INTERVAL '90 days', if_not_exists => TRUE);

\echo 'Retention policies configured'

-- ==============================================
-- Continuous Aggregates (Optional - for analytics)
-- ==============================================

-- Daily aggregated performance
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_ohlcv
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS day,
    symbol,
    FIRST(open, timestamp) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, timestamp) AS close,
    SUM(volume) AS volume
FROM ohlcv
WHERE timeframe = '5m'
GROUP BY day, symbol;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('daily_ohlcv',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE);

-- ==============================================
-- Utility Functions
-- ==============================================

\echo 'Creating utility functions...'

-- Function to get latest price
CREATE OR REPLACE FUNCTION get_latest_price(
    p_symbol VARCHAR,
    p_exchange VARCHAR DEFAULT 'binance',
    p_timeframe VARCHAR DEFAULT '5m'
)
RETURNS NUMERIC(20, 8) AS $$
BEGIN
    RETURN (
        SELECT close
        FROM ohlcv
        WHERE symbol = p_symbol
            AND exchange = p_exchange
            AND timeframe = p_timeframe
        ORDER BY timestamp DESC
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql;

-- Function to calculate strategy returns
CREATE OR REPLACE FUNCTION calculate_strategy_return(
    p_strategy VARCHAR,
    p_start_date TIMESTAMPTZ,
    p_end_date TIMESTAMPTZ
)
RETURNS TABLE (
    total_return NUMERIC,
    sharpe_ratio NUMERIC,
    num_trades INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        SUM(pnl_percent) as total_return,
        CASE
            WHEN STDDEV(pnl_percent) > 0
            THEN AVG(pnl_percent) / STDDEV(pnl_percent)
            ELSE NULL
        END as sharpe_ratio,
        COUNT(*)::INTEGER as num_trades
    FROM trades
    WHERE strategy_name = p_strategy
        AND entry_time >= p_start_date
        AND (exit_time <= p_end_date OR exit_time IS NULL)
        AND status IN ('closed', 'open');
END;
$$ LANGUAGE plpgsql;

-- Function to clean old data
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Retention policies handle most cleanup automatically
    -- This can be extended for custom cleanup logic
    RAISE NOTICE 'Cleanup completed';
END;
$$ LANGUAGE plpgsql;

\echo 'Utility functions created'

-- ==============================================
-- Grants (if using non-superuser)
-- ==============================================

-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO trading_bot_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO trading_bot_user;

-- ==============================================
-- Verification
-- ==============================================

\echo ''
\echo '====================================='
\echo 'Database Initialization Summary'
\echo '====================================='

-- Show created tables
\echo 'Tables created:'
SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;

\echo ''
\echo 'Hypertables configured:'
SELECT hypertable_name, num_dimensions FROM timescaledb_information.hypertables;

\echo ''
\echo '====================================='
\echo 'Database initialization completed!'
\echo '====================================='
