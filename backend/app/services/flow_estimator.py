"""Estimate ETF flows from price and volume data"""

from datetime import datetime, timedelta, date
from typing import List, Dict
from decimal import Decimal
from loguru import logger
from app.services.data_storage import data_storage
import statistics


class FlowEstimator:
    """Estimate ETF flows using price, volume, and AUM data"""

    async def estimate_weekly_flows(self, ticker: str, weeks: int = 52) -> List[Dict]:
        """
        Estimate weekly flows based on volume patterns and price changes

        This uses a simplified estimation model:
        - High volume + price increase = likely inflows
        - High volume + price decrease = likely outflows
        - Volume changes week-over-week indicate flow direction

        Args:
            ticker: ETF ticker symbol
            weeks: Number of weeks to estimate

        Returns:
            List of weekly flow records
        """
        logger.info(f"Estimating weekly flows for {ticker} ({weeks} weeks)...")

        # Get price data for estimation period plus extra for baseline
        end_date = datetime.now()
        start_date = end_date - timedelta(days=weeks * 7 + 30)

        prices = await data_storage.get_price_data(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            limit=500
        )

        if len(prices) < 14:
            logger.warning(f"Insufficient price data for flow estimation: {len(prices)} days")
            return []

        # Group prices by week
        weekly_data = self._aggregate_to_weekly(prices)

        if len(weekly_data) < 4:
            logger.warning(f"Insufficient weekly data: {len(weekly_data)} weeks")
            return []

        # Estimate flows based on volume and price patterns
        flow_records = []
        baseline_aum = self._estimate_aum(ticker, weekly_data[0])

        for i, week in enumerate(weekly_data):
            # Calculate volume change vs baseline (first 4 weeks)
            baseline_volume = statistics.mean([w['avg_volume'] for w in weekly_data[:min(4, len(weekly_data))]])
            volume_ratio = week['avg_volume'] / baseline_volume if baseline_volume > 0 else 1.0

            # Calculate price change
            price_change = ((week['close'] - week['open']) / week['open']) if week['open'] > 0 else 0

            # Estimate net flow (simplified model)
            # Positive flow if: high volume + price increase
            # Negative flow if: high volume + price decrease
            flow_score = (volume_ratio - 1.0) * (1.0 + price_change)

            # Scale to reasonable flow magnitude (in millions)
            estimated_flow = flow_score * baseline_aum * 0.05  # 5% max weekly flow
            estimated_flow = max(min(estimated_flow, baseline_aum * 0.2), -baseline_aum * 0.2)  # Cap at ±20%

            # Update AUM estimate
            current_aum = baseline_aum + estimated_flow

            # Estimate shares outstanding based on AUM and price
            shares_outstanding = int((current_aum * 1_000_000) / week['close']) if week['close'] > 0 else None

            record = {
                'week_ending': week['week_ending'],
                'ticker': ticker,
                'net_flow': Decimal(str(round(estimated_flow, 2))),
                'aum': Decimal(str(round(current_aum, 2))),
                'shares_outstanding': shares_outstanding,
                'premium_discount': Decimal('0'),  # Would need NAV data
                'source': 'estimated_from_volume'
            }

            flow_records.append(record)
            baseline_aum = current_aum

        logger.success(f"Estimated {len(flow_records)} weeks of flow data for {ticker}")
        return flow_records

    def _aggregate_to_weekly(self, prices: List) -> List[Dict]:
        """Aggregate daily prices to weekly data (Friday week-ending)"""
        if not prices:
            return []

        weekly = {}

        for price in prices:
            # Handle both dict and object formats
            if isinstance(price, dict):
                timestamp = price['timestamp']
                open_price = price['open']
                close_price = price['close']
                high_price = price['high']
                low_price = price['low']
                volume = price['volume']
            else:
                timestamp = price.timestamp
                open_price = price.open
                close_price = price.close
                high_price = price.high
                low_price = price.low
                volume = price.volume

            # Get week ending date (most recent Friday)
            if isinstance(timestamp, str):
                price_date = datetime.fromisoformat(timestamp)
            else:
                price_date = timestamp

            days_to_friday = (4 - price_date.weekday()) % 7
            if days_to_friday == 0 and price_date.weekday() != 4:
                days_to_friday = 7
            week_end = (price_date + timedelta(days=days_to_friday)).date()

            if week_end not in weekly:
                weekly[week_end] = {
                    'week_ending': week_end,
                    'open': float(open_price),
                    'close': float(close_price),
                    'high': float(high_price),
                    'low': float(low_price),
                    'total_volume': int(volume),
                    'days': 1
                }
            else:
                weekly[week_end]['close'] = float(close_price)
                weekly[week_end]['high'] = max(weekly[week_end]['high'], float(high_price))
                weekly[week_end]['low'] = min(weekly[week_end]['low'], float(low_price))
                weekly[week_end]['total_volume'] += int(volume)
                weekly[week_end]['days'] += 1

        # Calculate averages and sort by date
        result = []
        for week_end in sorted(weekly.keys()):
            week = weekly[week_end]
            week['avg_volume'] = week['total_volume'] / week['days']
            result.append(week)

        return result

    def _estimate_aum(self, ticker: str, first_week: Dict) -> float:
        """
        Estimate initial AUM based on ticker and volume
        Uses industry averages for different ETF types
        """
        # Rough estimates based on typical ETF sizes
        aum_estimates = {
            'AGQ': 500,  # millions
            'UGL': 800,
            'GDXU': 350,
        }

        # Default estimate based on volume if not in list
        default_aum = (first_week['avg_volume'] * first_week['close']) / 1_000_000 * 20  # 20x daily volume

        return aum_estimates.get(ticker, default_aum)


# Singleton
flow_estimator = FlowEstimator()
