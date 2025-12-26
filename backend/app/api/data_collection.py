"""Data collection management endpoints"""

from fastapi import APIRouter, BackgroundTasks
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

from app.services.data_collector import data_collector

router = APIRouter()


class CollectionStats(BaseModel):
    """Collection statistics response"""
    status: str
    message: str
    stats: dict | None = None


@router.post("/collect/daily", response_model=CollectionStats)
async def trigger_daily_collection(period: str = "5d"):
    """
    Trigger daily price collection for all configured tickers

    - **period**: Time period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max')
    """
    try:
        stats = await data_collector.collect_all_market_data(period=period)
        return CollectionStats(
            status="success",
            message="Data collection completed",
            stats=stats
        )
    except Exception as e:
        return CollectionStats(
            status="error",
            message=f"Data collection failed: {str(e)}",
            stats=None
        )


@router.post("/collect/etf/{ticker}", response_model=CollectionStats)
async def collect_single_ticker(ticker: str, period: str = "1mo"):
    """
    Collect data for a single ticker

    - **ticker**: Ticker symbol (e.g., 'AGQ', 'UGL')
    - **period**: Time period to collect
    """
    try:
        stats = await data_collector.collect_daily_prices(
            tickers=[ticker],
            period=period
        )
        return CollectionStats(
            status="success",
            message=f"Collected data for {ticker}",
            stats=stats
        )
    except Exception as e:
        return CollectionStats(
            status="error",
            message=f"Collection failed: {str(e)}",
            stats=None
        )


@router.post("/backfill", response_model=CollectionStats)
async def backfill_historical(
    ticker: str,
    start_date: str,
    end_date: Optional[str] = None
):
    """
    Backfill historical data for a ticker

    - **ticker**: Ticker symbol
    - **start_date**: Start date (YYYY-MM-DD)
    - **end_date**: End date (YYYY-MM-DD), defaults to today
    """
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()

        stats = await data_collector.backfill_historical_data(
            tickers=[ticker],
            start_date=start,
            end_date=end
        )

        return CollectionStats(
            status="success",
            message=f"Backfilled {ticker} from {start_date} to {end.date()}",
            stats=stats
        )
    except Exception as e:
        return CollectionStats(
            status="error",
            message=f"Backfill failed: {str(e)}",
            stats=None
        )


@router.post("/backfill/all", response_model=CollectionStats)
async def backfill_all_tickers(
    start_date: str,
    end_date: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Backfill historical data for all configured tickers

    This runs in the background as it may take a while

    - **start_date**: Start date (YYYY-MM-DD)
    - **end_date**: End date (YYYY-MM-DD), defaults to today
    """
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date) if end_date else datetime.utcnow()

        # Get all tickers from settings
        from app.core.config import settings
        all_tickers = settings.PRIMARY_TICKERS + settings.EXTENDED_TICKERS + settings.FUTURES_SYMBOLS

        # Run in background
        if background_tasks:
            background_tasks.add_task(
                data_collector.backfill_historical_data,
                tickers=all_tickers,
                start_date=start,
                end_date=end
            )
            return CollectionStats(
                status="success",
                message=f"Backfill started for {len(all_tickers)} tickers (running in background)",
                stats={'tickers_count': len(all_tickers)}
            )
        else:
            stats = await data_collector.backfill_historical_data(
                tickers=all_tickers,
                start_date=start,
                end_date=end
            )
            return CollectionStats(
                status="success",
                message="Backfill completed",
                stats=stats
            )

    except Exception as e:
        return CollectionStats(
            status="error",
            message=f"Backfill failed: {str(e)}",
            stats=None
        )
