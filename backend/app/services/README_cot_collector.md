# CFTC Commitment of Traders (COT) Collector Service

## Overview

The COT Collector service retrieves and analyzes Commitment of Traders (COT) positioning data from the CFTC (Commodity Futures Trading Commission) for precious metals (gold, silver, platinum).

COT reports are published weekly on Friday afternoons with data as of the previous Tuesday. They show how different market participants (commercials, speculators, retail traders) are positioned in futures markets.

## Why COT Data Matters

COT positioning is a **contrarian indicator**:

- **Extreme Bullish Positioning** (high net long speculators) → Often signals a market top (too many bulls)
- **Extreme Bearish Positioning** (high net short speculators) → Often signals a market bottom (too many bears)

When managed money (large speculators like hedge funds) reaches extreme levels, it often precedes a reversal because:
1. Positioning becomes crowded
2. There are fewer new buyers/sellers to push the trend further
3. Any adverse news triggers rapid unwinding

## Data Source

- **URL**: https://www.cftc.gov/dea/newcot/c_disagg.txt
- **Report Type**: Disaggregated Futures-Only
- **Frequency**: Weekly (published Friday, data as of Tuesday)
- **Format**: Pipe-delimited text file

## Commodity Codes

| Commodity | CFTC Code | Description |
|-----------|-----------|-------------|
| Gold      | 088691    | COMEX Gold Futures |
| Silver    | 084691    | COMEX Silver Futures |
| Platinum  | 076651    | NYMEX Platinum Futures |

## Market Participant Categories

### 1. Commercial (Hedgers)
- **Producer/Merchant**: Mining companies, refiners, jewelry manufacturers
- **Swap Dealers**: Banks and dealers managing client hedges
- **Positioning**: Usually opposite to speculators (natural hedgers)
- **Net Position**: Combined producer + swap dealer net

### 2. Managed Money (Large Speculators)
- **Who**: Hedge funds, CTAs (Commodity Trading Advisors), asset managers
- **Importance**: KEY indicator - their extreme positioning is most contrarian
- **Net Position**: Long minus Short positions
- **Long/Short Ratio**: Indicates bullish vs bearish sentiment

### 3. Other Reportables
- Smaller institutions that must report positions
- Less significant for analysis

### 4. Non-Reportables (Retail)
- Small traders below reporting thresholds
- Individual retail traders
- Generally considered the "weak hands"

## Key Metrics

| Metric | Description | Interpretation |
|--------|-------------|----------------|
| `managed_money_net` | Net long/short position of speculators | Core positioning metric |
| `managed_money_net_pct` | Net as % of open interest | Normalized for market size |
| `managed_money_long_short_ratio` | Longs divided by shorts | >2 = very bullish, <0.5 = very bearish |
| `percentile` | Current positioning vs historical | >90th = extreme bullish, <10th = extreme bearish |
| `z_score` | Standard deviations from mean | >2 or <-2 = statistically extreme |
| `contrarian_signal` | Contrarian trading signal | 'bullish' or 'bearish' when extreme |

## Service Methods

### 1. `fetch_cot_report(force_refresh: bool = False)`

Downloads and parses the full COT report from CFTC.

**Features**:
- Automatic caching (6 hours)
- Parses pipe-delimited format
- Converts dates and numeric fields
- Handles comma-separated numbers

**Returns**: DataFrame with all COT data

```python
df = await cot_collector.fetch_cot_report()
```

### 2. `get_commodity_positioning(commodity: str, as_of_date: Optional[date] = None)`

Get current or historical positioning for a specific commodity.

**Parameters**:
- `commodity`: 'gold', 'silver', or 'platinum'
- `as_of_date`: Specific date (defaults to most recent)

**Returns**: Dictionary with:
- Open interest
- Long/short/net positions for all categories
- Percentage metrics
- Long/short ratios

```python
gold = await cot_collector.get_commodity_positioning('gold')
print(f"Managed Money Net: {gold['managed_money_net']:,}")
print(f"Net % of OI: {gold['managed_money_net_pct']:.2f}%")
```

### 3. `calculate_net_positioning(as_of_date: Optional[date] = None)`

