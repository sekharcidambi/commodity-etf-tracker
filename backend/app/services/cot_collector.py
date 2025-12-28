"""CFTC Commitment of Traders (COT) data collector service"""

import httpx
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from io import StringIO
from loguru import logger


class COTCollector:
    """Collect Commitment of Traders positioning data from CFTC for precious metals"""

    # CFTC disaggregated futures-only report (weekly, published Friday for Tuesday data)
    BASE_URL = "https://www.cftc.gov/dea/newcot/c_disagg.txt"

    # Commodity codes for precious metals in disaggregated report
    COMMODITY_CODES = {
        'gold': '088691',
        'silver': '084691',
        'platinum': '076651'
    }

    # Column names in the disaggregated COT report
    COT_COLUMNS = [
        'Market_and_Exchange_Names',
        'As_of_Date_In_Form_YYMMDD',
        'Report_Date_as_YYYY_MM_DD',
        'CFTC_Contract_Market_Code',
        'CFTC_Market_Code',
        'CFTC_Region_Code',
        'CFTC_Commodity_Code',
        'Open_Interest_All',
        'Prod_Merc_Positions_Long_All',
        'Prod_Merc_Positions_Short_All',
        'Swap_Positions_Long_All',
        'Swap_Positions_Short_All',
        'Swap_Positions_Spread_All',
        'M_Money_Positions_Long_All',
        'M_Money_Positions_Short_All',
        'M_Money_Positions_Spread_All',
        'Other_Rept_Positions_Long_All',
        'Other_Rept_Positions_Short_All',
        'Other_Rept_Positions_Spread_All',
        'Tot_Rept_Positions_Long_All',
        'Tot_Rept_Positions_Short_All',
        'NonRept_Positions_Long_All',
        'NonRept_Positions_Short_All',
    ]

    def __init__(self):
        """Initialize COT collector with async HTTP client"""
        self.client = httpx.AsyncClient(
            headers={
                'User-Agent': 'Commodity-ETF-Tracker/1.0',
                'Accept': 'text/plain',
            },
            timeout=60.0,  # COT file can be large
            follow_redirects=True
        )
        self._cached_report: Optional[pd.DataFrame] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = timedelta(hours=6)  # Cache for 6 hours

    async def fetch_cot_report(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Download and parse the disaggregated COT report from CFTC

        The report is published weekly on Friday afternoon (data as of Tuesday).
        File format is pipe-delimited text with headers.

        Args:
            force_refresh: Force download even if cache is valid

        Returns:
            DataFrame with all COT report data, indexed by commodity code and date
        """
        # Check cache
        if not force_refresh and self._cached_report is not None and self._cache_timestamp is not None:
            age = datetime.utcnow() - self._cache_timestamp
            if age < self._cache_duration:
                logger.debug(f"Using cached COT report (age: {age.total_seconds()/3600:.1f}h)")
                return self._cached_report

        try:
            logger.info(f"Downloading COT disaggregated report from CFTC")

            # Fetch the report
            response = await self.client.get(self.BASE_URL)
            response.raise_for_status()

            # Parse pipe-delimited text
            text_data = response.text

            # Read as CSV with pipe delimiter
            df = pd.read_csv(
                StringIO(text_data),
                delimiter='|',
                skipinitialspace=True,
                thousands=',',  # Handle comma-separated numbers
                low_memory=False
            )

            # Clean column names (remove extra spaces)
            df.columns = df.columns.str.strip()

            # Convert date columns
            if 'Report_Date_as_YYYY-MM-DD' in df.columns:
                df['report_date'] = pd.to_datetime(df['Report_Date_as_YYYY-MM-DD'])
            elif 'As_of_Date_In_Form_YYMMDD' in df.columns:
                # Parse YYMMDD format
                df['report_date'] = pd.to_datetime(
                    df['As_of_Date_In_Form_YYMMDD'].astype(str),
                    format='%y%m%d',
                    errors='coerce'
                )

            # Clean numeric columns (remove commas, convert to numeric)
            numeric_columns = [
                'Open_Interest_All',
                'Prod_Merc_Positions_Long_All',
                'Prod_Merc_Positions_Short_All',
                'Swap_Positions_Long_All',
                'Swap_Positions_Short_All',
                'M_Money_Positions_Long_All',
                'M_Money_Positions_Short_All',
                'Other_Rept_Positions_Long_All',
                'Other_Rept_Positions_Short_All',
                'NonRept_Positions_Long_All',
                'NonRept_Positions_Short_All',
            ]

            for col in numeric_columns:
                if col in df.columns:
                    # Remove commas and convert to numeric
                    df[col] = pd.to_numeric(
                        df[col].astype(str).str.replace(',', ''),
                        errors='coerce'
                    )

            # Cache the result
            self._cached_report = df
            self._cache_timestamp = datetime.utcnow()

            logger.success(
                f"Downloaded COT report: {len(df)} rows, "
                f"date range: {df['report_date'].min().date()} to {df['report_date'].max().date()}"
            )

            return df

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching COT report: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching COT report: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    async def get_commodity_positioning(
        self,
        commodity: str,
        as_of_date: Optional[date] = None
    ) -> Dict:
        """
        Get positioning data for a specific commodity (gold/silver/platinum)

        Args:
            commodity: Commodity name ('gold', 'silver', or 'platinum')
            as_of_date: Specific report date (defaults to most recent)

        Returns:
            Dictionary with positioning data and metrics
        """
        commodity = commodity.lower()

        if commodity not in self.COMMODITY_CODES:
            logger.error(f"Invalid commodity: {commodity}. Must be gold, silver, or platinum")
            return {}

        # Get commodity code
        commodity_code = self.COMMODITY_CODES[commodity]

        # Fetch report
        df = await self.fetch_cot_report()

        if df.empty:
            logger.error("No COT data available")
            return {}

        try:
            # Filter to commodity code (as string to match format)
            commodity_data = df[
                df['CFTC_Commodity_Code'].astype(str).str.strip() == commodity_code
            ].copy()

            if commodity_data.empty:
                logger.warning(f"No data found for {commodity} (code: {commodity_code})")
                return {}

            # Sort by date and get the requested date or most recent
            commodity_data = commodity_data.sort_values('report_date', ascending=False)

            if as_of_date:
                # Find exact or closest date
                target_date = pd.Timestamp(as_of_date)
                commodity_data = commodity_data[commodity_data['report_date'] <= target_date]

            if commodity_data.empty:
                logger.warning(f"No data found for {commodity} on or before {as_of_date}")
                return {}

            # Get most recent row
            latest = commodity_data.iloc[0]

            # Calculate net positions
            positioning = self._calculate_positioning(latest, commodity)

            logger.success(f"Retrieved {commodity} positioning for {positioning['report_date']}")

            return positioning

        except Exception as e:
            logger.error(f"Error processing {commodity} positioning: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    def _calculate_positioning(self, row: pd.Series, commodity: str) -> Dict:
        """
        Calculate net positioning and metrics from a COT data row

        Args:
            row: Single row from COT report DataFrame
            commodity: Commodity name

        Returns:
            Dictionary with calculated positioning metrics
        """
        # Extract values
        open_interest = float(row['Open_Interest_All'])

        # Producer/Merchant (Commercial hedgers)
        prod_long = float(row['Prod_Merc_Positions_Long_All'])
        prod_short = float(row['Prod_Merc_Positions_Short_All'])

        # Swap Dealers
        swap_long = float(row['Swap_Positions_Long_All'])
        swap_short = float(row['Swap_Positions_Short_All'])

        # Managed Money (Large speculators - hedge funds, CTAs)
        mm_long = float(row['M_Money_Positions_Long_All'])
        mm_short = float(row['M_Money_Positions_Short_All'])

        # Other Reportables
        other_long = float(row['Other_Rept_Positions_Long_All'])
        other_short = float(row['Other_Rept_Positions_Short_All'])

        # Non-Reportables (Small speculators/retail)
        nonrept_long = float(row['NonRept_Positions_Long_All'])
        nonrept_short = float(row['NonRept_Positions_Short_All'])

        # Calculate net positions
        prod_net = prod_long - prod_short
        swap_net = swap_long - swap_short
        commercial_net = prod_net + swap_net  # Combined commercial position
        mm_net = mm_long - mm_short
        other_net = other_long - other_short
        nonrept_net = nonrept_long - nonrept_short

        # Calculate percentages of open interest
        mm_net_pct = (mm_net / open_interest * 100) if open_interest > 0 else 0
        commercial_net_pct = (commercial_net / open_interest * 100) if open_interest > 0 else 0
        nonrept_net_pct = (nonrept_net / open_interest * 100) if open_interest > 0 else 0

        # Managed money long/short ratio
        mm_long_short_ratio = (mm_long / mm_short) if mm_short > 0 else 0

        return {
            'commodity': commodity,
            'report_date': row['report_date'].strftime('%Y-%m-%d'),
            'open_interest': int(open_interest),

            # Commercial positions (producers + swaps)
            'commercial_long': int(prod_long + swap_long),
            'commercial_short': int(prod_short + swap_short),
            'commercial_net': int(commercial_net),
            'commercial_net_pct': round(commercial_net_pct, 2),

            # Managed Money (key speculator indicator)
            'managed_money_long': int(mm_long),
            'managed_money_short': int(mm_short),
            'managed_money_net': int(mm_net),
            'managed_money_net_pct': round(mm_net_pct, 2),
            'managed_money_long_short_ratio': round(mm_long_short_ratio, 2),

            # Other reportables
            'other_reportable_long': int(other_long),
            'other_reportable_short': int(other_short),
            'other_reportable_net': int(other_net),

            # Non-reportables (retail)
            'nonreportable_long': int(nonrept_long),
            'nonreportable_short': int(nonrept_short),
            'nonreportable_net': int(nonrept_net),
            'nonreportable_net_pct': round(nonrept_net_pct, 2),

            # Breakdown
            'producer_merchant_net': int(prod_net),
            'swap_dealer_net': int(swap_net),
        }

    async def calculate_net_positioning(
        self,
        as_of_date: Optional[date] = None
    ) -> Dict[str, Dict]:
        """
        Calculate net positioning for all precious metals

        Args:
            as_of_date: Specific report date (defaults to most recent)

        Returns:
            Dictionary mapping commodity name to positioning data
        """
        results = {}

        for commodity in self.COMMODITY_CODES.keys():
            positioning = await self.get_commodity_positioning(commodity, as_of_date)
            if positioning:
                results[commodity] = positioning

        logger.info(f"Calculated net positioning for {len(results)} commodities")

        return results

    async def detect_extreme_positioning(
        self,
        commodity: str,
        lookback_weeks: int = 52,
        percentile_threshold: float = 90.0
    ) -> Dict:
        """
        Detect when speculators (managed money) are at extreme positioning levels

        Extreme positioning can be a contrarian indicator:
        - Extremely bullish speculators (high net long) -> potential top
        - Extremely bearish speculators (high net short) -> potential bottom

        Args:
            commodity: Commodity name ('gold', 'silver', or 'platinum')
            lookback_weeks: Number of weeks to use for historical comparison
            percentile_threshold: Percentile to define "extreme" (default: 90th)

        Returns:
            Dictionary with extreme positioning analysis
        """
        commodity = commodity.lower()

        if commodity not in self.COMMODITY_CODES:
            logger.error(f"Invalid commodity: {commodity}")
            return {}

        # Get historical data
        historical = await self.get_historical_positioning(commodity, lookback_weeks)

        if not historical or len(historical) < 10:
            logger.warning(f"Insufficient historical data for {commodity}")
            return {}

        try:
            # Convert to DataFrame for analysis
            hist_df = pd.DataFrame(historical)

            # Current positioning
            latest = hist_df.iloc[-1]

            # Calculate percentiles
            mm_net = hist_df['managed_money_net']
            mm_net_pct = hist_df['managed_money_net_pct']

            # Percentile of current positioning
            current_percentile_net = (mm_net <= latest['managed_money_net']).sum() / len(mm_net) * 100

            # Historical extremes
            p90_net = mm_net.quantile(0.90)
            p10_net = mm_net.quantile(0.10)
            median_net = mm_net.median()

            # Detect extreme condition
            is_extreme_bullish = current_percentile_net >= percentile_threshold
            is_extreme_bearish = current_percentile_net <= (100 - percentile_threshold)

            # Calculate z-score (standard deviations from mean)
            mean_net = mm_net.mean()
            std_net = mm_net.std()
            z_score = (latest['managed_money_net'] - mean_net) / std_net if std_net > 0 else 0

            # Contrarian signal
            contrarian_signal = None
            if is_extreme_bullish:
                contrarian_signal = 'bearish'  # Too many bulls = contrarian bearish
            elif is_extreme_bearish:
                contrarian_signal = 'bullish'  # Too many bears = contrarian bullish

            result = {
                'commodity': commodity,
                'report_date': latest['report_date'],
                'current_positioning': {
                    'managed_money_net': int(latest['managed_money_net']),
                    'managed_money_net_pct': float(latest['managed_money_net_pct']),
                    'percentile': round(current_percentile_net, 1),
                    'z_score': round(z_score, 2),
                },
                'historical_context': {
                    'lookback_weeks': lookback_weeks,
                    'median_net': int(median_net),
                    '90th_percentile': int(p90_net),
                    '10th_percentile': int(p10_net),
                    'mean_net': int(mean_net),
                    'std_dev': int(std_net),
                },
                'extreme_positioning': {
                    'is_extreme': is_extreme_bullish or is_extreme_bearish,
                    'is_extreme_bullish': is_extreme_bullish,
                    'is_extreme_bearish': is_extreme_bearish,
                    'contrarian_signal': contrarian_signal,
                },
                'interpretation': self._generate_interpretation(
                    commodity,
                    current_percentile_net,
                    is_extreme_bullish,
                    is_extreme_bearish,
                    z_score
                )
            }

            logger.success(
                f"{commodity} positioning at {current_percentile_net:.1f} percentile "
                f"(z-score: {z_score:.2f})"
            )

            return result

        except Exception as e:
            logger.error(f"Error detecting extreme positioning for {commodity}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    def _generate_interpretation(
        self,
        commodity: str,
        percentile: float,
        is_extreme_bullish: bool,
        is_extreme_bearish: bool,
        z_score: float
    ) -> str:
        """Generate human-readable interpretation of positioning"""

        if is_extreme_bullish:
            return (
                f"Speculators are EXTREMELY BULLISH on {commodity.upper()} "
                f"({percentile:.0f}th percentile, z-score: {z_score:.1f}). "
                f"This is a contrarian BEARISH signal - too many bulls may indicate "
                f"positioning is crowded and vulnerable to correction."
            )
        elif is_extreme_bearish:
            return (
                f"Speculators are EXTREMELY BEARISH on {commodity.upper()} "
                f"({percentile:.0f}th percentile, z-score: {z_score:.1f}). "
                f"This is a contrarian BULLISH signal - too many bears may indicate "
                f"positioning is washed out and primed for a rally."
            )
        elif percentile > 75:
            return (
                f"Speculators are notably bullish on {commodity.upper()} "
                f"({percentile:.0f}th percentile, z-score: {z_score:.1f}). "
                f"Approaching extreme levels - monitor for potential reversal."
            )
        elif percentile < 25:
            return (
                f"Speculators are notably bearish on {commodity.upper()} "
                f"({percentile:.0f}th percentile, z-score: {z_score:.1f}). "
                f"Approaching extreme levels - monitor for potential bounce."
            )
        else:
            return (
                f"Speculators have neutral positioning on {commodity.upper()} "
                f"({percentile:.0f}th percentile, z-score: {z_score:.1f}). "
                f"No extreme positioning signals."
            )

    async def get_historical_positioning(
        self,
        commodity: str,
        weeks: int = 52
    ) -> List[Dict]:
        """
        Get historical positioning data for a commodity

        Args:
            commodity: Commodity name ('gold', 'silver', or 'platinum')
            weeks: Number of weeks of historical data to retrieve

        Returns:
            List of positioning dictionaries, sorted by date (oldest to newest)
        """
        commodity = commodity.lower()

        if commodity not in self.COMMODITY_CODES:
            logger.error(f"Invalid commodity: {commodity}")
            return []

        commodity_code = self.COMMODITY_CODES[commodity]

        # Fetch report
        df = await self.fetch_cot_report()

        if df.empty:
            logger.error("No COT data available")
            return []

        try:
            # Filter to commodity code
            commodity_data = df[
                df['CFTC_Commodity_Code'].astype(str).str.strip() == commodity_code
            ].copy()

            if commodity_data.empty:
                logger.warning(f"No data found for {commodity} (code: {commodity_code})")
                return []

            # Sort by date (newest first) and take requested number of weeks
            commodity_data = commodity_data.sort_values('report_date', ascending=False)
            commodity_data = commodity_data.head(weeks)

            # Calculate positioning for each row
            results = []
            for _, row in commodity_data.iterrows():
                positioning = self._calculate_positioning(row, commodity)
                results.append(positioning)

            # Reverse to get oldest to newest
            results.reverse()

            logger.success(
                f"Retrieved {len(results)} weeks of historical positioning for {commodity} "
                f"({results[0]['report_date']} to {results[-1]['report_date']})"
            )

            return results

        except Exception as e:
            logger.error(f"Error retrieving historical positioning for {commodity}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    async def get_all_commodities_summary(self) -> Dict:
        """
        Get a comprehensive summary of positioning for all precious metals

        Returns:
            Dictionary with positioning summary for gold, silver, and platinum
        """
        logger.info("Generating COT summary for all precious metals")

        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'commodities': {}
        }

        for commodity in self.COMMODITY_CODES.keys():
            try:
                # Get current positioning
                positioning = await self.get_commodity_positioning(commodity)

                if not positioning:
                    continue

                # Get extreme positioning analysis
                extremes = await self.detect_extreme_positioning(commodity)

                summary['commodities'][commodity] = {
                    'current_positioning': positioning,
                    'extreme_analysis': extremes if extremes else None
                }

            except Exception as e:
                logger.error(f"Error getting summary for {commodity}: {e}")
                continue

        logger.success(f"Generated COT summary for {len(summary['commodities'])} commodities")

        return summary

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
        logger.debug("COT collector HTTP client closed")


# Singleton instance
cot_collector = COTCollector()
