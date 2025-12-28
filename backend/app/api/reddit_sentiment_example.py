"""
Reddit Sentiment API Endpoints - Example Integration

This file demonstrates how to integrate the Reddit sentiment collector
into your FastAPI application. Add these endpoints to your router or
create a new router in app/api/routers/sentiment.py
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

from app.services.reddit_sentiment_collector import reddit_sentiment_collector

router = APIRouter(prefix="/sentiment", tags=["Reddit Sentiment"])


@router.get("/daily/{commodity}")
async def get_daily_sentiment(
    commodity: str,
    hours: int = Query(24, description="Hours to look back", ge=1, le=168)
) -> Dict[str, Any]:
    """
    Get daily sentiment summary for a commodity

    Args:
        commodity: Commodity name (e.g., 'silver', 'gold', 'AGQ', 'SLV')
        hours: Hours to look back (1-168, default 24)

    Returns:
        Comprehensive sentiment summary with mentions, scores, and top posts
    """
    try:
        logger.info(f"Fetching daily sentiment for {commodity}")

        summary = await reddit_sentiment_collector.get_daily_sentiment_summary(
            commodity=commodity.lower(),
            hours=hours
        )

        return summary

    except Exception as e:
        logger.error(f"Error getting daily sentiment for {commodity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickers")
async def get_multi_ticker_sentiment(
    tickers: Optional[str] = Query(None, description="Comma-separated tickers (e.g., 'AGQ,SLV,GLD')"),
    hours: int = Query(24, description="Hours to look back", ge=1, le=168)
) -> Dict[str, Any]:
    """
    Get sentiment for multiple tickers

    Args:
        tickers: Comma-separated ticker list (uses default if not provided)
        hours: Hours to look back

    Returns:
        Dictionary mapping tickers to sentiment data
    """
    try:
        ticker_list = None
        if tickers:
            ticker_list = [t.strip().upper() for t in tickers.split(',')]

        logger.info(f"Fetching sentiment for tickers: {ticker_list or 'default list'}")

        result = await reddit_sentiment_collector.get_multi_ticker_sentiment(
            tickers=ticker_list,
            hours=hours
        )

        return result

    except Exception as e:
        logger.error(f"Error getting multi-ticker sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/velocity/{keyword}")
async def get_mention_velocity(
    keyword: str,
    hours: int = Query(24, description="Hours to look back", ge=1, le=168)
) -> Dict[str, Any]:
    """
    Get mention velocity (mentions per hour/day) for a keyword

    Args:
        keyword: Keyword to track
        hours: Hours to look back

    Returns:
        Velocity metrics
    """
    try:
        logger.info(f"Calculating mention velocity for '{keyword}'")

        velocity = await reddit_sentiment_collector.get_mention_velocity(
            keyword=keyword,
            hours=hours
        )

        return velocity

    except Exception as e:
        logger.error(f"Error calculating velocity for '{keyword}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spike-detection/{keyword}")
async def detect_activity_spike(
    keyword: str,
    threshold: float = Query(3.0, description="Multiplier for spike detection", ge=1.0, le=10.0)
) -> Dict[str, Any]:
    """
    Detect unusual spikes in mentions

    Args:
        keyword: Keyword to check
        threshold: Threshold multiplier (e.g., 3.0 = 3x normal activity)

    Returns:
        Spike detection results with confidence level
    """
    try:
        logger.info(f"Checking for activity spikes on '{keyword}'")

        spike_data = await reddit_sentiment_collector.detect_unusual_activity(
            keyword=keyword,
            threshold_multiplier=threshold
        )

        return spike_data

    except Exception as e:
        logger.error(f"Error detecting spikes for '{keyword}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subreddit/{subreddit}")
async def get_subreddit_posts(
    subreddit: str,
    limit: int = Query(25, description="Number of posts to fetch", ge=1, le=100),
    time_filter: str = Query('day', description="Time filter: hour, day, week, month, year, all")
) -> Dict[str, Any]:
    """
    Fetch recent posts from a specific subreddit

    Args:
        subreddit: Subreddit name (without r/)
        limit: Number of posts to fetch (1-100)
        time_filter: Time filter for posts

    Returns:
        List of posts with metadata
    """
    try:
        logger.info(f"Fetching {limit} posts from r/{subreddit}")

        posts = await reddit_sentiment_collector.fetch_subreddit_posts(
            subreddit=subreddit,
            limit=limit,
            time_filter=time_filter
        )

        # Calculate sentiment for each post
        for post in posts:
            text = f"{post['title']} {post['selftext']}"
            post['sentiment'] = reddit_sentiment_collector.calculate_sentiment_score(text)

        return {
            'subreddit': subreddit,
            'count': len(posts),
            'time_filter': time_filter,
            'posts': posts,
            'fetched_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching posts from r/{subreddit}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/{keyword}")
async def search_keyword(
    keyword: str,
    subreddits: Optional[str] = Query(
        None,
        description="Comma-separated subreddits (e.g., 'wallstreetbets,investing')"
    ),
    limit: int = Query(50, description="Results per subreddit", ge=1, le=100)
) -> Dict[str, Any]:
    """
    Search for keyword mentions across subreddits

    Args:
        keyword: Keyword to search for
        subreddits: Comma-separated subreddit names (uses default if not provided)
        limit: Maximum results per subreddit

    Returns:
        List of posts mentioning the keyword
    """
    try:
        subreddit_list = None
        if subreddits:
            subreddit_list = [s.strip() for s in subreddits.split(',')]

        logger.info(f"Searching for '{keyword}' in {subreddit_list or 'default subreddits'}")

        mentions = await reddit_sentiment_collector.search_keyword_mentions(
            keyword=keyword,
            subreddits=subreddit_list,
            limit=limit
        )

        # Calculate sentiment for each mention
        for mention in mentions:
            text = f"{mention['title']} {mention['selftext']}"
            mention['sentiment'] = reddit_sentiment_collector.calculate_sentiment_score(text)

        # Calculate aggregate stats
        sentiments = [m['sentiment'] for m in mentions]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

        bullish_count = sum(1 for s in sentiments if s > 0.2)
        bearish_count = sum(1 for s in sentiments if s < -0.2)

        return {
            'keyword': keyword,
            'total_mentions': len(mentions),
            'subreddits_searched': subreddit_list or list(reddit_sentiment_collector.SUBREDDITS.keys()),
            'average_sentiment': round(avg_sentiment, 3),
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'mentions': mentions,
            'searched_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error searching for '{keyword}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment-score")
async def calculate_text_sentiment(
    text: str = Query(..., description="Text to analyze")
) -> Dict[str, Any]:
    """
    Calculate sentiment score for arbitrary text

    Args:
        text: Text to analyze

    Returns:
        Sentiment score and breakdown
    """
    try:
        score = reddit_sentiment_collector.calculate_sentiment_score(text)

        # Determine classification
        if score > 0.2:
            classification = "Bullish"
        elif score < -0.2:
            classification = "Bearish"
        else:
            classification = "Neutral"

        return {
            'text': text[:200] + ('...' if len(text) > 200 else ''),
            'sentiment_score': score,
            'classification': classification,
            'calculated_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error calculating sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_sentiment_dashboard(
    hours: int = Query(24, description="Hours to look back", ge=1, le=168)
) -> Dict[str, Any]:
    """
    Get comprehensive sentiment dashboard for all tracked assets

    Returns:
        Dashboard with sentiment for all tickers, top posts, and unusual activity
    """
    try:
        logger.info("Generating sentiment dashboard")

        # Get multi-ticker sentiment
        ticker_sentiment = await reddit_sentiment_collector.get_multi_ticker_sentiment(
            hours=hours
        )

        # Check for unusual activity on main keywords
        unusual_activity = []
        for keyword in ['silver', 'gold', 'AGQ', 'SLV', 'GLD']:
            spike = await reddit_sentiment_collector.detect_unusual_activity(keyword)
            if spike['is_unusual']:
                unusual_activity.append(spike)

        # Get overall market sentiment from r/investing
        market_posts = await reddit_sentiment_collector.fetch_subreddit_posts(
            'investing',
            limit=50
        )

        market_sentiments = [
            reddit_sentiment_collector.calculate_sentiment_score(f"{p['title']} {p['selftext']}")
            for p in market_posts
        ]
        market_sentiment_avg = sum(market_sentiments) / len(market_sentiments) if market_sentiments else 0.0

        return {
            'time_period_hours': hours,
            'ticker_sentiment': ticker_sentiment['tickers'],
            'unusual_activity': unusual_activity,
            'market_sentiment': {
                'average_score': round(market_sentiment_avg, 3),
                'sample_size': len(market_posts),
                'source': 'r/investing'
            },
            'generated_at': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating sentiment dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Example: How to integrate this into your main app
"""
In your app/main.py or app/api/__init__.py:

from app.api import reddit_sentiment_example

app.include_router(
    reddit_sentiment_example.router,
    prefix="/api/v1",
    tags=["Reddit Sentiment"]
)

Then access endpoints at:
- GET /api/v1/sentiment/daily/silver
- GET /api/v1/sentiment/tickers?tickers=AGQ,SLV,GLD
- GET /api/v1/sentiment/velocity/silver
- GET /api/v1/sentiment/spike-detection/AGQ
- GET /api/v1/sentiment/dashboard
"""
