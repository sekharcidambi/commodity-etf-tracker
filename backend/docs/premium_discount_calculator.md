# Premium/Discount Calculator Service

## Overview

The `PremiumDiscountCalculatorService` calculates the premium or discount to Net Asset Value (NAV) for leveraged precious metals ETFs. This service helps identify when ETFs are trading significantly above (premium) or below (discount) their estimated NAV, which can signal trading opportunities.

## Supported ETFs

The service currently supports three leveraged precious metals ETFs:

| Ticker | Name | Leverage | Underlying | Type |
|--------|------|----------|------------|------|
| **AGQ** | ProShares Ultra Silver | 2x | Silver (SI=F) | Leveraged Long |
| **UGL** | ProShares Ultra Gold | 2x | Gold (GC=F) | Leveraged Long |
| **ZSL** | ProShares UltraShort Silver | -2x | Silver (SI=F) | Inverse |

## Key Concepts

### Premium/Discount Formula

```
premium_discount_pct = (etf_price - estimated_nav) / estimated_nav * 100
```

- **Positive value**: ETF trading at a premium (above NAV)
- **Negative value**: ETF trading at a discount (below NAV)

### NAV Estimation

The service uses a simplified NAV calculation:

```python
# For leveraged long ETFs (AGQ, UGL):
estimated_nav = leverage * commodity_price

# For inverse ETFs (ZSL):
estimated_nav = leverage * commodity_price  # Note: simplified calculation
```

**Important**: This is a simplified approximation. Actual NAV calculations would require:
- Exact shares per creation unit
- Daily reset/rebalancing effects
- Management fees and expenses
- Swap financing costs

## Service Methods

### 1. `calculate_premium_discount(ticker: str)`

Calculate the current premium/discount for a single ETF.

**Parameters:**
- `ticker`: ETF ticker symbol (AGQ, UGL, or ZSL)

**Returns:**
```python
{
    'ticker': 'AGQ',
    'etf_name': 'ProShares Ultra Silver',
    'etf_price': 25.30,
    'etf_timestamp': '2025-12-28T15:30:00Z',
    'commodity_symbol': 'SI=F',
    'commodity_price': 29.85,
    'commodity_timestamp': '2025-12-28T15:00:00Z',
    'estimated_nav': 59.70,
    'premium_discount_pct': -0.15,
    'leverage': 2.0,
    'inverse': False,
    'calculated_at': '2025-12-28T15:30:15Z'
}
```

**Usage:**
```python
from app.services import premium_discount_calculator

result = await premium_discount_calculator.calculate_premium_discount("AGQ")
print(f"AGQ Premium/Discount: {result['premium_discount_pct']:.2f}%")
```

### 2. `get_historical_premium_discount(ticker: str, days: int = 30)`

Retrieve historical premium/discount data for analysis.

**Parameters:**
- `ticker`: ETF ticker symbol
- `days`: Number of days of historical data (default: 30)

**Returns:**
```python
[
    {
        'timestamp': '2025-12-28T20:00:00Z',
        'date': '2025-12-28',
        'etf_price': 25.30,
        'commodity_price': 29.85,
        'estimated_nav': 59.70,
        'premium_discount_pct': -0.15
    },
    # ... more records
]
```

**Usage:**
```python
historical = await premium_discount_calculator.get_historical_premium_discount(
    ticker="UGL",
    days=90
)

# Calculate statistics
prem_disc_values = [r['premium_discount_pct'] for r in historical]
avg = sum(prem_disc_values) / len(prem_disc_values)
print(f"Average premium/discount over 90 days: {avg:.2f}%")
```

### 3. `detect_premium_discount_extreme(ticker: str, threshold: float = 1.5)`

Detect if the current premium/discount is at an extreme level compared to historical norms.

**Parameters:**
- `ticker`: ETF ticker symbol
- `threshold`: Z-score threshold for extreme detection (default: 1.5 std deviations)

**Returns:**
```python
{
    'ticker': 'AGQ',
    'current_premium_discount_pct': 2.35,
    'z_score': 2.15,
    'percentile': 96.5,
    'mean': 0.15,
    'std_dev': 1.02,
    'is_extreme': True,
    'direction': 'PREMIUM',
    'severity': 'EXTREME',  # or 'ELEVATED'
    'threshold': 1.5,
    'etf_price': 25.30,
    'estimated_nav': 24.72,
    'notes': 'EXTREME premium detected: 2.35% (z-score: 2.15)',
    'calculated_at': '2025-12-28T15:30:15Z'
}
```

Returns `None` if not extreme.

**Usage:**
```python
extreme = await premium_discount_calculator.detect_premium_discount_extreme(
    ticker="ZSL",
    threshold=1.5
)

if extreme:
    print(f"ALERT: {extreme['severity']} {extreme['direction']} detected!")
    print(f"Z-Score: {extreme['z_score']:.2f}")
```

**Severity Levels:**
- **ELEVATED**: Z-score between 1.5 and 2.0 (or -1.5 and -2.0)
- **EXTREME**: Z-score >= 2.0 (or <= -2.0)

### 4. `get_all_etf_premium_discounts()`

Calculate premium/discount for all configured ETFs at once.

