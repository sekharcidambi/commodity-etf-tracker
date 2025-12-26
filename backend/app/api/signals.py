"""Trading signals endpoints"""

from fastapi import APIRouter, Query
from typing import Optional, List
from enum import Enum

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
    # TODO: Implement database query
    return {
        "ticker": ticker,
        "signal_type": signal_type,
        "status": status,
        "signals": []
    }


@router.get("/latest")
async def get_latest_signals():
    """
    Get the latest active signal for each ticker
    """
    # TODO: Implement query for latest signals per ticker
    return {
        "signals": []
    }


@router.get("/{signal_id}")
async def get_signal_detail(signal_id: int):
    """
    Get detailed information about a specific signal
    """
    # TODO: Implement signal detail query
    return {
        "signal_id": signal_id,
        "ticker": None,
        "signal_type": None,
        "direction": None,
        "strength": None,
        "trigger_values": {},
        "generated_at": None,
        "expires_at": None,
        "status": None
    }


@router.get("/history/performance")
async def get_signal_performance(
    ticker: Optional[str] = Query(None),
    signal_type: Optional[SignalType] = Query(None)
):
    """
    Get historical signal performance metrics

    Returns:
    - Total signals generated
    - Win rate
    - Average return
    - Average hold time
    """
    # TODO: Implement performance calculation
    return {
        "ticker": ticker,
        "signal_type": signal_type,
        "total_signals": 0,
        "win_rate": None,
        "avg_return": None,
        "avg_hold_time_days": None
    }
