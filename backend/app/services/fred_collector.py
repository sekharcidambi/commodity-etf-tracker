"""Federal Reserve Economic Data (FRED) API collector service"""

import httpx
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from loguru import logger

from app.core.config import settings


class FREDCollector:
    """Collect macroeconomic data from FRED API"""

    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    # FRED series configuration with metadata
    MACRO_SERIES = {
        'DGS10': {
            'name': '10-Year Treasury Yield',
            'frequency': 'daily',
            'unit': 'percent'
        },
        'DTWEXBGS': {
            'name': 'Trade Weighted Dollar Index',
            'frequency': 'daily',
            'unit': 'index'
        },
        'T10YIE': {
            'name': '10-Year Breakeven Inflation',
            'frequency': 'daily',
            'unit': 'percent'
        },
        'VIXCLS': {
            'name': 'VIX Index',
            'frequency': 'daily',
            'unit': 'index'
        },
        'FEDFUNDS': {
            'name': 'Fed Funds Rate',
            'frequency': 'monthly',
            'unit': 'percent'
        },
        'CPIAUCSL': {
            'name': 'CPI All Items',
            'frequency': 'monthly',
            'unit': 'index'
        },
        'M2SL': {
            'name': 'M2 Money Supply',
            'frequency': 'weekly',
            'unit': 'billions'
        }
    }

    def __init__(self):
        """Initialize FRED collector with async HTTP client"""
        self.api_key = settings.FRED_API_KEY
        self.client = httpx.AsyncClient(
            headers={
                'User-Agent': 'Commodity-ETF-Tracker/1.0',
                'Accept': 'application/json',
            },
            timeout=30.0,
            follow_redirects=True
        )

        if not self.api_key:
            logger.warning("FRED_API_KEY not configured. FRED data collection will not work.")

    async def fetch_series(
        self,
        series_id: str,
        start_date: date,
        end_date: date
    ) -> pd.DataFrame:
        """
        Fetch a single FRED series

        Args:
            series_id: FRED series identifier (e.g., 'DGS10')
            start_date: Start date for data
            end_date: End date for data

        Returns:
            DataFrame with columns: date, series_id, value
        """
        if not self.api_key:
            logger.error("FRED_API_KEY not configured")
            return pd.DataFrame()

        try:
            logger.info(
                f"Fetching FRED series {series_id} from {start_date} to {end_date}"
            )

            # Build request parameters
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'observation_start': start_date.strftime('%Y-%m-%d'),
                'observation_end': end_date.strftime('%Y-%m-%d'),
            }

            # Make API request
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()

            data = response.json()

            # Parse observations
            observations = data.get('observations', [])

            if not observations:
                logger.warning(f"No observations returned for {series_id}")
                return pd.DataFrame()

            # Convert to DataFrame
            df = pd.DataFrame(observations)

            # Filter out missing values (FRED uses '.' for missing data)
            df = df[df['value'] != '.'].copy()

            if df.empty:
                logger.warning(f"All values are missing for {series_id}")
                return pd.DataFrame()

            # Convert types
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')

            # Add series metadata
            df['series_id'] = series_id
            if series_id in self.MACRO_SERIES:
                df['name'] = self.MACRO_SERIES[series_id]['name']
                df['frequency'] = self.MACRO_SERIES[series_id]['frequency']
                df['unit'] = self.MACRO_SERIES[series_id]['unit']

            # Select and order columns
            df = df[['date', 'series_id', 'value', 'name', 'frequency', 'unit']].copy()

            # Drop any rows with NaN values
            df = df.dropna(subset=['value'])

            logger.success(
                f"Fetched {len(df)} observations for {series_id} "
                f"({df['date'].min().date()} to {df['date'].max().date()})"
            )

            return df

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching FRED series {series_id}: {e}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error fetching FRED series {series_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    async def fetch_all_macro_indicators(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        lookback_days: int = 90
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch all configured macro indicators

        Args:
            start_date: Start date (defaults to lookback_days ago)
            end_date: End date (defaults to today)
            lookback_days: Days to look back if start_date not provided

        Returns:
            Dictionary mapping series_id to DataFrame
        """
        if end_date is None:
            end_date = date.today()

        if start_date is None:
            start_date = end_date - timedelta(days=lookback_days)

        logger.info(
            f"Fetching {len(self.MACRO_SERIES)} FRED series from {start_date} to {end_date}"
        )

        results = {}

        for series_id in self.MACRO_SERIES.keys():
            try:
                df = await self.fetch_series(series_id, start_date, end_date)

                if not df.empty:
                    results[series_id] = df

                # Be polite to the API - add small delay between requests
                import asyncio
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching {series_id}: {e}")
                continue

        logger.info(
            f"Successfully fetched {len(results)}/{len(self.MACRO_SERIES)} FRED series"
        )

        return results

    async def calculate_real_rates(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        lookback_days: int = 90
    ) -> pd.DataFrame:
        """
        Calculate real rates (DGS10 - T10YIE)

        Real interest rates are nominal rates minus expected inflation,
        providing insight into actual borrowing costs and economic conditions.

        Args:
            start_date: Start date
            end_date: End date
            lookback_days: Days to look back if start_date not provided

        Returns:
            DataFrame with columns: date, nominal_rate, breakeven_inflation, real_rate
        """
        if end_date is None:
            end_date = date.today()

        if start_date is None:
            start_date = end_date - timedelta(days=lookback_days)

        logger.info(f"Calculating real rates from {start_date} to {end_date}")

        try:
            # Fetch both series
            dgs10 = await self.fetch_series('DGS10', start_date, end_date)
            t10yie = await self.fetch_series('T10YIE', start_date, end_date)

            if dgs10.empty or t10yie.empty:
                logger.warning("Missing data for real rate calculation")
                return pd.DataFrame()

            # Merge on date
            merged = pd.merge(
                dgs10[['date', 'value']].rename(columns={'value': 'nominal_rate'}),
                t10yie[['date', 'value']].rename(columns={'value': 'breakeven_inflation'}),
                on='date',
                how='inner'
            )

            # Calculate real rate
            merged['real_rate'] = merged['nominal_rate'] - merged['breakeven_inflation']

            # Sort by date
            merged = merged.sort_values('date').reset_index(drop=True)

            logger.success(
                f"Calculated {len(merged)} real rate observations. "
                f"Latest real rate: {merged['real_rate'].iloc[-1]:.2f}%"
            )

            return merged

        except Exception as e:
            logger.error(f"Error calculating real rates: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    async def get_latest_indicators(self) -> Dict[str, Dict]:
        """
        Get the most recent values for all macro indicators

        Returns:
            Dictionary mapping series_id to latest observation data
        """
        logger.info("Fetching latest values for all FRED indicators")

        # Fetch last 30 days to ensure we get latest available data
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        all_data = await self.fetch_all_macro_indicators(start_date, end_date)

        latest = {}

        for series_id, df in all_data.items():
            if not df.empty:
                # Get the most recent observation
                latest_row = df.sort_values('date').iloc[-1]

                latest[series_id] = {
                    'series_id': series_id,
                    'name': latest_row.get('name', series_id),
                    'value': float(latest_row['value']),
                    'date': latest_row['date'].strftime('%Y-%m-%d'),
                    'unit': latest_row.get('unit', ''),
                    'frequency': latest_row.get('frequency', ''),
                }

        # Also calculate latest real rate
        try:
            real_rates = await self.calculate_real_rates(lookback_days=30)
            if not real_rates.empty:
                latest_real = real_rates.iloc[-1]
                latest['REAL_RATE'] = {
                    'series_id': 'REAL_RATE',
                    'name': 'Real Interest Rate (10Y)',
                    'value': float(latest_real['real_rate']),
                    'date': latest_real['date'].strftime('%Y-%m-%d'),
                    'unit': 'percent',
                    'frequency': 'daily',
                    'components': {
                        'nominal_rate': float(latest_real['nominal_rate']),
                        'breakeven_inflation': float(latest_real['breakeven_inflation'])
                    }
                }
        except Exception as e:
            logger.warning(f"Could not calculate latest real rate: {e}")

        logger.success(f"Retrieved latest values for {len(latest)} indicators")

        return latest

    async def get_macro_summary(self) -> Dict:
        """
        Get a comprehensive summary of current macro conditions

        Returns:
            Dictionary with categorized macro indicators and analysis
        """
        latest = await self.get_latest_indicators()

        if not latest:
            logger.warning("No latest indicators available")
            return {}

        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'rates': {},
            'inflation': {},
            'monetary': {},
            'market_stress': {},
            'dollar': {}
        }

        # Categorize indicators
        if 'DGS10' in latest:
            summary['rates']['treasury_10y'] = latest['DGS10']

        if 'FEDFUNDS' in latest:
            summary['rates']['fed_funds'] = latest['FEDFUNDS']

        if 'REAL_RATE' in latest:
            summary['rates']['real_rate'] = latest['REAL_RATE']

        if 'T10YIE' in latest:
            summary['inflation']['breakeven_10y'] = latest['T10YIE']

        if 'CPIAUCSL' in latest:
            summary['inflation']['cpi'] = latest['CPIAUCSL']

        if 'M2SL' in latest:
            summary['monetary']['m2_supply'] = latest['M2SL']

        if 'VIXCLS' in latest:
            summary['market_stress']['vix'] = latest['VIXCLS']

        if 'DTWEXBGS' in latest:
            summary['dollar']['trade_weighted_index'] = latest['DTWEXBGS']

        logger.info("Generated macro summary")

        return summary

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
        logger.debug("FRED collector HTTP client closed")


# Singleton instance
fred_collector = FREDCollector()
