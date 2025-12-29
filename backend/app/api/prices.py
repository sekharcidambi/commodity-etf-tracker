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
    interval: str = Query("1d"),
    limit: int = Query(100, description="Maximum number of records")
):
    """
    Get futures price data (GC=F for gold, SI=F for silver, PL=F for platinum)

    - **symbol**: Futures symbol (e.g., GC=F, SI=F, PL=F)
    - **start_date**: Optional start date (YYYY-MM-DD)
    - **end_date**: Optional end date (YYYY-MM-DD)
    - **limit**: Maximum records to return
    """
    start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None

    data = await data_storage.get_commodity_price_data(
        symbol=symbol.upper(),
        start_date=start_dt,
        end_date=end_dt,
        limit=limit
    )

    return {
        "symbol": symbol.upper(),
        "interval": interval,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(data),
        "data": data
    }


@router.get("/spot/{metal}")
async def get_spot_prices(
    metal: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(100, description="Maximum number of records")
):
    """
    Get spot prices for precious metals (gold, silver, platinum)

    - **metal**: Metal name (gold, silver, platinum)
    - **start_date**: Optional start date (YYYY-MM-DD)
    - **end_date**: Optional end date (YYYY-MM-DD)
    - **limit**: Maximum records to return
    """
    valid_metals = ["gold", "silver", "platinum"]
    if metal.lower() not in valid_metals:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid metal. Must be one of: {', '.join(valid_metals)}"
        )

    # Map metal names to spot symbols
    metal_to_symbol = {
        "gold": "XAUUSD",
        "silver": "XAGUSD",
        "platinum": "XPTUSD"
    }
    symbol = metal_to_symbol[metal.lower()]

    start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None

    data = await data_storage.get_commodity_price_data(
        symbol=symbol,
        start_date=start_dt,
        end_date=end_dt,
        limit=limit
    )

    return {
        "metal": metal.lower(),
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(data),
        "data": data
    }


@router.get("/realtime/{ticker}")
async def get_realtime_quote(ticker: str):
    """
    Get real-time quote for a ticker using yfinance

    - **ticker**: Ticker symbol (e.g., AGQ, UGL, GC=F)

    Returns latest available quote data from Yahoo Finance
    """
    import yfinance as yf
    from loguru import logger

    try:
        # Fetch quote from yfinance
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        # Get fast_info for quick data access
        fast_info = stock.fast_info

        # Calculate change from previous close
        last_price = fast_info.get('lastPrice') or info.get('regularMarketPrice')
        prev_close = fast_info.get('previousClose') or info.get('previousClose')

        change = None
        change_percent = None
        if last_price and prev_close:
            change = round(last_price - prev_close, 4)
            change_percent = round((change / prev_close) * 100, 2)

        return {
            "ticker": ticker.upper(),
            "timestamp": datetime.utcnow().isoformat(),
            "last_price": last_price,
            "bid": info.get('bid'),
            "ask": info.get('ask'),
            "volume": fast_info.get('lastVolume') or info.get('volume'),
            "change": change,
            "change_percent": change_percent,
            "day_high": info.get('dayHigh'),
            "day_low": info.get('dayLow'),
            "previous_close": prev_close
        }

    except Exception as e:
        logger.warning(f"Error fetching realtime quote for {ticker}: {e}")
        return {
            "ticker": ticker.upper(),
            "timestamp": datetime.utcnow().isoformat(),
            "last_price": None,
            "bid": None,
            "ask": None,
            "volume": None,
            "change": None,
            "change_percent": None,
            "error": str(e)
        }
