# Composite Signal Scorer Service

## Overview

The Composite Signal Scorer combines multiple data signals into a single actionable score for each ticker. The service integrates 8 different factors with weighted contributions to produce a score from -100 (Strong SELL) to +100 (Strong BUY).

## Score Interpretation

| Score Range | Recommendation | Action |
|------------|----------------|--------|
| > +60 | Strong BUY | High conviction long position |
| +30 to +60 | Moderate BUY | Consider accumulation |
| -30 to +30 | NEUTRAL | No strong directional bias |
| -60 to -30 | Moderate SELL | Consider reducing exposure |
| < -60 | Strong SELL | High conviction short/avoid |

## Factor Weights

The composite score uses the following weighted factors:

1. **Flow Momentum (20%)** - ETF flow z-score over 13 weeks
2. **Korean Retail Contrarian (15%)** - Asian hours volume analysis (contrarian)
3. **Institutional Accumulation (15%)** - 13F quarterly holdings changes
4. **Futures Basis (10%)** - Contango/backwardation impact on leveraged ETFs
5. **COT Positioning (15%)** - Managed money positioning (contrarian)
6. **Premium/Discount (10%)** - ETF premium/discount to NAV
7. **Google Trends (10%)** - Search interest sentiment (contrarian)
8. **Reddit Sentiment (5%)** - Social media sentiment analysis

## Usage Examples

### Calculate Composite Score

```python
from app.services.composite_signal_scorer import composite_signal_scorer

# Get composite score for a ticker
score = await composite_signal_scorer.calculate_composite_score('AGQ')

print(f"Ticker: {score['ticker']}")
print(f"Score: {score['composite_score']}")
print(f"Recommendation: {score['recommendation']}")
print(f"Confidence: {score['confidence']}")
print(f"Factors Available: {score['factors_available']}/{score['factors_total']}")
```

**Example Output:**
```python
{
    'ticker': 'AGQ',
    'composite_score': 45.5,
    'recommendation': 'Moderate BUY',
    'confidence': 'high',
    'factor_scores': {...},
    'factor_contributions': {
        'flow_momentum': 12.5,
        'korean_retail': -5.3,
        'institutional': 8.2,
        'futures_basis': 3.1,
        'cot_positioning': 10.2,
        'premium_discount': -2.1,
        'google_trends': -1.5,
        'reddit_sentiment': 1.2
    },
    'factors_available': 8,
    'factors_total': 8,
    'calculated_at': '2025-12-28T12:00:00'
}
```

### Get Factor Breakdown

```python
# Get detailed breakdown of all factors
breakdown = await composite_signal_scorer.get_factor_breakdown('AGQ')

for factor_name, factor_data in breakdown['factors'].items():
    print(f"{factor_name}: {factor_data['normalized_score']:.2f}")
    print(f"  Weight: {factor_data['weight']*100:.0f}%")
    print(f"  Interpretation: {factor_data['interpretation']}")
```

### Get All Ticker Scores

```python
# Get scores for all primary tickers (AGQ, UGL)
all_scores = await composite_signal_scorer.get_all_ticker_scores()

for score in all_scores:
    print(f"{score['ticker']}: {score['composite_score']:+.1f} - {score['recommendation']}")
```

**Example Output:**
```
AGQ: +45.5 - Moderate BUY
UGL: -12.3 - NEUTRAL
```

### Get Signal Recommendation with Rationale

```python
# Get detailed recommendation with supporting rationale
recommendation = await composite_signal_scorer.get_signal_recommendation('AGQ')

print(f"Recommendation: {recommendation['recommendation']}")
print(f"Rationale: {recommendation['rationale']}")
print(f"\nTop Contributing Factors:")
for factor in recommendation['top_factors']:
    print(f"  - {factor['name']}: {factor['contribution']:+.1f} pts")
    print(f"    {factor['interpretation']}")
```

**Example Output:**
```
Recommendation: Moderate BUY
Rationale: Flow Momentum: Z-score: 1.85 (Strong inflows) (bullish, 12.5 pts); COT Positioning: Managed Money at 85th percentile (bullish, 10.2 pts); Institutional: 2/3 quarters accumulating (bullish, 8.2 pts)

Top Contributing Factors:
  - flow_momentum: +12.5 pts
    Z-score: 1.85 (Strong inflows)
  - cot_positioning: +10.2 pts
    Managed Money at 85th percentile (Extreme bearish - contrarian BUY)
  - institutional: +8.2 pts
    2/3 quarters accumulating
```

### Check Confidence Level

```python
# Get confidence metrics
confidence = await composite_signal_scorer.get_confidence_level('AGQ')

print(f"Confidence: {confidence['confidence']}")
print(f"Data Availability: {confidence['availability_pct']:.0f}%")
print(f"Data Freshness: {confidence['data_freshness']}")
```

## Factor Normalization

All factors are normalized to a -1 to +1 scale before weighting:

- **Flow Momentum**: z-score / 3 (±3σ = ±1.0)
- **Korean Retail**: -proxy_score / 100 (contrarian, inverted)
- **Institutional**: net_quarters / 3 (3 quarters accumulation = +1.0)
- **Futures Basis**: -basis_pct / 5 (inverted, ±5% = ±1.0)
- **COT Positioning**: -z_score / 3 (contrarian, inverted)
- **Premium/Discount**: -z_score / 3 (inverted, premium = negative)
- **Google Trends**: -(normalized_score - 100) / 50 (contrarian)
- **Reddit Sentiment**: sentiment_score (already -1 to +1)

## Handling Missing Data

The service automatically handles missing factor data:

1. **Weight Rescaling**: When factors are unavailable, remaining weights are proportionally increased
2. **Confidence Adjustment**: Confidence level reflects data availability:
   - **High**: ≥75% of factors available
   - **Medium**: ≥50% of factors available
   - **Low**: <50% of factors available

## Integration with API

The composite scorer can be easily integrated into API endpoints:

```python
from fastapi import APIRouter
from app.services.composite_signal_scorer import composite_signal_scorer

router = APIRouter()

@router.get("/api/composite-score/{ticker}")
async def get_composite_score(ticker: str):
    """Get composite score for a ticker"""
    score = await composite_signal_scorer.calculate_composite_score(ticker)
    return score

@router.get("/api/composite-scores")
async def get_all_scores():
    """Get composite scores for all tickers"""
    scores = await composite_signal_scorer.get_all_ticker_scores()
    return {'scores': scores}
```

## Best Practices

1. **Check Confidence**: Always review the `confidence` field before acting on signals
2. **Review Factors**: Examine `factor_contributions` to understand score drivers
3. **Data Freshness**: Use `get_confidence_level()` to verify data currency
4. **Multiple Timeframes**: Consider combining with other analysis timeframes
5. **Risk Management**: Use scores as input to position sizing, not absolute signals

## Logging

The service uses loguru for comprehensive logging:

```python
# Logs include:
# - Score calculations with factor availability
# - Individual factor scores and interpretations
# - Errors and warnings for missing/stale data
# - Performance metrics
```

## Error Handling

The service gracefully handles errors:

- Missing data returns `None` for specific factors
- Failed calculations return neutral scores with error flags
- Partial data availability is clearly indicated in confidence metrics

## Performance Considerations

- Factor calculations run in parallel where possible
- Results can be cached for frequently requested tickers
- Historical factor scores can be pre-computed for faster response times
