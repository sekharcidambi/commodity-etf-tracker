# Premium Discount Calculator - Quick Reference

## Quick Start

```python
from app.services import premium_discount_calculator

# Calculate current premium/discount
result = await premium_discount_calculator.calculate_premium_discount("AGQ")
print(f"AGQ trading at {result['premium_discount_pct']:+.2f}% to NAV")

# Check for extreme levels
extreme = await premium_discount_calculator.detect_premium_discount_extreme("AGQ", threshold=1.5)
if extreme:
    print(f"ALERT: {extreme['severity']} {extreme['direction']} detected!")

# Get all ETFs
all_results = await premium_discount_calculator.get_all_etf_premium_discounts()
for r in all_results:
    print(f"{r['ticker']}: {r['premium_discount_pct']:+.2f}%")
```

## Supported ETFs

- **AGQ**: ProShares Ultra Silver (2x)
- **UGL**: ProShares Ultra Gold (2x)
- **ZSL**: ProShares UltraShort Silver (-2x)

## Methods

1. `calculate_premium_discount(ticker)` - Current premium/discount
2. `get_historical_premium_discount(ticker, days)` - Historical data
3. `detect_premium_discount_extreme(ticker, threshold)` - Extreme detection
4. `get_all_etf_premium_discounts()` - All ETFs at once
5. `check_all_etf_extremes(threshold)` - Check all for extremes

## Formula

```
premium_discount_pct = (etf_price - estimated_nav) / estimated_nav * 100
```

- **Positive**: Premium (ETF above NAV)
- **Negative**: Discount (ETF below NAV)

## Documentation

See `/home/user/commodity-etf-tracker/backend/docs/premium_discount_calculator.md` for full documentation.

## Example

Run the example script:
```bash
python examples/premium_discount_example.py
```
