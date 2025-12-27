# Recent Updates - December 26, 2025

## ✅ GDXU ETF Added to Tracker

Successfully added GDXU (MicroSectors Gold Miners 3X Leveraged ETN) to the commodity ETF tracker.

### Data Collected
- **GDXU**: 251 days of historical price data (1 year)
- Latest price: $298.69 (as of 2025-12-26)
- Complete OHLCV data available

### Files Modified
1. **frontend/src/lib/utils/constants.ts**
   - Added GDXU to TICKERS constant: `['AGQ', 'UGL', 'GDXU']`

2. **frontend/src/lib/stores/tickerStore.ts**
   - Updated to use dynamic Ticker type from TICKERS constant
   - Now automatically supports any ticker added to constants

3. **frontend/src/components/layout/TickerSelector.tsx**
   - Updated to use TICKERS constant instead of hardcoded array
   - Now shows all three tickers: AGQ, UGL, GDXU

### How to Add More Tickers
To add additional ETFs in the future:
1. Collect data: `curl -X POST "http://localhost:8000/api/v1/data/collect/etf/TICKER?period=1y"`
2. Update `frontend/src/lib/utils/constants.ts` - add ticker to TICKERS array
3. TypeScript types and UI will automatically update

---

## ✅ Volume Display Added to Price Chart

Updated the price tracking chart at `/prices` to show volume alongside price.

### What Changed
- **Chart Type**: Changed from LineChart to ComposedChart
- **Volume Display**: Blue bars showing trading volume (semi-transparent)
- **Dual Y-Axes**:
  - Left axis: Price in USD
  - Right axis: Volume
- **Chart Height**: Increased from 400px to 500px for better visibility
- **Legend**: Added legend to distinguish Price vs Volume

### Files Modified
1. **frontend/src/pages/PriceTracking.tsx**
   - Imported ComposedChart, Bar, Legend from recharts
   - Added secondary Y-axis for volume
   - Added Bar component for volume display
   - Updated tooltip formatter to handle both Price and Volume
   - Increased chart height to 500px

### Visual Features
- Volume bars: Light blue (#93c5fd) with 60% opacity
- Price line: Blue (#2563eb) with 2px stroke
- Interactive legend showing/hiding data series
- Tooltip shows both Price (formatted as currency) and Volume (formatted as number)

---

## Current Ticker Status

| Ticker | Data Points | Date Range | Latest Price |
|--------|------------|------------|--------------|
| AGQ    | 251        | 2024-12-26 to 2025-12-26 | $199.77 |
| UGL    | 251        | 2024-12-26 to 2025-12-26 | $61.85  |
| GDXU   | 251        | 2024-12-26 to 2025-12-26 | $298.69 |

---

## Data Source Notes

All price data is collected from **Stooq** (via pandas_datareader) as a fallback from Yahoo Finance:
- Yahoo Finance primary source (currently rate-limited)
- Stooq automatic fallback with 2-second delays between requests
- Data automatically converted to UTC timezone for database storage
- Supports any US-listed ETF (uses `.US` suffix for Stooq)

To collect data for any ticker:
```bash
curl -X POST "http://localhost:8000/api/v1/data/collect/etf/TICKER?period=1y"
```

Available periods: `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`
