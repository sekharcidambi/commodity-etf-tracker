"""Ticker management endpoints"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from sqlalchemy import select
from loguru import logger

from app.db.database import AsyncSessionLocal
from app.models import Ticker, InstitutionalHolding
from app.services.data_storage import data_storage

router = APIRouter()


@router.get("/")
async def list_tickers(
    active_only: bool = Query(True, description="Only return active tickers"),
    asset_class: Optional[str] = Query(None, description="Filter by asset class")
):
    """
    Get all tracked tickers with metadata

    - **active_only**: Only return active (non-delisted) tickers
    - **asset_class**: Optional filter by asset class (e.g., SILVER_LEVERAGED, GOLD_LEVERAGED)
    """
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(Ticker)

            if active_only:
                stmt = stmt.where(Ticker.is_active == True)

            if asset_class:
                stmt = stmt.where(Ticker.asset_class == asset_class.upper())

            stmt = stmt.order_by(Ticker.ticker)

            result = await session.execute(stmt)
            tickers = result.scalars().all()

            return {
                "count": len(tickers),
                "tickers": [
                    {
                        "ticker": t.ticker,
                        "name": t.name,
                        "asset_class": t.asset_class,
                        "leverage_factor": float(t.leverage_factor) if t.leverage_factor else None,
                        "expense_ratio": float(t.expense_ratio) if t.expense_ratio else None,
                        "is_active": t.is_active,
                        "avg_daily_volume": int(t.avg_daily_volume) if t.avg_daily_volume else None,
                        "inception_date": t.inception_date.isoformat() if t.inception_date else None
                    }
                    for t in tickers
                ]
            }

    except Exception as e:
        logger.error(f"Error listing tickers: {e}")
        # Return default tickers if database query fails
        return {
            "count": 2,
            "tickers": [
                {
                    "ticker": "AGQ",
                    "name": "ProShares Ultra Silver",
                    "asset_class": "SILVER_LEVERAGED",
                    "leverage_factor": 2.0,
                    "is_active": True,
                    "avg_daily_volume": None,
                    "inception_date": None
                },
                {
                    "ticker": "UGL",
                    "name": "ProShares Ultra Gold",
                    "asset_class": "GOLD_LEVERAGED",
                    "leverage_factor": 2.0,
                    "is_active": True,
                    "avg_daily_volume": None,
                    "inception_date": None
                }
            ]
        }


@router.get("/{ticker}")
async def get_ticker_info(ticker: str):
    """
    Get detailed information about a specific ticker

    - **ticker**: ETF ticker symbol (e.g., AGQ, UGL)

    Returns comprehensive ticker metadata from database
    """
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(Ticker).where(Ticker.ticker == ticker.upper())
            result = await session.execute(stmt)
            t = result.scalar_one_or_none()

            if not t:
                raise HTTPException(
                    status_code=404,
                    detail=f"Ticker {ticker.upper()} not found"
                )

            return {
                "ticker": t.ticker,
                "name": t.name,
                "asset_class": t.asset_class,
                "leverage_factor": float(t.leverage_factor) if t.leverage_factor else None,
                "expense_ratio": float(t.expense_ratio) if t.expense_ratio else None,
                "inception_date": t.inception_date.isoformat() if t.inception_date else None,
                "is_active": t.is_active,
                "avg_daily_volume": int(t.avg_daily_volume) if t.avg_daily_volume else None,
                "last_volume_check": t.last_volume_check.isoformat() if t.last_volume_check else None,
                "delisted_date": t.delisted_date.isoformat() if t.delisted_date else None,
                "notes": t.notes,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticker info for {ticker}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving ticker information: {str(e)}"
        )


@router.get("/{ticker}/institutional-holders")
async def get_institutional_holders(
    ticker: str,
    limit: int = Query(20, description="Maximum number of holders to return")
):
    """
    Get institutional holders from 13F filings

    - **ticker**: ETF ticker symbol
    - **limit**: Maximum number of holders to return

    Returns top institutional holders with quarter-over-quarter changes
    """
    try:
        holdings = await data_storage.get_institutional_holdings(
            ticker=ticker.upper(),
            limit=limit
        )

        # Group by institution and calculate changes
        institutions = {}
        for h in holdings:
            inst_name = h.get('institution_name', 'Unknown')
            if inst_name not in institutions:
                institutions[inst_name] = {
                    'institution_name': inst_name,
                    'cik': h.get('institution_cik'),
                    'filings': []
                }
            institutions[inst_name]['filings'].append({
                'filing_date': h.get('filing_date'),
                'report_date': h.get('report_date'),
                'shares_held': h.get('shares_held'),
                'market_value': h.get('market_value'),
                'percent_of_portfolio': h.get('percent_of_portfolio')
            })

        # Calculate QoQ changes for each institution
        holders_list = []
        for inst_name, data in institutions.items():
            filings = sorted(data['filings'], key=lambda x: x.get('filing_date') or '', reverse=True)

            latest = filings[0] if filings else {}
            previous = filings[1] if len(filings) > 1 else {}

            shares_change = None
            shares_change_pct = None
            if latest.get('shares_held') and previous.get('shares_held'):
                shares_change = latest['shares_held'] - previous['shares_held']
                shares_change_pct = round((shares_change / previous['shares_held']) * 100, 2)

            holders_list.append({
                'institution_name': inst_name,
                'cik': data['cik'],
                'shares_held': latest.get('shares_held'),
                'market_value': latest.get('market_value'),
                'percent_of_portfolio': latest.get('percent_of_portfolio'),
                'latest_filing_date': latest.get('filing_date'),
                'shares_change': shares_change,
                'shares_change_pct': shares_change_pct
            })

        # Sort by market value descending
        holders_list.sort(key=lambda x: x.get('market_value') or 0, reverse=True)

        return {
            "ticker": ticker.upper(),
            "total_institutions": len(holders_list),
            "as_of_date": holdings[0].get('filing_date') if holdings else None,
            "holders": holders_list[:limit]
        }

    except Exception as e:
        logger.error(f"Error getting institutional holders for {ticker}: {e}")
        return {
            "ticker": ticker.upper(),
            "total_institutions": 0,
            "as_of_date": None,
            "holders": [],
            "error": str(e)
        }
