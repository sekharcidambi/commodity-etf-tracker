# Commodity ETF Tracker - Project Status

**Last Updated**: December 26, 2024

## Project Overview

**Completely separate from patient-discharge project**

This is a standalone commodity trading system for tracking gold, silver, and platinum ETFs with automated flow data collection and buy/sell signal generation.

## Repository Structure

```
commodity-etf-tracker/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── api/               # REST API endpoints
│   │   │   ├── analytics.py   # Analytics endpoints
│   │   │   ├── data_collection.py  # Data collection triggers
│   │   │   ├── flows.py       # ETF flow data endpoints
│   │   │   ├── prices.py      # Price data endpoints
│   │   │   ├── signals.py     # Trading signals endpoints
│   │   │   └── tickers.py     # Ticker management
│   │   ├── core/              # Configuration & settings
│   │   ├── db/                # Database connection
│   │   ├── models/            # SQLAlchemy models
│   │   │   ├── flow.py        # ETFFlow, InstitutionalHolding
│   │   │   ├── price.py       # ETFPrice, CommodityPrice
│   │   │   └── ticker.py      # Ticker metadata
│   │   ├── services/          # Business logic
│   │   │   ├── data_collector.py     # Orchestrates data collection
│   │   │   ├── data_storage.py       # Database operations
│   │   │   ├── etfdb_scraper.py      # ETFdb.com web scraper
│   │   │   ├── flow_collector.py     # Flow data orchestration
│   │   │   ├── sec_scraper.py        # SEC 13F filings scraper
│   │   │   └── yfinance_collector.py # Yahoo Finance API
│   │   └── utils/             # Utility functions
│   └── scripts/               # Test & utility scripts
├── database/                  # SQL schema & migrations
├── frontend/                  # React + TypeScript + Vite
├── docker-compose.yml         # PostgreSQL + TimescaleDB + Redis
└── REQUIREMENTS.md            # Comprehensive system requirements
```

## Technology Stack

### Backend
- **Framework**: FastAPI (async Python)
- **Database**: PostgreSQL 15 + TimescaleDB
- **ORM**: SQLAlchemy 2.0 (async)
- **Data Sources**:
  - Yahoo Finance (yfinance) - Price data
  - ETFdb.com (web scraping) - Flow data
  - SEC EDGAR API - 13F institutional holdings
- **Caching**: Redis
- **HTTP Client**: httpx (async)
- **HTML Parsing**: BeautifulSoup4

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **UI**: Tailwind CSS + shadcn/ui
- **Charts**: Recharts

### Database Schema
- **TimescaleDB Hypertables**:
  - `etf_prices` - Daily ETF price data
  - `commodity_prices` - Futures price data
  - `etf_flows` - Weekly ETF flow data
  - `intraday_bars` - Intraday price data
- **PostgreSQL Tables**:
  - `tickers` - ETF metadata
  - `institutional_holdings` - 13F filings
  - `investor_segment_flows` - Segment attribution
  - `signals` - Trading signals
  - `alert_log` - Signal alerts

## Primary Tickers

- **AGQ** - ProShares Ultra Silver 2x
- **UGL** - ProShares Ultra Gold 2x
- **ZSL** - ProShares UltraShort Silver 2x
- **GLD** - SPDR Gold Trust
- **SLV** - iShares Silver Trust
- **PPLT** - Aberdeen Standard Physical Platinum Shares

## Features Implemented

### ✅ Phase 1: Data Collection (COMPLETE)

1. **Price Data Collection**
   - Yahoo Finance integration for ETF prices
   - Futures data (GC=F gold, SI=F silver, PL=F platinum)
   - Historical backfill capability
   - Async batch collection
   - PostgreSQL upsert for idempotency

2. **Flow Data Collection** (NEW - Automated)
   - ETFdb.com web scraper for AUM, volume, expense ratio
   - SEC EDGAR 13F scraper for institutional holdings
   - Tracks 10 major institutions (Blackrock, Vanguard, etc.)
   - Flow data storage with upsert
   - Institutional holdings tracking

