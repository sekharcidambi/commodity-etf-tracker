-- ============================================================================
-- MACRO INDICATORS TABLE (Phase 1 Enhancement)
-- ============================================================================
-- This migration adds tables for storing FRED macro data and related analytics

-- Macro indicators (FRED data and other macro series)
CREATE TABLE IF NOT EXISTS macro_indicators (
    date DATE NOT NULL,
    series_id VARCHAR(20) NOT NULL,
    value DECIMAL(15,4),
    source VARCHAR(50) DEFAULT 'FRED',
    name VARCHAR(100),
    frequency VARCHAR(20),  -- daily, weekly, monthly
    unit VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date, series_id)
);

-- Create index for time-series queries
CREATE INDEX IF NOT EXISTS idx_macro_indicators_series_date
    ON macro_indicators (series_id, date DESC);

CREATE INDEX IF NOT EXISTS idx_macro_indicators_date
    ON macro_indicators (date DESC);

-- ============================================================================
-- KOREAN RETAIL FLOWS TABLE (Phase 1 Enhancement)
-- ============================================================================
-- For storing actual Korean retail flow data from KSD/SEIBRO

CREATE TABLE IF NOT EXISTS korean_retail_flows (
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    net_purchase_krw DECIMAL(18,2),  -- Korean Won
    net_purchase_usd DECIMAL(15,2),  -- US Dollars
    shares_bought BIGINT,
    shares_sold BIGINT,
    net_shares BIGINT,
    exchange_rate DECIMAL(10,4),  -- KRW/USD
    data_source VARCHAR(50) DEFAULT 'KSD',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_korean_retail_flows_ticker_date
    ON korean_retail_flows (ticker, date DESC);

-- ============================================================================
-- ASIAN HOURS VOLUME CACHE TABLE (Phase 1 Enhancement)
-- ============================================================================
-- Cache for pre-calculated Asian hours volume analysis

CREATE TABLE IF NOT EXISTS asian_hours_volume_cache (
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    asian_hours_volume BIGINT,
    regular_hours_volume BIGINT,
    asian_volume_ratio DECIMAL(8,6),
    pre_market_volume BIGINT,
    after_hours_volume BIGINT,
    korean_retail_proxy_score DECIMAL(5,2),  -- 0-100
    trend VARCHAR(20),  -- increasing, decreasing, stable
    confidence VARCHAR(20),  -- high, medium, low
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_asian_hours_cache_ticker_date
    ON asian_hours_volume_cache (ticker, date DESC);

-- ============================================================================
-- PREMIUM DISCOUNT HISTORY TABLE (Phase 1 Enhancement)
-- ============================================================================
-- Cache for ETF premium/discount calculations

CREATE TABLE IF NOT EXISTS premium_discount_history (
    timestamp TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    etf_price DECIMAL(12,4),
    estimated_nav DECIMAL(12,4),
    premium_discount_pct DECIMAL(8,4),
    commodity_price DECIMAL(12,4),
    commodity_symbol VARCHAR(10),
    z_score DECIMAL(8,4),
    percentile DECIMAL(5,2),
    is_extreme BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (timestamp, ticker)
);

-- Convert to hypertable for efficient time-series queries
SELECT create_hypertable('premium_discount_history', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_premium_discount_ticker_time
    ON premium_discount_history (ticker, timestamp DESC);

-- ============================================================================
-- FUTURES BASIS TABLE (Phase 1 Enhancement)
-- ============================================================================
-- Track futures-spot basis for contango/backwardation analysis

CREATE TABLE IF NOT EXISTS futures_basis (
    timestamp TIMESTAMPTZ NOT NULL,
    commodity VARCHAR(20) NOT NULL,  -- gold, silver, platinum
    spot_price DECIMAL(12,4),
    futures_price DECIMAL(12,4),
    futures_symbol VARCHAR(10),
    basis_pct DECIMAL(8,4),  -- (futures - spot) / spot * 100
    market_structure VARCHAR(20),  -- contango, backwardation, flat
    days_to_expiry INT,
    annualized_basis_pct DECIMAL(8,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (timestamp, commodity)
);

-- Convert to hypertable
SELECT create_hypertable('futures_basis', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_futures_basis_commodity_time
    ON futures_basis (commodity, timestamp DESC);

-- ============================================================================
-- MARKET REGIME TABLE (Phase 1 Enhancement)
-- ============================================================================
-- Store detected market regime for context-aware signals

CREATE TABLE IF NOT EXISTS market_regime (
    date DATE NOT NULL,
    regime VARCHAR(30) NOT NULL,  -- RISK_ON, RISK_OFF, INFLATION_FEAR, DEFLATION_FEAR, STAGFLATION
    confidence DECIMAL(3,2),  -- 0.0-1.0
    real_rate DECIMAL(6,4),
    vix DECIMAL(8,4),
    dollar_index DECIMAL(10,4),
    breakeven_10y DECIMAL(6,4),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date)
);

CREATE INDEX IF NOT EXISTS idx_market_regime_date
    ON market_regime (date DESC);

-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

-- Latest macro indicators view
CREATE OR REPLACE VIEW latest_macro_indicators AS
SELECT DISTINCT ON (series_id)
    series_id,
    date,
    value,
    name,
    frequency,
    unit,
    source
FROM macro_indicators
ORDER BY series_id, date DESC;

-- Real rates view (calculated from DGS10 and T10YIE)
CREATE OR REPLACE VIEW real_rates AS
SELECT
    dgs.date,
    dgs.value as nominal_rate,
    t10.value as breakeven_inflation,
    dgs.value - t10.value as real_rate
FROM macro_indicators dgs
JOIN macro_indicators t10 ON dgs.date = t10.date
WHERE dgs.series_id = 'DGS10'
  AND t10.series_id = 'T10YIE'
ORDER BY dgs.date DESC;

-- Latest futures basis view
CREATE OR REPLACE VIEW latest_futures_basis AS
SELECT DISTINCT ON (commodity)
    commodity,
    timestamp,
    spot_price,
    futures_price,
    futures_symbol,
    basis_pct,
    market_structure,
    annualized_basis_pct
FROM futures_basis
ORDER BY commodity, timestamp DESC;

-- Korean retail activity summary view
CREATE OR REPLACE VIEW korean_retail_summary AS
SELECT
    ticker,
    date,
    korean_retail_proxy_score,
    asian_volume_ratio,
    trend,
    confidence
FROM asian_hours_volume_cache
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY ticker, date DESC;
