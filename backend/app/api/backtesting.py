"""Backtesting API endpoints"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from loguru import logger

from app.services.backtesting_service import backtesting_service

router = APIRouter()


@router.post("/run")
async def run_backtest(
    start_date: date = Query(..., description="Backtest start date"),
    end_date: date = Query(..., description="Backtest end date"),
    tickers: str = Query("AGQ,UGL", description="Comma-separated tickers"),
    signal_types: Optional[str] = Query(None, description="Comma-separated signal types (optional, null=all)"),
    initial_capital: float = Query(100000, description="Starting capital"),
    position_size_pct: float = Query(10, description="Position size as % of capital"),
    stop_loss_pct: Optional[float] = Query(None, description="Stop loss % (optional)"),
    take_profit_pct: Optional[float] = Query(None, description="Take profit % (optional)"),
    max_holding_days: int = Query(14, description="Maximum holding period in days")
) -> Dict[str, Any]:
    """
    Run a backtest on historical signals

    Tests how signals would have performed if traded with the specified parameters.
    """
    try:
        # Parse tickers
        ticker_list = [t.strip().upper() for t in tickers.split(',')]

        # Parse signal types if provided
        signal_type_list = None
        if signal_types:
            signal_type_list = [s.strip().upper() for s in signal_types.split(',')]

        # Build configuration
        config = {
            'initial_capital': initial_capital,
            'position_size_pct': position_size_pct,
            'max_holding_days': max_holding_days
        }

        if stop_loss_pct is not None:
            config['stop_loss_pct'] = stop_loss_pct

        if take_profit_pct is not None:
            config['take_profit_pct'] = take_profit_pct

        logger.info(f"Starting backtest: {start_date} to {end_date}, tickers={ticker_list}")

        # Run backtest
        results = await backtesting_service.run_backtest(
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time()),
            tickers=ticker_list,
            signal_types=signal_type_list,
            config=config
        )

        return {
            "status": "completed",
            "parameters": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "tickers": ticker_list,
                "signal_types": signal_type_list,
                "config": config
            },
            "results": results,
            "completed_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signal-performance/{signal_type}")
async def get_signal_type_performance(
    signal_type: str,
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    days: int = Query(90, description="Lookback period in days")
) -> Dict[str, Any]:
    """
    Get historical performance for a specific signal type
    """
    try:
        signal_type = signal_type.upper()

        performance = await backtesting_service.get_signal_type_performance(
            signal_type=signal_type,
            ticker=ticker.upper() if ticker else None,
            days=days
        )

        return {
            "signal_type": signal_type,
            "ticker": ticker,
            "lookback_days": days,
            "performance": performance,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting signal performance for {signal_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signal-performance")
async def get_all_signal_performance(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    days: int = Query(90, description="Lookback period in days")
) -> Dict[str, Any]:
    """
    Get historical performance for all signal types
    """
    try:
        # All signal types
        signal_types = [
            "EXTREME_FLOW",
            "FLOW_PRICE_DIVERGENCE",
            "FUTURES_SPOT_BASIS",
            "MOMENTUM_ALIGNMENT",
            "SMART_MONEY_DIVERGENCE",
            "KOREAN_RETAIL_EUPHORIA",
            "INSTITUTIONAL_ACCUMULATION",
            "PREMIUM_DISCOUNT_EXTREME",
            "COT_EXTREME_POSITIONING",
            "RETAIL_SENTIMENT_SPIKE"
        ]

        results = {}
        for signal_type in signal_types:
            try:
                perf = await backtesting_service.get_signal_type_performance(
                    signal_type=signal_type,
                    ticker=ticker.upper() if ticker else None,
                    days=days
                )
                if perf and perf.get('total_signals', 0) > 0:
                    results[signal_type] = perf
            except Exception as e:
                logger.warning(f"Error getting performance for {signal_type}: {e}")

        return {
            "ticker": ticker,
            "lookback_days": days,
            "signal_types_count": len(results),
            "performance_by_type": results,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting all signal performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs")
async def get_backtest_runs(
    limit: int = Query(20, description="Number of runs to return"),
    status: Optional[str] = Query(None, description="Filter by status")
) -> Dict[str, Any]:
    """
    Get list of backtest runs
    """
    try:
        runs = await backtesting_service.get_backtest_runs(
            limit=limit,
            status=status.upper() if status else None
        )

        return {
            "count": len(runs),
            "runs": runs,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting backtest runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}")
async def get_backtest_run(run_id: int) -> Dict[str, Any]:
    """
    Get details of a specific backtest run
    """
    try:
        run = await backtesting_service.get_backtest_run(run_id)

        if not run:
            raise HTTPException(status_code=404, detail=f"Backtest run {run_id} not found")

        return {
            "run": run,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest run {run_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/leaderboard")
async def get_signal_leaderboard(
    days: int = Query(90, description="Lookback period in days"),
    min_signals: int = Query(5, description="Minimum signals to include")
) -> Dict[str, Any]:
    """
    Get a leaderboard of signal types ranked by performance
    """
    try:
        # Get performance for all signal types
        signal_types = [
            "EXTREME_FLOW",
            "FLOW_PRICE_DIVERGENCE",
            "FUTURES_SPOT_BASIS",
            "MOMENTUM_ALIGNMENT",
            "SMART_MONEY_DIVERGENCE",
            "KOREAN_RETAIL_EUPHORIA",
            "INSTITUTIONAL_ACCUMULATION",
            "PREMIUM_DISCOUNT_EXTREME",
            "COT_EXTREME_POSITIONING",
            "RETAIL_SENTIMENT_SPIKE"
        ]

        leaderboard = []
        for signal_type in signal_types:
            try:
                perf = await backtesting_service.get_signal_type_performance(
                    signal_type=signal_type,
                    ticker=None,
                    days=days
                )
                if perf and perf.get('total_signals', 0) >= min_signals:
                    leaderboard.append({
                        "signal_type": signal_type,
                        "total_signals": perf.get('total_signals', 0),
                        "win_rate": perf.get('win_rate', 0),
                        "avg_return": perf.get('avg_return', 0),
                        "profit_factor": perf.get('profit_factor', 0),
                        "sharpe_ratio": perf.get('sharpe_ratio', 0)
                    })
            except Exception as e:
                logger.warning(f"Error getting performance for {signal_type}: {e}")

        # Sort by win rate
        leaderboard.sort(key=lambda x: x.get('win_rate', 0), reverse=True)

        return {
            "lookback_days": days,
            "min_signals": min_signals,
            "signal_types_count": len(leaderboard),
            "leaderboard": leaderboard,
            "retrieved_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting signal leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))
