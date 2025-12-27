"""Trading signals endpoints"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from enum import Enum
from loguru import logger

from app.services.data_storage import data_storage
from app.services.signal_generator import SignalGeneratorService

router = APIRouter()


class SignalType(str, Enum):
    EXTREME_FLOW = "EXTREME_FLOW"
    FLOW_PRICE_DIVERGENCE = "FLOW_PRICE_DIVERGENCE"
    FUTURES_SPOT_BASIS = "FUTURES_SPOT_BASIS"
    MOMENTUM_ALIGNMENT = "MOMENTUM_ALIGNMENT"
    SMART_MONEY_DIVERGENCE = "SMART_MONEY_DIVERGENCE"
    KOREAN_RETAIL_EUPHORIA = "KOREAN_RETAIL_EUPHORIA"
    INSTITUTIONAL_ACCUMULATION = "INSTITUTIONAL_ACCUMULATION"


class SignalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"


@router.get("/")
async def get_signals(
    ticker: Optional[str] = Query(None),
    signal_type: Optional[SignalType] = Query(None),
    status: SignalStatus = Query(SignalStatus.ACTIVE)
):
    """
    Get trading signals

    - **ticker**: Filter by ticker (optional)
    - **signal_type**: Filter by signal type (optional)
    - **status**: Filter by status (ACTIVE, EXPIRED, CLOSED)
    """
    try:
        signals = await data_storage.get_signals(
            ticker=ticker.upper() if ticker else None,
            signal_type=signal_type.value if signal_type else None,
            status=status.value,
            limit=100
        )

        return {
            "ticker": ticker,
            "signal_type": signal_type,
            "status": status,
            "signals": signals
        }
    except Exception as e:
        logger.error(f"Error retrieving signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_signals():
    """
    Get the latest active signal for each ticker
    """
    try:
        # Get latest signals for AGQ and UGL
        all_signals = []

        for ticker in ['AGQ', 'UGL']:
            signals = await data_storage.get_signals(
                ticker=ticker,
                status='ACTIVE',
                limit=1
            )
            if signals:
                all_signals.extend(signals)

        return {
            "signals": all_signals
        }
    except Exception as e:
        logger.error(f"Error retrieving latest signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{signal_id}")
async def get_signal_detail(signal_id: int):
    """
    Get detailed information about a specific signal
    """
    try:
        from sqlalchemy import select
        from app.models import Signal
        from app.db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            stmt = select(Signal).where(Signal.id == signal_id)
            result = await session.execute(stmt)
            signal = result.scalar_one_or_none()

            if not signal:
                raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")

            return {
                "id": signal.id,
                "ticker": signal.ticker,
                "signal_type": signal.signal_type,
                "direction": signal.direction,
                "strength": float(signal.strength) if signal.strength else None,
                "trigger_values": signal.trigger_values,
                "generated_at": signal.generated_at.isoformat(),
                "expires_at": signal.expires_at.isoformat() if signal.expires_at else None,
                "closed_at": signal.closed_at.isoformat() if signal.closed_at else None,
                "status": signal.status,
                "notes": signal.notes
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving signal {signal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/performance")
async def get_signal_performance(
    ticker: Optional[str] = Query(None),
    signal_type: Optional[SignalType] = Query(None)
):
    """
    Get historical signal performance metrics

    Returns:
    - Total signals generated
    - Win rate (simplified: count of closed vs expired)
    - Average hold time
    """
    try:
        # Get closed and expired signals
        closed_signals = await data_storage.get_signals(
            ticker=ticker.upper() if ticker else None,
            signal_type=signal_type.value if signal_type else None,
            status='CLOSED',
            limit=1000
        )

        expired_signals = await data_storage.get_signals(
            ticker=ticker.upper() if ticker else None,
            signal_type=signal_type.value if signal_type else None,
            status='EXPIRED',
            limit=1000
        )

        total_signals = len(closed_signals) + len(expired_signals)

        if total_signals == 0:
            return {
                "ticker": ticker,
                "signal_type": signal_type,
                "total_signals": 0,
                "win_rate": None,
                "avg_hold_time_days": None
            }

        # Calculate win rate (simplified: closed signals are wins, expired are losses)
        win_rate = len(closed_signals) / total_signals if total_signals > 0 else None

        # Calculate average hold time
        from datetime import datetime
        hold_times = []

        for sig in closed_signals:
            if sig['generated_at'] and sig['closed_at']:
                gen_time = datetime.fromisoformat(sig['generated_at'].replace('Z', '+00:00'))
                close_time = datetime.fromisoformat(sig['closed_at'].replace('Z', '+00:00'))
                hold_time = (close_time - gen_time).days
                hold_times.append(hold_time)

        for sig in expired_signals:
            if sig['generated_at'] and sig['expires_at']:
                gen_time = datetime.fromisoformat(sig['generated_at'].replace('Z', '+00:00'))
                expire_time = datetime.fromisoformat(sig['expires_at'].replace('Z', '+00:00'))
                hold_time = (expire_time - gen_time).days
                hold_times.append(hold_time)

        avg_hold_time = sum(hold_times) / len(hold_times) if hold_times else None

        return {
            "ticker": ticker,
            "signal_type": signal_type,
            "total_signals": total_signals,
            "win_rate": round(win_rate, 3) if win_rate else None,
            "avg_hold_time_days": round(avg_hold_time, 1) if avg_hold_time else None
        }

    except Exception as e:
        logger.error(f"Error calculating signal performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))