**Returns:**
```python
[
    {'ticker': 'AGQ', 'premium_discount_pct': -0.15, ...},
    {'ticker': 'UGL', 'premium_discount_pct': 0.25, ...},
    {'ticker': 'ZSL', 'premium_discount_pct': -0.50, ...}
]
```

**Usage:**
```python
all_results = await premium_discount_calculator.get_all_etf_premium_discounts()

for result in all_results:
    print(f"{result['ticker']}: {result['premium_discount_pct']:+.2f}%")
```

### 5. `check_all_etf_extremes(threshold: float = 1.5)`

Check all configured ETFs for extreme premium/discount levels.

**Returns:**
```python
[
    {
        'ticker': 'AGQ',
        'severity': 'EXTREME',
        'direction': 'PREMIUM',
        'current_premium_discount_pct': 2.35,
        'z_score': 2.15,
        ...
    },
    # ... only ETFs with extreme levels
]
```

**Usage:**
```python
extremes = await premium_discount_calculator.check_all_etf_extremes(threshold=1.5)

if extremes:
    print(f"Found {len(extremes)} ETFs with extreme levels:")
    for extreme in extremes:
        print(f"  - {extreme['ticker']}: {extreme['severity']} {extreme['direction']}")
```

## Integration with Data Storage

The service relies on the `DataStorageService` to retrieve:

1. **ETF Prices**: From the `etf_prices` table
2. **Commodity Prices**: From the `commodity_prices` table (SI=F for silver, GC=F for gold)

### New Method Added to DataStorageService

A new method `get_commodity_price_data()` was added to retrieve commodity/futures prices:

```python
async def get_commodity_price_data(
    self,
    symbol: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100
) -> List[dict]:
    """Retrieve commodity price data from database"""
```

## Use Cases

### 1. Trading Signal Generation

Extreme premium/discount levels can indicate:
- **Large Premium**: ETF may be overbought, potential short opportunity
- **Large Discount**: ETF may be oversold, potential long opportunity

```python
# Check for trading opportunities
extremes = await premium_discount_calculator.check_all_etf_extremes(threshold=2.0)

for extreme in extremes:
    if extreme['direction'] == 'DISCOUNT' and extreme['z_score'] <= -2.0:
        print(f"BUY signal for {extreme['ticker']}")
    elif extreme['direction'] == 'PREMIUM' and extreme['z_score'] >= 2.0:
        print(f"SELL signal for {extreme['ticker']}")
```

### 2. Arbitrage Detection

Identify arbitrage opportunities between ETF and underlying commodity.

### 3. Risk Monitoring

Monitor for unusual ETF behavior that may indicate:
- Liquidity issues
- Market dislocations
- Creation/redemption imbalances

### 4. Historical Analysis

Analyze premium/discount patterns over time:

```python
historical = await premium_discount_calculator.get_historical_premium_discount(
    ticker="AGQ",
    days=365
)

# Identify periods of persistent premium/discount
# Correlate with market events, flows, etc.
```

## Example Script

See `/home/user/commodity-etf-tracker/backend/examples/premium_discount_example.py` for a complete usage example.

To run the example:

```bash
cd /home/user/commodity-etf-tracker/backend
python examples/premium_discount_example.py
```

## Dependencies

- **SQLAlchemy**: For database queries
- **NumPy**: For statistical calculations (z-score, percentile)
- **Loguru**: For logging
- **Existing Services**: DataStorageService

## Logging

The service uses Loguru for comprehensive logging:

- **INFO**: Normal operations, calculation results
- **WARNING**: Extreme premium/discount detected, insufficient data
- **ERROR**: Database errors, calculation failures

## Limitations

1. **Simplified NAV Calculation**: The current implementation uses a simplified NAV estimation. For production use, consider:
   - Integrating official NAV data from ETF providers
   - Accounting for daily rebalancing effects
   - Including management fees and expenses

2. **Data Availability**: Requires both ETF and commodity price data in the database.

3. **Market Hours**: Commodity futures and ETFs may trade at different times, leading to stale price comparisons.

4. **Creation/Redemption Lag**: Actual NAV may differ from estimated NAV due to creation/redemption basket composition.

## Future Enhancements

Potential improvements:

1. **Official NAV Integration**: Fetch official NAV from ETF providers (e.g., ProShares)
2. **Intraday Calculations**: Use intraday prices for real-time monitoring
3. **Alert System**: Automatic notifications when extreme levels detected
4. **Historical NAV Storage**: Store calculated NAV values in database
5. **Regression Analysis**: Predict future premium/discount based on flows, volatility
6. **Additional ETFs**: Support more leveraged commodity ETFs (e.g., NUGT, DUST, JNUG)

## Files Created

1. **Service File**: `/home/user/commodity-etf-tracker/backend/app/services/premium_discount_calculator.py`
2. **Example Script**: `/home/user/commodity-etf-tracker/backend/examples/premium_discount_example.py`
3. **Documentation**: `/home/user/commodity-etf-tracker/backend/docs/premium_discount_calculator.md` (this file)
4. **Updated Files**:
   - `/home/user/commodity-etf-tracker/backend/app/services/data_storage.py` (added `get_commodity_price_data` method)
   - `/home/user/commodity-etf-tracker/backend/app/services/__init__.py` (added export)

## Author

Created: 2025-12-28
