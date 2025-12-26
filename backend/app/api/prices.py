"""Price data endpoints"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import date, datetime

from app.services.data_storage import data_storage

router = APIRouter()


@router.get("/etf/{ticker}")
async def get_etf_prices(
    ticker: str,
    start_date: Optional[date] = Query(None, description="Start date for price data"),
    end_date: Optional[date] = Query(None, description="End date for price data"),
    interval: str = Query("1d", description="Data interval: 1d, 1h, 5m, 1m"),
    limit: int = Query(100, description="Maximum number of records")
):
    """
    Get price data for an ETF ticker (AGQ, UGL, etc.)

    - **ticker**: ETF ticker symbol
    - **start_date**: Optional start date (YYYY-MM-DD)
    - **end_date**: Optional end date (YYYY-MM-DD)
    - **interval**: Data interval (1d=daily)
    - **limit**: Maximum records to return
    """
    start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None

    data = await data_storage.get_price_data(
        ticker=ticker.upper(),
        start_date=start_dt,
        end_date=end_dt,
        limit=limit
    )

    return {
        "ticker": ticker.upper(),
        "interval": interval,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(data),
        "data": data
    }


@router.get("/futures/{symbol}")
async def get_futures_prices(
    symbol: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    interval: str = Query("1d")
):
    """
    Get futures price data (GC=F for gold, SI=F for silver, PL=F for platinum)
    """
    # TODO: Implement database query
    return {
        "symbol": symbol,
        "interval": interval,
        "start_date": start_date,
        "end_date": end_date,
        "data": []
    }


@router.get("/spot/{metal}")
async def get_spot_prices(
    metal: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    """
    Get spot prices for precious metals (gold, silver, platinum)
    """
    valid_metals = ["gold", "silver", "platinum"]
    if metal.lower() not in valid_metals:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metal. Must be one of: {', '.join(valid_metals)}"
        )

    # TODO: Implement database query
    return {
        "metal": metal.lower(),
        "start_date": start_date,
        "end_date": end_date,
        "data": []
    }


@router.get("/realtime/{ticker}")
async def get_realtime_quote(ticker: str):
    """
    Get real-time quote for a ticker
    """
    # TODO: Implement real-time data fetch or cache query
    return {
        "ticker": ticker.upper(),
        "timestamp": datetime.utcnow().isoformat(),
        "last_price": None,
        "bid": None,
        "ask": None,
        "volume": None,
        "change": None,
        "change_percent": None
    }
