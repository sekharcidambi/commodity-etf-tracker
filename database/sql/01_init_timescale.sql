-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================================
-- TIME-SERIES TABLES (Using TimescaleDB Hypertables)
-- ============================================================================

-- Commodity prices (spot, futures, ETF)
CREATE TABLE IF NOT EXISTS commodity_prices (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,  -- XAU, XAG, XPT
    instrument_type VARCHAR(20) NOT NULL,  -- SPOT, FUTURES, ETF
    contract_month DATE,          -- for futures (NULL for spot/ETF)
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    open_interest BIGINT,         -- for futures (NULL for spot/ETF)
    PRIMARY KEY (timestamp, symbol, instrument_type, COALESCE(contract_month, '1970-01-01'))
);

-- Convert to hypertable
SELECT create_hypertable('commodity_prices', 'timestamp', if_not_exists => TRUE);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_commodity_prices_symbol_time
    ON commodity_prices (symbol, instrument_type, timestamp DESC);

-- ETF prices (AGQ, UGL, etc.)
CREATE TABLE IF NOT EXISTS etf_prices (
    timestamp TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    adj_close DECIMAL(12,4),
    vwap DECIMAL(12,4),           -- Volume Weighted Average Price
    PRIMARY KEY (timestamp, ticker)
);

-- Convert to hypertable
SELECT create_hypertable('etf_prices', 'timestamp', if_not_exists => TRUE);

-- Create index
CREATE INDEX IF NOT EXISTS idx_etf_prices_ticker_time
    ON etf_prices (ticker, timestamp DESC);

-- ETF flows (weekly data)
CREATE TABLE IF NOT EXISTS etf_flows (
    week_ending DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    net_flow DECIMAL(16,2),        -- in USD millions
    aum DECIMAL(16,2),             -- Assets Under Management in USD millions
    shares_outstanding BIGINT,
    premium_discount DECIMAL(6,4), -- percentage (0.0050 = 0.50%)
    source VARCHAR(50),            -- ETFdb, ETF.com, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (week_ending, ticker)
);

-- Convert to hypertable
SELECT create_hypertable('etf_flows', 'week_ending', if_not_exists => TRUE);

-- Create index
CREATE INDEX IF NOT EXISTS idx_etf_flows_ticker_week
    ON etf_flows (ticker, week_ending DESC);

-- Investor segment flows
CREATE TABLE IF NOT EXISTS investor_segment_flows (
    week_ending DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    segment VARCHAR(50) NOT NULL,  -- KOREAN_RETAIL, US_RETAIL, INSTITUTIONAL, SOVEREIGN, UNKNOWN
    estimated_flow DECIMAL(16,2),  -- in USD millions
    confidence_score DECIMAL(3,2), -- 0.0-1.0 (data quality indicator)
    data_source VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (week_ending, ticker, segment)
);

-- Convert to hypertable
SELECT create_hypertable('investor_segment_flows', 'week_ending', if_not_exists => TRUE);

-- Create index
CREATE INDEX IF NOT EXISTS idx_investor_segment_flows
    ON investor_segment_flows (ticker, segment, week_ending DESC);

-- Intraday bars (1-minute, 5-minute data)
CREATE TABLE IF NOT EXISTS intraday_bars (
    timestamp TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    interval VARCHAR(5) NOT NULL,  -- 1m, 5m, 15m, 1h
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    vwap DECIMAL(12,4),
    PRIMARY KEY (timestamp, ticker, interval)
);

-- Convert to hypertable
SELECT create_hypertable('intraday_bars', 'timestamp', if_not_exists => TRUE);

-- Create index
CREATE INDEX IF NOT EXISTS idx_intraday_bars
    ON intraday_bars (ticker, interval, timestamp DESC);

-- ============================================================================
-- RELATIONAL TABLES
-- ============================================================================

