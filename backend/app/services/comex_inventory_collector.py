"""COMEX warehouse inventory collector for physical supply analysis"""

import httpx
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger
import re
import pandas as pd


class COMEXInventoryCollector:
    """Collector for COMEX warehouse inventory data"""

    BASE_URL = "https://www.cmegroup.com/delivery_reports"

    # Contract specifications (ounces per contract)
    CONTRACT_SIZES = {
        'gold': 100,      # GC contract = 100 troy oz
        'silver': 5000,   # SI contract = 5,000 troy oz
        'platinum': 50,   # PL contract = 50 troy oz
        'palladium': 100, # PA contract = 100 troy oz
        'copper': 25000,  # HG contract = 25,000 lbs
    }

    # CME product codes for inventory reports
    PRODUCT_CODES = {
        'gold': 'GC',
        'silver': 'SI',
        'platinum': 'PL',
        'palladium': 'PA',
        'copper': 'HG',
    }

    # Squeeze detection thresholds
    SQUEEZE_THRESHOLDS = {
        'registered_decline_days': 5,      # Consecutive days of decline
        'registered_to_oi_ratio_pct': 10,  # Below 10% is critical
        'inventory_coverage_days': 30,      # Below 30 days is tight
    }

    def __init__(self):
        """Initialize COMEX inventory collector with async HTTP client"""
        self.client = httpx.AsyncClient(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            },
            timeout=60.0,  # CME site can be slow
            follow_redirects=True
        )

        # Cache for storing historical inventory data
        self._inventory_cache: Dict[str, List[Dict]] = {}

    async def fetch_comex_inventory(self, commodity: str) -> Optional[Dict[str, Any]]:
        """
        Fetch current COMEX warehouse inventory levels

        Args:
            commodity: Commodity name ('gold', 'silver', 'platinum', etc.)

        Returns:
            Dictionary with inventory data:
            {
                'commodity': str,
                'date': date,
                'registered_oz': float,
                'eligible_oz': float,
                'total_oz': float,
                'registered_pct': float,
                'source': str
            }
        """
        commodity = commodity.lower()

        if commodity not in self.PRODUCT_CODES:
            logger.error(f"Unsupported commodity: {commodity}")
            return None

        try:
            logger.info(f"Fetching COMEX inventory for {commodity}")

            # Try to fetch from CME delivery reports page
            product_code = self.PRODUCT_CODES[commodity]
            url = f"{self.BASE_URL}/{product_code}_stocks.xml"

            response = await self.client.get(url)

            if response.status_code == 200:
                # Parse XML/HTML response
                inventory = self._parse_cme_inventory(response.text, commodity)

                if inventory:
                    logger.success(
                        f"Fetched {commodity} inventory: "
                        f"Registered={inventory['registered_oz']:,.0f} oz, "
                        f"Total={inventory['total_oz']:,.0f} oz"
                    )

                    # Add to cache
                    self._add_to_cache(commodity, inventory)

                    return inventory

            # Fallback: Try alternative scraping method
            logger.warning(f"Primary source failed for {commodity}, trying alternative method")
            inventory = await self._fetch_from_alternative_source(commodity)

            if inventory:
                self._add_to_cache(commodity, inventory)
                return inventory

            logger.error(f"Failed to fetch inventory for {commodity}")
            return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {commodity} inventory: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {commodity} inventory: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _parse_cme_inventory(self, content: str, commodity: str) -> Optional[Dict[str, Any]]:
        """
        Parse CME inventory data from XML/HTML content

        Args:
            content: Raw HTML/XML content from CME
            commodity: Commodity name

        Returns:
            Parsed inventory dictionary or None
        """
        try:
            soup = BeautifulSoup(content, 'html.parser')

            # CME uses different formats - try to find inventory tables
            # Look for tables with "Registered" and "Eligible" columns

            registered_oz = None
            eligible_oz = None
            inventory_date = date.today()  # Default to today

            # Try to find date
            date_pattern = re.compile(r'(\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})')
            date_match = date_pattern.search(content)
            if date_match:
                try:
                    date_str = date_match.group(1)
                    if '/' in date_str:
                        inventory_date = datetime.strptime(date_str, '%m/%d/%Y').date()
                    else:
                        inventory_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except:
                    pass

            # Try to find registered and eligible inventory
            # Pattern: Look for "Registered" followed by a number
            registered_pattern = re.compile(r'Registered[:\s]+([0-9,]+)', re.IGNORECASE)
            eligible_pattern = re.compile(r'Eligible[:\s]+([0-9,]+)', re.IGNORECASE)

            registered_match = registered_pattern.search(content)
            eligible_match = eligible_pattern.search(content)

            if registered_match:
                registered_oz = float(registered_match.group(1).replace(',', ''))

            if eligible_match:
                eligible_oz = float(eligible_match.group(1).replace(',', ''))

            # If we found data, construct the result
            if registered_oz is not None and eligible_oz is not None:
                total_oz = registered_oz + eligible_oz
                registered_pct = (registered_oz / total_oz * 100) if total_oz > 0 else 0

                return {
                    'commodity': commodity,
                    'date': inventory_date,
                    'registered_oz': registered_oz,
                    'eligible_oz': eligible_oz,
                    'total_oz': total_oz,
                    'registered_pct': registered_pct,
                    'source': 'CME_GROUP'
                }

            logger.warning(f"Could not parse inventory data from CME response for {commodity}")
            return None

        except Exception as e:
            logger.error(f"Error parsing CME inventory: {e}")
            return None

    async def _fetch_from_alternative_source(self, commodity: str) -> Optional[Dict[str, Any]]:
        """
        Fetch from alternative data source (e.g., CME FTP, third-party aggregator)

        This is a placeholder for alternative data sources. In production, you might:
        - Access CME FTP server directly
        - Use a paid data provider API
        - Scrape from financial news sites that aggregate this data

        Args:
            commodity: Commodity name

        Returns:
            Inventory data or None
        """
        logger.info(f"Attempting alternative source for {commodity} inventory")

        # Placeholder: In production, implement alternative data source
        # For now, return None to indicate no alternative source available

        return None

    async def get_inventory_trend(
        self,
        commodity: str,
        days: int = 30
    ) -> Optional[pd.DataFrame]:
        """
        Get historical inventory trend

        Args:
            commodity: Commodity name
            days: Number of days to retrieve

        Returns:
            DataFrame with columns: date, registered_oz, eligible_oz, total_oz, registered_pct
        """
        commodity = commodity.lower()

        try:
            logger.info(f"Fetching {days}-day inventory trend for {commodity}")

            # Check cache first
            if commodity in self._inventory_cache:
                cache_data = self._inventory_cache[commodity]

                # Filter for requested date range
                cutoff_date = date.today() - timedelta(days=days)
                filtered_data = [
                    d for d in cache_data
                    if d['date'] >= cutoff_date
                ]

                if filtered_data:
                    df = pd.DataFrame(filtered_data)
                    df = df.sort_values('date', ascending=False)

                    logger.success(f"Retrieved {len(df)} days of cached inventory data for {commodity}")
                    return df

            # If not in cache or insufficient data, this would be where we'd
            # fetch historical data from CME's historical delivery reports
            # For now, return current inventory as single-row DataFrame

            current = await self.fetch_comex_inventory(commodity)

            if current:
                df = pd.DataFrame([current])
                logger.info(f"Returning current inventory data for {commodity} (historical data not available)")
                return df

            return None

        except Exception as e:
            logger.error(f"Error getting inventory trend for {commodity}: {e}")
            return None

    async def calculate_inventory_coverage(
        self,
        commodity: str,
        open_interest: Optional[int] = None
    ) -> Optional[Dict[str, float]]:
        """
        Calculate inventory coverage metrics

        Args:
            commodity: Commodity name
            open_interest: Open interest in number of contracts (if known)

        Returns:
            Dictionary with coverage metrics:
            {
                'registered_oz': float,
                'total_oz': float,
                'open_interest_contracts': int,
                'open_interest_oz': float,
                'registered_to_oi_ratio_pct': float,
                'total_to_oi_ratio_pct': float,
                'oi_coverage_days': float  (estimated)
            }
        """
        commodity = commodity.lower()

        try:
            # Get current inventory
            inventory = await self.fetch_comex_inventory(commodity)

            if not inventory:
                logger.warning(f"No inventory data available for {commodity}")
                return None

            registered_oz = inventory['registered_oz']
            total_oz = inventory['total_oz']

            # If open interest not provided, try to fetch it
            # (In production, this would integrate with futures data service)
            if open_interest is None:
                logger.warning("Open interest not provided, cannot calculate OI ratios")
                return {
                    'registered_oz': registered_oz,
                    'total_oz': total_oz,
                    'open_interest_contracts': None,
                    'open_interest_oz': None,
                    'registered_to_oi_ratio_pct': None,
                    'total_to_oi_ratio_pct': None,
                    'oi_coverage_days': None
                }

            # Calculate open interest in ounces
            contract_size = self.CONTRACT_SIZES[commodity]
            open_interest_oz = open_interest * contract_size

            # Calculate ratios
            registered_to_oi_ratio_pct = (registered_oz / open_interest_oz * 100) if open_interest_oz > 0 else 0
            total_to_oi_ratio_pct = (total_oz / open_interest_oz * 100) if open_interest_oz > 0 else 0

            # Estimate coverage days (assuming 5% of OI could stand for delivery per month)
            # This is a rough heuristic - actual delivery patterns vary
            monthly_delivery_rate = open_interest * 0.05
            monthly_delivery_oz = monthly_delivery_rate * contract_size
            daily_delivery_oz = monthly_delivery_oz / 30  # Approximate

            oi_coverage_days = (registered_oz / daily_delivery_oz) if daily_delivery_oz > 0 else float('inf')

            result = {
                'registered_oz': registered_oz,
                'total_oz': total_oz,
                'open_interest_contracts': open_interest,
                'open_interest_oz': open_interest_oz,
                'registered_to_oi_ratio_pct': registered_to_oi_ratio_pct,
                'total_to_oi_ratio_pct': total_to_oi_ratio_pct,
                'oi_coverage_days': oi_coverage_days
            }

            logger.success(
                f"Coverage for {commodity}: "
                f"Registered/OI={registered_to_oi_ratio_pct:.1f}%, "
                f"Coverage={oi_coverage_days:.0f} days"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating inventory coverage for {commodity}: {e}")
            return None

    async def detect_inventory_squeeze(
        self,
        commodity: str,
        open_interest: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Detect potential inventory squeeze conditions

        A squeeze occurs when:
        1. Registered inventory declining for 5+ consecutive days
        2. Registered-to-OI ratio below 10%
        3. Inventory coverage below 30 days

        Args:
            commodity: Commodity name
            open_interest: Current open interest in contracts

        Returns:
            Squeeze detection result:
            {
                'is_squeeze': bool,
                'squeeze_severity': str ('none', 'moderate', 'severe', 'extreme'),
                'signals': List[str],
                'metrics': Dict,
                'recommendation': str
            }
        """
        commodity = commodity.lower()

        try:
            logger.info(f"Detecting inventory squeeze for {commodity}")

            signals = []
            squeeze_severity = 'none'

            # Get inventory trend
            trend = await self.get_inventory_trend(commodity, days=10)

            if trend is None or len(trend) < 2:
                logger.warning(f"Insufficient trend data for squeeze detection: {commodity}")
                return None

            # Check 1: Declining registered inventory
            trend = trend.sort_values('date')
            registered_values = trend['registered_oz'].values

            declining_days = 0
            for i in range(1, len(registered_values)):
                if registered_values[i] < registered_values[i-1]:
                    declining_days += 1
                else:
                    declining_days = 0  # Reset counter

            if declining_days >= self.SQUEEZE_THRESHOLDS['registered_decline_days']:
                signals.append(
                    f"Registered inventory declining for {declining_days} consecutive days"
                )
                squeeze_severity = 'moderate'

            # Check 2: Low registered-to-OI ratio
            coverage = await self.calculate_inventory_coverage(commodity, open_interest)

            if coverage and coverage['registered_to_oi_ratio_pct'] is not None:
                ratio = coverage['registered_to_oi_ratio_pct']

                if ratio < self.SQUEEZE_THRESHOLDS['registered_to_oi_ratio_pct']:
                    signals.append(
                        f"Registered-to-OI ratio critically low: {ratio:.1f}% "
                        f"(threshold: {self.SQUEEZE_THRESHOLDS['registered_to_oi_ratio_pct']}%)"
                    )

                    if ratio < 5:
                        squeeze_severity = 'extreme'
                    elif ratio < 7:
                        squeeze_severity = 'severe'
                    elif squeeze_severity == 'none':
                        squeeze_severity = 'moderate'

                # Check 3: Low inventory coverage days
                if coverage['oi_coverage_days'] is not None:
                    coverage_days = coverage['oi_coverage_days']

                    if coverage_days < self.SQUEEZE_THRESHOLDS['inventory_coverage_days']:
                        signals.append(
                            f"Low inventory coverage: {coverage_days:.0f} days "
                            f"(threshold: {self.SQUEEZE_THRESHOLDS['inventory_coverage_days']})"
                        )

                        if coverage_days < 10:
                            squeeze_severity = 'extreme'
                        elif coverage_days < 20 and squeeze_severity != 'extreme':
                            squeeze_severity = 'severe'

            is_squeeze = squeeze_severity != 'none'

            # Generate recommendation
            if squeeze_severity == 'extreme':
                recommendation = (
                    f"EXTREME SQUEEZE RISK: {commodity.upper()} registered inventory critically low. "
                    "Consider bullish positioning on physical delivery expectations."
                )
            elif squeeze_severity == 'severe':
                recommendation = (
                    f"SEVERE SQUEEZE RISK: {commodity.upper()} showing tight physical supply. "
                    "Monitor for delivery month positioning."
                )
            elif squeeze_severity == 'moderate':
                recommendation = (
                    f"MODERATE SQUEEZE RISK: {commodity.upper()} inventory declining. "
                    "Watch for deterioration in supply metrics."
                )
            else:
                recommendation = f"No squeeze detected for {commodity.upper()}. Inventory levels adequate."

            result = {
                'commodity': commodity,
                'is_squeeze': is_squeeze,
                'squeeze_severity': squeeze_severity,
                'signals': signals,
                'metrics': coverage if coverage else {},
                'declining_days': declining_days,
                'recommendation': recommendation,
                'timestamp': datetime.utcnow()
            }

            if is_squeeze:
                logger.warning(
                    f"SQUEEZE DETECTED for {commodity}: "
                    f"Severity={squeeze_severity}, Signals={len(signals)}"
                )
            else:
                logger.info(f"No squeeze detected for {commodity}")

            return result

        except Exception as e:
            logger.error(f"Error detecting inventory squeeze for {commodity}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _add_to_cache(self, commodity: str, inventory: Dict[str, Any]) -> None:
        """
        Add inventory data to internal cache

        Args:
            commodity: Commodity name
            inventory: Inventory data dictionary
        """
        if commodity not in self._inventory_cache:
            self._inventory_cache[commodity] = []

        # Add to cache if not already present for this date
        cache = self._inventory_cache[commodity]
        existing_dates = {item['date'] for item in cache}

        if inventory['date'] not in existing_dates:
            cache.append(inventory)

            # Keep only last 90 days in cache
            cache.sort(key=lambda x: x['date'], reverse=True)
            self._inventory_cache[commodity] = cache[:90]

            logger.debug(f"Added {commodity} inventory to cache ({len(cache)} entries)")

    async def get_all_commodities_summary(
        self,
        open_interest_map: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Get inventory summary for all supported commodities

        Args:
            open_interest_map: Dictionary mapping commodity -> open interest contracts

        Returns:
            Dictionary with summary data for all commodities
        """
        logger.info("Fetching inventory summary for all commodities")

        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'commodities': {}
        }

        for commodity in self.PRODUCT_CODES.keys():
            try:
                # Get inventory
                inventory = await self.fetch_comex_inventory(commodity)

                if not inventory:
                    continue

                # Get open interest if provided
                oi = open_interest_map.get(commodity) if open_interest_map else None

                # Calculate coverage
                coverage = await self.calculate_inventory_coverage(commodity, oi)

                # Detect squeeze
                squeeze = await self.detect_inventory_squeeze(commodity, oi)

                summary['commodities'][commodity] = {
                    'inventory': inventory,
                    'coverage': coverage,
                    'squeeze': squeeze
                }

                # Be polite - add delay between requests
                import asyncio
                await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Error processing {commodity}: {e}")
                continue

        logger.success(
            f"Retrieved inventory summary for {len(summary['commodities'])} commodities"
        )

        return summary

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
        logger.debug("COMEX inventory collector HTTP client closed")


# Singleton instance
comex_inventory_collector = COMEXInventoryCollector()
