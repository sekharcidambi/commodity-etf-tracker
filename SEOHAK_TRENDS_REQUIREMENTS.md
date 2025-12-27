# Seohak Trends App - Requirements Specification

## Executive Summary
Real-time tracking dashboard for Korean retail investor ("Seohak ants"/서학개미) activity in US markets, enabling users to make informed daily trading decisions.

## Project Goals
- **Primary**: Provide near-real-time (< 15 min delay) Korean retail investor sentiment and trading data
- **Secondary**: Translate Korean sources to English for global accessibility
- **Tertiary**: Enable actionable insights for daily trading decisions

---

## 1. Data Sources & Requirements

### 1.1 Primary Data Sources (Official)

#### Korea Securities Depository (KSD) / 한국예탁결제원
- **URL**: https://www.ksd.or.kr
- **Data Available**: Daily/weekly net buy/sell rankings for US stocks
- **Update Frequency**: Daily (weekdays), typically published next business day ~9AM KST
- **Lag**: 1 business day
- **Key Metrics**:
  - Top 10 net buy stocks
  - Top 10 net sell stocks
  - Trading volumes (USD)
  - Number of Korean accounts trading
- **Access Method**: Web scraping or API if available
- **Translation Needed**: Yes (Korean → English)

#### Naver Finance / 네이버 파이낸스
- **URL**: https://finance.naver.com
- **Search Query**: "서학개미 순매수"
- **Data Available**: Real-time to hourly updates on top net buys
- **Update Frequency**: Hourly during market hours
- **Lag**: 1-4 hours
- **Key Metrics**:
  - Current top net buy stocks
  - Intraday trading trends
  - Price movements
- **Access Method**: Web scraping (may require handling dynamic content)
- **Translation Needed**: Yes

### 1.2 Secondary Data Sources

#### YouTube Channels
- **Channels**:
  - 서학개미TV
  - @us.stock.investor
  - Other finance channels
- **Data Available**: Daily TOP 10 videos with KSD data
- **Update Frequency**: Daily (morning KST)
- **Use Case**: Validation and supplementary data
- **Access Method**: YouTube Data API v3
- **Translation Needed**: Yes (video titles, descriptions)

#### Korean News Aggregators
- **Sources**:
  - Chosun Ilbo (조선일보)
  - Korea Herald
  - Investing.com Korea
  - FnGuide
- **Search Query**: "서학개미 순매수", "서학개미 투자"
- **Data Available**: News articles, analysis, trends
- **Update Frequency**: Multiple times daily
- **Use Case**: Sentiment analysis and context
- **Access Method**: RSS feeds or web scraping
- **Translation Needed**: Yes

### 1.3 Augmented Data Sources (for Real-Time Enhancement)

#### US Market Data (Alpha Vantage, Finnhub, or Yahoo Finance)
- **Purpose**: Real-time price data for stocks popular with Korean investors
- **Update Frequency**: Real-time (15-second to 1-minute intervals)
- **Key Metrics**:
  - Current price
  - Volume
  - Percent change
  - Market cap
- **Access Method**: REST APIs
- **Cost**: Free tier available

#### Social Media Sentiment (Twitter/X API)
- **Search Queries**:
  - "#서학개미"
  - "Seohak ants"
  - Popular stock tickers + Korean keywords
- **Purpose**: Real-time sentiment analysis
- **Update Frequency**: Real-time
- **Access Method**: Twitter API v2
- **Translation Needed**: Yes (Korean tweets)

#### Korean Online Communities
- **Sources**:
  - r/hanguk (Reddit)
  - Korean stock forums (DCInside 주식갤러리)
  - Naver Cafe stock communities
- **Purpose**: Grassroots sentiment and trending discussions
- **Update Frequency**: Real-time
- **Access Method**: Web scraping (with rate limiting)
- **Translation Needed**: Yes

#### Currency Exchange Rates (KRW/USD)
- **Purpose**: Context for Korean buying power
- **Source**: Bank of Korea or forex APIs
- **Update Frequency**: Real-time
- **Access Method**: REST API

---

## 2. Technical Architecture

### 2.1 Frontend (React Web App)

