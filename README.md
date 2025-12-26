# Commodity ETF Tracker

A comprehensive commodity trading intelligence platform that tracks precious metals (gold, silver, platinum) and leveraged ETF products, providing actionable buy/sell signals based on fund flows, price movements, and futures market activity.

## Overview

This system combines strategic weekly flow data with near real-time market microstructure, options activity, and macroeconomic indicators for multi-timeframe trading signals.

### Primary Focus Tickers
- **AGQ** (ProShares Ultra Silver - 2x leveraged long)
- **UGL** (ProShares Ultra Gold - 2x leveraged long)

### Key Features

- **Multi-Source Data Collection**
  - Weekly ETF flows (ETFdb.com, ETF.com)
  - Real-time price data (stocks, futures, options)
  - Institutional holdings (13F filings)
  - Korean retail flow tracking (ETFGI, KSD)
  - Futures & options market data
  - Social sentiment analysis
  - Macroeconomic indicators

- **Investor Segment Attribution**
  - South Korean retail investors
  - US retail investors
  - Hedge funds & institutional investors
  - Sovereign wealth funds

- **Advanced Analytics**
  - Z-score analysis of fund flows
  - Correlation analysis (flow vs. price)
  - Options flow analysis
  - COT (Commitment of Traders) reports
  - Premium/Discount to NAV tracking

- **Trading Signals**
  - Extreme Flow Signal
  - Flow-Price Divergence
  - Futures-Spot Basis Signal
  - Momentum Alignment
  - Smart Money Divergence (segment-based)
  - Korean Retail Euphoria Indicator
  - Institutional Accumulation

- **Real-Time Capabilities**
  - Intraday 1-minute bars
  - WebSocket streaming (Phase 2+)
  - Volume spike detection
  - Asian hours volume analysis (Korean retail proxy)
  - Options unusual activity alerts
  - News event monitoring

## Documentation

- [Requirements Document](./REQUIREMENTS.md) - Complete system requirements and specifications

## Technology Stack (Planned)

### Backend
- **Runtime**: Python (FastAPI) or Node.js (TypeScript)
- **Database**: PostgreSQL + TimescaleDB (time-series)
- **Cache**: Redis
- **Task Scheduler**: APScheduler (Python) or node-cron

### Frontend
- **Framework**: React + TypeScript
- **Charting**: TradingView Lightweight Charts or Recharts
- **State Management**: React Query + Zustand
- **UI Components**: shadcn/ui

### Data Sources
- **Free Tier**: Twelve Data, FRED API, yfinance, Reddit/Twitter
- **Paid Tier**: Polygon.io ($199-399/mo), Unusual Whales ($200/mo), Benzinga ($300/mo)

### Infrastructure
- **Container**: Docker + Docker Compose
- **Deployment**: Kubernetes (production) or VPS (MVP)
- **Monitoring**: Prometheus + Grafana

## Development Phases

### Phase 1: MVP (6-8 weeks)
- Basic dashboard for AGQ/UGL + spot commodities + futures
- Manual CSV upload for flow data
- Core analytics (z-scores, rolling sums, correlation)
- Simple extreme flow alerts
- Email notifications

### Phase 2: Enhanced Analytics (4-6 weeks)
- Automated ETF flow scraping
- Multi-ticker support (GLD, SLV, PPLT, ZSL)
- Advanced signals (divergence, momentum, segment-based)
- WebSocket real-time updates
- Signal backtesting

### Phase 3: Production Hardening (3-4 weeks)
- Production APIs (Polygon.io Advanced)
- Options data integration
- Kubernetes deployment
- Monitoring infrastructure
- User authentication

### Phase 4: Advanced Features
- Machine learning signals
- Sentiment analysis automation
- Automated trading integration
- Mobile app

## Getting Started

(Coming soon - project setup instructions)

## License

(To be determined)

## Disclaimer

This software is for informational purposes only and does not constitute financial advice. Trading leveraged ETFs involves significant risk. Past performance does not guarantee future results.
