# Commodity ETF Tracker: Data Enhancement Strategy

## Executive Summary

This document provides a comprehensive analysis of the current data infrastructure and recommends enhancements to make trading signals **more accurate**, **closer to real-time**, and **more actionable**. It also identifies **unconventional public data sources** that can provide edge in commodity ETF analysis.

---

## 1. Current State Analysis

### 1.1 What's Working Well
| Component | Status | Notes |
|-----------|--------|-------|
| Price Data Collection | ✅ Solid | yfinance + Stooq fallback provides reliable daily OHLCV |
| TimescaleDB Schema | ✅ Well-designed | Hypertables for time-series, proper indexing |
| Signal Framework | ✅ Extensible | 6 of 7 signal types implemented with clear patterns |
| Flow Statistics | ✅ Functional | Z-scores, percentiles, rolling windows working |
| API Structure | ✅ Clean | FastAPI with proper async patterns |

### 1.2 Critical Gaps

| Gap | Impact | Current State |
|-----|--------|---------------|
| **Korean Retail Flow Data** | 🔴 HIGH | Placeholder only - core thesis depends on this |
| **SEC 13F Detail Parsing** | 🔴 HIGH | Only metadata, no actual share counts |
| **Real-time Data** | 🟡 MEDIUM | Daily only, intraday table unused |
| **Macro Correlations** | 🟡 MEDIUM | FRED API configured but not integrated |
| **Options Flow** | 🟡 MEDIUM | Not tracked at all |
| **Futures-Spot Basis** | 🟡 MEDIUM | Signal defined but not implemented |

---

## 2. Signal Accuracy Enhancements

### 2.1 Priority 1: Korean Retail Flow Attribution (CRITICAL)

The **KOREAN_RETAIL_EUPHORIA** signal is central to the trading thesis but currently has no real data source.

#### Recommended Data Sources:

