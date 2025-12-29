-- ============================================================================
-- PHASE 3: ADVANCED FEATURES TABLES
-- ============================================================================
-- Tables for scheduler, composite scoring, and backtesting

-- ============================================================================
-- DATA JOBS TABLE (Scheduler Job Tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_jobs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    job_type VARCHAR(50) NOT NULL,  -- PRICE_COLLECTION, FLOW_SCRAPE, COT_COLLECTION, etc.

    -- Execution status
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING, RUNNING, SUCCESS, FAILED, CANCELLED

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds DECIMAL(10,3),

    -- Metrics
    records_processed INT DEFAULT 0,
    records_saved INT DEFAULT 0,
    error_count INT DEFAULT 0,

    -- Error details
    error_message TEXT,
    error_traceback TEXT,

    -- Retry logic
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    parent_job_id INT REFERENCES data_jobs(id),

    -- Additional metadata
    parameters JSONB,
    result_summary JSONB
);

CREATE INDEX IF NOT EXISTS idx_data_jobs_name_status
    ON data_jobs (job_name, status);

CREATE INDEX IF NOT EXISTS idx_data_jobs_created
    ON data_jobs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_data_jobs_type_status
    ON data_jobs (job_type, status, created_at DESC);

-- ============================================================================
-- COMPOSITE SCORES TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS composite_scores (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ticker VARCHAR(10) NOT NULL,

    -- Overall score (-100 to +100)
    composite_score DECIMAL(6,2) NOT NULL,
    recommendation VARCHAR(20) NOT NULL,  -- STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL

    -- Individual factor scores (-1 to +1)
    flow_momentum_score DECIMAL(5,3),
    korean_retail_score DECIMAL(5,3),
    institutional_score DECIMAL(5,3),
    futures_basis_score DECIMAL(5,3),
    cot_positioning_score DECIMAL(5,3),
    premium_discount_score DECIMAL(5,3),
    google_trends_score DECIMAL(5,3),
    reddit_sentiment_score DECIMAL(5,3),

    -- Data availability
    factors_available INT DEFAULT 0,
    factors_total INT DEFAULT 8,
    confidence_level VARCHAR(20),  -- HIGH, MEDIUM, LOW

    -- Weights used (may differ if factors missing)
    weights_used JSONB,

    -- Raw values for debugging
    raw_values JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable for time-series queries
SELECT create_hypertable('composite_scores', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_composite_scores_ticker_time
    ON composite_scores (ticker, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_composite_scores_recommendation
    ON composite_scores (recommendation, timestamp DESC);

-- ============================================================================
-- SIGNAL PERFORMANCE TABLE (Backtesting)
-- ============================================================================

CREATE TABLE IF NOT EXISTS signal_performance (
    id SERIAL PRIMARY KEY,
    signal_id INT NOT NULL,  -- References signals table
    ticker VARCHAR(10) NOT NULL,
    signal_type VARCHAR(50) NOT NULL,
    direction VARCHAR(10) NOT NULL,  -- BUY, SELL, WATCH

    -- Signal timing
    signal_generated_at TIMESTAMPTZ NOT NULL,
    signal_strength DECIMAL(4,2),

    -- Entry point
    entry_price DECIMAL(12,4),
    entry_timestamp TIMESTAMPTZ,

    -- Exit point
    exit_price DECIMAL(12,4),
    exit_timestamp TIMESTAMPTZ,
    exit_reason VARCHAR(50),  -- TARGET_HIT, STOP_LOSS, EXPIRED, MANUAL

    -- Performance metrics
    return_pct DECIMAL(8,4),  -- (exit - entry) / entry * 100
    holding_period_hours DECIMAL(10,2),

    -- Maximum adverse/favorable excursion
    max_drawdown_pct DECIMAL(8,4),
    max_profit_pct DECIMAL(8,4),

    -- Win/Loss classification
    is_winner BOOLEAN,

    -- Context at signal time
    market_regime VARCHAR(30),
    composite_score_at_signal DECIMAL(6,2),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_performance_ticker
    ON signal_performance (ticker, signal_generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_signal_performance_type
    ON signal_performance (signal_type, is_winner);

-- ============================================================================
-- BACKTEST RUNS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS backtest_runs (
    id SERIAL PRIMARY KEY,
    run_name VARCHAR(100),

    -- Backtest parameters
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    tickers JSONB NOT NULL,  -- Array of tickers tested
    signal_types JSONB,  -- Array of signal types to test (null = all)

    -- Configuration
    initial_capital DECIMAL(15,2) DEFAULT 100000,
    position_size_pct DECIMAL(5,2) DEFAULT 10,  -- % of capital per trade
    stop_loss_pct DECIMAL(5,2),
    take_profit_pct DECIMAL(5,2),
    max_holding_days INT DEFAULT 14,

    -- Results summary
    total_trades INT DEFAULT 0,
    winning_trades INT DEFAULT 0,
    losing_trades INT DEFAULT 0,
    win_rate DECIMAL(5,2),

    -- Returns
    total_return_pct DECIMAL(10,4),
    annualized_return_pct DECIMAL(10,4),
    max_drawdown_pct DECIMAL(10,4),
    sharpe_ratio DECIMAL(6,3),

    -- Per signal type performance
    signal_type_results JSONB,

    -- Status
    status VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, RUNNING, COMPLETED, FAILED
    error_message TEXT,

    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_status
    ON backtest_runs (status, created_at DESC);

-- ============================================================================
-- USER ALERT SUBSCRIPTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS alert_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,  -- Can be email or user ID

    -- Subscription settings
    alert_types JSONB NOT NULL,  -- Array of AlertType values
    channels JSONB NOT NULL,  -- Array of AlertChannel values
    tickers JSONB,  -- Specific tickers (null = all)

    -- Thresholds
    min_signal_strength DECIMAL(4,2) DEFAULT 0.5,

    -- Contact info
    email VARCHAR(255),
    slack_channel VARCHAR(100),
    webhook_url TEXT,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_subscriptions_user
    ON alert_subscriptions (user_id, is_active);

CREATE INDEX IF NOT EXISTS idx_alert_subscriptions_active
    ON alert_subscriptions (is_active) WHERE is_active = TRUE;

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Latest composite scores view
CREATE OR REPLACE VIEW latest_composite_scores AS
SELECT DISTINCT ON (ticker)
    ticker,
    timestamp,
    composite_score,
    recommendation,
    confidence_level,
    factors_available,
    factors_total
FROM composite_scores
ORDER BY ticker, timestamp DESC;

-- Signal performance summary by type
CREATE OR REPLACE VIEW signal_performance_summary AS
SELECT
    signal_type,
    ticker,
    COUNT(*) as total_signals,
    SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as winners,
    SUM(CASE WHEN NOT is_winner THEN 1 ELSE 0 END) as losers,
    ROUND(AVG(CASE WHEN is_winner THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate_pct,
    ROUND(AVG(return_pct), 4) as avg_return_pct,
    ROUND(AVG(holding_period_hours), 2) as avg_hold_hours,
    ROUND(MAX(max_profit_pct), 4) as best_trade_pct,
    ROUND(MIN(return_pct), 4) as worst_trade_pct
FROM signal_performance
WHERE exit_timestamp IS NOT NULL
GROUP BY signal_type, ticker
ORDER BY win_rate_pct DESC;

-- Recent job execution summary
CREATE OR REPLACE VIEW recent_job_summary AS
SELECT
    job_name,
    job_type,
    COUNT(*) as total_runs,
    SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successes,
    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failures,
    ROUND(AVG(duration_seconds), 2) as avg_duration_sec,
    MAX(completed_at) as last_run,
    MAX(CASE WHEN status = 'SUCCESS' THEN completed_at END) as last_success
FROM data_jobs
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY job_name, job_type
ORDER BY last_run DESC NULLS LAST;