-- Tickers metadata
CREATE TABLE IF NOT EXISTS tickers (
    ticker VARCHAR(10) PRIMARY KEY,
    name VARCHAR(200),
    asset_class VARCHAR(50),      -- SILVER_LEVERAGED, GOLD_ETF, etc.
    leverage_factor DECIMAL(4,2), -- 2.0 for 2x, -2.0 for inverse 2x
    expense_ratio DECIMAL(5,4),   -- 0.0095 = 0.95%
    inception_date DATE,
    is_active BOOLEAN DEFAULT true,
    last_volume_check DATE,
    avg_daily_volume BIGINT,
    delisted_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Signals
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    ticker VARCHAR(10) REFERENCES tickers(ticker),
    signal_type VARCHAR(50) NOT NULL,      -- EXTREME_FLOW, DIVERGENCE, MOMENTUM, etc.
    direction VARCHAR(10) NOT NULL,        -- BUY, SELL, WATCH
    strength DECIMAL(3,2),        -- 0.0 to 1.0
    trigger_values JSONB,         -- store z-scores, correlations, etc.
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, EXPIRED, CLOSED
    expires_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_ticker_time
    ON signals (ticker, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_status
    ON signals (status, generated_at DESC);

-- Alert log
CREATE TABLE IF NOT EXISTS alert_log (
    id SERIAL PRIMARY KEY,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    alert_type VARCHAR(50) NOT NULL,
    ticker VARCHAR(10),
    channel VARCHAR(20) NOT NULL,          -- EMAIL, SLACK, IN_APP, etc.
    recipient VARCHAR(200),
    message TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- SENT, FAILED, PENDING
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_log_time
    ON alert_log (sent_at DESC);

-- Institutional holdings (from 13F filings)
CREATE TABLE IF NOT EXISTS institutional_holdings (
    filing_date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    institution_name VARCHAR(200) NOT NULL,
    shares BIGINT,
    value_usd DECIMAL(16,2),      -- in USD
    percent_of_portfolio DECIMAL(6,4),
    change_shares BIGINT,         -- change from previous quarter
    change_percent DECIMAL(7,4),
    PRIMARY KEY (filing_date, ticker, institution_name)
);

CREATE INDEX IF NOT EXISTS idx_institutional_holdings
    ON institutional_holdings (ticker, filing_date DESC);

-- Data collection jobs status
CREATE TABLE IF NOT EXISTS data_jobs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    job_type VARCHAR(50) NOT NULL,  -- PRICE_COLLECTION, FLOW_SCRAPE, etc.
    status VARCHAR(20) NOT NULL,     -- RUNNING, SUCCESS, FAILED
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    records_processed INT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_data_jobs_time
    ON data_jobs (created_at DESC);

-- ============================================================================
-- VIEWS
-- ============================================================================

-- Latest active signals per ticker
CREATE OR REPLACE VIEW latest_signals AS
SELECT DISTINCT ON (ticker)
    ticker,
    signal_type,
    direction,
    strength,
    generated_at,
    trigger_values,
    expires_at
FROM signals
WHERE status = 'ACTIVE' AND expires_at > NOW()
ORDER BY ticker, generated_at DESC;

-- Flow statistics (rolling sums and z-scores)
CREATE OR REPLACE VIEW flow_statistics AS
SELECT
    ticker,
    week_ending,
    net_flow,
    AVG(net_flow) OVER (
        PARTITION BY ticker
        ORDER BY week_ending
        ROWS BETWEEN 51 PRECEDING AND CURRENT ROW
    ) as flow_52w_avg,
    STDDEV(net_flow) OVER (
        PARTITION BY ticker
        ORDER BY week_ending
        ROWS BETWEEN 51 PRECEDING AND CURRENT ROW
    ) as flow_52w_stddev,
    SUM(net_flow) OVER (
        PARTITION BY ticker
        ORDER BY week_ending
        ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
    ) as flow_4w_sum,
    SUM(net_flow) OVER (
        PARTITION BY ticker
        ORDER BY week_ending
        ROWS BETWEEN 12 PRECEDING AND CURRENT ROW
    ) as flow_13w_sum,
    SUM(net_flow) OVER (
        PARTITION BY ticker
        ORDER BY week_ending
        ROWS BETWEEN 25 PRECEDING AND CURRENT ROW
    ) as flow_26w_sum,
    SUM(net_flow) OVER (
        PARTITION BY ticker
        ORDER BY week_ending
        ROWS BETWEEN 51 PRECEDING AND CURRENT ROW
    ) as flow_52w_sum
FROM etf_flows
ORDER BY ticker, week_ending DESC;

-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Insert primary tickers
INSERT INTO tickers (ticker, name, asset_class, leverage_factor, expense_ratio, inception_date, is_active)
VALUES
    ('AGQ', 'ProShares Ultra Silver', 'SILVER_LEVERAGED', 2.0, 0.0095, '2008-12-01', true),
    ('UGL', 'ProShares Ultra Gold', 'GOLD_LEVERAGED', 2.0, 0.0095, '2008-12-01', true),
    ('ZSL', 'ProShares UltraShort Silver', 'SILVER_INVERSE', -2.0, 0.0095, '2008-12-01', true),
    ('GLD', 'SPDR Gold Shares', 'GOLD_ETF', 1.0, 0.0040, '2004-11-18', true),
    ('SLV', 'iShares Silver Trust', 'SILVER_ETF', 1.0, 0.0050, '2006-04-28', true),
    ('PPLT', 'abrdn Physical Platinum Shares ETF', 'PLATINUM_ETF', 1.0, 0.0060, '2010-01-08', true)
ON CONFLICT (ticker) DO NOTHING;

-- Grant permissions (if using specific user)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO commodity_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO commodity_user;
