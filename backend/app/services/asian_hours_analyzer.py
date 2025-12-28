"""Asian hours volume analyzer for detecting Korean retail activity"""

from datetime import datetime, timedelta, date, time
from typing import List, Dict, Optional
import numpy as np
from loguru import logger
from zoneinfo import ZoneInfo
from sqlalchemy import select, and_, func

from app.services.data_storage import DataStorageService
from app.models import IntradayBar
from app.db.database import AsyncSessionLocal


class AsianHoursAnalyzerService:
    """Service for analyzing volume patterns during Asian trading hours to detect Korean retail activity"""

    def __init__(self):
        self.data_storage = DataStorageService()

        # Define trading sessions in US/Eastern timezone
        # Korean retail traders are active during Asian hours which map to:
        # - After-hours: 8:00 PM - 11:59 PM ET (after US market close)
        # - Pre-market: 4:00 AM - 9:30 AM ET (before US market open)
        self.SESSION_DEFINITIONS = {
            "after_hours": {
                "start": time(20, 0),  # 8:00 PM ET
                "end": time(23, 59)    # 11:59 PM ET
            },
            "pre_market": {
                "start": time(4, 0),   # 4:00 AM ET
                "end": time(9, 29)     # 9:29 AM ET (before market open)
            },
            "regular_hours": {
                "start": time(9, 30),  # 9:30 AM ET
                "end": time(15, 59)    # 3:59 PM ET (market close)
            }
        }

        self.ET_TIMEZONE = ZoneInfo("US/Eastern")

    def _classify_session(self, timestamp: datetime) -> str:
        """
        Classify a timestamp into a trading session

        Args:
            timestamp: Timezone-aware timestamp

        Returns:
            Session name: "after_hours", "pre_market", "regular_hours", or "other"
        """
        # Convert to ET timezone
        et_time = timestamp.astimezone(self.ET_TIMEZONE)
        time_only = et_time.time()

        for session_name, session_def in self.SESSION_DEFINITIONS.items():
            if session_def["start"] <= time_only <= session_def["end"]:
                return session_name

        return "other"

    async def get_volume_by_session(self, ticker: str, target_date: date) -> Dict:
        """
        Break down volume by trading session for a specific date

        Args:
            ticker: ETF ticker symbol
            target_date: Date to analyze

        Returns:
            Dictionary with volume breakdown by session:
                {
                    "date": "2025-12-28",
                    "ticker": "AGQ",
                    "sessions": {
                        "after_hours": {"volume": 12345, "bar_count": 24},
                        "pre_market": {"volume": 23456, "bar_count": 30},
                        "regular_hours": {"volume": 456789, "bar_count": 390},
                        "other": {"volume": 100, "bar_count": 5}
                    },
                    "asian_hours_volume": 35801,  # after_hours + pre_market
                    "regular_hours_volume": 456789,
                    "asian_volume_ratio": 0.078
                }
        """
        try:
            async with AsyncSessionLocal() as session:
                # Query all intraday bars for this date
                start_dt = datetime.combine(target_date, time(0, 0), tzinfo=self.ET_TIMEZONE)
                end_dt = start_dt + timedelta(days=1)

                stmt = select(IntradayBar).where(
                    and_(
                        IntradayBar.ticker == ticker,
                        IntradayBar.timestamp >= start_dt,
                        IntradayBar.timestamp < end_dt
                    )
                ).order_by(IntradayBar.timestamp)

                result = await session.execute(stmt)
                bars = result.scalars().all()

                if not bars:
                    logger.warning(f"No intraday data found for {ticker} on {target_date}")
                    return self._empty_session_response(ticker, target_date)

                # Classify and aggregate by session
                sessions = {
                    "after_hours": {"volume": 0, "bar_count": 0},
                    "pre_market": {"volume": 0, "bar_count": 0},
                    "regular_hours": {"volume": 0, "bar_count": 0},
                    "other": {"volume": 0, "bar_count": 0}
                }

                for bar in bars:
                    session_type = self._classify_session(bar.timestamp)
                    volume = int(bar.volume) if bar.volume else 0

                    sessions[session_type]["volume"] += volume
                    sessions[session_type]["bar_count"] += 1

                # Calculate Asian hours aggregates
                asian_hours_volume = (
                    sessions["after_hours"]["volume"] +
                    sessions["pre_market"]["volume"]
                )
                regular_hours_volume = sessions["regular_hours"]["volume"]

                # Calculate ratio
                asian_volume_ratio = 0.0
                if regular_hours_volume > 0:
                    asian_volume_ratio = asian_hours_volume / regular_hours_volume

                return {
                    "date": target_date.isoformat(),
                    "ticker": ticker,
                    "sessions": sessions,
                    "asian_hours_volume": asian_hours_volume,
                    "regular_hours_volume": regular_hours_volume,
                    "asian_volume_ratio": float(asian_volume_ratio)
                }

        except Exception as e:
            logger.error(f"Error getting volume by session for {ticker} on {target_date}: {e}")
            return self._empty_session_response(ticker, target_date)

    async def analyze_asian_hours_volume(
        self,
        ticker: str,
        days: int = 30
    ) -> Dict:
        """
        Analyze volume patterns over multiple days to detect trends in Korean retail activity

        Args:
            ticker: ETF ticker symbol
            days: Number of days to analyze (default 30)

        Returns:
            Dictionary with analysis results:
                {
                    "ticker": "AGQ",
                    "analysis_period_days": 30,
                    "start_date": "2025-11-28",
                    "end_date": "2025-12-28",
                    "daily_breakdown": [...],  # List of daily session breakdowns
                    "summary": {
                        "avg_asian_volume_ratio": 0.085,
                        "median_asian_volume_ratio": 0.078,
                        "std_asian_volume_ratio": 0.023,
                        "trend": "increasing",  # increasing, decreasing, stable
                        "total_asian_hours_volume": 1234567,
                        "total_regular_hours_volume": 14567890,
                        "days_with_data": 28
                    }
                }
        """
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            # Get volume breakdown for each day
            daily_breakdowns = []
            current_date = start_date

            while current_date <= end_date:
                breakdown = await self.get_volume_by_session(ticker, current_date)

                # Only include days with actual data
                if breakdown.get("regular_hours_volume", 0) > 0:
                    daily_breakdowns.append(breakdown)

                current_date += timedelta(days=1)

            if not daily_breakdowns:
                logger.warning(f"No data available for {ticker} in the last {days} days")
                return self._empty_analysis_response(ticker, days, start_date, end_date)

            # Calculate summary statistics
            ratios = [d["asian_volume_ratio"] for d in daily_breakdowns]
            total_asian = sum(d["asian_hours_volume"] for d in daily_breakdowns)
            total_regular = sum(d["regular_hours_volume"] for d in daily_breakdowns)

            # Determine trend using linear regression on ratios
            trend = self._calculate_trend(ratios)

            summary = {
                "avg_asian_volume_ratio": float(np.mean(ratios)),
                "median_asian_volume_ratio": float(np.median(ratios)),
                "std_asian_volume_ratio": float(np.std(ratios)),
                "min_asian_volume_ratio": float(np.min(ratios)),
                "max_asian_volume_ratio": float(np.max(ratios)),
                "trend": trend,
                "total_asian_hours_volume": total_asian,
                "total_regular_hours_volume": total_regular,
                "days_with_data": len(daily_breakdowns)
            }

            return {
                "ticker": ticker,
                "analysis_period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily_breakdown": daily_breakdowns,
                "summary": summary
            }

        except Exception as e:
            logger.error(f"Error analyzing Asian hours volume for {ticker}: {e}")
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            return self._empty_analysis_response(ticker, days, start_date, end_date)

    async def calculate_korean_retail_proxy(self, ticker: str) -> Dict:
        """
        Calculate a Korean retail activity proxy score (0-100)

        The score is based on:
        - Recent Asian hours volume ratio compared to historical baseline
        - Consistency of Asian hours activity
        - Trend direction

        Args:
            ticker: ETF ticker symbol

        Returns:
            Dictionary with score and supporting metrics:
                {
                    "ticker": "AGQ",
                    "korean_retail_proxy_score": 75.5,
                    "confidence": "high",  # high, medium, low
                    "metrics": {
                        "recent_asian_ratio": 0.12,
                        "baseline_asian_ratio": 0.08,
                        "ratio_percentile": 85.3,
                        "trend": "increasing",
                        "consistency_score": 0.78
                    },
                    "interpretation": "High Korean retail activity detected"
                }
        """
        try:
            # Analyze recent period (7 days) and baseline (90 days)
            recent_analysis = await self.analyze_asian_hours_volume(ticker, days=7)
            baseline_analysis = await self.analyze_asian_hours_volume(ticker, days=90)

            if not recent_analysis["daily_breakdown"] or not baseline_analysis["daily_breakdown"]:
                logger.warning(f"Insufficient data for Korean retail proxy calculation for {ticker}")
                return self._empty_proxy_response(ticker)

            recent_ratio = recent_analysis["summary"]["avg_asian_volume_ratio"]
            baseline_ratio = baseline_analysis["summary"]["avg_asian_volume_ratio"]
            trend = recent_analysis["summary"]["trend"]

            # Calculate percentile of recent ratio against historical distribution
            all_ratios = [d["asian_volume_ratio"] for d in baseline_analysis["daily_breakdown"]]
            ratio_percentile = float(np.sum(np.array(all_ratios) <= recent_ratio) / len(all_ratios) * 100)

            # Calculate consistency score (inverse of coefficient of variation)
            recent_std = recent_analysis["summary"]["std_asian_volume_ratio"]
            consistency_score = 0.0
            if recent_ratio > 0:
                cv = recent_std / recent_ratio  # Coefficient of variation
                consistency_score = max(0, min(1, 1 - cv))  # Normalize to 0-1

            # Calculate composite score (0-100)
            # Weight: 50% percentile, 30% trend, 20% consistency
            percentile_component = ratio_percentile * 0.5

            trend_component = 0.0
            if trend == "increasing":
                trend_component = 30.0
            elif trend == "stable":
                trend_component = 15.0

            consistency_component = consistency_score * 20.0

            proxy_score = percentile_component + trend_component + consistency_component

            # Determine confidence level based on data availability
            days_with_data = recent_analysis["summary"]["days_with_data"]
            if days_with_data >= 5:
                confidence = "high"
            elif days_with_data >= 3:
                confidence = "medium"
            else:
                confidence = "low"

            # Generate interpretation
            interpretation = self._generate_interpretation(proxy_score, trend)

            return {
                "ticker": ticker,
                "korean_retail_proxy_score": float(proxy_score),
                "confidence": confidence,
                "metrics": {
                    "recent_asian_ratio": float(recent_ratio),
                    "baseline_asian_ratio": float(baseline_ratio),
                    "ratio_percentile": float(ratio_percentile),
                    "trend": trend,
                    "consistency_score": float(consistency_score)
                },
                "interpretation": interpretation
            }

        except Exception as e:
            logger.error(f"Error calculating Korean retail proxy for {ticker}: {e}")
            return self._empty_proxy_response(ticker)

    def _calculate_trend(self, ratios: List[float]) -> str:
        """
        Calculate trend direction using simple linear regression

        Args:
            ratios: List of volume ratios over time

        Returns:
            "increasing", "decreasing", or "stable"
        """
        if len(ratios) < 3:
            return "stable"

        # Simple linear regression
        x = np.arange(len(ratios))
        y = np.array(ratios)

        # Calculate slope
        x_mean = np.mean(x)
        y_mean = np.mean(y)

        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Determine significance (relative to mean)
        if y_mean > 0:
            relative_slope = slope / y_mean

            if relative_slope > 0.05:  # 5% increase per day
                return "increasing"
            elif relative_slope < -0.05:  # 5% decrease per day
                return "decreasing"

        return "stable"

    def _generate_interpretation(self, score: float, trend: str) -> str:
        """Generate human-readable interpretation of the proxy score"""

        if score >= 75:
            level = "Very high"
        elif score >= 60:
            level = "High"
        elif score >= 40:
            level = "Moderate"
        elif score >= 25:
            level = "Low"
        else:
            level = "Minimal"

        trend_text = ""
        if trend == "increasing":
            trend_text = " and increasing"
        elif trend == "decreasing":
            trend_text = " but decreasing"

        return f"{level} Korean retail activity detected{trend_text}"

    def _empty_session_response(self, ticker: str, target_date: date) -> Dict:
        """Return empty response when no session data available"""
        return {
            "date": target_date.isoformat(),
            "ticker": ticker,
            "sessions": {
                "after_hours": {"volume": 0, "bar_count": 0},
                "pre_market": {"volume": 0, "bar_count": 0},
                "regular_hours": {"volume": 0, "bar_count": 0},
                "other": {"volume": 0, "bar_count": 0}
            },
            "asian_hours_volume": 0,
            "regular_hours_volume": 0,
            "asian_volume_ratio": 0.0
        }

    def _empty_analysis_response(
        self,
        ticker: str,
        days: int,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Return empty response when no analysis data available"""
        return {
            "ticker": ticker,
            "analysis_period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily_breakdown": [],
            "summary": {
                "avg_asian_volume_ratio": None,
                "median_asian_volume_ratio": None,
                "std_asian_volume_ratio": None,
                "min_asian_volume_ratio": None,
                "max_asian_volume_ratio": None,
                "trend": None,
                "total_asian_hours_volume": 0,
                "total_regular_hours_volume": 0,
                "days_with_data": 0
            }
        }

    def _empty_proxy_response(self, ticker: str) -> Dict:
        """Return empty response when proxy calculation not possible"""
        return {
            "ticker": ticker,
            "korean_retail_proxy_score": None,
            "confidence": "low",
            "metrics": {
                "recent_asian_ratio": None,
                "baseline_asian_ratio": None,
                "ratio_percentile": None,
                "trend": None,
                "consistency_score": None
            },
            "interpretation": "Insufficient data for analysis"
        }
