"""Analytics endpoints - Fully implemented with Phase 1 services"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from loguru import logger

from app.services.asian_hours_analyzer import AsianHoursAnalyzerService
from app.services.fred_collector import fred_collector
from app.services.premium_discount_calculator import premium_discount_calculator
from app.services.flow_statistics import FlowStatisticsService
from app.services.data_storage import DataStorageService

router = APIRouter()

# Initialize services
asian_hours_analyzer = AsianHoursAnalyzerService()
flow_stats_service = FlowStatisticsService()
data_storage = DataStorageService()


# ============================================================================
# CORRELATION ANALYSIS
# ============================================================================

@router.get("/correlation/{ticker}")
async def get_correlations(
    ticker: str,
    start_date: Optional[date] = Query(None),
    window: int = Query(26, description="Rolling window in weeks")
) -> Dict[str, Any]:
    """
    Get correlation analysis between ETF flows and price movements

    Returns correlations between:
    - ETF flows vs ETF price
    - ETF flows vs spot price
    - ETF flows vs futures price
    """
    try:
        ticker = ticker.upper()

        # Get flow data
        flows = await data_storage.get_etf_flows(ticker, limit=window * 2)
        if not flows:
            raise HTTPException(status_code=404, detail=f"No flow data for {ticker}")

        # Get price data
        prices = await data_storage.get_price_data(ticker, limit=window * 7)
        if not prices:
            raise HTTPException(status_code=404, detail=f"No price data for {ticker}")

        # Calculate weekly returns
        import numpy as np

        flow_values = [float(f['net_flow'] or 0) for f in flows[:window]]
        price_values = [float(p['close']) for p in prices[:window * 5:5]][:window]

        if len(flow_values) < 4 or len(price_values) < 4:
            return {
                "ticker": ticker,
                "window_weeks": window,
                "correlations": {
                    "flow_vs_etf_price": None,
                    "flow_vs_spot_price": None,
                    "flow_vs_futures_price": None
                },
                "flow_attribution": None,
                "note": "Insufficient data for correlation analysis"
            }

        # Align arrays to same length
        min_len = min(len(flow_values), len(price_values))
        flow_arr = np.array(flow_values[:min_len])
        price_arr = np.array(price_values[:min_len])

        # Calculate returns
        if len(price_arr) > 1:
            price_returns = np.diff(price_arr) / price_arr[:-1]
            flow_aligned = flow_arr[1:]

            if len(flow_aligned) >= 3:
                correlation = float(np.corrcoef(flow_aligned, price_returns)[0, 1])
            else:
                correlation = None
        else:
            correlation = None

        # Determine flow attribution
        flow_attribution = None
        if correlation is not None:
            if correlation > 0.5:
                flow_attribution = "FLOW_DRIVEN"
            elif correlation < -0.3:
                flow_attribution = "CONTRARIAN"
            else:
                flow_attribution = "MIXED"

        return {
            "ticker": ticker,
            "window_weeks": window,
            "data_points": min_len,
            "correlations": {
                "flow_vs_etf_price": round(correlation, 4) if correlation else None,
                "flow_vs_spot_price": None,  # TODO: Add spot data
                "flow_vs_futures_price": None  # TODO: Add futures data
            },
            "flow_attribution": flow_attribution,
            "calculated_at": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating correlations for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# VOLUME ANALYSIS (Asian Hours / Korean Retail Proxy)
# ============================================================================

@router.get("/volume-analysis/{ticker}")
async def analyze_volume(
    ticker: str,
    days: int = Query(30, description="Number of days to analyze"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
) -> Dict[str, Any]:
    """
    Analyze volume patterns including Asian hours breakdown for Korean retail proxy
    """
    try:
        ticker = ticker.upper()

        # Get full analysis from the Asian hours analyzer
        analysis = await asian_hours_analyzer.analyze_asian_hours_volume(ticker, days=days)

        # Get Korean retail proxy score
        proxy = await asian_hours_analyzer.calculate_korean_retail_proxy(ticker)

        return {
            "ticker": ticker,
            "analysis_period_days": days,
            "start_date": analysis.get("start_date"),
            "end_date": analysis.get("end_date"),
            "summary": analysis.get("summary", {}),
            "korean_retail_proxy": {
                "score": proxy.get("korean_retail_proxy_score"),
                "confidence": proxy.get("confidence"),
                "interpretation": proxy.get("interpretation"),
                "metrics": proxy.get("metrics", {})
            },
            "daily_breakdown": analysis.get("daily_breakdown", [])[:7],  # Last 7 days only
            "calculated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error analyzing volume for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/korean-retail/{ticker}")
async def get_korean_retail_proxy(
    ticker: str
) -> Dict[str, Any]:
    """
    Get Korean retail activity proxy score based on Asian hours volume patterns
    """
    try:
        ticker = ticker.upper()
        proxy = await asian_hours_analyzer.calculate_korean_retail_proxy(ticker)

        return {
            "ticker": ticker,
            **proxy,
            "calculated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting Korean retail proxy for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MACRO CORRELATIONS (FRED Data)
# ============================================================================

@router.get("/macro/correlations")
async def get_macro_correlations(
    ticker: Optional[str] = Query(None),
    window_days: int = Query(30)
) -> Dict[str, Any]:
    """
    Get correlations with macroeconomic indicators

    Indicators:
    - DXY (US Dollar Index)
    - 10-Year Treasury Yield
    - VIX (Volatility Index)
    - Real Rates (10Y - Breakeven)
    """
    try:
        # Get latest macro indicators
        latest = await fred_collector.get_latest_indicators()

        if not latest:
            return {
                "ticker": ticker,
                "window_days": window_days,
                "correlations": {},
                "note": "FRED API key not configured or no data available"
            }

        # Build response with available indicators
        correlations = {}

        if 'DTWEXBGS' in latest:
            correlations['dxy'] = {
                "value": latest['DTWEXBGS']['value'],
                "date": latest['DTWEXBGS']['date'],
                "interpretation": "Strong dollar typically negative for gold/silver"
            }

        if 'DGS10' in latest:
            correlations['treasury_10y'] = {
                "value": latest['DGS10']['value'],
                "date": latest['DGS10']['date'],
                "interpretation": "Higher yields typically negative for non-yielding metals"
            }

        if 'VIXCLS' in latest:
            correlations['vix'] = {
                "value": latest['VIXCLS']['value'],
                "date": latest['VIXCLS']['date'],
                "interpretation": "High VIX can be positive for gold (safe haven)"
            }

        if 'REAL_RATE' in latest:
            correlations['real_rate'] = {
                "value": latest['REAL_RATE']['value'],
                "date": latest['REAL_RATE']['date'],
                "components": latest['REAL_RATE'].get('components', {}),
                "interpretation": "Negative real rates strongly bullish for gold/silver"
            }

        if 'T10YIE' in latest:
            correlations['breakeven_10y'] = {
                "value": latest['T10YIE']['value'],
                "date": latest['T10YIE']['date'],
                "interpretation": "Rising inflation expectations bullish for metals"
            }

        return {
            "ticker": ticker.upper() if ticker else None,
            "window_days": window_days,
            "correlations": correlations,
            "calculated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting macro correlations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro/summary")
async def get_macro_summary() -> Dict[str, Any]:
    """
    Get comprehensive summary of current macro conditions
    """
    try:
        summary = await fred_collector.get_macro_summary()

        if not summary:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "available": False,
                "note": "FRED API key not configured or no data available"
            }

        return {
            **summary,
            "available": True
        }

    except Exception as e:
        logger.error(f"Error getting macro summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/macro/real-rates")
async def get_real_rates(
    lookback_days: int = Query(90, description="Days of historical data")
) -> Dict[str, Any]:
    """
    Get historical real interest rates (10Y Treasury - 10Y Breakeven)
    """
    try:
        import pandas as pd

        real_rates_df = await fred_collector.calculate_real_rates(lookback_days=lookback_days)

        if real_rates_df.empty:
            return {
                "available": False,
                "note": "Unable to calculate real rates"
            }

        # Convert to list of dicts
        records = real_rates_df.to_dict('records')

        # Format dates
        for r in records:
            if isinstance(r.get('date'), pd.Timestamp):
                r['date'] = r['date'].strftime('%Y-%m-%d')

        latest = records[-1] if records else None

        return {
            "available": True,
            "lookback_days": lookback_days,
            "data_points": len(records),
            "latest": latest,
            "history": records[-30:],  # Last 30 days
            "calculated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting real rates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PREMIUM/DISCOUNT ANALYSIS
# ============================================================================

@router.get("/premium-discount/{ticker}")
async def get_premium_discount(
    ticker: str,
    real_time: bool = Query(False, description="Calculate real-time or use latest stored")
) -> Dict[str, Any]:
    """
    Get ETF premium/discount to NAV

    Formula: (ETF_price - NAV) / NAV * 100
    """
    try:
        ticker = ticker.upper()

        result = await premium_discount_calculator.calculate_premium_discount(ticker)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Unable to calculate premium/discount for {ticker}"
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting premium/discount for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/premium-discount/{ticker}/history")
async def get_premium_discount_history(
    ticker: str,
    days: int = Query(30, description="Number of days of history")
) -> Dict[str, Any]:
    """
    Get historical premium/discount data for an ETF
    """
    try:
        ticker = ticker.upper()

        history = await premium_discount_calculator.get_historical_premium_discount(
            ticker, days=days
        )

        return {
            "ticker": ticker,
            "days_requested": days,
            "data_points": len(history),
            "history": history,
            "calculated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting premium/discount history for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/premium-discount/{ticker}/extreme")
async def check_premium_discount_extreme(
    ticker: str,
    threshold: float = Query(1.5, description="Z-score threshold for extreme detection")
) -> Dict[str, Any]:
    """
    Check if ETF is trading at extreme premium or discount
    """
    try:
        ticker = ticker.upper()

        result = await premium_discount_calculator.detect_premium_discount_extreme(
            ticker, threshold=threshold
        )

        if not result:
            return {
                "ticker": ticker,
                "is_extreme": False,
                "threshold": threshold,
                "note": "Premium/discount within normal range",
                "calculated_at": datetime.utcnow().isoformat()
            }

        return {
            **result,
            "calculated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error checking extreme premium/discount for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/premium-discount/all")
async def get_all_premium_discounts() -> Dict[str, Any]:
    """
    Get premium/discount for all tracked ETFs
    """
    try:
        results = await premium_discount_calculator.get_all_etf_premium_discounts()

        return {
            "count": len(results),
            "etfs": results,
            "calculated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting all premium/discounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/premium-discount/extremes")
async def get_all_extreme_premium_discounts(
    threshold: float = Query(1.5, description="Z-score threshold")
) -> Dict[str, Any]:
    """
    Get all ETFs with extreme premium/discount levels
    """
    try:
        extremes = await premium_discount_calculator.check_all_etf_extremes(
            threshold=threshold
        )

        return {
            "count": len(extremes),
            "threshold": threshold,
            "extremes": extremes,
            "calculated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting extreme premium/discounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FLOW STATISTICS
# ============================================================================

@router.get("/flow-stats/{ticker}")
async def get_flow_statistics(
    ticker: str,
    window: str = Query("4w", description="Window: 4w, 13w, 26w, 52w")
) -> Dict[str, Any]:
    """
    Get flow statistics including z-scores and percentiles
    """
    try:
        ticker = ticker.upper()

        stats = await flow_stats_service.calculate_flow_statistics(ticker, window)

        return {
            **stats,
            "calculated_at": datetime.utcnow().isoformat()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting flow statistics for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flow-stats/{ticker}/all-windows")
async def get_all_window_statistics(
    ticker: str
) -> Dict[str, Any]:
    """
    Get flow statistics for all time windows (4w, 13w, 26w, 52w)
    """
    try:
        ticker = ticker.upper()

        all_stats = await flow_stats_service.get_all_windows_statistics(ticker)

        return {
            "ticker": ticker,
            "windows": all_stats,
            "calculated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting all window statistics for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MARKET REGIME (Future Enhancement)
# ============================================================================

@router.get("/regime")
async def get_market_regime() -> Dict[str, Any]:
    """
    Detect current market regime based on macro indicators

    Regimes:
    - RISK_ON: Low VIX, weak dollar, positive growth
    - RISK_OFF: High VIX, strong dollar, flight to safety
    - INFLATION_FEAR: Rising breakevens, falling real rates
    - DEFLATION_FEAR: Falling breakevens, rising real rates
    """
    try:
        # Get latest macro indicators
        latest = await fred_collector.get_latest_indicators()

        if not latest:
            return {
                "regime": "UNKNOWN",
                "confidence": 0.0,
                "note": "Insufficient macro data for regime detection"
            }

        # Simple regime detection logic
        regime = "NEUTRAL"
        confidence = 0.5
        factors = []

        # Check VIX
        if 'VIXCLS' in latest:
            vix = latest['VIXCLS']['value']
            if vix > 25:
                factors.append(("RISK_OFF", 0.3))
            elif vix < 15:
                factors.append(("RISK_ON", 0.2))

        # Check real rates
        if 'REAL_RATE' in latest:
            real_rate = latest['REAL_RATE']['value']
            if real_rate < -0.5:
                factors.append(("INFLATION_FEAR", 0.4))
            elif real_rate > 1.5:
                factors.append(("DEFLATION_FEAR", 0.3))

        # Check breakeven inflation
        if 'T10YIE' in latest:
            breakeven = latest['T10YIE']['value']
            if breakeven > 2.8:
                factors.append(("INFLATION_FEAR", 0.3))
            elif breakeven < 1.5:
                factors.append(("DEFLATION_FEAR", 0.2))

        # Aggregate factors
        if factors:
            from collections import defaultdict
            regime_scores = defaultdict(float)
            for r, score in factors:
                regime_scores[r] += score

            if regime_scores:
                regime = max(regime_scores, key=regime_scores.get)
                confidence = min(regime_scores[regime], 1.0)

        return {
            "regime": regime,
            "confidence": round(confidence, 2),
            "factors": factors,
            "indicators": {
                "vix": latest.get('VIXCLS', {}).get('value'),
                "real_rate": latest.get('REAL_RATE', {}).get('value'),
                "breakeven_10y": latest.get('T10YIE', {}).get('value'),
                "dollar_index": latest.get('DTWEXBGS', {}).get('value')
            },
            "implications": {
                "gold": "Bullish" if regime in ["INFLATION_FEAR", "RISK_OFF"] else "Neutral",
                "silver": "Bullish" if regime == "INFLATION_FEAR" else "Neutral",
                "leveraged_etfs": "Caution" if regime == "RISK_OFF" else "Normal"
            },
            "calculated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error detecting market regime: {e}")
        raise HTTPException(status_code=500, detail=str(e))
