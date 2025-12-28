-- ============================================================================
-- PHASE 2: CORE DATA ENHANCEMENT TABLES
-- ============================================================================
-- This migration adds tables for COT, Google Trends, COMEX, and Reddit data

-- ============================================================================
-- CFTC COMMITMENT OF TRADERS (COT) DATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS cot_positioning (
    report_date DATE NOT NULL,
    commodity VARCHAR(20) NOT NULL,  -- gold, silver, platinum
    commodity_code VARCHAR(10),  -- CFTC code (088691, 084691, 076651)

    -- Open Interest
    open_interest BIGINT,

    -- Commercial (Producers + Swap Dealers)
    commercial_long BIGINT,
    commercial_short BIGINT,
    commercial_net BIGINT,

    -- Managed Money (Large Speculators - KEY INDICATOR)
    managed_money_long BIGINT,
    managed_money_short BIGINT,
    managed_money_net BIGINT,
    managed_money_net_pct DECIMAL(6,2),  -- % of open interest

    -- Other Reportables
    other_reportable_long BIGINT,
    other_reportable_short BIGINT,
    other_reportable_net BIGINT,

    -- Non-Reportable (Small Speculators/Retail)
    nonreportable_long BIGINT,
    nonreportable_short BIGINT,
    nonreportable_net BIGINT,

    -- Analytics
    managed_money_percentile DECIMAL(5,2),  -- 52-week percentile
    managed_money_z_score DECIMAL(6,3),
    is_extreme_bullish BOOLEAN DEFAULT FALSE,
    is_extreme_bearish BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (report_date, commodity)
);

CREATE INDEX IF NOT EXISTS idx_cot_positioning_commodity_date
    ON cot_positioning (commodity, report_date DESC);

CREATE INDEX IF NOT EXISTS idx_cot_positioning_extreme
    ON cot_positioning (commodity, is_extreme_bullish, is_extreme_bearish);

-- ============================================================================
-- GOOGLE TRENDS INTEREST DATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS google_trends_interest (
    timestamp TIMESTAMPTZ NOT NULL,
    commodity VARCHAR(20) NOT NULL,  -- gold, silver, precious_metals
    keyword VARCHAR(100) NOT NULL,

    -- Interest metrics (0-100 scale)
    interest_value INT,

    -- Aggregated metrics
    avg_interest DECIMAL(5,2),
    max_interest INT,
    min_interest INT,
    std_dev DECIMAL(5,2),

    -- Spike detection
    z_score DECIMAL(6,3),
    is_spike BOOLEAN DEFAULT FALSE,

    timeframe VARCHAR(20),  -- 'now 7-d', 'today 1-m', etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (timestamp, commodity, keyword)
);

-- Convert to hypertable for time-series queries
SELECT create_hypertable('google_trends_interest', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_google_trends_commodity_time
    ON google_trends_interest (commodity, timestamp DESC);

-- Aggregated daily interest scores
CREATE TABLE IF NOT EXISTS google_trends_daily (
    date DATE NOT NULL,
    commodity VARCHAR(20) NOT NULL,

    -- Aggregated interest score (0-100)
    interest_score DECIMAL(5,2),
    normalized_score DECIMAL(5,2),  -- vs historical average

    -- Statistics
    avg_interest DECIMAL(5,2),
    max_interest INT,
    trend VARCHAR(20),  -- increasing, decreasing, stable

    -- Spike detection
    is_spike BOOLEAN DEFAULT FALSE,
    z_score DECIMAL(6,3),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date, commodity)
);

CREATE INDEX IF NOT EXISTS idx_google_trends_daily_commodity
    ON google_trends_daily (commodity, date DESC);

-- ============================================================================
-- COMEX WAREHOUSE INVENTORY
-- ============================================================================

CREATE TABLE IF NOT EXISTS comex_inventory (
    date DATE NOT NULL,
    commodity VARCHAR(20) NOT NULL,  -- gold, silver, platinum

    -- Inventory levels (in ounces)
    registered_oz DECIMAL(18,2),  -- Available for delivery
    eligible_oz DECIMAL(18,2),    -- Meets specs but not registered
    total_oz DECIMAL(18,2),

    -- Changes
    registered_change_oz DECIMAL(18,2),
    eligible_change_oz DECIMAL(18,2),
    total_change_oz DECIMAL(18,2),

    -- Coverage metrics
    open_interest_contracts BIGINT,
    registered_to_oi_ratio_pct DECIMAL(8,4),  -- Key squeeze indicator
    oi_coverage_days DECIMAL(8,2),

    -- Squeeze detection
    consecutive_decline_days INT DEFAULT 0,
    is_squeeze_warning BOOLEAN DEFAULT FALSE,
    squeeze_severity VARCHAR(20),  -- none, moderate, severe, extreme

    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date, commodity)
);

CREATE INDEX IF NOT EXISTS idx_comex_inventory_commodity_date
    ON comex_inventory (commodity, date DESC);

CREATE INDEX IF NOT EXISTS idx_comex_inventory_squeeze
    ON comex_inventory (commodity, is_squeeze_warning);

