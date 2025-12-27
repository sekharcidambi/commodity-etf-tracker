"""Signal generation service for creating trading signals"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import numpy as np
from loguru import logger

from app.services.data_storage import DataStorageService
from app.services.flow_statistics import FlowStatisticsService


class SignalGeneratorService:
    """Service for generating trading signals from flow and price data"""

    def __init__(self):
        self.data_storage = DataStorageService()
        self.flow_stats_service = FlowStatisticsService()

        # Signal expiration defaults (in days)
        self.SIGNAL_EXPIRATION_DAYS = {
            "EXTREME_FLOW": 14,  # 2 weeks
            "FLOW_PRICE_DIVERGENCE": 7,  # 1 week
            "FUTURES_SPOT_BASIS": 14,  # 2 weeks
            "MOMENTUM_ALIGNMENT": 7,  # 1 week
            "SMART_MONEY_DIVERGENCE": 14,  # 2 weeks
            "KOREAN_RETAIL_EUPHORIA": 7,  # 1 week
            "INSTITUTIONAL_ACCUMULATION": 90  # 3 months (longer-term signal)
        }

    async def generate_signals(self, ticker: str) -> List[Dict[str, Any]]:
        """
        Generate all applicable signals for a ticker

        Args:
            ticker: ETF ticker symbol

        Returns:
            List of signal dictionaries ready for database insertion
        """
        signals = []

        try:
            # Check each signal type
            signal_checks = [
                self.check_extreme_flow(ticker),
                self.check_flow_price_divergence(ticker),
                self.check_momentum_alignment(ticker),
                self.check_smart_money_divergence(ticker),
                self.check_korean_retail_euphoria(ticker),
                self.check_institutional_accumulation(ticker),
            ]

            # Execute all checks
            for check in signal_checks:
                signal = await check
                if signal:
                    signals.append(signal)

            logger.info(f"Generated {len(signals)} signals for {ticker}")
            return signals

        except Exception as e:
            logger.error(f"Error generating signals for {ticker}: {e}")
            return []

    async def check_extreme_flow(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Signal Type 1: EXTREME_FLOW
        Trigger: Flow z-score exceeds ±2.0 (top/bottom 2.5% historically)
        """
        try:
            stats = await self.flow_stats_service.calculate_flow_statistics(ticker, "4w")

            if not stats or stats['z_score'] is None:
                return None

            z_score = stats['z_score']

            # Check if z-score is extreme (outside ±2.0)
            if abs(z_score) > 2.0:
                direction = "BUY" if z_score > 2.0 else "SELL"
                strength = min(abs(z_score) / 3.0, 1.0)  # Cap at 1.0 for z=3.0+

                return self._create_signal(
                    ticker=ticker,
                    signal_type="EXTREME_FLOW",
                    direction=direction,
                    strength=strength,
                    trigger_values={
                        "z_score": float(z_score),
                        "percentile": stats['percentile'],
                        "rolling_sum_4w": stats['rolling_sum'],
                        "threshold": 2.0
                    },
                    notes=f"Extreme {'inflow' if z_score > 0 else 'outflow'} detected (z-score: {z_score:.2f})"
                )

            return None

        except Exception as e:
            logger.error(f"Error checking extreme flow for {ticker}: {e}")
            return None

    async def check_flow_price_divergence(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Signal Type 2: FLOW_PRICE_DIVERGENCE
        Trigger: Flow and price move in opposite directions
        """
        try:
            # Get 4-week flow stats
            flow_stats = await self.flow_stats_service.calculate_flow_statistics(ticker, "4w")
            if not flow_stats or flow_stats['rolling_sum'] is None:
                return None

            # Get price data (30 days ~ 4 weeks)
            prices = await self.data_storage.get_price_data(ticker, limit=30)
            if not prices or len(prices) < 20:
                return None

            # Calculate 4-week price change
            current_price = float(prices[0]['close'])
            price_4w_ago = float(prices[min(19, len(prices)-1)]['close'])  # ~4 weeks ago
            price_change_pct = (current_price - price_4w_ago) / price_4w_ago

            flow_trend = flow_stats['rolling_sum']

            # Check for divergence
            if flow_trend > 0 and price_change_pct < -0.05:  # Buying but price down >5%
                direction = "BUY"
                strength = min(abs(flow_trend) / 100.0, 1.0) * (abs(price_change_pct) / 0.10)
                strength = min(strength, 1.0)

                return self._create_signal(
                    ticker=ticker,
                    signal_type="FLOW_PRICE_DIVERGENCE",
                    direction=direction,
                    strength=strength,
                    trigger_values={
                        "flow_4w": float(flow_trend),
                        "price_change_pct": float(price_change_pct),
                        "current_price": current_price,
                        "price_4w_ago": price_4w_ago
                    },
                    notes=f"Positive flows ({flow_trend:.1f}M) despite price decline ({price_change_pct*100:.1f}%)"
                )

            elif flow_trend < 0 and price_change_pct > 0.05:  # Selling but price up >5%
                direction = "SELL"
                strength = min(abs(flow_trend) / 100.0, 1.0) * (abs(price_change_pct) / 0.10)
                strength = min(strength, 1.0)

                return self._create_signal(
                    ticker=ticker,
                    signal_type="FLOW_PRICE_DIVERGENCE",
                    direction=direction,
                    strength=strength,
                    trigger_values={
                        "flow_4w": float(flow_trend),
                        "price_change_pct": float(price_change_pct),
                        "current_price": current_price,
                        "price_4w_ago": price_4w_ago
                    },
                    notes=f"Negative flows ({flow_trend:.1f}M) despite price rally ({price_change_pct*100:.1f}%)"
                )

            return None

        except Exception as e:
            logger.error(f"Error checking flow/price divergence for {ticker}: {e}")
            return None

    async def check_momentum_alignment(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Signal Type 4: MOMENTUM_ALIGNMENT
        Trigger: Flow momentum and price momentum aligned
        """
        try:
            # Get flow stats for multiple windows
            flow_4w = await self.flow_stats_service.calculate_flow_statistics(ticker, "4w")
            flow_13w = await self.flow_stats_service.calculate_flow_statistics(ticker, "13w")

            if not flow_4w or not flow_13w:
                return None
            if flow_4w['rolling_sum'] is None or flow_13w['rolling_sum'] is None:
                return None

            # Get price data
            prices = await self.data_storage.get_price_data(ticker, limit=90)
            if not prices or len(prices) < 65:
                return None

            # Calculate price momentum
            current_price = float(prices[0]['close'])
            price_4w_ago = float(prices[min(19, len(prices)-1)]['close'])
            price_13w_ago = float(prices[min(64, len(prices)-1)]['close'])

            price_change_4w = (current_price - price_4w_ago) / price_4w_ago
            price_change_13w = (current_price - price_13w_ago) / price_13w_ago

            # Check momentum alignment
            flow_momentum_positive = flow_4w['rolling_sum'] > flow_13w['rolling_sum'] / 3.25  # Normalize for window size
            price_momentum_positive = price_change_4w > price_change_13w / 3.25

            flow_momentum_negative = flow_4w['rolling_sum'] < flow_13w['rolling_sum'] / 3.25
            price_momentum_negative = price_change_4w < price_change_13w / 3.25

            if flow_momentum_positive and price_momentum_positive:
                direction = "BUY"
                strength = min((abs(price_change_4w) + abs(flow_4w['z_score'] or 0) / 2) / 2, 1.0)

                return self._create_signal(
                    ticker=ticker,
                    signal_type="MOMENTUM_ALIGNMENT",
                    direction=direction,
                    strength=strength,
                    trigger_values={
                        "flow_4w": float(flow_4w['rolling_sum']),
                        "flow_13w": float(flow_13w['rolling_sum']),
                        "price_change_4w": float(price_change_4w),
                        "price_change_13w": float(price_change_13w)
                    },
                    notes=f"Positive flow and price momentum aligned"
                )

            elif flow_momentum_negative and price_momentum_negative:
                direction = "SELL"
                strength = min((abs(price_change_4w) + abs(flow_4w['z_score'] or 0) / 2) / 2, 1.0)

                return self._create_signal(
                    ticker=ticker,
                    signal_type="MOMENTUM_ALIGNMENT",
                    direction=direction,
                    strength=strength,
                    trigger_values={
                        "flow_4w": float(flow_4w['rolling_sum']),
                        "flow_13w": float(flow_13w['rolling_sum']),
                        "price_change_4w": float(price_change_4w),
                        "price_change_13w": float(price_change_13w)
                    },
                    notes=f"Negative flow and price momentum aligned"
                )

            return None

        except Exception as e:
            logger.error(f"Error checking momentum alignment for {ticker}: {e}")
            return None

    async def check_smart_money_divergence(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Signal Type 5: SMART_MONEY_DIVERGENCE
        Trigger: Institutional flows diverge from retail flows
        """
        try:
            # Get investor segment flows
            segments = await self.data_storage.get_investor_segment_flows(ticker, limit=8)  # ~8 weeks

            if not segments or 'INSTITUTIONAL' not in segments or 'KOREAN_RETAIL' not in segments:
                return None

            # Calculate recent flows for each segment (last 4 weeks)
            inst_flows = segments['INSTITUTIONAL'][:4] if len(segments['INSTITUTIONAL']) >= 4 else segments['INSTITUTIONAL']
            retail_flows = segments['KOREAN_RETAIL'][:4] if len(segments['KOREAN_RETAIL']) >= 4 else segments['KOREAN_RETAIL']

            if not inst_flows or not retail_flows:
                return None

            inst_4w_sum = sum([f['estimated_flow'] or 0 for f in inst_flows])
            retail_4w_sum = sum([f['estimated_flow'] or 0 for f in retail_flows])

            # Check for divergence (institutions buying, retail selling)
            if inst_4w_sum > 10 and retail_4w_sum < -10:  # Threshold: $10M
                direction = "BUY"
                strength = min(abs(inst_4w_sum) / 50.0, 1.0)  # Scale to 0-1

                return self._create_signal(
                    ticker=ticker,
                    signal_type="SMART_MONEY_DIVERGENCE",
                    direction=direction,
                    strength=strength,
                    trigger_values={
                        "institutional_4w": float(inst_4w_sum),
                        "korean_retail_4w": float(retail_4w_sum),
                        "divergence_magnitude": float(inst_4w_sum - retail_4w_sum)
                    },
                    notes=f"Institutions accumulating ({inst_4w_sum:.1f}M) while retail sells ({retail_4w_sum:.1f}M)"
                )

            # Check for opposite divergence (retail buying, institutions selling)
            elif retail_4w_sum > 10 and inst_4w_sum < -10:
                direction = "SELL"
                strength = min(abs(retail_4w_sum) / 50.0, 1.0)

                return self._create_signal(
                    ticker=ticker,
                    signal_type="SMART_MONEY_DIVERGENCE",
                    direction=direction,
                    strength=strength,
                    trigger_values={
                        "institutional_4w": float(inst_4w_sum),
                        "korean_retail_4w": float(retail_4w_sum),
                        "divergence_magnitude": float(retail_4w_sum - inst_4w_sum)
                    },
                    notes=f"Retail buying ({retail_4w_sum:.1f}M) while institutions sell ({inst_4w_sum:.1f}M)"
                )

            return None

        except Exception as e:
            logger.error(f"Error checking smart money divergence for {ticker}: {e}")
            return None

    async def check_korean_retail_euphoria(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Signal Type 6: KOREAN_RETAIL_EUPHORIA
        Trigger: Korean retail flows extreme (contrarian indicator)
        """
        try:
            # Get Korean retail segment flows
            segments = await self.data_storage.get_investor_segment_flows(ticker, limit=52)
            if not segments or 'KOREAN_RETAIL' not in segments:
                return None

            retail_flows = segments['KOREAN_RETAIL']
            if len(retail_flows) < 13:  # Need at least 13 weeks for statistics
                return None

            # Calculate z-score for Korean retail 4-week rolling sum
            flow_values = np.array([f['estimated_flow'] or 0 for f in retail_flows])

            # Calculate 4-week rolling sums
            rolling_sums = []
            for i in range(len(flow_values) - 3):
                rolling_sums.append(np.sum(flow_values[i:i+4]))

            if not rolling_sums:
                return None

            rolling_sums = np.array(rolling_sums)
            current_rolling_sum = rolling_sums[0]
            mean = np.mean(rolling_sums)
            std_dev = np.std(rolling_sums)

            if std_dev == 0:
                return None

            z_score = (current_rolling_sum - mean) / std_dev

            # Check for extreme retail buying (contrarian sell signal)
            if z_score > 2.5:  # Higher threshold for contrarian signal
                direction = "SELL"
                strength = min((z_score - 2.0) / 2.0, 1.0)  # Scale above 2.0

                return self._create_signal(
                    ticker=ticker,
                    signal_type="KOREAN_RETAIL_EUPHORIA",
                    direction=direction,
                    strength=strength,
                    trigger_values={
                        "korean_retail_z_score": float(z_score),
                        "korean_retail_4w": float(current_rolling_sum),
                        "mean": float(mean),
                        "std_dev": float(std_dev)
                    },
                    notes=f"Extreme Korean retail buying (z-score: {z_score:.2f}) - contrarian sell signal"
                )

            # Check for extreme retail selling (contrarian buy signal)
            elif z_score < -2.5:
                direction = "BUY"
                strength = min((abs(z_score) - 2.0) / 2.0, 1.0)

                return self._create_signal(
                    ticker=ticker,
                    signal_type="KOREAN_RETAIL_EUPHORIA",
                    direction=direction,
                    strength=strength,
                    trigger_values={
                        "korean_retail_z_score": float(z_score),
                        "korean_retail_4w": float(current_rolling_sum),
                        "mean": float(mean),
                        "std_dev": float(std_dev)
                    },
                    notes=f"Extreme Korean retail selling (z-score: {z_score:.2f}) - contrarian buy signal"
                )

            return None

        except Exception as e:
            logger.error(f"Error checking Korean retail euphoria for {ticker}: {e}")
            return None

    async def check_institutional_accumulation(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Signal Type 7: INSTITUTIONAL_ACCUMULATION
        Trigger: 2+ quarters of consistent 13F institutional buying
        """
        try:
            # Get institutional holdings (last 3 quarters)
            holdings = await self.data_storage.get_institutional_holdings(ticker, limit=100)

            if not holdings:
                return None

            # Group by filing_date to get quarterly data
            quarterly_changes = {}
            for h in holdings:
                filing_date = h['filing_date']
                change_shares = h['change_shares']

                if filing_date not in quarterly_changes:
                    quarterly_changes[filing_date] = 0
                if change_shares:
                    quarterly_changes[filing_date] += change_shares

            # Get last 3 quarters
            sorted_quarters = sorted(quarterly_changes.keys(), reverse=True)[:3]

            if len(sorted_quarters) < 2:
                return None

            # Check for accumulation (2+ quarters of positive net change)
            accumulation_quarters = sum(1 for q in sorted_quarters if quarterly_changes[q] > 0)

            if accumulation_quarters >= 2:
                total_accumulation = sum(quarterly_changes[q] for q in sorted_quarters if quarterly_changes[q] > 0)

                direction = "BUY"
                strength = min(accumulation_quarters / 3.0, 1.0)

                return self._create_signal(
                    ticker=ticker,
                    signal_type="INSTITUTIONAL_ACCUMULATION",
                    direction=direction,
                    strength=strength,
                    trigger_values={
                        "accumulation_quarters": accumulation_quarters,
                        "total_shares_accumulated": int(total_accumulation),
                        "recent_quarters": [q for q in sorted_quarters],
                        "quarterly_changes": {q: int(quarterly_changes[q]) for q in sorted_quarters}
                    },
                    notes=f"Institutional accumulation for {accumulation_quarters} of last 3 quarters"
                )

            return None

        except Exception as e:
            logger.error(f"Error checking institutional accumulation for {ticker}: {e}")
            return None

    def _create_signal(
        self,
        ticker: str,
        signal_type: str,
        direction: str,
        strength: float,
        trigger_values: Dict[str, Any],
        notes: str
    ) -> Dict[str, Any]:
        """
        Create a signal dictionary ready for database insertion

        Returns:
            Signal dictionary with all required fields
        """
        now = datetime.now()
        expiration_days = self.SIGNAL_EXPIRATION_DAYS.get(signal_type, 7)
        expires_at = now + timedelta(days=expiration_days)

        return {
            "ticker": ticker,
            "signal_type": signal_type,
            "direction": direction,
            "strength": round(min(max(strength, 0.0), 1.0), 2),  # Clamp to 0.0-1.0
            "trigger_values": trigger_values,
            "status": "ACTIVE",
            "expires_at": expires_at,
            "notes": notes
        }
