# Asian Hours Analyzer Service

## Overview

The Asian Hours Analyzer Service detects and quantifies Korean retail trading activity in US-listed ETFs by analyzing volume patterns during Asian trading hours. Korean retail traders, particularly active in leveraged commodity ETFs like AGQ (2x Silver) and UGL (2x Gold), tend to trade during hours that align with their timezone, which corresponds to US after-hours and pre-market sessions.

## Trading Session Definitions

All times are in US/Eastern timezone:

### Asian Hours (Korean Retail Activity Windows)
- **After Hours**: 8:00 PM - 11:59 PM ET
  - Corresponds to morning hours in Korea (9:00 AM - 12:59 PM KST)
- **Pre-Market**: 4:00 AM - 9:29 AM ET
  - Corresponds to evening hours in Korea (5:00 PM - 10:29 PM KST)

### Regular Trading Hours
- **Regular Hours**: 9:30 AM - 3:59 PM ET
  - Primary US trading session

## Key Metrics

### 1. Asian Volume Ratio
```
Asian Volume Ratio = (After Hours Volume + Pre-Market Volume) / Regular Hours Volume
```

**Interpretation:**
- Higher ratio indicates more trading during Asian hours relative to regular hours
- Typical ratios: 0.05 - 0.15 (5-15%)
- Elevated ratios (>0.20) suggest strong Korean retail interest

### 2. Korean Retail Proxy Score (0-100)

A composite score that combines multiple factors:

**Components:**
- **Percentile Rank (50%)**: How recent Asian volume compares to historical distribution
- **Trend Direction (30%)**: Whether Asian activity is increasing, stable, or decreasing
- **Consistency (20%)**: How stable the Asian volume pattern is

**Score Ranges:**
- **75-100**: Very high Korean retail activity
- **60-74**: High Korean retail activity
- **40-59**: Moderate Korean retail activity
- **25-39**: Low Korean retail activity
- **0-24**: Minimal Korean retail activity

## Service Methods

### 1. `get_volume_by_session(ticker: str, target_date: date)`

Breaks down intraday volume by trading session for a specific date.

**Returns:**
```python
{
    "date": "2025-12-28",
    "ticker": "AGQ",
    "sessions": {
        "after_hours": {"volume": 12345, "bar_count": 24},
        "pre_market": {"volume": 23456, "bar_count": 30},
        "regular_hours": {"volume": 456789, "bar_count": 390},
        "other": {"volume": 100, "bar_count": 5}
    },
    "asian_hours_volume": 35801,
    "regular_hours_volume": 456789,
    "asian_volume_ratio": 0.078
}
```

**Use Case:** Daily monitoring and detailed session analysis

### 2. `analyze_asian_hours_volume(ticker: str, days: int = 30)`

Analyzes volume patterns over multiple days to identify trends.

**Returns:**
```python
{
    "ticker": "AGQ",
    "analysis_period_days": 30,
    "start_date": "2025-11-28",
    "end_date": "2025-12-28",
    "daily_breakdown": [...],  # List of daily session breakdowns
    "summary": {
        "avg_asian_volume_ratio": 0.085,
        "median_asian_volume_ratio": 0.078,
        "std_asian_volume_ratio": 0.023,
        "min_asian_volume_ratio": 0.045,
        "max_asian_volume_ratio": 0.142,
        "trend": "increasing",
        "total_asian_hours_volume": 1234567,
        "total_regular_hours_volume": 14567890,
        "days_with_data": 28
    }
}
```

**Use Case:** Historical trend analysis and pattern detection

### 3. `calculate_korean_retail_proxy(ticker: str)`

Calculates a comprehensive Korean retail activity score.

**Returns:**
```python
{
    "ticker": "AGQ",
    "korean_retail_proxy_score": 75.5,
    "confidence": "high",
    "metrics": {
        "recent_asian_ratio": 0.12,
        "baseline_asian_ratio": 0.08,
        "ratio_percentile": 85.3,
        "trend": "increasing",
        "consistency_score": 0.78
    },
    "interpretation": "Very high Korean retail activity detected and increasing"
}
```

**Use Case:** Signal generation and trading alerts

## Usage Examples

### Basic Usage

