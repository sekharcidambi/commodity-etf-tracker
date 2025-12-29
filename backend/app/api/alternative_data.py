"""Alternative Data API endpoints - COT, Google Trends, COMEX, Reddit"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from loguru import logger

from app.services.cot_collector import cot_collector
from app.services.google_trends_collector import google_trends_collector
from app.services.comex_inventory_collector import comex_inventory_collector
from app.services.reddit_sentiment_collector import reddit_sentiment_collector

router = APIRouter()


# ============================================================================
# CFTC COMMITMENT OF TRADERS (COT) ENDPOINTS
# ============================================================================

@router.get("/cot/{commodity}")
async def get_cot_positioning(
    commodity: str,
    as_of_date: Optional[date] = Query(None, description="Specific report date")
) -> Dict[str, Any]:
    """
    Get COT positioning data for a commodity

    Commodities: gold, silver, platinum
    """
    try:
        commodity = commodity.lower()
        if commodity not in ['gold', 'silver', 'platinum']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid commodity. Must be: gold, silver, platinum"
            )

        positioning = await cot_collector.get_commodity_positioning(
            commodity=commodity,
            as_of_date=as_of_date
        )

        if not positioning:
            raise HTTPException(
                status_code=404,
                detail=f"No COT data found for {commodity}"
            )

        return {
            "commodity": commodity,
            **positioning,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting COT positioning for {commodity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cot/{commodity}/extreme")
async def get_cot_extreme_positioning(
    commodity: str,
    lookback_weeks: int = Query(52, description="Weeks of history for percentile"),
    percentile_threshold: float = Query(90.0, description="Percentile threshold for extreme")
) -> Dict[str, Any]:
    """
    Detect extreme COT positioning (contrarian indicator)

    Returns contrarian signal when speculators are at extreme levels.
    """
    try:
        commodity = commodity.lower()

        extreme = await cot_collector.detect_extreme_positioning(
            commodity=commodity,
            lookback_weeks=lookback_weeks,
            percentile_threshold=percentile_threshold
        )

        if not extreme:
            return {
                "commodity": commodity,
                "is_extreme": False,
                "note": "No extreme positioning detected",
                "retrieved_at": datetime.utcnow().isoformat()
            }

        return {
            "commodity": commodity,
            **extreme,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error checking COT extreme for {commodity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cot/{commodity}/history")
async def get_cot_history(
    commodity: str,
    weeks: int = Query(52, description="Number of weeks of history")
) -> Dict[str, Any]:
    """
    Get historical COT positioning data
    """
    try:
        commodity = commodity.lower()

        history = await cot_collector.get_historical_positioning(
            commodity=commodity,
            weeks=weeks
        )

        return {
            "commodity": commodity,
            "weeks_requested": weeks,
            "data_points": len(history),
            "history": history,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting COT history for {commodity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cot/summary")
async def get_cot_summary() -> Dict[str, Any]:
    """
    Get COT summary for all precious metals
    """
    try:
        summary = await cot_collector.get_all_commodities_summary()

        return {
            "commodities": summary,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting COT summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GOOGLE TRENDS ENDPOINTS
# ============================================================================

@router.get("/trends/{commodity}")
async def get_google_trends(
    commodity: str,
    timeframe: str = Query("now 7-d", description="Timeframe: now 1-d, now 7-d, today 1-m, today 3-m")
) -> Dict[str, Any]:
    """
    Get Google Trends interest data for a commodity
    """
    try:
        commodity = commodity.lower()

        interest = await google_trends_collector.calculate_interest_score(
            commodity=commodity,
            timeframe=timeframe
        )

        return {
            "commodity": commodity,
            "timeframe": timeframe,
            **interest,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting Google Trends for {commodity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/{commodity}/spike")
async def detect_trends_spike(
    commodity: str,
    timeframe: str = Query("now 7-d"),
    threshold_multiplier: float = Query(2.0, description="Threshold multiplier for spike detection")
) -> Dict[str, Any]:
    """
    Detect unusual spike in search interest
    """
    try:
        commodity = commodity.lower()

        spike = await google_trends_collector.detect_interest_spike(
            commodity=commodity,
            timeframe=timeframe,
            threshold_multiplier=threshold_multiplier
        )

        return {
            "commodity": commodity,
            "timeframe": timeframe,
            "threshold_multiplier": threshold_multiplier,
            **spike,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error detecting trends spike for {commodity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/sentiment")
async def get_comprehensive_sentiment(
    timeframe: str = Query("now 7-d")
) -> Dict[str, Any]:
    """
    Get comprehensive sentiment analysis from Google Trends
    """
    try:
        sentiment = await google_trends_collector.get_comprehensive_sentiment(
            timeframe=timeframe
        )

        return {
            "timeframe": timeframe,
            **sentiment,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting comprehensive sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/{keyword}/related")
async def get_related_queries(
    keyword: str
) -> Dict[str, Any]:
    """
    Get related queries for a keyword
    """
    try:
        related = await google_trends_collector.get_related_queries(keyword)

        return {
            "keyword": keyword,
            **related,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting related queries for {keyword}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMEX INVENTORY ENDPOINTS
# ============================================================================

@router.get("/comex/{commodity}")
async def get_comex_inventory(
    commodity: str
) -> Dict[str, Any]:
    """
    Get current COMEX warehouse inventory for a commodity
    """
    try:
        commodity = commodity.lower()

        inventory = await comex_inventory_collector.fetch_comex_inventory(commodity)

        if not inventory:
            raise HTTPException(
                status_code=404,
                detail=f"No COMEX inventory data for {commodity}"
            )

        return {
            "commodity": commodity,
            **inventory,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting COMEX inventory for {commodity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comex/{commodity}/trend")
async def get_comex_inventory_trend(
    commodity: str,
    days: int = Query(30, description="Number of days of history")
) -> Dict[str, Any]:
    """
    Get historical COMEX inventory trend
    """
    try:
        commodity = commodity.lower()

        trend = await comex_inventory_collector.get_inventory_trend(
            commodity=commodity,
            days=days
        )

        # Convert DataFrame to list of dicts if needed
        if hasattr(trend, 'to_dict'):
            trend_data = trend.to_dict('records')
        else:
            trend_data = trend

        return {
            "commodity": commodity,
            "days_requested": days,
            "data_points": len(trend_data) if trend_data else 0,
            "trend": trend_data,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting COMEX trend for {commodity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comex/{commodity}/squeeze")
async def detect_comex_squeeze(
    commodity: str,
    open_interest: Optional[int] = Query(None, description="Current open interest (contracts)")
) -> Dict[str, Any]:
    """
    Detect potential COMEX inventory squeeze

    A squeeze occurs when:
    - Registered inventory declining for 5+ days
    - Registered-to-OI ratio below 10%
    - Coverage below 30 days
    """
    try:
        commodity = commodity.lower()

        squeeze = await comex_inventory_collector.detect_inventory_squeeze(
            commodity=commodity,
            open_interest=open_interest
        )

        return {
            "commodity": commodity,
            **squeeze,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error detecting COMEX squeeze for {commodity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/comex/summary")
async def get_comex_summary() -> Dict[str, Any]:
    """
    Get COMEX inventory summary for all commodities
    """
    try:
        summary = await comex_inventory_collector.get_all_commodities_summary()

        return {
            "commodities": summary,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting COMEX summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# REDDIT SENTIMENT ENDPOINTS
# ============================================================================

@router.get("/reddit/{commodity}/sentiment")
async def get_reddit_sentiment(
    commodity: str,
    hours: int = Query(24, description="Hours of history to analyze")
) -> Dict[str, Any]:
    """
    Get Reddit sentiment for a commodity
    """
    try:
        commodity = commodity.lower()

        sentiment = await reddit_sentiment_collector.get_daily_sentiment_summary(
            commodity=commodity,
            hours=hours
        )

        return {
            "commodity": commodity,
            "hours_analyzed": hours,
            **sentiment,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting Reddit sentiment for {commodity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reddit/tickers")
async def get_reddit_ticker_sentiment(
    tickers: str = Query("AGQ,UGL,SLV,GLD", description="Comma-separated tickers"),
    hours: int = Query(24)
) -> Dict[str, Any]:
    """
    Get Reddit sentiment for multiple tickers
    """
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(',')]

        sentiment = await reddit_sentiment_collector.get_multi_ticker_sentiment(
            tickers=ticker_list,
            hours=hours
        )

        return {
            "tickers": ticker_list,
            "hours_analyzed": hours,
            **sentiment,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting Reddit ticker sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reddit/{keyword}/velocity")
async def get_reddit_mention_velocity(
    keyword: str,
    hours: int = Query(24)
) -> Dict[str, Any]:
    """
    Get mention velocity for a keyword
    """
    try:
        velocity = await reddit_sentiment_collector.get_mention_velocity(
            keyword=keyword,
            hours=hours
        )

        return {
            "keyword": keyword,
            "hours_analyzed": hours,
            **velocity,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting Reddit velocity for {keyword}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reddit/{keyword}/spike")
async def detect_reddit_activity_spike(
    keyword: str,
    threshold_multiplier: float = Query(3.0, description="Threshold for unusual activity")
) -> Dict[str, Any]:
    """
    Detect unusual activity spike for a keyword
    """
    try:
        spike = await reddit_sentiment_collector.detect_unusual_activity(
            keyword=keyword,
            threshold_multiplier=threshold_multiplier
        )

        return {
            "keyword": keyword,
            "threshold_multiplier": threshold_multiplier,
            **spike,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error detecting Reddit spike for {keyword}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# COMBINED ALTERNATIVE DATA DASHBOARD
# ============================================================================

@router.get("/dashboard/{commodity}")
async def get_alternative_data_dashboard(
    commodity: str
) -> Dict[str, Any]:
    """
    Get combined alternative data dashboard for a commodity

    Includes: COT positioning, Google Trends, COMEX inventory, Reddit sentiment
    """
    try:
        commodity = commodity.lower()

        # Fetch all data sources in parallel
        import asyncio

        cot_task = cot_collector.detect_extreme_positioning(commodity)
        trends_task = google_trends_collector.calculate_interest_score(commodity)
        comex_task = comex_inventory_collector.fetch_comex_inventory(commodity)
        reddit_task = reddit_sentiment_collector.get_daily_sentiment_summary(commodity)

        results = await asyncio.gather(
            cot_task, trends_task, comex_task, reddit_task,
            return_exceptions=True
        )

        cot_data = results[0] if not isinstance(results[0], Exception) else None
        trends_data = results[1] if not isinstance(results[1], Exception) else None
        comex_data = results[2] if not isinstance(results[2], Exception) else None
        reddit_data = results[3] if not isinstance(results[3], Exception) else None

        # Build composite sentiment
        signals = []

        if cot_data and cot_data.get('extreme_positioning', {}).get('is_extreme_bullish'):
            signals.append({"source": "COT", "signal": "CONTRARIAN_SELL", "strength": 0.8})
        elif cot_data and cot_data.get('extreme_positioning', {}).get('is_extreme_bearish'):
            signals.append({"source": "COT", "signal": "CONTRARIAN_BUY", "strength": 0.8})

        if trends_data and trends_data.get('z_score', 0) > 2:
            signals.append({"source": "TRENDS", "signal": "SPIKE_DETECTED", "strength": 0.5})

        if comex_data and comex_data.get('is_squeeze_warning'):
            signals.append({"source": "COMEX", "signal": "SQUEEZE_WARNING", "strength": 0.7})

        if reddit_data and reddit_data.get('is_unusual_activity'):
            signals.append({"source": "REDDIT", "signal": "UNUSUAL_ACTIVITY", "strength": 0.4})

        return {
            "commodity": commodity,
            "cot": cot_data,
            "google_trends": trends_data,
            "comex_inventory": comex_data,
            "reddit_sentiment": reddit_data,
            "signals": signals,
            "signal_count": len(signals),
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting alternative data dashboard for {commodity}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
