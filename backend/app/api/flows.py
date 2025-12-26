"""ETF flow data endpoints"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel

from app.services.data_storage import data_storage
from app.services.flow_collector import flow_collector

router = APIRouter()


class FlowCollectionStats(BaseModel):
    """Flow collection statistics response"""
    status: str
    message: str
    stats: dict | None = None


@router.get("/{ticker}")
async def get_etf_flows(
    ticker: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(52, description="Maximum number of weeks to return")
):
    """
    Get weekly ETF flow data for a ticker

    Returns:
    - week_ending: Date
    - net_flow: Net inflows/outflows in USD millions
    - aum: Assets under management
    - shares_outstanding: Total shares
    - premium_discount: Premium/discount to NAV (%)
    """
    start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None
    end_dt = datetime.combine(end_date, datetime.max.time()) if end_date else None

    flows = await data_storage.get_etf_flows(
        ticker=ticker.upper(),
        start_date=start_dt,
        end_date=end_dt,
        limit=limit
    )

    return {
        "ticker": ticker.upper(),
        "start_date": start_date,
        "end_date": end_date,
        "count": len(flows),
        "flows": flows
    }


@router.get("/{ticker}/segments")
async def get_flow_segments(
    ticker: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    """
    Get ETF flow data broken down by investor segment

    Segments:
    - KOREAN_RETAIL
    - US_RETAIL
    - INSTITUTIONAL
    - SOVEREIGN
    - UNKNOWN
    """
    # TODO: Implement investor segment flow query
    return {
        "ticker": ticker.upper(),
        "start_date": start_date,
        "end_date": end_date,
        "segments": []
    }


@router.get("/{ticker}/statistics")
async def get_flow_statistics(
    ticker: str,
    window: str = Query("52w", description="Window for statistics: 4w, 13w, 26w, 52w")
):
    """
    Get flow statistics (rolling sums, z-scores, percentiles)
    """
    valid_windows = ["4w", "13w", "26w", "52w"]
    if window not in valid_windows:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window. Must be one of: {', '.join(valid_windows)}"
        )

    # TODO: Implement statistics calculation
    return {
        "ticker": ticker.upper(),
        "window": window,
        "current_flow": None,
        "rolling_sum": None,
        "z_score": None,
        "percentile": None,
        "mean": None,
        "std_dev": None
    }


@router.post("/{ticker}/upload")
async def upload_flow_data(ticker: str):
    """
    Manual upload endpoint for CSV flow data (DEPRECATED)

    Use /flows/collect endpoints instead for automated scraping
    """
    return {
        "status": "deprecated",
        "message": "Use /flows/collect endpoints for automated data collection"
    }


@router.post("/collect/etfdb", response_model=FlowCollectionStats)
async def collect_etfdb_flows(tickers: Optional[list[str]] = None):
    """
    Collect ETF flow data from ETFdb.com

    - **tickers**: Optional list of ticker symbols (defaults to PRIMARY_TICKERS)

    Returns collection statistics
    """
    try:
        stats = await flow_collector.collect_etfdb_flows(tickers=tickers)
        return FlowCollectionStats(
            status="success",
            message="ETFdb flow collection completed",
            stats=stats
        )
    except Exception as e:
        return FlowCollectionStats(
            status="error",
            message=f"Flow collection failed: {str(e)}",
            stats=None
        )


@router.post("/collect/institutional/{ticker}", response_model=FlowCollectionStats)
async def collect_institutional_holdings(ticker: str):
    """
    Collect institutional holdings (13F) data for a ticker

    - **ticker**: Ticker symbol

    Returns collection statistics from major institutions
    """
    try:
        stats = await flow_collector.collect_institutional_holdings(ticker.upper())
        return FlowCollectionStats(
            status="success",
            message=f"Institutional holdings collected for {ticker.upper()}",
            stats=stats
        )
    except Exception as e:
        return FlowCollectionStats(
            status="error",
            message=f"Holdings collection failed: {str(e)}",
            stats=None
        )


@router.post("/collect/all", response_model=FlowCollectionStats)
async def collect_all_flows():
    """
    Collect all flow data from all sources

    This triggers:
    1. ETFdb.com flow data collection
    2. SEC 13F institutional holdings collection

    Returns aggregated collection statistics
    """
    try:
        stats = await flow_collector.collect_all_flow_data()
        return FlowCollectionStats(
            status="success",
            message="All flow data collection completed",
            stats=stats
        )
    except Exception as e:
        return FlowCollectionStats(
            status="error",
            message=f"Flow collection failed: {str(e)}",
            stats=None
        )


@router.get("/institutional/{ticker}")
async def get_institutional_holdings(
    ticker: str,
    start_date: Optional[date] = Query(None),
    limit: int = Query(20, description="Maximum number of filings to return")
):
    """
    Get institutional holdings (13F) data for a ticker

    Returns recent 13F filings showing institutional positions
    """
    start_dt = datetime.combine(start_date, datetime.min.time()) if start_date else None

    holdings = await data_storage.get_institutional_holdings(
        ticker=ticker.upper(),
        start_date=start_dt,
        limit=limit
    )

    return {
        "ticker": ticker.upper(),
        "start_date": start_date,
        "count": len(holdings),
        "holdings": holdings
    }