#### Framework & Libraries
- **Core**: React 18+ with TypeScript
- **Styling**: Tailwind CSS + shadcn/ui components
- **Charts**: Recharts or Chart.js for visualizations
- **State Management**: React Query for server state, Zustand for client state
- **Internationalization**: i18next (English primary, Korean optional)
- **Real-time Updates**: WebSocket connection or polling (every 5-15 min)

#### Pages/Routes
1. **Dashboard** (`/`) - Main real-time overview
2. **Stock Detail** (`/stock/:ticker`) - Individual stock trends
3. **Historical Trends** (`/history`) - Time-series analysis
4. **Sentiment Analysis** (`/sentiment`) - Social media trends
5. **About/Methodology** (`/about`) - Data sources and methodology

### 2.2 Backend (API Layer)

#### Framework Options
- **Option A**: Next.js API Routes (serverless on Vercel)
- **Option B**: Express.js + Node.js (containerized)
- **Recommendation**: Next.js for seamless Vercel deployment

#### API Endpoints
```
GET  /api/stocks/trending          - Current top 10 net buys
GET  /api/stocks/selling           - Current top 10 net sells
GET  /api/stocks/:ticker           - Individual stock details
GET  /api/stocks/:ticker/history   - Historical trends
GET  /api/sentiment/overview       - Aggregated sentiment
GET  /api/news                     - Latest translated news
GET  /api/health                   - System health check
```

### 2.3 Data Pipeline

#### Data Collection (Scheduled Jobs)
- **Cron Jobs** (using Vercel Cron or external scheduler):
  - KSD scraper: Daily at 9:30 AM KST
  - Naver Finance scraper: Every 15-30 minutes during market hours (9:30 AM - 4 PM ET)
  - News aggregator: Every 1 hour
  - YouTube API: Daily at 10 AM KST
  - Social media: Every 5-15 minutes

#### Data Processing Pipeline
1. **Scraping Layer**: Puppeteer or Cheerio for web scraping
2. **Translation Layer**: Google Translate API or DeepL API
3. **Normalization Layer**: Standardize data formats
4. **Storage Layer**: Database persistence
5. **Caching Layer**: Redis for real-time data

### 2.4 Database

#### Options
- **Option A**: PostgreSQL (Vercel Postgres or Supabase)
- **Option B**: MongoDB (MongoDB Atlas)
- **Recommendation**: PostgreSQL for structured time-series data

#### Schema (Simplified)
```sql
-- Stocks table
stocks (
  ticker VARCHAR PRIMARY KEY,
  name VARCHAR,
  name_kr VARCHAR,
  sector VARCHAR,
  last_updated TIMESTAMP
)

-- Daily trends
daily_trends (
  id SERIAL PRIMARY KEY,
  ticker VARCHAR REFERENCES stocks(ticker),
  date DATE,
  net_buy_volume_usd DECIMAL,
  net_buy_accounts INTEGER,
  rank INTEGER,
  price_usd DECIMAL,
  price_change_pct DECIMAL,
  source VARCHAR
)

-- Intraday updates
intraday_trends (
  id SERIAL PRIMARY KEY,
  ticker VARCHAR REFERENCES stocks(ticker),
  timestamp TIMESTAMP,
  current_volume_usd DECIMAL,
  current_rank INTEGER,
  sentiment_score DECIMAL,
  source VARCHAR
)

-- News articles
news (
  id SERIAL PRIMARY KEY,
  title VARCHAR,
  title_en VARCHAR,
  content TEXT,
  content_en TEXT,
  source VARCHAR,
  published_at TIMESTAMP,
  url VARCHAR
)

-- Sentiment data
sentiment (
  id SERIAL PRIMARY KEY,
  ticker VARCHAR REFERENCES stocks(ticker),
  timestamp TIMESTAMP,
  platform VARCHAR,
  sentiment_score DECIMAL,
  mention_count INTEGER
)
```

### 2.5 Caching Strategy
- **Redis** or Vercel KV for:
  - API response caching (5-15 min TTL)
  - Rate limiting
  - Session management
- **CDN**: Vercel Edge Network for static assets

---

## 3. Core Features & Functionality

### 3.1 Real-Time Dashboard

#### Hero Section
- **Live Market Status**: US market open/closed indicator with countdown
- **Last Updated**: Timestamp showing data freshness
- **KRW/USD Rate**: Current exchange rate with trend indicator

