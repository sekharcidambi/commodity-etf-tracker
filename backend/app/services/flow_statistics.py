"""Flow statistics service for calculating z-scores and percentiles"""

from datetime import datetime, timedelta
from typing import Optional
import numpy as np
from loguru import logger

from app.services.data_storage import DataStorageService


class FlowStatisticsService:
    """Service for calculating flow statistics including z-scores and percentiles"""

    def __init__(self):
        self.data_storage = DataStorageService()

        # Window definitions in weeks
        self.WINDOW_WEEKS = {
            "4w": 4,
            "13w": 13,
            "26w": 26,
            "52w": 52
        }

    async def calculate_flow_statistics(
        self,
        ticker: str,
        window: str = "52w"
    ) -> dict:
        """
        Calculate flow statistics for a given window

        Args:
            ticker: ETF ticker (AGQ, UGL)
            window: Time window (4w, 13w, 26w, 52w)

        Returns:
            Dictionary with:
                - ticker: Ticker symbol
                - window: Window period
                - current_flow: Most recent week's flow
                - rolling_sum: Sum of net_flow over window
                - z_score: Standardized score
                - percentile: Historical percentile rank (0-100)
                - mean: 52-week average flow
                - std_dev: 52-week standard deviation
        """
        if window not in self.WINDOW_WEEKS:
            raise ValueError(f"Invalid window: {window}. Must be one of {list(self.WINDOW_WEEKS.keys())}")

        # Get flow data - need at least 104 weeks (2 years) for robust statistics
        flows = await self.data_storage.get_etf_flows(
            ticker=ticker,
            limit=104
        )

        if not flows or len(flows) == 0:
            logger.warning(f"No flow data available for {ticker}")
            return self._empty_response(ticker, window)

        # Convert to numpy arrays for calculations
        flow_values = np.array([float(flow['net_flow'] or 0) for flow in flows])
        weeks = len(flow_values)

        if weeks < self.WINDOW_WEEKS[window]:
            logger.warning(f"Insufficient data for {window} window (have {weeks} weeks, need {self.WINDOW_WEEKS[window]})")
            return self._partial_response(ticker, window, flows, flow_values)

        # Calculate current window rolling sum
        window_size = self.WINDOW_WEEKS[window]
        current_rolling_sum = np.sum(flow_values[:window_size])
        current_flow = float(flow_values[0]) if len(flow_values) > 0 else None

        # Calculate 52-week baseline statistics for z-score
        # Use all available rolling windows for distribution
        baseline_weeks = min(52, weeks)

        # Calculate all possible rolling sums for this window size
        rolling_sums = []
        for i in range(len(flow_values) - window_size + 1):
            rolling_sums.append(np.sum(flow_values[i:i+window_size]))

        rolling_sums = np.array(rolling_sums)

        # Calculate mean and std dev from rolling sums
        mean = float(np.mean(rolling_sums))
        std_dev = float(np.std(rolling_sums))

        # Calculate z-score
        if std_dev > 0:
            z_score = (current_rolling_sum - mean) / std_dev
        else:
            z_score = 0.0

        # Calculate percentile rank
        percentile = float(np.sum(rolling_sums <= current_rolling_sum) / len(rolling_sums) * 100)

        return {
            "ticker": ticker,
            "window": window,
            "current_flow": current_flow,
            "rolling_sum": float(current_rolling_sum),
            "z_score": float(z_score),
            "percentile": float(percentile),
            "mean": mean,
            "std_dev": std_dev
        }

    async def get_all_windows_statistics(
        self,
        ticker: str
    ) -> dict:
        """
        Get statistics for all time windows

        Args:
            ticker: ETF ticker

        Returns:
            Dictionary with keys: "4w", "13w", "26w", "52w"
            Each containing the statistics for that window
        """
        results = {}

        for window in self.WINDOW_WEEKS.keys():
            try:
                stats = await self.calculate_flow_statistics(ticker, window)
                results[window] = stats
            except Exception as e:
                logger.error(f"Error calculating {window} statistics for {ticker}: {e}")
                results[window] = self._empty_response(ticker, window)

        return results

    def _empty_response(self, ticker: str, window: str) -> dict:
        """Return empty response when no data available"""
        return {
            "ticker": ticker,
            "window": window,
            "current_flow": None,
            "rolling_sum": None,
            "z_score": None,
            "percentile": None,
            "mean": None,
            "std_dev": None
        }

    def _partial_response(self, ticker: str, window: str, flows: list, flow_values: np.ndarray) -> dict:
        """Return partial response with available data when window is too large"""
        current_flow = float(flow_values[0]) if len(flow_values) > 0 else None

        return {
            "ticker": ticker,
            "window": window,
            "current_flow": current_flow,
            "rolling_sum": float(np.sum(flow_values)),  # Sum all available
            "z_score": None,
            "percentile": None,
            "mean": None,
            "std_dev": None
        }
