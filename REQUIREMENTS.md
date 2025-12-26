# Commodity Trading Dashboard - Requirements Document

## 1. Executive Summary

### 1.1 Project Overview
A comprehensive commodity trading intelligence platform that tracks precious metals (gold, silver, platinum) and leveraged ETF products, providing actionable buy/sell signals based on fund flows, price movements, and futures market activity. The system combines strategic weekly flow data with near real-time market microstructure, options activity, and macroeconomic indicators for multi-timeframe trading signals.

### 1.2 Primary Objectives
- Monitor real-time and historical price data for precious metals across multiple instruments (spot, futures, options, ETFs)
- Track fund flows for leveraged commodity ETFs with focus on silver and gold products (AGQ, UGL, etc.)
- Attribute flows by investor segment (South Korean retail, US retail, institutional, sovereign funds)
- Generate trading signals based on statistical analysis of flow patterns, price correlations, and investor behavior
- Provide visual dashboard for decision-making and alerting system for extreme market conditions

### 1.3 Target Users
- Commodity traders focusing on precious metals
- Quantitative analysts tracking ETF flows
- Portfolio managers with commodity exposure

---

## 2. System Architecture

### 2.1 High-Level Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Dashboard                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Price Charts │  │ Flow Analysis│  │ Signals/     │      │
│  │              │  │              │  │ Alerts       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                             ↕
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway / Backend                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Data Service │  │ Analytics    │  │ Alert Engine │      │
│  │              │  │ Engine       │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                             ↕
┌─────────────────────────────────────────────────────────────┐
│                    Data Collection Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Market Data  │  │ ETF Flow     │  │ Futures/     │      │
│  │ Collectors   │  │ Scrapers     │  │ Options API  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                             ↕
┌─────────────────────────────────────────────────────────────┐
│                    Data Storage Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Time-Series  │  │ Relational   │  │ Cache/       │      │
│  │ DB (Prices)  │  │ DB (Metadata)│  │ Redis        │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Recommended Technology Stack

#### Frontend
- **Framework**: React with TypeScript
- **Charting**: TradingView Lightweight Charts or Recharts
- **State Management**: React Query + Zustand
- **UI Components**: shadcn/ui or Material-UI
- **Build Tool**: Vite

#### Backend
- **Runtime**: Node.js (TypeScript) or Python (FastAPI)
- **API**: RESTful + WebSocket for real-time updates
- **Task Scheduler**: node-cron or APScheduler (Python)
- **Data Processing**: Pandas (Python) or TypeScript data libraries

#### Database
- **Time-Series**: TimescaleDB (PostgreSQL extension) or InfluxDB
- **Relational**: PostgreSQL
- **Cache**: Redis
- **File Storage**: S3-compatible (MinIO or AWS S3) for CSV archives

#### Infrastructure
- **Container**: Docker + Docker Compose
- **Orchestration**: Kubernetes (production) or Docker Swarm (simple deployment)
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana

---

## 3. Functional Requirements

### 3.1 Commodity Data Collection

#### 3.1.1 Precious Metals Coverage
**Requirement**: System shall track the following precious metals:
- **Gold (XAU)**
- **Silver (XAG)**
- **Platinum (XPT)**

#### 3.1.2 Instrument Types Per Commodity
For each metal, collect:

**A. Spot Prices**
- Real-time spot price ($/oz)
- Bid/Ask spreads
- Intraday tick data (optional for Phase 1, required for Phase 2)
- Daily OHLCV (Open, High, Low, Close, Volume)

**B. Futures Contracts**
- Front-month contract data (primary focus)
- Next 3-6 contracts (for curve analysis)
- Contract specifications: symbol, expiry, multiplier
- OHLCV data
- Open interest
- Exchange: COMEX (CME Group)

**C. Options Data** (Phase 2)
- At-the-money (ATM) options for front-month futures
- Implied volatility
- Put/Call ratios
- Open interest by strike

**D. Physical ETFs & ETNs**
- GLD (Gold Trust)
- SLV (iShares Silver Trust)
- PPLT (Physical Platinum)
- Daily price, volume, AUM

### 3.2 Leveraged ETF Tracking

#### 3.2.1 Target Tickers
**Primary Focus**:
- **AGQ** (ProShares Ultra Silver - 2x leveraged long)
- **UGL** (ProShares Ultra Gold - 2x leveraged long)

**Extended List** (monitor for delisting/low volume):
- **USLV** (VelocityShares 3x Long Silver ETN) - *likely delisted*
- **DSLV** (VelocityShares 3x Inverse Silver ETN) - *likely delisted*
- **ZSL** (ProShares UltraShort Silver - 2x inverse)
- **UBG** (ProShares Ultra Basic Materials - includes gold/silver miners)
- **SLVP** (iShares MSCI Global Silver Miners ETF) - miners, not pure silver
- **SILJ** (ETFMG Junior Silver Miners ETF)

**Action Items**:
- Maintain a configurable list of active tickers
- Flag tickers with average daily volume < 100k shares
- Auto-detect delisted products

#### 3.2.2 ETF Data Points
For each ticker, collect:
- Daily OHLCV
- Fund flows (weekly aggregation)
- AUM (Assets Under Management)
- Expense ratio
- Holdings composition (if available)
- Creation/Redemption activity (if available)
- Premium/Discount to NAV

### 3.3 Fund Flow Data Acquisition

#### 3.3.1 Data Sources
**Primary Sources**:
1. **ETFdb.com** - Free tier provides basic flow data
2. **ETF.com** - Flow data via CSV export or API
3. **Fallback**: Bloomberg, FactSet (require subscriptions)

**Data Format**:
- Weekly fund flow reports (net inflows/outflows in $)
- Historical flow data (minimum 2 years for z-score analysis)

#### 3.3.2 Collection Workflow
**Frequency**: Weekly (every Monday morning, capturing prior week data)

**Process**:
1. Automated scraper/API call to ETFdb.com or ETF.com
2. Download CSV or parse HTML tables
3. Validate data completeness
4. Store in database with timestamp
5. Trigger analytics pipeline

**Manual Override**: UI to manually upload CSV if automation fails

#### 3.3.3 Investor Segment Attribution

**Overview**:
Leveraged commodity ETFs like AGQ and UGL attract diverse investor segments with different trading behaviors and market impact. Understanding flow attribution by investor type provides deeper signal intelligence.

**Key Investor Segments**:

**A. South Korean Retail Investors**

South Korean retail investors have emerged as a dominant force in US leveraged ETF markets, particularly for commodity and volatility products. As of 2025, they hold an estimated **$15.6 billion in US-listed equity leveraged ETFs**, with **28.7% of overseas ETF holdings in leveraged or inverse funds**.

**Why Track Korean Retail**:
- High concentration in leveraged products (AGQ, UGL likely targets)
- Retail sentiment indicator (contrarian signals when extreme)
- Flow volumes often spike during Asian trading hours
- Known for momentum-chasing behavior (can amplify trends)

**Data Sources**:
1. **Korea Securities Depository (KSD)** - Primary source for Korean overseas securities purchases
   - URL: Available through Korean financial data providers
   - Update frequency: Monthly official reports
   - Access: Requires Korean language capability or third-party aggregator