3. **API Endpoints**
   - `POST /data/collect/daily` - Trigger price collection
   - `POST /data/backfill` - Historical data backfill
   - `GET /prices/etf/{ticker}` - Query price data
   - `POST /flows/collect/etfdb` - Scrape ETFdb.com
   - `POST /flows/collect/institutional/{ticker}` - Collect 13F data
   - `POST /flows/collect/all` - Full flow collection
   - `GET /flows/{ticker}` - Query flow data
   - `GET /flows/institutional/{ticker}` - Query holdings

4. **Test Scripts**
   - `scripts/test_collection.py` - Price data collection tests
   - `scripts/test_flow_collection.py` - Flow scraper tests

### 🚧 Phase 2: Analytics & Signals (TODO)

1. **Flow Analytics**
   - Z-score calculation for flow extremes
   - Rolling sums (4w, 13w, 26w, 52w)
   - Percentile rankings
   - Correlation analysis (flow vs price)

2. **Trading Signals** (7 types planned)
   - Flow Extreme Signals
   - Flow Reversal Signals
   - Institutional Accumulation Signals
   - Korean Retail Flow Signals
   - Flow-Price Divergence Signals
   - Multi-ETF Correlation Signals
   - Composite Sentiment Signals

3. **Signal Generation Engine**
   - Automated signal detection
   - Confidence scoring
   - Alert system
   - Historical backtesting

### 🚧 Phase 3: Dashboard & Visualization (TODO)

1. **Dashboard Features**
   - Real-time price charts
   - Flow visualization
   - Signal display with confidence scores
   - Institutional holdings breakdown
   - Segment attribution (Korean retail, US retail, institutional)

2. **Interactive Charts**
   - Multi-timeframe support
   - Technical indicators overlay
   - Flow vs price correlation plots
   - Signal timeline

### 🚧 Phase 4: Advanced Features (TODO)

1. **Near Real-Time Data**
   - Intraday price updates
   - Options flow integration
   - Social sentiment analysis
   - News event tracking

2. **Scheduling**
   - APScheduler for automated jobs
   - Daily price collection (market close)
   - Weekly flow updates (Friday)
   - Quarterly 13F filings

## Git Status

- **Branch**: `claude/commodity-dashboard-signals-q2G91`
- **Latest Commit**: `106983a` - Implement automated flow data collection system
- **Total Commits**: 4
- **Remote**: Not configured (local repository only)

### Recent Commits
```
106983a Implement automated flow data collection system
a5fae67 Implement data collection system with yfinance
e95eb32 Add complete project structure and foundation
7cd429c Initial commit: Commodity ETF Tracker project setup
```

## Separation from Patient-Discharge

This project is **completely independent** from the patient-discharge healthcare application:

- ✅ Separate directory: `/home/user/commodity-etf-tracker/`
- ✅ Separate git repository and history
- ✅ Different technology focus (financial vs healthcare)
- ✅ Different database schema (commodities vs patient records)
- ✅ Different API modules (trading vs patient management)
- ✅ No shared code or dependencies
- ✅ Commodity requirements removed from patient-discharge

## Next Steps

1. **Set up GitHub Repository**
   - Create remote repository
   - Configure git remote origin
   - Push to GitHub

2. **Launch Development Environment**
   - `docker-compose up -d` to start PostgreSQL/TimescaleDB
   - Run database migrations
   - Test data collection scripts

3. **Build Analytics Engine**
   - Implement z-score calculations
   - Build correlation analysis
   - Create signal generation logic

4. **Develop Dashboard**
   - Build React components
   - Integrate charts
   - Connect to API endpoints

## Running the Application

```bash
# Start infrastructure
cd /home/user/commodity-etf-tracker
docker-compose up -d

# Run backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Test data collection
python scripts/test_collection.py
python scripts/test_flow_collection.py

# Access API docs
open http://localhost:8000/docs
```

## Documentation

- `REQUIREMENTS.md` - Comprehensive system requirements (58KB)
- `QUICKSTART.md` - Quick start guide
- `README.md` - Project overview
- `PROJECT_STATUS.md` - This file

---

**This is a standalone project for commodity ETF trading analysis, completely separate from patient-discharge.**
