# Reddit Sentiment Collector Service

This service tracks retail sentiment from Reddit communities to gauge retail investor interest in precious metals and related ETFs.

## Features

- **Multi-Subreddit Monitoring**: Tracks r/wallstreetbets, r/Silverbugs, r/Gold, and r/investing
- **Keyword Tracking**: Monitors tickers (AGQ, UGL, SLV, GLD, PSLV) and terms (silver, gold, platinum, etc.)
- **Sentiment Analysis**: Simple keyword-based sentiment scoring (-1 to +1)
- **Velocity Tracking**: Calculates mentions per hour/day
- **Spike Detection**: Identifies unusual activity (>3x normal mentions)
- **Aggregated Summaries**: Daily sentiment summaries with top posts

## Setup

### 1. Get Reddit API Credentials

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Fill in the form:
   - **name**: Commodity ETF Tracker
   - **App type**: Select "script"
   - **description**: Sentiment analysis for commodity ETFs
   - **about url**: (leave blank)
   - **redirect uri**: http://localhost:8080 (required but not used)
4. Click "Create app"
5. Copy the credentials:
   - **client_id**: The string under "personal use script" (14 characters)
   - **client_secret**: The "secret" field (27 characters)

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
REDDIT_CLIENT_ID=your_client_id_here
REDDIT_CLIENT_SECRET=your_client_secret_here
```

### 3. Usage Examples

```python
from app.services.reddit_sentiment_collector import reddit_sentiment_collector

# Get daily sentiment for silver
sentiment = await reddit_sentiment_collector.get_daily_sentiment_summary('silver', hours=24)
print(f"Sentiment: {sentiment['sentiment_score']}")
print(f"Mentions: {sentiment['mentions']}")
print(f"Bullish ratio: {sentiment['bullish_ratio']}")

# Search for specific keyword mentions
mentions = await reddit_sentiment_collector.search_keyword_mentions('AGQ', limit=100)
print(f"Found {len(mentions)} mentions of AGQ")

# Check for unusual activity
spike = await reddit_sentiment_collector.detect_unusual_activity('silver', threshold_multiplier=3.0)
if spike['is_unusual']:
    print(f"SPIKE DETECTED: {spike['multiplier']}x normal activity!")

# Get mention velocity
velocity = await reddit_sentiment_collector.get_mention_velocity('GLD', hours=24)
print(f"GLD mentioned {velocity['mentions_per_day']:.1f} times per day")

# Get sentiment for multiple tickers
multi = await reddit_sentiment_collector.get_multi_ticker_sentiment(['AGQ', 'SLV', 'GLD'])
for ticker, data in multi['tickers'].items():
    print(f"{ticker}: {data['mentions']} mentions, sentiment={data['sentiment_score']}")
```

## API Methods

### `fetch_subreddit_posts(subreddit: str, limit: int = 100, time_filter: str = 'day')`
Fetch recent posts from a subreddit.

### `search_keyword_mentions(keyword: str, subreddits: List[str], limit: int = 100)`
Search for keyword mentions across multiple subreddits.

### `calculate_sentiment_score(text: str) -> float`
Calculate sentiment score using keyword matching (-1 to +1).

### `get_mention_velocity(keyword: str, hours: int = 24)`
Calculate mentions per hour/day for a keyword.

### `detect_unusual_activity(keyword: str, threshold_multiplier: float = 3.0)`
Detect spikes in mentions (>3x normal activity).

### `get_daily_sentiment_summary(commodity: str, hours: int = 24)`
Get comprehensive daily sentiment summary.

### `get_multi_ticker_sentiment(tickers: List[str], hours: int = 24)`
Get sentiment for multiple tickers.

## Sentiment Scoring

The service uses simple keyword matching for sentiment analysis:

**Bullish Keywords:**
- buy, buying, moon, squeeze, bullish, long, undervalued
- rocket, calls, accumulating, hodl, diamond hands, btfd
- breakout, rally, pump, to the moon, lfg, yolo

**Bearish Keywords:**
- sell, selling, dump, dumping, bearish, short, overvalued
- crash, puts, distributing, exit, paper hands, rug pull
- breakdown, tank, fade, dead cat, bubble

**Score Calculation:**
```
sentiment = (bullish_count - bearish_count) / total_keywords
```

## Return Data Structure

### Daily Sentiment Summary
```json
{
  "commodity": "silver",
  "time_period_hours": 24,
  "mentions": 142,
  "sentiment_score": 0.651,
  "velocity": 5.92,
  "bullish_ratio": 0.718,
  "sentiment_distribution": {
    "bullish": 102,
    "neutral": 28,
    "bearish": 12
  },
  "top_posts": [
    {
      "title": "Silver squeeze incoming?",
      "score": 1547,
      "comments": 234,
      "sentiment": 0.857,
      "permalink": "https://reddit.com/r/wallstreetbets/...",
      "subreddit": "wallstreetbets",
      "created_utc": "2025-12-28T10:30:00Z"
    }
  ],
  "subreddits_covered": ["wallstreetbets", "Silverbugs", "investing"],
  "calculated_at": "2025-12-28T18:45:12.345Z"
}
```

### Unusual Activity Detection
```json
{
  "keyword": "silver",
  "is_unusual": true,
  "current_rate": 12.5,
  "baseline_rate": 3.2,
  "multiplier": 3.91,
  "threshold": 3.0,
  "confidence": "high",
  "data_points": 15
}
```

## Rate Limits

The Reddit API has rate limits:
- **OAuth authenticated**: 60 requests per minute
- **Unauthenticated**: 10 requests per minute (not used)

The service includes 1-second delays between requests to be respectful to Reddit's API.

## Notes

- The service uses Reddit's OAuth2 authentication with client credentials flow
- Access tokens are cached and automatically refreshed when expired
- Historical mention data is stored for 7 days for velocity calculations
- Sentiment analysis is keyword-based and relatively simple; consider upgrading to ML-based sentiment for production
- All timestamps are in UTC

## Future Enhancements

1. **ML-based Sentiment**: Integrate transformer models (BERT, DistilBERT) for more accurate sentiment
2. **Comment Analysis**: Analyze post comments in addition to post titles/bodies
3. **Trending Detection**: Identify rapidly trending topics
4. **User Influence**: Weight sentiment by user karma/influence
5. **Cross-Platform**: Expand to Twitter, Discord, StockTwits
6. **Real-time Streaming**: Use Reddit's streaming API for real-time updates
7. **Database Storage**: Persist sentiment data for historical analysis
8. **Alert System**: Trigger alerts on unusual activity or sentiment shifts