**A. Korea Securities Depository (KSD) Data**
- **What**: Official daily foreign stock holdings by Korean investors
- **Access**: Public reports at [seibro.or.kr](http://seibro.or.kr)
- **Data**: Daily net purchases/sales of foreign stocks by Korean retail
- **Lag**: T+1 (next day)
- **Implementation**: Web scraper for daily reports

```python
# Example structure for KSD scraper
class KSDScraper:
    """
    Scrape Korean retail foreign stock holdings from KSD/SEIBRO

    Reports available:
    - Daily: Net purchase amounts by ticker
    - Weekly: Accumulated holdings
    - Monthly: Top holdings rankings
    """
    BASE_URL = "http://seibro.or.kr"

    async def fetch_daily_foreign_holdings(self, date: date) -> List[Dict]:
        # Parse the foreign stock statistics page
        # Filter for US-listed ETFs (AGQ, UGL, etc.)
        pass
```

**B. ETFGI Flow Reports**
- **What**: Weekly global ETF flow reports with regional breakdown
- **Access**: [etfgi.com](https://etfgi.com) - some data publicly available
- **Data**: Weekly flows by region/investor type
- **Lag**: Weekly (T+7)

**C. Asian Hours Volume Proxy (Immediate Implementation)**
- **What**: Infer Korean retail activity from after-hours volume patterns
- **Logic**: Volume during 8pm-4am ET correlates with Asian retail
- **Accuracy**: ~70-80% correlation with actual Korean flows
- **Implementation**: Parse intraday bars, segment by time zone

```python
# Immediate implementation possible
async def calculate_asian_hours_volume_proxy(ticker: str, date: date) -> Dict:
    """
    Proxy Korean retail activity using extended hours volume

    Asian trading hours (Korean morning):
    - 8:00 PM - 11:59 PM ET (previous day close to midnight)
    - 4:00 AM - 9:30 AM ET (pre-market)

    Returns:
        asian_volume_ratio: Asian hours volume / Regular hours volume
        korean_retail_proxy_score: Normalized 0-100 score
    """
    pass
```

### 2.2 Priority 2: Complete SEC 13F Parsing

Current state only fetches filing metadata. Need to parse actual InfoTable.xml for share counts.

```python
# Required enhancement to sec_scraper.py
async def parse_13f_infotable(self, accession_number: str, cik: str) -> List[Dict]:
    """
    Parse the InfoTable.xml from a 13F-HR filing

    Steps:
    1. Fetch filing index: /Archives/edgar/data/{cik}/{accession}/
    2. Find infotable.xml or primary_doc.xml
    3. Parse XML for CUSIP, shares, value, investment discretion
    4. Match CUSIP to our tracked tickers

    Returns:
        List of holdings with actual share counts and market values
    """
    # InfoTable XML structure:
    # <infoTable>
    #   <nameOfIssuer>PROSHARES ULTRA SILVER</nameOfIssuer>
    #   <cusip>74347R107</cusip>
    #   <value>12345</value>  (in thousands)
    #   <shrsOrPrnAmt><sshPrnamt>50000</sshPrnamt></shrsOrPrnAmt>
    # </infoTable>
    pass
```

**CUSIP Mapping Required:**
| Ticker | CUSIP | Name |
|--------|-------|------|
| AGQ | 74347R107 | ProShares Ultra Silver |
| UGL | 74347R305 | ProShares Ultra Gold |
| ZSL | 74347R206 | ProShares UltraShort Silver |
| GLD | 78463V107 | SPDR Gold Shares |
| SLV | 46428Q109 | iShares Silver Trust |

### 2.3 Priority 3: Implement Futures-Spot Basis Signal

```python
# New signal implementation
async def check_futures_spot_basis(self, ticker: str) -> Optional[Dict]:
    """
    Signal Type 3: FUTURES_SPOT_BASIS

    Trigger: Basis spread indicates contango/backwardation extreme

    For Silver (AGQ/ZSL):
    - Spot: XAG or SLV as proxy
    - Futures: SI=F (front month)
    - Basis = (Futures - Spot) / Spot * 100

    Thresholds:
    - Basis > +2%: Contango extreme → SELL leveraged long
    - Basis < -1%: Backwardation → BUY leveraged long

    Rationale: 2x leveraged ETFs suffer from contango decay
    """
    pass
```

### 2.4 Priority 4: Multi-Factor Signal Scoring

Current signals are binary. Implement a composite scoring system:

```python
class CompositeSignalScorer:
    """
    Combine multiple signal factors into a single actionable score

    Factors and Weights:
    - Flow momentum (z-score): 25%
    - Korean retail contrarian: 20%
    - Institutional accumulation: 20%
    - Futures basis: 15%
    - Macro regime: 10%
    - Options sentiment: 10%

    Output: -100 to +100 score
    - > +60: Strong BUY
    - +30 to +60: Moderate BUY
    - -30 to +30: NEUTRAL
    - -60 to -30: Moderate SELL
    - < -60: Strong SELL
    """
    pass
```

---

## 3. Real-Time Data Enhancements

### 3.1 Intraday Data Collection

The `intraday_bars` table exists but is unused. Implement collection:

```python
# Data sources for intraday (in priority order):

# 1. Polygon.io (configured, API key exists)
#    - 1-min bars for all US equities
#    - WebSocket streaming available
#    - Cost: $29-199/month

# 2. Twelve Data (configured)
#    - Real-time and historical intraday
#    - Good international coverage
#    - Cost: Free tier available

# 3. Yahoo Finance (current)
#    - 1-min bars available via yfinance
#    - Rate limited, less reliable
#    - Cost: Free

async def collect_intraday_bars(ticker: str, interval: str = "5m"):
    """
    Collect intraday bars for real-time analysis

    Intervals: 1m, 5m, 15m, 1h
    Storage: intraday_bars hypertable (already defined)
    Retention: 30 days of minute bars, 1 year of hourly
    """
    pass
```

### 3.2 WebSocket Streaming Architecture

```python
# FastAPI WebSocket endpoint for real-time updates
@router.websocket("/ws/prices/{ticker}")
async def websocket_prices(websocket: WebSocket, ticker: str):
    """
    Stream real-time price updates

    Message types:
    - PRICE_UPDATE: {ticker, price, volume, timestamp}
    - SIGNAL_ALERT: {signal_type, direction, strength}
    - FLOW_UPDATE: {estimated_flow, source}
    """
    await websocket.accept()

    # Subscribe to Redis pub/sub for this ticker
    async for message in redis.subscribe(f"prices:{ticker}"):
        await websocket.send_json(message)
```

### 3.3 Real-Time Premium/Discount Calculation

```python
async def calculate_realtime_premium_discount(ticker: str) -> Dict:
    """
    Calculate ETF premium/discount to NAV in real-time

    For leveraged precious metals ETFs:

    AGQ (2x Silver):
        NAV = 2 * (SI=F or XAG) * shares_per_unit
        Premium = (AGQ_price - NAV) / NAV * 100

    UGL (2x Gold):
        NAV = 2 * (GC=F or XAU) * shares_per_unit
        Premium = (UGL_price - NAV) / NAV * 100

    Signal when |premium| > 1.5%:
        - Premium > +1.5%: SELL (overpriced)
        - Discount < -1.5%: BUY (underpriced)
    """
    pass
```

---

## 4. Unconventional Public Data Sources

### 4.1 Reddit/Social Sentiment (WallStreetBets, Silverbugs)

```python
class RedditSentimentCollector:
    """
    Track retail sentiment from Reddit communities

    Subreddits:
    - r/wallstreetbets (9M+ members)
    - r/Silverbugs (100K+ members)
    - r/Gold (50K+ members)
    - r/investing (2M+ members)

    Metrics:
    - Mention frequency (ticker, commodity names)
    - Sentiment score (bullish/bearish)
    - Post/comment velocity
    - Award count (indicates conviction)

    API: Reddit API (free tier: 60 req/min)
    Alternative: Pushshift API for historical
    """

    SUBREDDITS = ["wallstreetbets", "Silverbugs", "Gold", "investing"]
    KEYWORDS = ["silver", "gold", "AGQ", "UGL", "SLV", "GLD", "platinum"]

    async def fetch_daily_sentiment(self) -> Dict:
        # Return: {ticker: {mentions: int, sentiment: float, velocity: float}}
        pass
```

### 4.2 Google Trends (Search Interest)

```python
from pytrends.request import TrendReq

class GoogleTrendsCollector:
    """
    Track search interest as leading indicator

    Keywords to track:
    - "buy silver"
    - "silver price"
    - "gold investment"
    - "precious metals"
    - "inflation hedge"

    Signal: Spike in search interest often precedes retail buying

    Lag: Real-time (hourly data available)
    """

    KEYWORDS = [
        "buy silver", "silver price", "silver investment",
        "buy gold", "gold price", "gold investment",
        "precious metals ETF", "inflation hedge"
    ]

    async def fetch_trend_data(self, timeframe: str = "now 7-d") -> Dict:
        # Returns interest over time, normalized 0-100
        pass
```

### 4.3 CFTC Commitment of Traders (COT) Reports

```python
class COTDataCollector:
    """
    Weekly positioning data from CFTC

    URL: https://www.cftc.gov/dea/futures/deacmxsf.htm (Short Format)

    Key metrics for Silver (Commodity Code: 084691):
    - Commercial (hedgers): Typically short, provides baseline
    - Non-Commercial (speculators): Large specs, trend followers
    - Nonreportable (retail): Small traders, often contrarian

    Signals:
    - Extreme Non-Commercial long: Contrarian SELL
    - Extreme Non-Commercial short: Contrarian BUY
    - Commercial short covering: Bullish

    Update: Every Friday (data as of Tuesday)
    """

    COT_URL = "https://www.cftc.gov/dea/newcot/c_disagg.txt"

    COMMODITY_CODES = {
        "gold": "088691",
        "silver": "084691",
        "platinum": "076651"
    }

    async def fetch_cot_positioning(self) -> Dict:
        # Parse disaggregated COT report
        # Return net positioning by trader category
        pass
```

### 4.4 Shanghai Futures Exchange (SHFE) Data

```python
class SHFEDataCollector:
    """
    Chinese futures market data - leading indicator for Asian demand

    Contracts:
    - AG (Silver): Shanghai silver futures
    - AU (Gold): Shanghai gold futures

    Data available:
    - Daily open interest
    - Volume
    - Settlement price
    - Warehouse stocks (physical inventory)

    Signal: SHFE premium/discount to COMEX indicates Asian demand

    URL: http://www.shfe.com.cn/statements/
    """

    async def fetch_shfe_data(self, commodity: str) -> Dict:
        # Returns: {open_interest, volume, settlement, warehouse_stocks}
        pass
```

### 4.5 India Import/Export Data (MCX)

```python
class IndiaGoldImportCollector:
    """
    India is world's 2nd largest gold consumer

    Data sources:
    - Ministry of Commerce: Monthly import statistics
    - World Gold Council: Quarterly demand reports
    - MCX (Multi Commodity Exchange): Daily futures data

    Signal: Surge in Indian imports precedes price rallies

    Key periods:
    - Diwali (Oct-Nov): Peak buying
    - Wedding season (Nov-Feb): Sustained demand
    - Akshaya Tritiya (Apr-May): Auspicious buying
    """

    async def fetch_india_gold_imports(self) -> Dict:
        # Returns: {monthly_imports_tonnes, yoy_change, seasonal_adjustment}
        pass
```

### 4.6 US Mint Coin Sales

```python
class USMintSalesCollector:
    """
    US Mint publishes daily/monthly coin sales figures

    URL: https://www.usmint.gov/about/production-sales-figures

    Products tracked:
    - American Eagle Gold (1oz, 1/2oz, 1/4oz, 1/10oz)
    - American Eagle Silver (1oz)
    - American Buffalo Gold (1oz)

    Signal: Retail physical demand indicator
    - Spike in sales = retail FOMO (often contrarian sell)
    - Collapse in sales = retail capitulation (contrarian buy)

    Update: Daily (with 1-2 day lag)
    """

    MINT_URL = "https://www.usmint.gov/about/production-sales-figures"

    async def fetch_mint_sales(self) -> Dict:
        # Returns: {gold_oz_sold, silver_oz_sold, yoy_change}
        pass
```

### 4.7 ETF Holdings Reports (Direct from Issuers)

```python
class ETFHoldingsCollector:
    """
    Physical ETFs publish daily holdings

    GLD (SPDR Gold):
    - URL: https://www.spdrgoldshares.com/usa/gold-bar-list/
    - Daily: Total ounces, bar count

    SLV (iShares Silver):
    - URL: https://www.ishares.com/us/products/239855/
    - Daily: Total ounces, NAV

    PSLV (Sprott Physical Silver):
    - URL: https://sprott.com/investment-strategies/physical-bullion-trusts/
    - Daily: Ounces, premium/discount to NAV

    Signal: Changes in physical holdings = institutional flow proxy
    """

    async def fetch_etf_holdings(self, ticker: str) -> Dict:
        # Returns: {total_ounces, change_ounces, nav_per_share}
        pass
```

### 4.8 Central Bank Gold Reserves (IMF/WGC)

```python
class CentralBankGoldCollector:
    """
    Central bank gold purchases - major demand driver

    Sources:
    - IMF IFS Database: Monthly (2-month lag)
    - World Gold Council: Quarterly reports
    - Individual central bank announcements

    Key buyers to track:
    - China (PBOC): Often unreported, then surprise announcements
    - Russia: Consistent buyer
    - Turkey: Volatile buyer/seller
    - India (RBI): Steady accumulator
    - Poland: Recent large buyer

    Signal: Central bank buying = long-term bullish
    """

    async def fetch_central_bank_reserves(self) -> Dict:
        # Returns: {country: {tonnes, monthly_change, yoy_change}}
        pass
```

### 4.9 Options Flow (CBOE/OCC)

```python
class OptionsFlowCollector:
    """
    Track options activity for sentiment/positioning

    Sources:
    - CBOE: Daily volume reports (free)
    - OCC: Daily cleared volume (free)
    - Unusual Whales / FlowAlgo: Unusual activity (paid)

    Metrics:
    - Put/Call ratio: < 0.5 = extreme bullish, > 1.5 = extreme bearish
    - Open interest changes: Large builds = directional bets
    - IV percentile: > 80% = fear, < 20% = complacency

    Tickers: GLD, SLV options (most liquid for metals)
    """

    async def fetch_options_flow(self, ticker: str) -> Dict:
        # Returns: {put_call_ratio, iv_percentile, unusual_activity: []}
        pass
```

### 4.10 COMEX Warehouse Stocks

```python
class COMEXInventoryCollector:
    """
    COMEX registered/eligible inventory - physical supply indicator

    URL: https://www.cmegroup.com/delivery_reports/

    Categories:
    - Registered: Available for delivery
    - Eligible: Meets specs but not registered

    Signal:
    - Declining registered inventory = physical tightness
    - Inventory vs Open Interest ratio: < 10% = squeeze potential

    Update: Daily (end of day)
    """

    async def fetch_comex_inventory(self, commodity: str) -> Dict:
        # Returns: {registered_oz, eligible_oz, total_oz, oi_coverage_days}
        pass
```

---

## 5. Macro Correlation Implementation

### 5.1 FRED API Integration (Already Configured)

```python
class FREDDataCollector:
    """
    Federal Reserve Economic Data

    Key series for precious metals:

    | Series ID | Description | Update |
    |-----------|-------------|--------|
    | DGS10 | 10-Year Treasury Yield | Daily |
    | DTWEXBGS | Trade Weighted Dollar | Daily |
    | T10YIE | 10-Year Breakeven Inflation | Daily |
    | VIXCLS | VIX Index | Daily |
    | FEDFUNDS | Fed Funds Rate | Monthly |
    | CPIAUCSL | CPI All Items | Monthly |
    | M2SL | M2 Money Supply | Weekly |
    | WALCL | Fed Balance Sheet | Weekly |

    Correlations to track:
    - Gold vs Real Rates (DGS10 - T10YIE): Strong negative
    - Gold vs Dollar (DTWEXBGS): Strong negative
    - Silver vs VIX: Moderate positive (risk-off)
    """

    FRED_API_KEY = settings.FRED_API_KEY

    SERIES_MAP = {
        "treasury_10y": "DGS10",
        "dollar_index": "DTWEXBGS",
        "breakeven_10y": "T10YIE",
        "vix": "VIXCLS",
        "fed_funds": "FEDFUNDS",
        "cpi": "CPIAUCSL",
        "m2": "M2SL",
        "fed_balance_sheet": "WALCL"
    }

    async def fetch_macro_data(self) -> Dict:
        # Returns latest values for all series
        pass

    async def calculate_real_rates(self) -> float:
        # Real rate = Nominal 10Y - 10Y Breakeven
        # Negative real rates = bullish for gold
        pass
```

### 5.2 Correlation-Based Regime Detection

```python
class MarketRegimeDetector:
    """
    Detect current market regime for context-aware signals

    Regimes:
    1. RISK_ON: Stocks up, VIX low, dollar weak
       → Silver outperforms, leveraged OK

    2. RISK_OFF: Stocks down, VIX high, dollar strong
       → Gold outperforms, reduce leverage

    3. INFLATION_FEAR: Breakevens rising, real rates falling
       → Both metals rally, favor gold

    4. DEFLATION_FEAR: Breakevens falling, real rates rising
       → Metals sell off, avoid

    5. STAGFLATION: Inflation up, growth down
       → Gold rallies, silver lags

    Implementation: Rolling 20-day correlations + threshold triggers
    """

    async def detect_regime(self) -> str:
        # Returns current regime classification
        pass
```

---

## 6. Implementation Roadmap

### Phase 1: Quick Wins (1-2 weeks)

| Task | Impact | Effort | Data Source |
|------|--------|--------|-------------|
| Asian hours volume proxy | HIGH | LOW | Existing yfinance intraday |
| Complete 13F XML parsing | HIGH | MEDIUM | SEC EDGAR |
| FRED macro data integration | MEDIUM | LOW | FRED API (configured) |
| Futures-spot basis signal | MEDIUM | LOW | Existing futures data |
| Premium/discount calculation | MEDIUM | LOW | Existing price data |

### Phase 2: Core Enhancements (2-4 weeks)

| Task | Impact | Effort | Data Source |
|------|--------|--------|-------------|
| Korean retail via KSD | HIGH | HIGH | KSD/SEIBRO scraper |
| COT positioning data | HIGH | MEDIUM | CFTC public reports |
| Options put/call ratio | MEDIUM | MEDIUM | CBOE/OCC |
| Google Trends integration | MEDIUM | LOW | pytrends library |
| COMEX inventory tracking | MEDIUM | MEDIUM | CME Group |

### Phase 3: Advanced Features (4-8 weeks)

| Task | Impact | Effort | Data Source |
|------|--------|--------|-------------|
| Real-time WebSocket streaming | HIGH | HIGH | Polygon.io |
| Reddit sentiment analysis | MEDIUM | MEDIUM | Reddit API |
| Composite signal scoring | HIGH | MEDIUM | Internal |
| Market regime detection | MEDIUM | MEDIUM | FRED + derived |
| SHFE/Asian markets | MEDIUM | HIGH | SHFE scraper |
| Central bank tracking | LOW | MEDIUM | IMF/WGC |

### Phase 4: Production Hardening (Ongoing)

| Task | Impact | Effort |
|------|--------|--------|
| APScheduler for automated collection | HIGH | LOW |
| Alert delivery (Email/Slack) | HIGH | MEDIUM |
| Backtesting framework | HIGH | HIGH |
| Data quality monitoring | MEDIUM | MEDIUM |
| ML signal enhancement | MEDIUM | HIGH |

---

## 7. New Signal Types to Implement

### 7.1 Immediate Implementation

```python
# 1. FUTURES_SPOT_BASIS (defined but not implemented)
#    Trigger: Basis > +2% or < -1%

# 2. PREMIUM_DISCOUNT_EXTREME
#    Trigger: ETF premium/discount to NAV > ±1.5%

# 3. OPTIONS_SENTIMENT
#    Trigger: Put/Call ratio < 0.5 or > 1.5

# 4. COT_EXTREME_POSITIONING
#    Trigger: Speculator net position > 90th or < 10th percentile

# 5. VOLUME_SPIKE
#    Trigger: Volume > 3x 20-day average
```

### 7.2 Future Implementation

```python
# 6. ASIAN_HOURS_SURGE
#    Trigger: Asian hours volume > 2x normal (Korean retail proxy)

# 7. PHYSICAL_TIGHTNESS
#    Trigger: COMEX registered inventory declining + high OI

# 8. CENTRAL_BANK_ACCUMULATION
#    Trigger: 3+ months of central bank net buying

# 9. REDDIT_EUPHORIA
#    Trigger: Mention velocity > 3x normal + sentiment > 0.7

# 10. MACRO_REGIME_SHIFT
#     Trigger: Regime change detected (e.g., risk-on → risk-off)
```

---

## 8. Database Schema Additions

```sql
-- New tables needed:

-- 1. COT positioning data
CREATE TABLE cot_positioning (
    report_date DATE NOT NULL,
    commodity VARCHAR(20) NOT NULL,
    commercial_long BIGINT,
    commercial_short BIGINT,
    noncommercial_long BIGINT,
    noncommercial_short BIGINT,
    nonreportable_long BIGINT,
    nonreportable_short BIGINT,
    open_interest BIGINT,
    PRIMARY KEY (report_date, commodity)
);

-- 2. Options flow data
CREATE TABLE options_flow (
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    put_volume BIGINT,
    call_volume BIGINT,
    put_call_ratio DECIMAL(5,3),
    iv_percentile DECIMAL(5,2),
    unusual_activity JSONB,
    PRIMARY KEY (date, ticker)
);

-- 3. Macro indicators
CREATE TABLE macro_indicators (
    date DATE NOT NULL,
    series_id VARCHAR(20) NOT NULL,
    value DECIMAL(15,4),
    source VARCHAR(50),
    PRIMARY KEY (date, series_id)
);

-- 4. Social sentiment
CREATE TABLE social_sentiment (
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    source VARCHAR(50) NOT NULL,  -- reddit, twitter, google_trends
    mentions INT,
    sentiment_score DECIMAL(4,3),  -- -1 to +1
    velocity DECIMAL(8,2),  -- mentions per hour
    PRIMARY KEY (date, ticker, source)
);

-- 5. Physical inventory
CREATE TABLE physical_inventory (
    date DATE NOT NULL,
    commodity VARCHAR(20) NOT NULL,
    exchange VARCHAR(20) NOT NULL,  -- COMEX, LBMA, SHFE
    registered_oz DECIMAL(15,2),
    eligible_oz DECIMAL(15,2),
    total_oz DECIMAL(15,2),
    PRIMARY KEY (date, commodity, exchange)
);

-- 6. Korean retail flows (from KSD)
CREATE TABLE korean_retail_flows (
    date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    net_purchase_krw DECIMAL(15,2),
    net_purchase_usd DECIMAL(15,2),
    shares_bought BIGINT,
    shares_sold BIGINT,
    net_shares BIGINT,
    PRIMARY KEY (date, ticker)
);
```

---

## 9. API Endpoints to Add

```python
# Analytics (implement TODOs)
GET /api/v1/analytics/correlation/{ticker}  # Implement correlation calc
GET /api/v1/analytics/volume-analysis/{ticker}  # Implement volume patterns
GET /api/v1/analytics/macro/correlations  # Implement macro correlations
GET /api/v1/analytics/premium-discount/{ticker}  # Implement NAV calc
GET /api/v1/analytics/regime  # New: Current market regime

# New data endpoints
GET /api/v1/cot/{commodity}  # COT positioning
GET /api/v1/options/{ticker}  # Options flow
GET /api/v1/sentiment/{ticker}  # Social sentiment
GET /api/v1/inventory/{commodity}  # Physical inventory
GET /api/v1/korean-flows/{ticker}  # Korean retail flows

# Real-time
WS /api/v1/ws/prices/{ticker}  # WebSocket streaming
WS /api/v1/ws/signals  # Signal alerts
GET /api/v1/prices/realtime/{ticker}  # Implement real-time quote
```

---

## 10. Configuration Updates

```python
# Add to core/config.py

class Settings(BaseSettings):
    # ... existing settings ...

    # New API Keys
    REDDIT_CLIENT_ID: str = Field(default="", env="REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET: str = Field(default="", env="REDDIT_CLIENT_SECRET")

    # Data collection schedules (cron format)
    PRICE_COLLECTION_SCHEDULE: str = "*/5 9-16 * * 1-5"  # Every 5 min during market
    FLOW_COLLECTION_SCHEDULE: str = "0 18 * * 5"  # Friday 6pm (after week close)
    COT_COLLECTION_SCHEDULE: str = "0 17 * * 5"  # Friday 5pm (COT release)
    SENTIMENT_COLLECTION_SCHEDULE: str = "0 */4 * * *"  # Every 4 hours

    # Feature flags
    ENABLE_KOREAN_RETAIL: bool = Field(default=True)
    ENABLE_OPTIONS_FLOW: bool = Field(default=True)
    ENABLE_SOCIAL_SENTIMENT: bool = Field(default=True)
    ENABLE_WEBSOCKET: bool = Field(default=False)  # Enable when ready
```

---

## 11. Summary of Recommendations

### Highest Impact / Lowest Effort (Do First)
1. **Asian hours volume proxy** - Immediate Korean retail signal without new data
2. **FRED macro integration** - API key already configured
3. **Futures-spot basis signal** - Data already available
4. **Premium/discount calculation** - Pure calculation, no new data

### Highest Impact / Medium Effort (Do Next)
5. **Complete SEC 13F parsing** - Critical for institutional signals
6. **COT positioning data** - Free public data, high signal value
7. **Google Trends integration** - Easy API, good leading indicator

### Game Changers (Invest Time)
8. **Korean retail via KSD** - Validates core thesis
9. **Real-time intraday data** - Enables new signal types
10. **Composite signal scoring** - Actionable output for trading

---

## Appendix: Data Source Summary

| Source | Cost | Update Freq | Effort | Signal Value |
|--------|------|-------------|--------|--------------|
| KSD (Korean retail) | Free | Daily | High | ⭐⭐⭐⭐⭐ |
| CFTC COT | Free | Weekly | Medium | ⭐⭐⭐⭐⭐ |
| SEC 13F (detailed) | Free | Quarterly | Medium | ⭐⭐⭐⭐ |
| FRED API | Free | Daily/Weekly | Low | ⭐⭐⭐⭐ |
| Google Trends | Free | Real-time | Low | ⭐⭐⭐⭐ |
| COMEX Inventory | Free | Daily | Medium | ⭐⭐⭐⭐ |
| Reddit Sentiment | Free | Real-time | Medium | ⭐⭐⭐ |
| Options Flow | Free/Paid | Daily | Medium | ⭐⭐⭐⭐ |
| Polygon.io (real-time) | $29-199/mo | Real-time | Medium | ⭐⭐⭐⭐ |
| SHFE Data | Free | Daily | High | ⭐⭐⭐ |
| US Mint Sales | Free | Daily | Low | ⭐⭐⭐ |
| ETF Holdings (GLD/SLV) | Free | Daily | Low | ⭐⭐⭐ |
| Central Bank Reserves | Free | Monthly | Medium | ⭐⭐ |
