"""Premium/Discount calculator service for leveraged precious metals ETFs"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import numpy as np
from loguru import logger

from app.services.data_storage import DataStorageService


class PremiumDiscountCalculatorService:
    """Service for calculating ETF premium/discount to NAV for leveraged precious metals ETFs"""

    # ETF configuration with leverage and underlying commodity
    ETF_CONFIG = {
        "AGQ": {
            "name": "ProShares Ultra Silver",
            "leverage": 2.0,
            "commodity_symbol": "SI=F",
            "commodity_name": "Silver",
            "inverse": False,
        },
        "UGL": {
            "name": "ProShares Ultra Gold",
            "leverage": 2.0,
            "commodity_symbol": "GC=F",
            "commodity_name": "Gold",
            "inverse": False,
        },
        "ZSL": {
            "name": "ProShares UltraShort Silver",
            "leverage": 2.0,
            "commodity_symbol": "SI=F",
            "commodity_name": "Silver",
            "inverse": True,
        },
    }

    def __init__(self):
        self.data_storage = DataStorageService()

    async def calculate_premium_discount(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Calculate current premium/discount percentage for an ETF

        Args:
            ticker: ETF ticker symbol (AGQ, UGL, ZSL)

        Returns:
            Dictionary with premium/discount data or None if insufficient data
        """
        try:
            # Validate ticker
            if ticker not in self.ETF_CONFIG:
                logger.error(f"Unsupported ticker: {ticker}. Supported tickers: {list(self.ETF_CONFIG.keys())}")
                return None

            config = self.ETF_CONFIG[ticker]

            # Get latest ETF price
            etf_prices = await self.data_storage.get_price_data(ticker, limit=1)
            if not etf_prices or len(etf_prices) == 0:
                logger.warning(f"No ETF price data found for {ticker}")
                return None

            etf_price = float(etf_prices[0]['close'])
            etf_timestamp = etf_prices[0]['timestamp']

            # Get latest commodity price
            commodity_symbol = config['commodity_symbol']
            commodity_prices = await self.data_storage.get_commodity_price_data(
                commodity_symbol,
                limit=1
            )

            if not commodity_prices or len(commodity_prices) == 0:
                logger.warning(f"No commodity price data found for {commodity_symbol}")
                return None

            commodity_price = float(commodity_prices[0]['close'])
            commodity_timestamp = commodity_prices[0]['timestamp']

            # Calculate estimated NAV
            estimated_nav = self._calculate_nav(
                commodity_price=commodity_price,
                leverage=config['leverage'],
                inverse=config['inverse']
            )

            # Calculate premium/discount
            premium_discount_pct = (etf_price - estimated_nav) / estimated_nav * 100

            result = {
                'ticker': ticker,
                'etf_name': config['name'],
                'etf_price': etf_price,
                'etf_timestamp': etf_timestamp,
                'commodity_symbol': commodity_symbol,
                'commodity_price': commodity_price,
                'commodity_timestamp': commodity_timestamp,
                'estimated_nav': estimated_nav,
                'premium_discount_pct': round(premium_discount_pct, 4),
                'leverage': config['leverage'],
                'inverse': config['inverse'],
                'calculated_at': datetime.utcnow().isoformat()
            }

            logger.info(
                f"{ticker}: ETF=${etf_price:.2f}, NAV=${estimated_nav:.2f}, "
                f"Premium/Discount={premium_discount_pct:.2f}%"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating premium/discount for {ticker}: {e}")
            return None

    async def get_historical_premium_discount(
        self,
        ticker: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get historical premium/discount data for an ETF

        Args:
            ticker: ETF ticker symbol (AGQ, UGL, ZSL)
            days: Number of days of historical data to retrieve

        Returns:
            List of premium/discount records, ordered from newest to oldest
        """
        try:
            # Validate ticker
            if ticker not in self.ETF_CONFIG:
                logger.error(f"Unsupported ticker: {ticker}. Supported tickers: {list(self.ETF_CONFIG.keys())}")
                return []

            config = self.ETF_CONFIG[ticker]

            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Get ETF prices
            etf_prices = await self.data_storage.get_price_data(
                ticker,
                start_date=start_date,
                end_date=end_date,
                limit=days + 10  # Add buffer for weekends/holidays
            )

            if not etf_prices:
                logger.warning(f"No ETF price data found for {ticker}")
                return []

            # Get commodity prices
            commodity_symbol = config['commodity_symbol']
            commodity_prices = await self.data_storage.get_commodity_price_data(
                commodity_symbol,
                start_date=start_date,
                end_date=end_date,
                limit=days + 10
            )

            if not commodity_prices:
                logger.warning(f"No commodity price data found for {commodity_symbol}")
                return []

            # Create a lookup dict for commodity prices by date
            commodity_price_lookup = {
                datetime.fromisoformat(p['timestamp']).date(): float(p['close'])
                for p in commodity_prices
            }

            # Calculate premium/discount for each ETF price point
            historical_data = []
            for etf_price_record in etf_prices:
                etf_timestamp = datetime.fromisoformat(etf_price_record['timestamp'])
                etf_date = etf_timestamp.date()
                etf_price = float(etf_price_record['close'])

                # Find matching commodity price (same day or closest prior day)
                commodity_price = None
                for i in range(5):  # Look back up to 5 days
                    lookup_date = etf_date - timedelta(days=i)
                    if lookup_date in commodity_price_lookup:
                        commodity_price = commodity_price_lookup[lookup_date]
                        break

                if commodity_price is None:
                    logger.debug(f"No matching commodity price for {etf_date}")
                    continue

                # Calculate estimated NAV
                estimated_nav = self._calculate_nav(
                    commodity_price=commodity_price,
                    leverage=config['leverage'],
                    inverse=config['inverse']
                )

                # Calculate premium/discount
                premium_discount_pct = (etf_price - estimated_nav) / estimated_nav * 100

                historical_data.append({
                    'timestamp': etf_price_record['timestamp'],
                    'date': etf_date.isoformat(),
                    'etf_price': etf_price,
                    'commodity_price': commodity_price,
                    'estimated_nav': estimated_nav,
                    'premium_discount_pct': round(premium_discount_pct, 4)
                })

            logger.info(f"Retrieved {len(historical_data)} historical premium/discount records for {ticker}")

            return historical_data

        except Exception as e:
            logger.error(f"Error retrieving historical premium/discount for {ticker}: {e}")
            return []

    async def detect_premium_discount_extreme(
        self,
        ticker: str,
        threshold: float = 1.5
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if current premium/discount is at an extreme level

        Args:
            ticker: ETF ticker symbol (AGQ, UGL, ZSL)
            threshold: Z-score threshold for extreme detection (default: 1.5 std deviations)

        Returns:
            Dictionary with extreme detection results or None if not extreme
        """
        try:
            # Get current premium/discount
            current = await self.calculate_premium_discount(ticker)
            if not current:
                logger.warning(f"Could not calculate current premium/discount for {ticker}")
                return None

            current_prem_disc = current['premium_discount_pct']

            # Get historical data (90 days for meaningful statistics)
            historical = await self.get_historical_premium_discount(ticker, days=90)
            if len(historical) < 20:
                logger.warning(f"Insufficient historical data for {ticker} (need 20+, got {len(historical)})")
                return None

            # Calculate statistics
            prem_disc_values = np.array([h['premium_discount_pct'] for h in historical])
            mean = np.mean(prem_disc_values)
            std_dev = np.std(prem_disc_values)

            if std_dev == 0:
                logger.warning(f"Zero standard deviation for {ticker} premium/discount")
                return None

            # Calculate z-score
            z_score = (current_prem_disc - mean) / std_dev

            # Calculate percentile
            percentile = (np.sum(prem_disc_values <= current_prem_disc) / len(prem_disc_values)) * 100

            # Check if extreme
            is_extreme = abs(z_score) >= threshold

            if is_extreme:
                direction = "PREMIUM" if z_score > 0 else "DISCOUNT"
                severity = "EXTREME" if abs(z_score) >= 2.0 else "ELEVATED"

                result = {
                    'ticker': ticker,
                    'current_premium_discount_pct': current_prem_disc,
                    'z_score': round(z_score, 2),
                    'percentile': round(percentile, 2),
                    'mean': round(mean, 4),
                    'std_dev': round(std_dev, 4),
                    'is_extreme': is_extreme,
                    'direction': direction,
                    'severity': severity,
                    'threshold': threshold,
                    'etf_price': current['etf_price'],
                    'estimated_nav': current['estimated_nav'],
                    'notes': f"{severity} {direction.lower()} detected: {current_prem_disc:.2f}% (z-score: {z_score:.2f})",
                    'calculated_at': datetime.utcnow().isoformat()
                }

                logger.warning(
                    f"{ticker}: {severity} {direction} detected! "
                    f"Premium/Discount={current_prem_disc:.2f}% (z-score={z_score:.2f}, "
                    f"percentile={percentile:.1f}%)"
                )

                return result
            else:
                logger.info(
                    f"{ticker}: Premium/Discount within normal range "
                    f"({current_prem_disc:.2f}%, z-score={z_score:.2f})"
                )
                return None

        except Exception as e:
            logger.error(f"Error detecting extreme premium/discount for {ticker}: {e}")
            return None

    async def get_all_etf_premium_discounts(self) -> List[Dict[str, Any]]:
        """
        Calculate premium/discount for all configured ETFs

        Returns:
            List of premium/discount records for all ETFs
        """
        results = []

        for ticker in self.ETF_CONFIG.keys():
            result = await self.calculate_premium_discount(ticker)
            if result:
                results.append(result)

        logger.info(f"Calculated premium/discount for {len(results)}/{len(self.ETF_CONFIG)} ETFs")

        return results

    async def check_all_etf_extremes(
        self,
        threshold: float = 1.5
    ) -> List[Dict[str, Any]]:
        """
        Check all configured ETFs for extreme premium/discount levels

        Args:
            threshold: Z-score threshold for extreme detection

        Returns:
            List of ETFs with extreme premium/discount levels
        """
        extremes = []

        for ticker in self.ETF_CONFIG.keys():
            result = await self.detect_premium_discount_extreme(ticker, threshold)
            if result:
                extremes.append(result)

        if extremes:
            logger.warning(f"Found {len(extremes)} ETFs with extreme premium/discount levels")
        else:
            logger.info("No ETFs with extreme premium/discount levels detected")

        return extremes

    def _calculate_nav(
        self,
        commodity_price: float,
        leverage: float,
        inverse: bool
    ) -> float:
        """
        Calculate estimated NAV based on commodity price and leverage

        Note: This is a simplified calculation. Actual NAV calculation would need:
        - Shares per creation unit
        - Daily reset calculations for leveraged/inverse products
        - Management fees and other costs

        Args:
            commodity_price: Current commodity/futures price
            leverage: Leverage factor (e.g., 2.0 for 2x)
            inverse: Whether the ETF is inverse (-1x or -2x)

        Returns:
            Estimated NAV
        """
        if inverse:
            # Inverse ETF: NAV moves opposite to underlying
            # Simplified: NAV ≈ base_nav * (1 - leverage * (commodity_price / reference_price - 1))
            # For simplicity, we use the commodity price as a proxy
            # In reality, you'd need the creation basket value and daily rebalancing
            nav = leverage * commodity_price
        else:
            # Leveraged long ETF
            nav = leverage * commodity_price

        return nav


# Singleton instance
premium_discount_calculator = PremiumDiscountCalculatorService()