2. **ETFGI Reports** - Monthly tracking of Korean retail ETF flows
   - URL: [ETFGI.com](https://etfgi.com)
   - Sample data: $9.66B in overseas ETF purchases (June 2025), $15.85B all-time high (Oct 2025)
   - Access: Subscription required for detailed reports; press releases are public
   - Update frequency: Monthly

3. **Korea Exchange (KRX)** - Domestic ETF market data
   - URL: [KRX.co.kr](http://www.krx.co.kr)
   - Coverage: 1,370 ETFs with $167.38B AUM (as of June 2025)
   - Useful for cross-referencing Korean investor behavior patterns

**Implementation Strategy**:
- **Phase 1 (MVP)**: Manual monthly tracking via ETFGI press releases + estimated AGQ/UGL exposure
- **Phase 2**: Automated scraping of KRX data + paid ETFGI subscription for detailed breakdowns
- **Phase 3**: Time-zone analysis of AGQ/UGL volume during Asian hours as proxy for Korean activity

**B. Hedge Funds & Institutional Investors**

Hedge funds use leveraged ETFs for tactical positioning, hedging, and short-term momentum plays. Their flows tend to lead retail flows and can signal smart money positioning.

**Data Sources**:
1. **13F Filings (SEC)** - Quarterly institutional holdings
   - URL: [SEC EDGAR](https://www.sec.gov/edgar/searchedgar/companysearch)
   - Coverage: US institutions managing >$100M must disclose long equity positions
   - Limitations: 45-day lag, no short positions, no intra-quarter changes
   - Access: Free via SEC EDGAR or aggregators (WhaleWisdom, Dataroma)

2. **EPFR (Emerging Portfolio Fund Research)** - Real-time institutional flow tracking
   - URL: [EPFR.com](https://epfr.com)
   - Coverage: Global ETF and mutual fund flows with retail vs. institutional breakdown
   - Key feature: Can filter by investor type (retail vs. institutional)
   - Limitation: **Excludes pension funds, hedge funds, insurance companies, sovereign wealth funds** (tracks fund flows, not direct hedge fund activity)
   - Access: Expensive subscription (~$20k-50k/year)

3. **Prime Brokerage Reports** - Proprietary hedge fund flow data
   - Sources: Goldman Sachs, Morgan Stanley, JP Morgan client reports
   - Access: Restricted to institutional clients
   - Alternative: Some data leaked via financial media (Bloomberg, FT)

**Implementation Strategy**:
- **Phase 1 (MVP)**: Quarterly 13F scraping for AGQ/UGL institutional holders (free)
- **Phase 2**: Track changes in top 20 institutional holders quarter-over-quarter
- **Phase 3**: EPFR subscription for weekly institutional flow estimates (if budget allows)

**C. Sovereign Wealth Funds & Asset Owners**

Sovereign wealth funds (SWFs) and pension funds typically avoid leveraged ETFs due to risk constraints, but may use them during crisis periods or for currency hedging.

**Data Sources**:
1. **13F Filings** - Same as hedge funds (quarterly, 45-day lag)
2. **SWF Direct Disclosures** - Annual reports from major SWFs
   - Norway GPFG, Abu Dhabi ADIA, Singapore GIC, China CIC
   - Access: Public annual reports (published yearly)
   - Limitation: High-level allocations only, no specific ETF holdings

**Implementation Strategy**:
- **Phase 1**: Monitor 13F for unusual SWF activity in AGQ/UGL (rare but high-signal)
- **Phase 2**: Flag any SWF appearance in holder list as major event alert

**D. Retail Investors (US & Global)**

US and other global retail investors tracked via aggregate ETF flow data from ETFdb.com and ETF.com (already covered in Section 3.3.1).

**Attribution Analysis Framework**:

**Table: investor_segment_flows**
```sql
CREATE TABLE investor_segment_flows (
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

CREATE INDEX ON investor_segment_flows (ticker, segment, week_ending DESC);
```

**Calculation Methodology**:

1. **Korean Retail Flow Estimation**:
   ```
   Korean_AGQ_flow = (Total_Korean_Leveraged_ETF_Flow * AGQ_market_share)
                     + Asian_hours_volume_spike_adjustment
   ```
   - Use ETFGI monthly totals, prorate to weekly
   - Estimate AGQ/UGL market share based on AUM and volume rankings
   - Confidence score: 0.6-0.7 (estimation-based)

2. **Institutional Flow (13F-based)**:
   ```
   Institutional_quarterly_change = SUM(13F_new_positions + 13F_increased_positions - 13F_decreased_positions)
   Weekly_estimate = Institutional_quarterly_change / 13
   ```
   - Aggregate top 50 institutional holders' quarterly changes
   - Confidence score: 0.5-0.6 (stale data, smoothed over quarter)

3. **Residual Retail Flow**:
   ```
   US_Retail_flow = Total_ETF_flow - Korean_retail_flow - Institutional_flow
   ```
   - Confidence score: 0.4-0.5 (residual calculation)

**Signal Enhancements Using Segment Data**:

**1. Smart Money Divergence Alert**:
- Trigger: Institutional flows (13F) move opposite to total flows
- Example: AGQ sees +$50M total inflow, but top hedge funds reduce by 20% in 13F
- Signal: Retail buying peak, potential reversal

**2. Korean Retail Euphoria Indicator**:
- Trigger: Korean retail flows exceed 30% of total AGQ/UGL weekly flows
- Historical context: Korean retail often peak-buys during blow-off tops
- Signal: Contrarian sell signal (fade the Korean retail)

**3. Institutional Accumulation**:
- Trigger: 3+ consecutive quarters of increasing institutional 13F holdings
- Signal: Long-term bullish confirmation

**Dashboard Visualization**:
- Stacked bar chart: Weekly flows broken down by segment (Korean retail, US retail, institutional, unknown)
- Pie chart: Current month's flow composition by segment
- Time series: Korean retail flows vs. AGQ price (correlation analysis)

#### 3.3.4 Near Real-Time Data Sources

**Overview**:
While weekly ETF flows and quarterly 13F filings provide strategic positioning data, near real-time sources enable tactical trading decisions and early signal detection. This section covers intraday and sub-minute data feeds.

**A. Intraday Price & Volume Data**

**1. Real-Time Quote Data (Stocks & ETFs)**

**Data Sources**:

| Source | Latency | Coverage | Cost | Best For |
|--------|---------|----------|------|----------|
| **Polygon.io** | 15-min delayed (free)<br>Real-time (paid) | Stocks, ETFs, options, futures | Free tier: 5 calls/min<br>Starter: $199/mo (real-time)<br>Advanced: $399/mo (WebSocket) | Production-grade, reliable API |
| **Alpha Vantage** | Real-time | Stocks, ETFs, limited futures | Free: 25 calls/day<br>Premium: $49.99/mo (75 calls/min) | MVP testing (limited calls) |
| **Twelve Data** | Real-time | Stocks, ETFs, futures, forex | Free: 800 calls/day<br>Basic: $79/mo (8 calls/sec) | Good free tier for testing |
| **Interactive Brokers API** | Real-time (market data sub required) | Everything (global) | $10/mo + $1-2/exchange | Best latency if you have IB account |
| **Yahoo Finance (yfinance)** | 15-min delayed | Stocks, ETFs, futures | Free (unofficial) | MVP only, unreliable |
| **Tradier** | Real-time | Stocks, ETFs, options | Free tier available<br>Brokerage account required | Options data included |

**Recommended Stack**:
- **MVP (Phase 1)**: Twelve Data (free tier) for intraday OHLCV
- **Phase 2**: Polygon.io Starter ($199/mo) for real-time prices + WebSocket
- **Phase 3**: Add Interactive Brokers for lowest latency execution signals

**Data Points Collected** (per ticker: AGQ, UGL, GC=F, SI=F, etc.):
- **1-minute OHLCV bars** (for intraday charts and volume analysis)
- **Real-time quotes**: Last price, bid/ask, spread
- **Level 1 data**: Volume, VWAP (Volume Weighted Average Price)
- **Tick data** (optional Phase 3): Every trade for microstructure analysis

**2. Intraday Volume Analysis**

**Volume Spike Detection**:
- Compare current 5-min volume to 20-day average 5-min volume
- Alert when volume exceeds 3x average (potential breakout or news event)
- Track volume by time zone (US hours vs. Asian hours for Korean retail proxy)

**Time-Zone Volume Breakdown**:
```sql
-- Example query to detect Asian hours volume spikes (Korean retail proxy)
SELECT
    DATE_TRUNC('hour', timestamp AT TIME ZONE 'America/New_York') as hour_et,
    ticker,
    SUM(volume) as total_volume,
    AVG(SUM(volume)) OVER (
        PARTITION BY ticker, EXTRACT(HOUR FROM timestamp AT TIME ZONE 'America/New_York')
        ORDER BY DATE_TRUNC('day', timestamp)
        ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
    ) as avg_volume_20d
FROM intraday_bars
WHERE ticker IN ('AGQ', 'UGL')
    AND EXTRACT(HOUR FROM timestamp AT TIME ZONE 'America/New_York') BETWEEN 20 AND 23  -- 8pm-11pm ET = 9am-12pm KST
GROUP BY DATE_TRUNC('hour', timestamp AT TIME ZONE 'America/New_York'), ticker;
```

**Signal**: If AGQ volume during 8pm-11pm ET (Korean morning) is >2x normal, flag as potential Korean retail activity.

**B. Options Flow & Unusual Activity**

Options data provides leading indicators of institutional positioning and hedging activity.

**Data Sources**:

| Source | Latency | Coverage | Cost | Best For |
|--------|---------|----------|------|----------|
| **CBOE DataShop** | Real-time | All US options | Varies (exchange data expensive) | Official but costly |
| **Tradier** | Real-time | All US options | Free with brokerage account | Good free option |
| **Polygon.io** | Real-time | Options quotes + Greeks | Included in Advanced plan ($399/mo) | Good value bundle |
| **Unusual Whales** | Near real-time | Options flow analysis | $50/mo (retail)<br>$200/mo (pro) | Pre-analyzed unusual activity |
| **FlowAlgo** | Real-time | Options flow scanner | $150-300/mo | Alerts for block trades |

**Data Points**:
- **Unusual options activity**: Block trades (>$100k premium) in AGQ/UGL/GLD/SLV calls/puts
- **Put/Call ratio**: Intraday AGQ put/call volume ratio (sentiment indicator)
- **Implied volatility (IV)**: Front-month ATM IV spikes indicate expected moves
- **Greeks**: Delta, gamma to estimate dealer hedging flows

**Implementation**:
- **Phase 1 (MVP)**: Daily options data via free Tradier account (end-of-day summary)
- **Phase 2**: Real-time unusual options alerts via Polygon.io or Unusual Whales
- **Phase 3**: Full options flow analysis with Greeks and dealer positioning

**Signal Examples**:
- **Large call sweeps on AGQ**: Institutional bullish bet, confirm with flow data
- **IV spike on UGL**: Expect volatility, upcoming news or positioning
- **Put/Call ratio >2.0**: Bearish sentiment (contrarian bullish?)

**C. Futures Market Microstructure**

CME COMEX futures for gold (GC), silver (SI), and platinum (PL) trade nearly 24/5, providing continuous price discovery.

**Data Sources**:

| Source | Latency | Coverage | Cost | Best For |
|--------|---------|----------|------|----------|
| **CME DataMine** | Real-time | All CME futures (official) | $500-5000+/mo depending on data | Official, expensive |
| **Interactive Brokers API** | Real-time | CME futures | $10/mo + $1.50 CME fee | Best value for futures data |
| **Polygon.io** | Real-time | Major futures contracts | Included in Advanced ($399/mo) | Good bundle deal |
| **Barchart** | Real-time | Futures + commitments of traders | $40-200/mo | COT reports included |

**Data Points**:
- **Front-month futures prices** (GC, SI, PL): 1-minute bars
- **Open interest (OI)**: Daily OI changes (increasing OI + rising price = bullish)
- **Commitment of Traders (COT) reports**: Weekly (Fridays 3:30pm ET) - shows commercial vs. speculative positioning
- **Funding rate / basis**: Spot vs. futures spread (contango/backwardation)

**COT Report Analysis**:
- **Commercials (hedgers)** typically sell into strength (contrarian indicator)
- **Large speculators (hedge funds)** follow trends
- **Small speculators (retail)** are wrong at extremes (contrarian indicator)

**Implementation**:
- **Phase 1**: Daily futures data via Twelve Data or yfinance
- **Phase 2**: Real-time futures via Interactive Brokers API
- **Phase 3**: Automated COT report parsing and extreme positioning alerts

**D. Alternative Data Sources**

**1. Social Media Sentiment**

Track retail sentiment and early trend detection.

**Data Sources**:

| Source | Coverage | Cost | Best For |
|--------|----------|------|----------|
| **Twitter API v2** | Tweets, mentions | $100-5000/mo (paid tiers) | Real-time keyword tracking |
| **Reddit API (PRAW)** | r/WallStreetBets, r/Silverbugs | Free | Retail sentiment gauge |
| **StockTwits API** | Social sentiment for $AGQ, $UGL | Free tier available | Trader-focused sentiment |
| **LunarCrush** | Crypto + stock social metrics | Free tier + $50-200/mo | Aggregated sentiment scores |

**Tracked Metrics**:
- **Mention volume**: Spikes in "$AGQ" or "silver" mentions on Twitter/Reddit
- **Sentiment score**: Bullish vs. bearish (NLP analysis)
- **Influencer activity**: Track key commodity traders/analysts

**Signal Example**:
- **Reddit WallStreetBets "silver squeeze" mentions >1000/day**: Retail euphoria, contrarian sell signal (historically preceded tops)

**Implementation**:
- **Phase 1**: Manual check of r/WallStreetBets daily threads
- **Phase 2**: Automated Reddit/Twitter scraping with sentiment analysis (VADER, FinBERT)
- **Phase 3**: Real-time StockTwits feed with sentiment scoring

**2. News & Event Detection**

Real-time financial news can move commodity prices instantly.

**Data Sources**:

| Source | Latency | Coverage | Cost | Best For |
|--------|----------|------|----------|----------|
| **Benzinga News API** | Real-time | Financial news, earnings | $300-1000/mo | Fast, reliable |
| **Alpha Vantage News** | Real-time | General + ticker-specific | Free tier available | Good for testing |
| **NewsAPI.org** | Real-time | Global news (general) | Free: 100 calls/day<br>Paid: $449/mo | Good free tier |
| **Google News RSS** | 15-min delay | Free scraping (check ToS) | Free | MVP, legal gray area |
| **Bloomberg Terminal** | Real-time | Everything (best-in-class) | $25,000/year | Only if you already have access |

**Tracked Keywords**:
- "Silver", "gold", "platinum", "Fed", "inflation", "dollar", "China demand"
- Company names: ProShares (AGQ/UGL issuer)
- Central bank policy: "FOMC", "Powell", "rate hike/cut"

**Implementation**:
- **Phase 1**: Google News RSS scraping for "silver news" + "gold news"
- **Phase 2**: Alpha Vantage News API (free tier)
- **Phase 3**: Benzinga News API with NLP categorization (hawkish/dovish, bullish/bearish)

**E. Macroeconomic Indicators (Real-Time)**

Commodities correlate strongly with macro factors.

**Key Indicators to Track**:

| Indicator | Impact on Gold/Silver | Data Source | Update Frequency |
|-----------|----------------------|-------------|------------------|
| **US Dollar Index (DXY)** | Inverse correlation | Twelve Data, Polygon.io, IB | Real-time |
| **10-Year Treasury Yield** | Gold inverse to real yields | FRED API, Twelve Data | Real-time |
| **Real Yields (TIPS)** | Strongest gold correlation | FRED API | Daily |
| **VIX (Volatility Index)** | Risk-off → gold up | CBOE, Polygon.io | Real-time |
| **Bitcoin (BTC)** | Correlation varies (digital gold?) | Coinbase API, Polygon.io | Real-time |
| **Oil (CL futures)** | Commodity complex correlation | Same as futures sources | Real-time |
| **China PMI, CPI** | Demand indicator for metals | Trading Economics API | Monthly |

**Correlation Trading Signals**:
- **DXY down + Gold up**: Reinforcing trend, bullish for UGL
- **DXY up + Gold up**: Divergence, defensive buying (geopolitical risk)
- **VIX spike >30 + Gold flat**: Gold underperforming safe-haven bid, potential catch-up trade

**Data Source: FRED (Federal Reserve Economic Data)**
- **URL**: [FRED API](https://fred.stlouisfed.org/docs/api/fred/)
- **Cost**: Free
- **Data**: 10Y yield (DGS10), inflation (CPI), GDP, employment
- **Update**: Daily for most series

**Implementation**:
- **Phase 1**: Daily FRED API pulls for DXY, 10Y yield, VIX
- **Phase 2**: Real-time macro dashboard panel with correlation heatmap
- **Phase 3**: Automated correlation breakout alerts

**F. Intraday ETF Creation/Redemption Data**

ETF creation/redemption is a leading indicator of institutional flows, faster than weekly flow data.

**Challenge**: Official creation/redemption data is reported with a 1-day lag (next business day).

**Proxy Method**:
- **ETF Premium/Discount to NAV**: Intraday tracking
  - Formula: `(ETF_price - estimated_NAV) / estimated_NAV`
  - Data source: Calculate using ETF price + underlying commodity spot price
  - Signal: Premium >0.5% suggests strong buying (creation likely), Discount <-0.5% suggests redemption

**Data Sources**:
- ETF price: Real-time via Polygon.io, Twelve Data
- Spot gold/silver: Same sources
- Estimated NAV: `Spot_price × Leverage_factor × (1 - daily_fee_accrual)`

**Implementation**:
- **Phase 2**: Real-time premium/discount calculator for AGQ, UGL
- **Phase 3**: Alert when premium/discount exceeds thresholds

---

**G. Real-Time Data Infrastructure**

**WebSocket Streaming**:
For sub-second latency, replace polling with WebSocket streams.

**Supported by**:
- **Polygon.io** (Advanced plan): WebSocket for stocks, options, futures
- **Interactive Brokers**: Native streaming via TWS API
- **Twelve Data**: WebSocket available on higher tiers
- **Alpaca Markets**: Free WebSocket for stocks (if using their broker)

**Architecture**:
```
┌──────────────────────────────────────────────┐
│  Data Source WebSocket (Polygon.io, etc.)   │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│  WebSocket Handler Service (Python/Node.js)  │
│  - Parse incoming messages                    │
│  - Calculate derived metrics (VWAP, etc.)    │
│  - Check alert conditions                    │
└──────────────────────────────────────────────┘
                    ↓
          ┌─────────┴─────────┐
          ↓                   ↓
┌──────────────────┐  ┌──────────────────┐
│  Redis Pub/Sub   │  │  TimescaleDB     │
│  (real-time)     │  │  (persistence)   │
└──────────────────┘  └──────────────────┘
          ↓
┌──────────────────────────────────────────────┐
│  Frontend WebSocket (dashboard updates)      │
└──────────────────────────────────────────────┘
```

**Implementation**:
- **Phase 1**: HTTP polling every 1 minute (sufficient for MVP)
- **Phase 2**: WebSocket for real-time price updates during market hours
- **Phase 3**: Full streaming analytics with Redis pub/sub

---

**H. Data Latency & Refresh Frequency Summary**

| Data Type | Source | Latency | Refresh Frequency | Phase |
|-----------|--------|---------|-------------------|-------|
| **Weekly ETF flows** | ETFdb.com | 3-7 days | Weekly (Monday) | 1 |
| **13F institutional** | SEC EDGAR | 45 days | Quarterly | 1 |
| **Korean retail flows** | ETFGI | 1 month | Monthly | 1 |
| **Daily OHLCV** | Twelve Data / Polygon | 15 min - EOD | Daily | 1 |
| **Intraday 1-min bars** | Polygon.io | Real-time | 1 minute | 2 |
| **Real-time quotes** | Polygon WebSocket | <100ms | Sub-second | 2 |
| **Options flow** | Unusual Whales | 1-5 min | Real-time | 2 |
| **Futures data** | Interactive Brokers | <50ms | Real-time | 2 |
| **COT reports** | CFTC / Barchart | Weekly (Fri 3:30pm) | Weekly | 2 |
| **News events** | Benzinga API | <1 sec | Real-time | 2 |
| **Social sentiment** | Twitter/Reddit | 5-15 min | Real-time | 3 |
| **Macro indicators** | FRED API | Daily | Daily (some weekly) | 1 |
| **Premium/Discount** | Calculated | Real-time | 1 minute | 2 |

---

**I. Real-Time Signal Enhancements**

Combining near real-time data with weekly flow analysis creates multi-timeframe signals:

**1. Volume Confirmation Signal**
- **Trigger**: Weekly flow z-score >2.0 (extreme inflow) **AND** intraday volume >3x average
- **Signal**: High-conviction buy, flows confirmed by immediate volume response
- **Timeframe**: Execute same-day

**2. Options-Flow Divergence**
- **Trigger**: Large institutional put-buying on AGQ **BUT** weekly flows show inflows
- **Signal**: Institutions hedging long exposure, potential top
- **Timeframe**: 1-3 days

**3. Asian Hours Pump**
- **Trigger**: AGQ volume during 8pm-11pm ET (Korean hours) >3x normal
- **Signal**: Korean retail FOMO, fade the move next day (contrarian)
- **Timeframe**: Next morning (US open)

**4. Macro Catalyst Alert**
- **Trigger**: DXY drops >1% intraday **AND** gold futures +2% **AND** AGQ/UGL lagging
- **Signal**: ETFs will catch up to futures, buy AGQ/UGL
- **Timeframe**: Intraday (minutes to hours)

**5. News Spike + Premium**
- **Trigger**: Hawkish Fed news + gold spikes + UGL premium to NAV >0.8%
- **Signal**: Institutions creating new UGL shares (strong buying), trend starting
- **Timeframe**: Same-day entry

---

**J. Cost-Benefit Analysis for Real-Time Data**

**Free Tier (MVP)**:
- Twelve Data (800 calls/day) - FREE
- FRED API - FREE
- yfinance (unreliable) - FREE
- Manual Reddit/Twitter checks - FREE
- **Total**: $0/month
- **Limitation**: 15-min delayed data, no WebSocket, rate limits

**Mid-Tier (Phase 2)**:
- Polygon.io Starter - $199/mo (real-time stocks, ETFs, futures)
- Alpha Vantage News - FREE tier
- StockTwits API - FREE tier
- **Total**: ~$200/month
- **Capability**: Real-time prices, intraday signals, basic news

**Production (Phase 3)**:
- Polygon.io Advanced - $399/mo (WebSocket, options)
- Unusual Whales - $200/mo (options flow)
- Benzinga News - $300/mo
- Interactive Brokers - $10/mo
- **Total**: ~$900/month
- **Capability**: Full real-time streaming, institutional-grade data

**Recommendation**: Start with free tier, upgrade to Polygon.io Starter ($199/mo) once MVP proves valuable, then scale to production tier if generating alpha.

### 3.4 Analytics & Signal Generation

#### 3.4.1 Flow Analysis Metrics

**A. Rolling Sums**
- 4-week rolling sum of fund flows
- 13-week rolling sum
- 26-week rolling sum
- 52-week rolling sum

**B. Z-Score Calculation**
For each ticker and rolling window:
```
z-score = (current_flow - mean_historical_flow) / std_dev_historical_flow
```
- Use rolling 52-week history as baseline
- Flag z-scores > 2.0 (extreme inflow) or < -2.0 (extreme outflow)

**C. Percentile Ranking**
- Rank current week's flow against historical distribution
- Alert on >95th percentile (extreme inflow) or <5th percentile (extreme outflow)

#### 3.4.2 Correlation Analysis

**A. Flow vs. Price**
- Pearson correlation between weekly ETF flows and:
  - AGQ price change (weekly)
  - Spot silver price change
  - Front-month COMEX futures price change
- Rolling 26-week correlation window

**B. Volume Analysis**
- Compare AGQ volume spikes with flow extremes
- Detect divergences (high volume without flow confirmation)

**C. Flow Attribution**
Classify price moves as:
- **Flow-driven**: High correlation (r > 0.6) between flows and price
- **Futures-driven**: Price moves driven by futures OI/volume, weak flow correlation
- **Mixed**: Moderate correlation (0.3 < r < 0.6)

#### 3.4.3 Trading Signals

**Signal Types**:

**1. Extreme Flow Signal**
- **Trigger**: Z-score > 2.5 (Strong Buy) or < -2.5 (Strong Sell)
- **Confirmation**: 2 consecutive weeks in same direction
- **Output**: BUY/SELL recommendation with confidence score

**2. Flow-Price Divergence**
- **Trigger**: Large flow (>90th percentile) but price unchanged or opposite direction
- **Signal**: Potential reversal or delayed reaction
- **Output**: WATCH alert

**3. Futures-Spot Basis Signal**
- **Trigger**: Abnormal spread between front-month futures and spot price
- **Signal**: Contango/backwardation extremes
- **Output**: Market structure alert

**4. Momentum Alignment**
- **Trigger**: AGQ flows, spot silver, and futures all trending same direction for 3+ weeks
- **Signal**: Strong trend confirmation
- **Output**: STRONG BUY/STRONG SELL

**5. Smart Money Divergence** (Segment-Based)
- **Trigger**: Institutional flows (13F) move opposite to total flows
- **Example**: AGQ sees +$50M total inflow, but top hedge funds reduce by 20%
- **Signal**: Retail buying peak, potential reversal
- **Output**: CONTRARIAN SELL (or vice versa)

**6. Korean Retail Euphoria Indicator** (Segment-Based)
- **Trigger**: Korean retail flows exceed 30% of total AGQ/UGL weekly flows
- **Context**: Korean retail historically peak-buys during blow-off tops
- **Signal**: Contrarian sell signal (fade the Korean retail momentum)
- **Output**: CONTRARIAN SELL with sentiment warning

**7. Institutional Accumulation** (Segment-Based)
- **Trigger**: 3+ consecutive quarters of increasing institutional 13F holdings
- **Signal**: Long-term bullish confirmation from smart money
- **Output**: LONG-TERM BUY with high conviction

**Signal Dashboard Display**:
- Current signal status for each ticker
- Signal strength (1-5 stars or percentage confidence)
- Time since signal triggered
- Historical signal accuracy (backtested win rate)

### 3.5 Alerting System

#### 3.5.1 Alert Channels
- **In-app notifications**: Dashboard banner
- **Email**: Digest summary + immediate alerts for extreme signals
- **Webhook**: Integration with Slack, Discord, or Telegram
- **SMS** (optional): For critical alerts only

#### 3.5.2 Alert Triggers
- Weekly flow data import complete
- Z-score exceeds threshold (configurable, default ±2.0)
- New trading signal generated
- Korean retail flows spike above 30% of total flows
- Smart money divergence detected (institutional selling while retail buying)
- 13F filing shows significant institutional position changes (>20%)
- Data collection failure (missing flows, API errors)
- Ticker delisted or volume below threshold

#### 3.5.3 Alert Configuration
User-configurable settings:
- Alert thresholds (z-score, percentile)
- Notification channels per alert type
- Quiet hours (suppress non-critical alerts)
- Digest schedule (daily, weekly)

---

## 4. Data Management Requirements

### 4.1 Data Storage Schema

#### 4.1.1 Time-Series Data (TimescaleDB/InfluxDB)

**Table: commodity_prices**
```sql
CREATE TABLE commodity_prices (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(10) NOT NULL,  -- XAU, XAG, XPT
    instrument_type VARCHAR(20),  -- SPOT, FUTURES, ETF
    contract_month DATE,          -- for futures
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    open_interest BIGINT,         -- for futures
    PRIMARY KEY (timestamp, symbol, instrument_type, contract_month)
);

SELECT create_hypertable('commodity_prices', 'timestamp');
CREATE INDEX ON commodity_prices (symbol, instrument_type, timestamp DESC);
```

**Table: etf_prices**
```sql
CREATE TABLE etf_prices (
    timestamp TIMESTAMPTZ NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    open DECIMAL(12,4),
    high DECIMAL(12,4),
    low DECIMAL(12,4),
    close DECIMAL(12,4),
    volume BIGINT,
    adj_close DECIMAL(12,4),
    PRIMARY KEY (timestamp, ticker)
);

SELECT create_hypertable('etf_prices', 'timestamp');
```

**Table: etf_flows**
```sql
CREATE TABLE etf_flows (
    week_ending DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    net_flow DECIMAL(16,2),        -- in USD millions
    aum DECIMAL(16,2),
    shares_outstanding BIGINT,
    premium_discount DECIMAL(6,4), -- percentage
    source VARCHAR(50),            -- ETFdb, ETF.com, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (week_ending, ticker)
);

SELECT create_hypertable('etf_flows', 'week_ending');
```

#### 4.1.2 Relational Data (PostgreSQL)

**Table: tickers**
```sql
CREATE TABLE tickers (
    ticker VARCHAR(10) PRIMARY KEY,
    name VARCHAR(200),
    asset_class VARCHAR(50),      -- SILVER_LEVERAGED, GOLD_ETF, etc.
    leverage_factor DECIMAL(4,2), -- 2.0 for 2x, -2.0 for inverse 2x
    expense_ratio DECIMAL(5,4),
    inception_date DATE,
    is_active BOOLEAN DEFAULT true,
    last_volume_check DATE,
    avg_daily_volume BIGINT,
    delisted_date DATE,
    notes TEXT
);
```

**Table: signals**
```sql
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    ticker VARCHAR(10) REFERENCES tickers(ticker),
    signal_type VARCHAR(50),      -- EXTREME_FLOW, DIVERGENCE, MOMENTUM, etc.
    direction VARCHAR(10),        -- BUY, SELL, WATCH
    strength DECIMAL(3,2),        -- 0.0 to 1.0
    trigger_values JSONB,         -- store z-scores, correlations, etc.
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, EXPIRED, CLOSED
    expires_at TIMESTAMPTZ
);

CREATE INDEX ON signals (ticker, generated_at DESC);
CREATE INDEX ON signals (status, generated_at DESC);
```

**Table: alert_log**
```sql
CREATE TABLE alert_log (
    id SERIAL PRIMARY KEY,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    alert_type VARCHAR(50),
    ticker VARCHAR(10),
    channel VARCHAR(20),          -- EMAIL, SLACK, IN_APP, etc.
    recipient VARCHAR(200),
    message TEXT,
    status VARCHAR(20)            -- SENT, FAILED, PENDING
);
```

#### 4.1.3 Computed Views

**View: latest_signals**
```sql
CREATE VIEW latest_signals AS
SELECT DISTINCT ON (ticker)
    ticker, signal_type, direction, strength, generated_at
FROM signals
WHERE status = 'ACTIVE' AND expires_at > NOW()
ORDER BY ticker, generated_at DESC;
```

**View: flow_statistics**
```sql
CREATE VIEW flow_statistics AS
SELECT
    ticker,
    week_ending,
    net_flow,
    AVG(net_flow) OVER (PARTITION BY ticker ORDER BY week_ending ROWS BETWEEN 51 PRECEDING AND CURRENT ROW) as flow_52w_avg,
    STDDEV(net_flow) OVER (PARTITION BY ticker ORDER BY week_ending ROWS BETWEEN 51 PRECEDING AND CURRENT ROW) as flow_52w_stddev,
    SUM(net_flow) OVER (PARTITION BY ticker ORDER BY week_ending ROWS BETWEEN 3 PRECEDING AND CURRENT ROW) as flow_4w_sum,
    SUM(net_flow) OVER (PARTITION BY ticker ORDER BY week_ending ROWS BETWEEN 12 PRECEDING AND CURRENT ROW) as flow_13w_sum
FROM etf_flows
ORDER BY ticker, week_ending DESC;
```

### 4.2 Data Retention Policy
- **Intraday data**: 90 days (if collected)
- **Daily OHLCV**: Indefinite (archive to cold storage after 5 years)
- **Weekly flows**: Indefinite
- **Signals**: 2 years active, then archive
- **Alert logs**: 1 year

### 4.3 Data Quality & Validation
- Validate price data: no negative values, close within 5% of prior day (flag outliers)
- Validate flow data: check for missing weeks, outliers >5 standard deviations
- Source data checksums: detect corrupted CSV imports
- Automated daily data quality report

---

## 5. User Interface Requirements

### 5.1 Dashboard Layout

#### 5.1.1 Main Dashboard View
**Components**:
1. **Header Bar**
   - Current date/time
   - Last data update timestamp
   - Active alerts badge
   - User settings icon

2. **Signals Summary Panel** (Top Section)
   - Card grid showing active signals per ticker
   - Signal strength visualization (gauges or progress bars)
   - Color coding: Green (Buy), Red (Sell), Yellow (Watch), Gray (Neutral)
   - Click to drill down into signal details

3. **Ticker Selector**
   - Dropdown or tabs to switch between AGQ, ZSL, etc.
   - Display ticker metadata (leverage, AUM, status)

4. **Main Chart Area** (Central Section)
   - Multi-series line chart with dual Y-axes:
     - **Primary Y-axis**: Price (spot silver, AGQ, futures)
     - **Secondary Y-axis**: Fund flows (bar chart overlay)
   - Time range selector: 1M, 3M, 6M, 1Y, 2Y, All
   - Toggle series visibility (checkboxes or legend clicks)
   - Annotations: Mark signal trigger dates

5. **Analytics Panel** (Right Sidebar or Bottom Section)
   - Current z-scores (4w, 13w, 26w flows)
   - Percentile rankings
   - Correlation coefficients (flow vs. price)
   - Volume analysis (current vs. 20-day avg)
   - Flow attribution classification

6. **Data Table** (Bottom Section, Collapsible)
   - Tabular view of weekly flows with calculated metrics
   - Sortable columns
   - Export to CSV button

#### 5.1.2 Additional Views

**Signals History Page**
- Table of all historical signals with outcomes
- Filter by ticker, date range, signal type
- Performance metrics: win rate, avg return, avg hold time

**Multi-Ticker Comparison View**
- Side-by-side charts for AGQ, GLD, SLV
- Correlation heatmap
- Relative strength indicators

**Settings/Configuration Page**
- Alert preferences
- Signal thresholds
- Ticker watchlist management
- Data source configuration
- API key management (if using paid APIs)

### 5.2 Interactivity Requirements
- Charts must be zoomable and pannable
- Hover tooltips showing exact values
- Clickable signal indicators to view trigger details
- Real-time updates (WebSocket) for price data during market hours
- Responsive design (desktop primary, tablet/mobile secondary)

### 5.3 Accessibility
- WCAG 2.1 AA compliance
- Keyboard navigation support
- Screen reader compatible
- High contrast mode for charts

---

## 6. Integration & API Requirements

### 6.1 External Data APIs

#### 6.1.1 Market Data Sources

**Option 1: Free/Freemium APIs**
- **Alpha Vantage** (Free tier: 5 calls/min, 500 calls/day)
  - Endpoints: TIME_SERIES_DAILY, DIGITAL_CURRENCY_DAILY (crypto as proxy for metals)
  - Limitations: No direct futures data, limited commodity coverage

- **Yahoo Finance (yfinance library)**
  - Tickers: GC=F (gold futures), SI=F (silver futures), PL=F (platinum futures)
  - ETF tickers: AGQ, GLD, SLV, PPLT
  - Free, no API key required
  - Risk: Unofficial API, may break

- **Twelve Data** (Free tier: 800 calls/day)
  - Commodities and ETFs
  - More reliable than Yahoo Finance

**Option 2: Paid APIs (Production)**
- **Polygon.io** (Starter: $199/mo)
  - Stocks, ETFs, futures, options
  - Real-time and historical data

- **IEX Cloud** (Launch: $9/mo, good for testing)
  - Limited commodity coverage

- **CME Group DataMine** (Futures data)
  - Official COMEX data
  - Requires exchange fees

**Recommendation for MVP**:
- Use **yfinance** for initial development
- Migrate to **Polygon.io** or **Twelve Data** for production

#### 6.1.2 ETF Flow Data Sources

**ETFdb.com**
- Method: Web scraping (BeautifulSoup + requests)
- URL pattern: `https://etfdb.com/etf/AGQ/#etf-ticker-flow-of-funds`
- Data: Weekly flows, AUM
- Update frequency: Weekly (Fridays)
- Legal: Check robots.txt and ToS

**ETF.com**
- Method: CSV download (manual) or API if available
- URL: `https://www.etf.com/[ticker]`
- Data: Similar to ETFdb

**Fallback: Manual CSV Upload**
- UI form to upload weekly flow CSVs
- Parser to validate and import data

#### 6.1.3 API Rate Limiting & Caching
- Implement exponential backoff for failed requests
- Cache responses in Redis (TTL: 1 hour for intraday, 24 hours for daily data)
- Queue system (Bull/BullMQ) for scheduled data collection jobs

### 6.2 Internal API Design

#### 6.2.1 RESTful Endpoints

**Base URL**: `/api/v1`

**Price Data**
```
GET /commodities/{symbol}/prices?start_date={date}&end_date={date}&interval={daily|weekly}
GET /etfs/{ticker}/prices?start_date={date}&end_date={date}
GET /futures/{symbol}/prices?contract={YYYY-MM}&start_date={date}
```

**Flow Data**
```
GET /etfs/{ticker}/flows?start_date={date}&end_date={date}
POST /etfs/{ticker}/flows  (manual upload)
```

**Analytics**
```
GET /analytics/flows/{ticker}/statistics?window={4w|13w|26w|52w}
GET /analytics/correlations/{ticker}?start_date={date}
GET /analytics/signals?ticker={ticker}&status={active|all}
```

**Signals**
```
GET /signals?ticker={ticker}&type={type}&status={active|expired}
GET /signals/{id}
POST /signals (manual signal creation)
PUT /signals/{id}/status  (mark as closed)
```

**Alerts**
```
GET /alerts/config
PUT /alerts/config
GET /alerts/history
POST /alerts/test  (send test alert)
```

**Admin**
```
GET /tickers
POST /tickers  (add new ticker)
PUT /tickers/{ticker}  (update metadata)
GET /jobs/status  (data collection job status)
POST /jobs/trigger/{job_name}  (manual job trigger)
```

#### 6.2.2 WebSocket Events

**Channel**: `/ws/updates`

**Event Types**:
```json
{
  "type": "price_update",
  "ticker": "AGQ",
  "price": 42.15,
  "change": -0.35,
  "timestamp": "2025-12-26T14:30:00Z"
}

{
  "type": "new_signal",
  "ticker": "AGQ",
  "signal": {
    "type": "EXTREME_FLOW",
    "direction": "BUY",
    "strength": 0.85
  }
}

{
  "type": "alert",
  "message": "AGQ weekly flow z-score: 2.8 (95th percentile)",
  "severity": "high"
}
```

---

## 7. Non-Functional Requirements

### 7.1 Performance
- Dashboard load time: <2 seconds
- Chart rendering: <500ms for 2 years of daily data
- API response time: <200ms (p95) for analytical queries
- Database query time: <100ms for price data, <500ms for complex analytics

### 7.2 Scalability
- Support up to 50 tickers (extensible beyond silver/gold/platinum)
- Handle 10+ years of historical data per ticker
- Concurrent users: 10-100 (initial scope)

### 7.3 Reliability
- System uptime: 99% (allow for maintenance windows)
- Data collection success rate: >95% (with retry logic)
- Alert delivery: 99.9% (critical alerts)
- Automated backup: Daily database snapshots

### 7.4 Security
- API authentication: JWT tokens
- HTTPS only (TLS 1.3)
- API key encryption at rest
- Rate limiting: 100 req/min per user
- CORS configuration for frontend
- Input validation and sanitization (prevent SQL injection)

### 7.5 Compliance
- GDPR compliance (if storing user data)
- Financial data disclaimer: "Not investment advice"
- Respect data source ToS (attribution, rate limits)

---

## 8. Development Phases

### Phase 1: MVP (Minimum Viable Product) - 6-8 weeks

**Goals**:
- Functional dashboard for AGQ + spot silver + COMEX futures
- Basic flow data collection (manual CSV upload)
- Core analytics: z-scores, rolling sums, correlation
- Simple signal generation (extreme flow alerts)

**Deliverables**:
1. Backend API with endpoints for prices, flows, analytics
2. Database schema and initial seed data
3. Data collectors for yfinance (daily job)
4. Frontend dashboard with charts and signal display
5. Email alerting for extreme z-scores
6. Docker Compose setup for local deployment

**Tech Decisions**:
- **Frontend**: React + TypeScript + Vite + Recharts
- **Backend**: Node.js + TypeScript + Express (or Python + FastAPI)
- **Database**: PostgreSQL + TimescaleDB extension
- **Deployment**: Docker Compose (local) or single VPS (DigitalOcean, Linode)

**Out of Scope for MVP**:
- Options data
- Automated web scraping (manual CSV only)
- WebSocket real-time updates
- Multi-ticker comparison view
- SMS alerts
- Mobile optimization

### Phase 2: Enhanced Analytics - 4-6 weeks

**Goals**:
- Automated ETF flow scraping (ETFdb.com)
- Multi-ticker support (add GLD, SLV, PPLT, ZSL)
- Advanced signals (divergence, momentum alignment)
- Signal backtesting and performance tracking
- WebSocket for real-time price updates

**Deliverables**:
1. Web scraper service (Python + BeautifulSoup or Playwright)
2. Scheduler for weekly flow collection
3. Expanded signal engine with 4 signal types
4. Signals history page with performance metrics
5. Real-time price updates via WebSocket

### Phase 3: Production Hardening - 3-4 weeks

**Goals**:
- Migrate to production-grade APIs (Polygon.io or Twelve Data)
- Add options data (implied vol, put/call ratios)
- Kubernetes deployment
- Monitoring and alerting infrastructure
- User authentication and multi-user support

**Deliverables**:
1. Paid API integration (Polygon.io)
2. Options data tables and charts
3. Kubernetes manifests and Helm charts
4. Prometheus metrics + Grafana dashboards
5. User login and role-based access control (RBAC)

### Phase 4: Advanced Features - Ongoing

**Potential Enhancements**:
- Machine learning signal generation (LSTM, XGBoost)
- Sentiment analysis from news/Twitter
- Automated trading integration (via Alpaca, Interactive Brokers API)
- Mobile app (React Native)
- PDF report generation for weekly summaries
- Multi-language support

---

## 9. Success Metrics

### 9.1 Technical Metrics
- **Data Collection Uptime**: >95% successful weekly flow imports
- **API Availability**: >99% uptime
- **Query Performance**: p95 response time <200ms

### 9.2 User Metrics
- **Dashboard Engagement**: Daily active users, session duration
- **Signal Accuracy**: Backtested win rate >55% (for actionable signals)
- **Alert Relevance**: Low false positive rate (<10% of alerts ignored)

### 9.3 Business Metrics (if applicable)
- **Trading Performance**: Simulated portfolio returns vs. buy-and-hold
- **User Retention**: Month-over-month active user growth
- **Cost Efficiency**: Data API costs <$X per month

---

## 10. Risk Assessment & Mitigation

### 10.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Data source API shutdown (yfinance) | High | Medium | Maintain fallback APIs, consider paid options |
| ETFdb.com blocks scraper | High | Medium | Implement polite scraping, manual CSV fallback |
| Database performance degradation | Medium | Low | Regular indexing, query optimization, TimescaleDB compression |
| Third-party API rate limits | Medium | Medium | Implement caching, request queuing, monitor usage |

### 10.2 Data Quality Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Missing weekly flow data | High | Automated alerts on missing data, manual upload UI |
| Incorrect/delayed price data | High | Validate against multiple sources, flag outliers |
| Signal false positives | Medium | Backtesting, confidence scoring, user feedback loop |

### 10.3 Operational Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Missed weekly data collection window | Medium | Retry logic, manual trigger, email notifications |
| Server downtime during market hours | Low | Deploy on reliable hosting, monitoring, auto-restart |
| Cost overruns from API usage | Medium | Set budget alerts, monitor API call counts |

---

## 11. Open Questions & Decisions Needed

### 11.1 Architecture Decisions
- [ ] **Backend Language**: Node.js/TypeScript vs. Python/FastAPI?
  - **Recommendation**: Python for easier data science libraries (pandas, numpy)

- [ ] **Chart Library**: TradingView Lightweight Charts (professional) vs. Recharts (easier)?
  - **Recommendation**: Recharts for MVP, migrate to TradingView if needed

- [ ] **Deployment**: Docker Compose on single server vs. Kubernetes?
  - **Recommendation**: Docker Compose for MVP, K8s for Phase 3

### 11.2 Data Decisions
- [ ] **Options Data Priority**: Include in Phase 1 or defer to Phase 2?
  - **Recommendation**: Defer to Phase 2 (complexity vs. value for MVP)

- [ ] **Intraday Data**: Collect tick/minute data or daily only?
  - **Recommendation**: Daily for MVP, add intraday in Phase 2 if needed

- [ ] **Historical Data Depth**: How many years to backload?
  - **Recommendation**: Minimum 2 years for z-score calculation, ideally 5 years

### 11.3 Feature Prioritization
- [ ] **Backtesting**: Build custom backtester or integrate existing library (e.g., Backtrader)?
- [ ] **Alert Channels**: Email only for MVP, or include Slack/Telegram?
  - **Recommendation**: Email + webhook (Slack) for MVP

- [ ] **User Management**: Single user (private tool) or multi-user from start?
  - **Recommendation**: Single user for MVP, add auth in Phase 3

### 11.4 Budget Considerations
- [ ] **API Costs**: Allocated budget for paid APIs (Polygon.io $199/mo)?
- [ ] **Hosting Costs**: VPS budget ($20-50/mo for MVP, $200+/mo for K8s cluster)?
- [ ] **Development Time**: Solo developer or team? Expected timeline flexibility?

---

## 12. Next Steps

### 12.1 Immediate Actions
1. **Validate requirements** with stakeholders/users
2. **Finalize technology stack** (backend language, database, deployment)
3. **Set up development environment**:
   - GitHub repository
   - Project management tool (GitHub Projects, Linear, Jira)
   - CI/CD pipeline
4. **Create initial project structure**:
   - Mono-repo vs. separate repos for frontend/backend
   - Folder structure, linting, formatting configs
5. **Acquire data sources**:
   - Sign up for Alpha Vantage/Twelve Data/Polygon.io
   - Test API access for AGQ, GC=F, SI=F
   - Download sample ETF flow CSV from ETFdb.com

### 12.2 Phase 1 Sprint Planning
**Sprint 1 (Week 1-2)**: Foundation
- Set up database schema
- Create seed data loader (historical AGQ + silver prices)
- Build basic API endpoints (GET /etfs/AGQ/prices, GET /commodities/XAG/prices)

**Sprint 2 (Week 3-4)**: Data Collection
- Implement yfinance collectors
- Schedule daily jobs (cron)
- Build manual CSV upload endpoint for flows

**Sprint 3 (Week 5-6)**: Analytics Engine
- Implement z-score calculation
- Build correlation analysis
- Create signal generation logic (extreme flow)

**Sprint 4 (Week 7-8)**: Frontend & Integration
- Build React dashboard
- Integrate charts (Recharts)
- Connect to backend APIs
- Implement email alerting
- End-to-end testing

---

## Appendix A: Sample Data Structures

### A.1 ETF Flow CSV Format (ETFdb.com)
```csv
Date,Net Flow ($ Mil),AUM ($ Mil),Shares Outstanding,Premium/Discount (%)
2025-12-20,15.3,245.7,12500000,0.12
2025-12-13,-8.2,230.4,11800000,-0.05
2025-12-06,22.1,238.6,12100000,0.18
```

### A.2 Signal JSON Schema
```json
{
  "id": 1234,
  "ticker": "AGQ",
  "signal_type": "EXTREME_FLOW",
  "direction": "BUY",
  "strength": 0.87,
  "generated_at": "2025-12-26T10:00:00Z",
  "expires_at": "2026-01-26T10:00:00Z",
  "trigger_values": {
    "z_score_4w": 2.8,
    "percentile": 95.2,
    "net_flow": 22.1,
    "price_change_pct": 5.3,
    "correlation_flow_price": 0.72
  },
  "status": "ACTIVE"
}
```

### A.3 Alert Email Template
```
Subject: [COMMODITY ALERT] AGQ - Extreme Inflow Detected

AGQ (ProShares Ultra Silver 2x) - BUY Signal

Signal Strength: ★★★★☆ (4/5)
Generated: Dec 26, 2025 10:00 AM ET

Key Metrics:
• Weekly Net Flow: $22.1M (95th percentile)
• 4-Week Z-Score: 2.8 (extreme)
• Flow-Price Correlation: 0.72 (strong)
• AGQ Price: $42.15 (+5.3% this week)
• Spot Silver: $30.85/oz (+4.2% this week)

Interpretation:
Strong institutional inflow into AGQ coinciding with silver price rally suggests flow-driven momentum. Historical patterns indicate continuation probability of 68% over next 2-4 weeks.

View Dashboard: [link]

---
Disclaimer: This is an automated alert for informational purposes only. Not financial advice.
```

---

## Appendix B: Glossary

- **AGQ**: ProShares Ultra Silver ETF (2x leveraged long silver)
- **AUM**: Assets Under Management
- **COMEX**: Commodity Exchange (division of CME for metals futures)
- **ETF**: Exchange-Traded Fund
- **Front-Month**: Nearest futures contract expiration
- **NAV**: Net Asset Value
- **OHLCV**: Open, High, Low, Close, Volume
- **OI**: Open Interest (futures contracts outstanding)
- **Z-Score**: Statistical measure of how many standard deviations a value is from the mean
- **Contango**: Futures price > spot price
- **Backwardation**: Futures price < spot price

---

**Document Version**: 1.0
**Last Updated**: December 26, 2025
**Status**: Draft for Review