Get net positioning for all precious metals at once.

**Returns**: Dictionary mapping commodity to positioning data

```python
all_positions = await cot_collector.calculate_net_positioning()
for commodity, pos in all_positions.items():
    print(f"{commodity}: {pos['managed_money_net']:,}")
```

### 4. `detect_extreme_positioning(commodity: str, lookback_weeks: int = 52, percentile_threshold: float = 90.0)`

**Most Important Method** - Detects extreme positioning for contrarian signals.

**Parameters**:
- `commodity`: Commodity to analyze
- `lookback_weeks`: Historical context period (default: 52 weeks = 1 year)
- `percentile_threshold`: What defines "extreme" (default: 90th percentile)

**Returns**: Dictionary with:
- Current positioning metrics
- Historical context (median, percentiles, z-score)
- Extreme positioning flags
- **Contrarian signal** ('bullish' or 'bearish')
- Human-readable interpretation

**Example**:
```python
extremes = await cot_collector.detect_extreme_positioning('gold')

if extremes['extreme_positioning']['is_extreme_bullish']:
    # Too many bulls - contrarian bearish signal
    print(f"SELL signal: {extremes['interpretation']}")

elif extremes['extreme_positioning']['is_extreme_bearish']:
    # Too many bears - contrarian bullish signal
    print(f"BUY signal: {extremes['interpretation']}")
```

### 5. `get_historical_positioning(commodity: str, weeks: int = 52)`

Retrieve historical positioning data for trend analysis.

**Parameters**:
- `commodity`: Commodity name
- `weeks`: Number of weeks of history

**Returns**: List of positioning dictionaries (oldest to newest)

**Use Cases**:
- Chart positioning trends
- Calculate moving averages
- Identify positioning extremes over time
- Correlation analysis with prices

```python
history = await cot_collector.get_historical_positioning('silver', weeks=26)
for record in history:
    print(f"{record['report_date']}: {record['managed_money_net']:,}")
```

### 6. `get_all_commodities_summary()`

Comprehensive summary of all precious metals with extreme analysis.

**Returns**: Dictionary with:
- Current positioning for all commodities
- Extreme positioning analysis for each
- Timestamp

**Perfect for**:
- Dashboard displays
- Regular monitoring
- Alerting on extreme conditions

```python
summary = await cot_collector.get_all_commodities_summary()
for commodity, data in summary['commodities'].items():
    if data['extreme_analysis']['extreme_positioning']['is_extreme']:
        print(f"⚠️ {commodity.upper()} at extreme positioning!")
```

## Trading Interpretation Guide

### Extreme Bullish (>90th Percentile)
- **Positioning**: Speculators heavily net long
- **Meaning**: Market is crowded with bulls
- **Contrarian Signal**: BEARISH
- **Risk**: Vulnerable to selling on any negative news
- **Action**: Consider reducing long exposure or taking short positions

### Extreme Bearish (<10th Percentile)
- **Positioning**: Speculators heavily net short
- **Meaning**: Market is washed out
- **Contrarian Signal**: BULLISH
- **Opportunity**: Potential for short squeeze and rally
- **Action**: Consider initiating long positions

### Neutral (25th-75th Percentile)
- **Positioning**: Balanced
- **Meaning**: No extreme positioning
- **Signal**: No contrarian signal
- **Action**: Follow other indicators (price action, fundamentals)

### Z-Score Interpretation
- **|z| > 2**: Statistically significant extreme (2+ standard deviations)
- **|z| > 3**: Very extreme (3+ standard deviations)
- **Negative z-score**: Below average (bearish positioning)
- **Positive z-score**: Above average (bullish positioning)

## Integration Examples

### Example 1: Weekly Monitoring
```python
async def check_weekly_positioning():
    """Check positioning every week when new COT data is released"""
    summary = await cot_collector.get_all_commodities_summary()

    alerts = []
    for commodity, data in summary['commodities'].items():
        ext = data['extreme_analysis']['extreme_positioning']
        if ext['is_extreme']:
            alerts.append({
                'commodity': commodity,
                'signal': ext['contrarian_signal'],
                'percentile': data['extreme_analysis']['current_positioning']['percentile']
            })

    return alerts
```

