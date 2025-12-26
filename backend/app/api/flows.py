"""ETF flow data endpoints"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import date

router = APIRouter()


@router.get("/{ticker}")
async def get_etf_flows(
    ticker: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
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
    # TODO: Implement database query
    return {
        "ticker": ticker.upper(),
        "start_date": start_date,
        "end_date": end_date,
        "flows": []
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
    Manual upload endpoint for CSV flow data

    TODO: Implement file upload and parsing
    """
    return {
        "status": "not_implemented",
        "message": "Manual CSV upload coming in Phase 1"
    }