```python
from app.services.asian_hours_analyzer import AsianHoursAnalyzerService
from datetime import date

async def analyze_korean_activity():
    analyzer = AsianHoursAnalyzerService()

    # Get today's volume breakdown
    today_data = await analyzer.get_volume_by_session("AGQ", date.today())

    # Get Korean retail proxy score
    proxy = await analyzer.calculate_korean_retail_proxy("AGQ")

    print(f"Korean Retail Score: {proxy['korean_retail_proxy_score']:.1f}")
    print(f"Interpretation: {proxy['interpretation']}")
```

### Signal Integration

```python
async def generate_korean_retail_signal(ticker: str):
    analyzer = AsianHoursAnalyzerService()
    proxy = await analyzer.calculate_korean_retail_proxy(ticker)

    # Generate signal when score is high and increasing
    if (proxy['korean_retail_proxy_score'] > 70 and
        proxy['metrics']['trend'] == 'increasing' and
        proxy['confidence'] == 'high'):

        return {
            "signal_type": "KOREAN_RETAIL_SURGE",
            "ticker": ticker,
            "strength": proxy['korean_retail_proxy_score'],
            "direction": "UP",  # Korean retail typically buys
            "notes": proxy['interpretation']
        }
```

### Monitoring Dashboard

```python
async def daily_korean_retail_monitor(tickers: list):
    analyzer = AsianHoursAnalyzerService()

    results = []
    for ticker in tickers:
        proxy = await analyzer.calculate_korean_retail_proxy(ticker)

        results.append({
            "ticker": ticker,
            "score": proxy['korean_retail_proxy_score'],
            "trend": proxy['metrics']['trend'],
            "recent_ratio": proxy['metrics']['recent_asian_ratio']
        })

    # Sort by score descending
    results.sort(key=lambda x: x['score'] or 0, reverse=True)

    return results
```

## Technical Implementation

### Data Requirements

The service requires intraday bar data stored in the `intraday_bars` table:
- **Interval**: Preferably 1-minute or 5-minute bars
- **Fields**: timestamp, ticker, volume
- **Coverage**: At least 7 days for recent analysis, 90 days for baseline

### Timezone Handling

The service uses `zoneinfo` for proper timezone conversion:
- All timestamps are converted to US/Eastern for session classification
- Handles daylight saving time transitions correctly
- Supports timezone-aware datetime objects

### Performance Considerations

- Database queries are optimized with date range filters
- Aggregations performed in-memory using NumPy
- Async/await pattern for non-blocking I/O
- Results can be cached for dashboard displays

## Interpretation Guidelines

### When Korean Retail Score is High (>70)

**Implications:**
- Increased volatility during Asian hours
- Potential continuation of trends into US session
- Higher likelihood of gap movements at market open
- Consider positioning before Asian hours trading begins

**Trading Considerations:**
- Korean retail tends to chase momentum
- Often provides liquidity during low-volume periods
- May amplify existing trends in silver/gold markets

### When Score is Increasing

**Implications:**
- Growing retail interest in the ETF
- Potential build-up to larger move
- Monitor news/catalysts in Korean financial media

### When Consistency Score is Low

**Warning Signs:**
- Erratic volume patterns
- Possible one-off events rather than sustained interest
- Lower confidence in signal reliability

## Integration with Other Signals

The Asian Hours Analyzer complements other data signals:

1. **ETF Flow Data**: Compare Asian hour activity with weekly institutional flows
2. **Premium/Discount**: Check if Korean retail is creating NAV deviations
3. **Futures Activity**: Monitor silver/gold futures during Asian hours
4. **Institutional Holdings**: Contrast retail patterns with institutional positioning

## Limitations and Considerations

1. **Correlation vs Causation**: High Asian hours volume doesn't guarantee Korean retail activity
2. **Market Events**: Overnight news can spike Asian hours volume independently
3. **Other Asian Markets**: Japanese, Chinese, and Australian traders also active
4. **Data Quality**: Requires clean, comprehensive intraday data
5. **Regulatory Changes**: Korean margin rules can shift trading patterns

## Future Enhancements

Potential improvements to the service:

- [ ] IP geolocation analysis (if available from broker data)
- [ ] Korean won/USD correlation analysis
- [ ] Integration with Korean social media sentiment
- [ ] Broker-specific flow attribution
- [ ] Machine learning for pattern recognition
- [ ] Real-time alert generation

## References

- US market hours: https://www.nyse.com/markets/hours-calendars
- Korean market hours: https://eng.krx.co.kr/
- Time zone handling: https://docs.python.org/3/library/zoneinfo.html