### Example 2: Signal Generation
```python
async def generate_cot_signals():
    """Generate trading signals based on COT extremes"""
    signals = []

    for commodity in ['gold', 'silver', 'platinum']:
        extremes = await cot_collector.detect_extreme_positioning(commodity)

        if extremes['extreme_positioning']['is_extreme_bullish']:
            signals.append({
                'commodity': commodity,
                'action': 'SELL',
                'reason': 'Extreme bullish positioning - contrarian bearish',
                'confidence': 'HIGH'
            })
        elif extremes['extreme_positioning']['is_extreme_bearish']:
            signals.append({
                'commodity': commodity,
                'action': 'BUY',
                'reason': 'Extreme bearish positioning - contrarian bullish',
                'confidence': 'HIGH'
            })

    return signals
```

### Example 3: Combine with Price Data
```python
async def cot_price_divergence(commodity: str):
    """Detect divergence between COT and price"""
    # Get positioning
    extremes = await cot_collector.detect_extreme_positioning(commodity)
    history = await cot_collector.get_historical_positioning(commodity, weeks=4)

    # Calculate positioning trend
    recent_net = [h['managed_money_net'] for h in history]
    positioning_trend = 'increasing' if recent_net[-1] > recent_net[0] else 'decreasing'

    # Get price data (from your price service)
    # price_trend = calculate_price_trend(commodity)

    # Detect divergence
    # if positioning_trend == 'increasing' and price_trend == 'decreasing':
    #     return 'bearish_divergence'  # Specs getting bullish as price falls
    # elif positioning_trend == 'decreasing' and price_trend == 'increasing':
    #     return 'bullish_divergence'  # Specs getting bearish as price rises
```

## Best Practices

1. **Update Frequency**: Check once per week after Friday's COT release
2. **Combine Indicators**: Don't use COT alone - combine with price action, fundamentals
3. **Look for Extremes**: Focus on >90th or <10th percentile
4. **Z-Score Confirmation**: Look for |z| > 2 for statistical confirmation
5. **Historical Context**: Use 52-week lookback for full-year perspective
6. **Divergences**: Most powerful when positioning and price diverge

## Caching

The service caches the COT report for 6 hours to:
- Reduce load on CFTC servers
- Improve performance
- Data updates weekly, so frequent fetching is unnecessary

Force refresh with: `fetch_cot_report(force_refresh=True)`

## Error Handling

All methods include comprehensive error handling:
- HTTP errors (network issues, server errors)
- Data parsing errors (malformed data)
- Missing data (commodity not found)
- Returns empty DataFrame/dict on errors
- Logs detailed error messages with traceback

## Dependencies

- `httpx`: Async HTTP client
- `pandas`: Data parsing and analysis
- `loguru`: Structured logging
- Standard library: `datetime`, `typing`, `io`

## Resources

- [CFTC COT Reports](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)
- [Disaggregated Report Explanatory Notes](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ExplanatoryNotes/index.htm)
- [Understanding COT Data](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalViewable/index.htm)

## Example Output

```
GOLD POSITIONING (Report Date: 2025-12-23)
================================
Open Interest: 498,234 contracts

Managed Money (Speculators):
  Long:  245,678 contracts
  Short:  89,234 contracts
  Net:   156,444 contracts (31.4% of OI)
  L/S Ratio: 2.75

Commercial (Hedgers):
  Net: -168,234 contracts (-33.8% of OI)

EXTREME POSITIONING ANALYSIS
================================
Current Percentile: 92.3rd
Z-Score: 2.41
Status: EXTREME BULLISH
Contrarian Signal: BEARISH

Interpretation:
Speculators are EXTREMELY BULLISH on GOLD (92nd percentile, z-score: 2.4).
This is a contrarian BEARISH signal - too many bulls may indicate positioning
is crowded and vulnerable to correction.
```

## Notes

- COT data is T+5 (published Friday for previous Tuesday)
- Data includes futures-only positions (not options)
- Disaggregated report used (more detailed than legacy report)
- All positions in number of contracts
- Percentages calculated relative to open interest