-- ============================================================================
-- REDDIT SENTIMENT DATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS reddit_sentiment (
    timestamp TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(10),
    commodity VARCHAR(20),
    subreddit VARCHAR(50) NOT NULL,

    -- Mention metrics
    mentions INT DEFAULT 0,
    velocity DECIMAL(8,4),  -- mentions per hour

    -- Sentiment metrics (-1 to +1)
    sentiment_score DECIMAL(4,3),
    bullish_count INT DEFAULT 0,
    bearish_count INT DEFAULT 0,
    neutral_count INT DEFAULT 0,
    bullish_ratio DECIMAL(4,3),

    -- Engagement
    total_upvotes INT DEFAULT 0,
    total_comments INT DEFAULT 0,
    avg_upvotes DECIMAL(10,2),

    -- Unusual activity detection
    is_unusual_activity BOOLEAN DEFAULT FALSE,
    activity_z_score DECIMAL(6,3),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (timestamp, subreddit, COALESCE(ticker, commodity))
);

-- Convert to hypertable
SELECT create_hypertable('reddit_sentiment', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_reddit_sentiment_ticker_time
    ON reddit_sentiment (ticker, timestamp DESC) WHERE ticker IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_reddit_sentiment_commodity_time
    ON reddit_sentiment (commodity, timestamp DESC) WHERE commodity IS NOT NULL;

-- Daily aggregated Reddit sentiment
CREATE TABLE IF NOT EXISTS reddit_sentiment_daily (
    date DATE NOT NULL,
    ticker VARCHAR(10),
    commodity VARCHAR(20),

    -- Aggregated metrics
    total_mentions INT DEFAULT 0,
    avg_sentiment DECIMAL(4,3),
    bullish_ratio DECIMAL(4,3),

    -- Velocity
    mentions_per_hour DECIMAL(8,4),
    peak_velocity DECIMAL(8,4),

    -- Top posts (JSON array)
    top_posts JSONB,

    -- Unusual activity
    is_unusual_activity BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date, COALESCE(ticker, commodity))
);

CREATE INDEX IF NOT EXISTS idx_reddit_daily_ticker
    ON reddit_sentiment_daily (ticker, date DESC) WHERE ticker IS NOT NULL;

-- ============================================================================
-- COMPOSITE SENTIMENT INDICATOR
-- ============================================================================

CREATE TABLE IF NOT EXISTS composite_sentiment (
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,

    -- Individual components (0-100 scale)
    google_trends_score DECIMAL(5,2),
    reddit_sentiment_score DECIMAL(5,2),
    cot_contrarian_score DECIMAL(5,2),
    flow_z_score DECIMAL(6,3),

    -- Composite score (0-100)
    composite_score DECIMAL(5,2),

    -- Interpretation
    sentiment_level VARCHAR(20),  -- very_bearish, bearish, neutral, bullish, very_bullish
    signal_direction VARCHAR(10),  -- BUY, SELL, HOLD
    confidence DECIMAL(3,2),  -- 0-1

    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_composite_sentiment_ticker
    ON composite_sentiment (ticker, date DESC);

-- ============================================================================
-- VIEWS FOR ANALYTICS
-- ============================================================================

-- Latest COT positioning view
CREATE OR REPLACE VIEW latest_cot_positioning AS
SELECT DISTINCT ON (commodity)
    commodity,
    report_date,
    open_interest,
    managed_money_net,
    managed_money_net_pct,
    managed_money_percentile,
    managed_money_z_score,
    is_extreme_bullish,
    is_extreme_bearish,
    CASE
        WHEN is_extreme_bullish THEN 'CONTRARIAN_SELL'
        WHEN is_extreme_bearish THEN 'CONTRARIAN_BUY'
        ELSE 'NEUTRAL'
    END as contrarian_signal
FROM cot_positioning
ORDER BY commodity, report_date DESC;

-- Latest COMEX inventory view
CREATE OR REPLACE VIEW latest_comex_inventory AS
SELECT DISTINCT ON (commodity)
    commodity,
    date,
    registered_oz,
    eligible_oz,
    total_oz,
    registered_to_oi_ratio_pct,
    oi_coverage_days,
    consecutive_decline_days,
    is_squeeze_warning,
    squeeze_severity
FROM comex_inventory
ORDER BY commodity, date DESC;

-- Sentiment dashboard view
CREATE OR REPLACE VIEW sentiment_dashboard AS
SELECT
    cs.date,
    cs.ticker,
    cs.composite_score,
    cs.sentiment_level,
    cs.signal_direction,
    cs.confidence,
    cs.google_trends_score,
    cs.reddit_sentiment_score,
    cs.cot_contrarian_score,
    cot.managed_money_net_pct as cot_spec_position_pct,
    cot.is_extreme_bullish as cot_extreme_bullish,
    cot.is_extreme_bearish as cot_extreme_bearish
FROM composite_sentiment cs
LEFT JOIN latest_cot_positioning cot ON
    (cs.ticker = 'AGQ' AND cot.commodity = 'silver') OR
    (cs.ticker = 'UGL' AND cot.commodity = 'gold') OR
    (cs.ticker = 'ZSL' AND cot.commodity = 'silver')
WHERE cs.date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY cs.date DESC, cs.ticker;