#### Top Net Buys Widget
- **Display**: Top 10 stocks with real-time updates
- **Columns**:
  1. Rank (#1-10)
  2. Ticker symbol (clickable)
  3. Company name (English)
  4. Net buy volume (USD)
  5. Current price + % change (color-coded)
  6. Trend indicator (↑↓→ compared to previous period)
  7. Sentiment score (optional)
- **Refresh**: Auto-refresh every 5-15 minutes
- **Visual**: Progress bars for volume comparison

#### Top Net Sells Widget
- Similar to Top Net Buys but for selling activity

#### Trending Stocks Chart
- **Type**: Time-series line chart
- **Data**: Top 5 stocks' net buy volumes over 7 days
- **Interaction**: Hover tooltips, clickable legends

#### Sentiment Heatmap
- **Visual**: Grid showing sentiment across sectors
- **Color Scale**: Red (bearish) → Yellow (neutral) → Green (bullish)
- **Data Source**: Social media + news aggregation

#### News Feed
- **Display**: Latest 5-10 translated news articles
- **Format**: Title, source, timestamp, excerpt
- **Link**: External link to original article

### 3.2 Stock Detail Page

#### Stock Header
- Ticker, company name, current price, % change
- Korean investor rank (e.g., "#3 Most Bought Today")

#### Historical Net Buy/Sell Chart
- **Timeframes**: 1D, 1W, 1M, 3M, 1Y
- **Chart Type**: Candlestick or area chart
- **Overlay**: Volume bars

#### Korean Investor Metrics
- Total net position (USD)
- Number of Korean accounts holding
- Average position size
- Historical rank trends

#### Sentiment Timeline
- Social media mentions over time
- News sentiment analysis
- Community discussion trends

#### Related News & Analysis
- Filtered news for this specific ticker
- Translated articles

### 3.3 Historical Trends Page

#### Top Stocks Over Time
- **Table/Chart**: Historical top 10 rankings
- **Filters**: Date range, sector, market cap
- **Export**: CSV download option

#### Trend Analysis
- Stocks gaining/losing Korean investor interest
- Sector rotation analysis
- Correlation with market events

### 3.4 Sentiment Analysis Page

#### Social Media Trends
- Trending hashtags and keywords
- Top mentioned stocks
- Sentiment distribution (positive/neutral/negative)

#### Community Insights
- Popular discussions from Korean forums
- Translated and summarized

#### News Sentiment
- Aggregated news sentiment by stock/sector
- Sentiment trend over time

---

## 4. Translation & Localization

### 4.1 Translation Requirements

#### Automated Translation
- **Service**: Google Cloud Translation API or DeepL API
- **Content to Translate**:
  - Stock names (Korean → English)
  - News headlines and articles
  - Social media posts
  - YouTube video titles/descriptions
  - Forum discussions

#### Translation Quality
- **Caching**: Store translations to avoid redundant API calls
- **Validation**: Basic quality checks for critical content
- **Fallback**: Display original Korean with translation if available

### 4.2 UI Localization
- **Primary Language**: English
- **Optional**: Korean toggle for bilingual users
- **Date/Time**: Display in both KST and user's local timezone
- **Currency**: Display in USD (primary) with KRW equivalent

---

## 5. Real-Time Update Strategy

### 5.1 Update Frequencies

| Data Type | Update Frequency | Method |
|-----------|-----------------|--------|
| KSD Official Data | Daily ~9:30 AM KST | Scheduled scraper |
| Naver Finance | Every 15-30 min (market hours) | Scheduled scraper |
| US Stock Prices | Every 1-5 min | Real-time API |
| Social Media | Every 5-15 min | Streaming API / polling |
| News Articles | Every 30-60 min | RSS feed / scraper |
| Currency Rates | Every 15 min | Real-time API |

### 5.2 Frontend Update Mechanism
- **WebSocket** (preferred): Server pushes updates to connected clients
- **Polling** (fallback): Client polls API every 15-30 seconds
- **Optimistic Updates**: Show loading states during refresh
- **Error Handling**: Graceful degradation if data source fails

### 5.3 Data Freshness Indicators
- **Color-coded timestamps**:
  - Green: < 5 min old
  - Yellow: 5-30 min old
  - Orange: 30-60 min old
  - Red: > 1 hour old
- **Auto-refresh indicator**: Visual spinner or pulse animation
- **Manual refresh button**: User-triggered update

---

## 6. Performance Requirements

### 6.1 Response Times
- **Page Load**: < 2 seconds (initial load)
- **API Responses**: < 500ms (cached), < 2s (uncached)
- **Data Refresh**: < 1 second (UI update)
- **Chart Rendering**: < 1 second

### 6.2 Scalability
- **Concurrent Users**: Support 1,000+ simultaneous users
- **Database**: Optimize queries with indexing
- **Caching**: Aggressive caching for read-heavy operations
- **CDN**: Static asset delivery via Vercel Edge

### 6.3 Reliability
- **Uptime**: 99.5% target
- **Error Handling**: Graceful fallbacks for failed data sources
- **Monitoring**: Error tracking (Sentry) and analytics (Vercel Analytics)
- **Rate Limiting**: Prevent API abuse

---

## 7. Deployment & Infrastructure

### 7.1 Hosting
- **Platform**: Vercel (primary choice)
- **Deployment**: Automatic deployment from Git (main branch)
- **Environments**:
  - Production: https://seohak-trends.vercel.app
  - Staging: https://seohak-trends-staging.vercel.app

### 7.2 Environment Variables
```
# Database
DATABASE_URL=postgresql://...

# APIs
GOOGLE_TRANSLATE_API_KEY=...
ALPHA_VANTAGE_API_KEY=...
TWITTER_API_KEY=...
YOUTUBE_API_KEY=...

# Redis/KV
REDIS_URL=...

# External Services
SENTRY_DSN=...
```

### 7.3 CI/CD Pipeline
- **Version Control**: Git (GitHub)
- **CI**: GitHub Actions for testing
- **CD**: Vercel automatic deployments
- **Testing**: Jest + React Testing Library
- **Linting**: ESLint + Prettier

### 7.4 Scheduled Jobs
- **Vercel Cron**: For scheduled data collection
- **Alternative**: External cron service (cron-job.org) if Vercel limits exceeded

---

## 8. Security & Compliance

### 8.1 Data Security
- **API Keys**: Stored in environment variables (never in code)
- **Rate Limiting**: Prevent abuse and protect APIs
- **CORS**: Restrict to approved domains
- **HTTPS**: Enforce SSL/TLS

### 8.2 Scraping Ethics
- **Robots.txt**: Respect robots.txt directives
- **Rate Limiting**: Reasonable delays between requests
- **User-Agent**: Identify scraper appropriately
- **Terms of Service**: Comply with source site ToS

### 8.3 Data Privacy
- **No PII**: Do not collect personal user data
- **Analytics**: Anonymous usage tracking only
- **Cookies**: Minimal cookie usage (preferences only)

---

## 9. Success Metrics

### 9.1 Data Quality KPIs
- **Data Freshness**: Average age of displayed data < 30 min during market hours
- **Data Accuracy**: 95%+ match with official KSD data
- **Translation Quality**: Manual review of sample translations
- **Uptime**: Data pipeline uptime > 98%

### 9.2 User Engagement KPIs
- **Daily Active Users** (DAU)
- **Average Session Duration** > 3 minutes
- **Bounce Rate** < 50%
- **Return User Rate** > 30%

### 9.3 Technical KPIs
- **API Response Time** (p95) < 1 second
- **Page Load Time** (p95) < 3 seconds
- **Error Rate** < 1%

---

## 10. Development Phases

### Phase 1: MVP (Weeks 1-2)
- [ ] Set up Next.js + React project
- [ ] KSD scraper for daily top 10
- [ ] Basic dashboard with top net buys
- [ ] PostgreSQL schema and setup
- [ ] Google Translate integration
- [ ] Deploy to Vercel

### Phase 2: Real-Time Enhancement (Weeks 3-4)
- [ ] Naver Finance scraper (hourly updates)
- [ ] US stock price integration (Alpha Vantage)
- [ ] Auto-refresh mechanism (WebSocket or polling)
- [ ] Stock detail pages
- [ ] Historical trends page
- [ ] Redis caching

### Phase 3: Sentiment & News (Weeks 5-6)
- [ ] News aggregator (Korean sources)
- [ ] YouTube API integration
- [ ] Social media sentiment (Twitter)
- [ ] Sentiment analysis page
- [ ] News feed on dashboard

### Phase 4: Polish & Optimization (Weeks 7-8)
- [ ] Performance optimization
- [ ] UI/UX refinements
- [ ] Mobile responsiveness
- [ ] Error monitoring (Sentry)
- [ ] Analytics integration
- [ ] Documentation

---

## 11. Open Questions / Decisions Needed

1. **Translation Service**: Google Translate (cheaper) vs DeepL (better quality)?
2. **Database**: Vercel Postgres vs Supabase vs self-hosted?
3. **Real-time**: WebSocket vs polling? (WebSocket better but more complex on Vercel)
4. **Social Media**: Twitter API paid tier needed for volume?
5. **Scraping**: Use Puppeteer (heavier) or Cheerio (lighter)?
6. **Charts Library**: Recharts vs Chart.js vs D3.js?
7. **Authentication**: Public app or require login? (Suggest public for MVP)
8. **Monetization**: Free or freemium model? (Suggest free for MVP)

---

## 12. Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data source blocks scraper | High | Multiple fallback sources, user-agent rotation, rate limiting |
| Translation API costs exceed budget | Medium | Cache translations, rate limit requests, use cheaper tier |
| Korean market holidays (no data) | Low | Display historical data, show market status |
| Vercel serverless timeout (10s limit) | Medium | Split long-running tasks, use external cron for scraping |
| Exchange rate volatility affects calculations | Low | Display both USD and KRW, update rates frequently |

---

## 13. Future Enhancements (Post-MVP)

- **Alerts**: Email/push notifications for specific stocks or thresholds
- **Portfolio Tracking**: Users can track their own holdings against Korean trends
- **Predictive Analytics**: ML model to predict Korean buying patterns
- **Mobile App**: React Native version
- **API Access**: Public API for developers
- **Premium Features**: Advanced analytics, historical data export, etc.
- **Community Features**: User comments, voting on predictions
- **Broker Integration**: Direct trading links

---

## Appendix A: Tech Stack Summary

### Frontend
- React 18+
- TypeScript
- Next.js 14+ (App Router)
- Tailwind CSS
- shadcn/ui
- Recharts
- React Query
- Zustand

### Backend
- Next.js API Routes
- Node.js 18+
- Puppeteer (for scraping)
- Google Translate API / DeepL
- Alpha Vantage / Finnhub
- YouTube Data API v3
- Twitter API v2

### Database & Caching
- PostgreSQL (Vercel Postgres or Supabase)
- Redis / Vercel KV

### DevOps
- Vercel (hosting + CI/CD)
- GitHub (version control)
- Sentry (error monitoring)
- Vercel Analytics

### APIs & Services
- Google Cloud Translation API
- Alpha Vantage (stock data)
- YouTube Data API
- Twitter API (sentiment)
- Bank of Korea API (exchange rates)

---

## Appendix B: Example User Stories

1. **As a trader**, I want to see which stocks Korean retail investors are buying today, so I can identify momentum plays.

2. **As a sentiment trader**, I want to see social media sentiment around popular stocks, so I can gauge retail enthusiasm.

3. **As a researcher**, I want to view historical trends of Korean buying patterns, so I can analyze correlations.

4. **As a non-Korean speaker**, I want news translated to English, so I can understand Korean market sentiment.

5. **As a day trader**, I want real-time updates during market hours, so I can make timely decisions.

6. **As a casual user**, I want a simple dashboard view, so I can quickly scan top trends without complexity.

---

## Appendix C: Data Source URLs

- KSD: https://www.ksd.or.kr
- Naver Finance: https://finance.naver.com
- Chosun Ilbo: https://www.chosun.com
- Korea Herald: https://www.koreaherald.com
- Investing.com Korea: https://kr.investing.com
- DCInside 주식갤러리: https://gall.dcinside.com/stock
- YouTube (서학개미TV example): Search "서학개미 순매수"

---

**Document Version**: 1.0
**Last Updated**: 2025-12-27
**Status**: Draft for Review
