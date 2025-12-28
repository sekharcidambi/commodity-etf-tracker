"""Google Trends data collector service for retail sentiment analysis"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from loguru import logger
from pytrends.request import TrendReq
import numpy as np


class GoogleTrendsCollector:
    """
    Collect Google search interest data as a leading indicator for retail sentiment.

    Tracks search interest for precious metals keywords to gauge retail investor
    interest and potential buying/selling pressure.
    """

    # Keyword groups for different commodities
    KEYWORDS = {
        'gold': ['buy gold', 'gold price', 'gold investment'],
        'silver': ['buy silver', 'silver price', 'silver investment'],
        'precious_metals': ['precious metals ETF', 'inflation hedge']
    }

    # Supported timeframes
    TIMEFRAMES = {
        'hour': 'now 1-H',      # Past hour, per minute
        '4hour': 'now 4-H',     # Past 4 hours
        'day': 'now 1-d',       # Past day
        'week': 'now 7-d',      # Past 7 days (default)
        'month': 'today 1-m',   # Past 30 days
        '3month': 'today 3-m',  # Past 90 days
    }

    def __init__(self):
        """Initialize Google Trends collector"""
        # pytrends instances are created per request due to session management
        self.hl = 'en-US'
        self.tz = 360  # US Central Time
        logger.info("Google Trends collector initialized")

    def _create_pytrends(self) -> TrendReq:
        """
        Create a new pytrends instance

        Returns:
            TrendReq instance
        """
        return TrendReq(hl=self.hl, tz=self.tz, timeout=(10, 25))

    async def fetch_trend_data(
        self,
        keywords: List[str],
        timeframe: str = "now 7-d"
    ) -> pd.DataFrame:
        """
        Fetch Google Trends data for specified keywords

        Args:
            keywords: List of search keywords to track (max 5)
            timeframe: Time period for trends (e.g., 'now 7-d', 'today 1-m')

        Returns:
            DataFrame with columns: timestamp, keyword, interest (0-100)
        """
        if not keywords:
            logger.warning("No keywords provided")
            return pd.DataFrame()

        if len(keywords) > 5:
            logger.warning(f"Too many keywords ({len(keywords)}). Limiting to first 5.")
            keywords = keywords[:5]

        try:
            logger.info(f"Fetching trend data for {keywords} with timeframe '{timeframe}'")

            # Run synchronous pytrends in thread pool
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None,
                self._fetch_trends_sync,
                keywords,
                timeframe
            )

            if df.empty:
                logger.warning(f"No trend data returned for {keywords}")
                return pd.DataFrame()

            logger.success(
                f"Fetched {len(df)} data points for {len(keywords)} keywords "
                f"({df.index.min()} to {df.index.max()})"
            )

            return df

        except Exception as e:
            logger.error(f"Error fetching trend data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return pd.DataFrame()

    def _fetch_trends_sync(self, keywords: List[str], timeframe: str) -> pd.DataFrame:
        """
        Synchronous method to fetch trends (runs in thread pool)

        Args:
            keywords: List of keywords
            timeframe: Timeframe string

        Returns:
            DataFrame with interest over time
        """
        try:
            pytrends = self._create_pytrends()
            pytrends.build_payload(keywords, timeframe=timeframe)
            df = pytrends.interest_over_time()

            if df.empty:
                return pd.DataFrame()

            # Remove 'isPartial' column if present
            if 'isPartial' in df.columns:
                df = df.drop('isPartial', axis=1)

            # Reset index to get timestamp as column
            df = df.reset_index()

            # Melt to long format for easier analysis
            df = df.melt(
                id_vars=['date'],
                var_name='keyword',
                value_name='interest'
            )

            df = df.rename(columns={'date': 'timestamp'})

            return df

        except Exception as e:
            logger.error(f"Error in sync trend fetch: {e}")
            return pd.DataFrame()

    async def get_precious_metals_interest(
        self,
        timeframe: str = "now 7-d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Get aggregated search interest for gold and silver keywords

        Args:
            timeframe: Time period for analysis

        Returns:
            Dictionary with 'gold', 'silver', and 'precious_metals' DataFrames
        """
        logger.info("Fetching precious metals search interest")

        results = {}

        try:
            # Fetch data for each commodity group
            for commodity, keywords in self.KEYWORDS.items():
                df = await self.fetch_trend_data(keywords, timeframe)

                if not df.empty:
                    # Calculate aggregate interest (average across keywords)
                    agg_df = df.groupby('timestamp')['interest'].agg([
                        ('avg_interest', 'mean'),
                        ('max_interest', 'max'),
                        ('min_interest', 'min')
                    ]).reset_index()

                    agg_df['commodity'] = commodity
                    results[commodity] = agg_df

                # Add delay between requests to be polite to Google
                await asyncio.sleep(2)

            logger.success(
                f"Fetched interest data for {len(results)} commodity groups"
            )

            return results

        except Exception as e:
            logger.error(f"Error fetching precious metals interest: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    async def calculate_interest_score(
        self,
        commodity: str,
        timeframe: str = "now 7-d"
    ) -> Dict[str, float]:
        """
        Calculate normalized interest score (0-100) for a commodity

        Args:
            commodity: Commodity name ('gold', 'silver', or 'precious_metals')
            timeframe: Time period for analysis

        Returns:
            Dictionary with current_score, avg_score, max_score, normalized_score
        """
        if commodity not in self.KEYWORDS:
            logger.error(f"Unknown commodity: {commodity}")
            return {}

        try:
            logger.info(f"Calculating interest score for {commodity}")

            keywords = self.KEYWORDS[commodity]
            df = await self.fetch_trend_data(keywords, timeframe)

            if df.empty:
                logger.warning(f"No data available for {commodity}")
                return {}

            # Calculate aggregate interest over time
            agg = df.groupby('timestamp')['interest'].mean()

            if agg.empty:
                return {}

            # Calculate metrics
            current_score = float(agg.iloc[-1])  # Most recent value
            avg_score = float(agg.mean())
            max_score = float(agg.max())
            min_score = float(agg.min())
            std_score = float(agg.std())

            # Normalized score (how current compares to average)
            if avg_score > 0:
                normalized_score = (current_score / avg_score) * 100
            else:
                normalized_score = 0.0

            result = {
                'commodity': commodity,
                'current_score': current_score,
                'avg_score': avg_score,
                'max_score': max_score,
                'min_score': min_score,
                'std_score': std_score,
                'normalized_score': normalized_score,
                'timestamp': df['timestamp'].max().isoformat(),
                'timeframe': timeframe
            }

            logger.success(
                f"{commodity} interest score: {current_score:.1f} "
                f"(avg: {avg_score:.1f}, normalized: {normalized_score:.1f}%)"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating interest score for {commodity}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    async def detect_interest_spike(
        self,
        commodity: str,
        timeframe: str = "now 7-d",
        threshold_multiplier: float = 2.0
    ) -> Dict:
        """
        Detect unusual search interest spikes (default: >2x normal)

        Args:
            commodity: Commodity name ('gold', 'silver', or 'precious_metals')
            timeframe: Time period for analysis
            threshold_multiplier: Spike threshold as multiple of average (default 2.0)

        Returns:
            Dictionary with spike detection results
        """
        if commodity not in self.KEYWORDS:
            logger.error(f"Unknown commodity: {commodity}")
            return {}

        try:
            logger.info(
                f"Detecting interest spikes for {commodity} "
                f"(threshold: {threshold_multiplier}x average)"
            )

            keywords = self.KEYWORDS[commodity]
            df = await self.fetch_trend_data(keywords, timeframe)

            if df.empty:
                logger.warning(f"No data available for {commodity}")
                return {}

            # Calculate aggregate interest over time
            agg = df.groupby('timestamp')['interest'].mean().reset_index()
            agg.columns = ['timestamp', 'interest']

            # Calculate statistics
            avg_interest = agg['interest'].mean()
            std_interest = agg['interest'].std()
            current_interest = agg['interest'].iloc[-1]

            # Spike threshold
            spike_threshold = avg_interest * threshold_multiplier

            # Detect spike
            is_spike = current_interest > spike_threshold

            # Calculate z-score for current interest
            if std_interest > 0:
                z_score = (current_interest - avg_interest) / std_interest
            else:
                z_score = 0.0

            # Find all spike points
            spike_points = agg[agg['interest'] > spike_threshold].copy()

            result = {
                'commodity': commodity,
                'is_spike': bool(is_spike),
                'current_interest': float(current_interest),
                'avg_interest': float(avg_interest),
                'spike_threshold': float(spike_threshold),
                'threshold_multiplier': threshold_multiplier,
                'z_score': float(z_score),
                'spike_count': len(spike_points),
                'latest_timestamp': agg['timestamp'].iloc[-1].isoformat(),
                'timeframe': timeframe
            }

            if is_spike:
                logger.warning(
                    f"🚨 SPIKE DETECTED for {commodity}! "
                    f"Current: {current_interest:.1f}, "
                    f"Avg: {avg_interest:.1f}, "
                    f"Threshold: {spike_threshold:.1f} "
                    f"(z-score: {z_score:.2f})"
                )
            else:
                logger.info(
                    f"No spike for {commodity}. "
                    f"Current: {current_interest:.1f}, "
                    f"Threshold: {spike_threshold:.1f}"
                )

            return result

        except Exception as e:
            logger.error(f"Error detecting interest spike for {commodity}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    async def get_related_queries(
        self,
        keyword: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Get rising and top related queries for a keyword

        Args:
            keyword: Search keyword to analyze

        Returns:
            Dictionary with 'rising' and 'top' DataFrames of related queries
        """
        try:
            logger.info(f"Fetching related queries for '{keyword}'")

            # Run synchronous pytrends in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._get_related_queries_sync,
                keyword
            )

            if result:
                logger.success(
                    f"Fetched related queries for '{keyword}': "
                    f"{len(result.get('rising', pd.DataFrame()))} rising, "
                    f"{len(result.get('top', pd.DataFrame()))} top"
                )
            else:
                logger.warning(f"No related queries found for '{keyword}'")

            return result or {}

        except Exception as e:
            logger.error(f"Error fetching related queries for '{keyword}': {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    def _get_related_queries_sync(self, keyword: str) -> Dict[str, pd.DataFrame]:
        """
        Synchronous method to get related queries (runs in thread pool)

        Args:
            keyword: Search keyword

        Returns:
            Dictionary with 'rising' and 'top' DataFrames
        """
        try:
            pytrends = self._create_pytrends()

            # Build payload with single keyword
            pytrends.build_payload([keyword], timeframe='today 3-m')

            # Get related queries
            related = pytrends.related_queries()

            result = {}

            if keyword in related:
                keyword_data = related[keyword]

                # Rising queries
                if keyword_data.get('rising') is not None and not keyword_data['rising'].empty:
                    result['rising'] = keyword_data['rising']

                # Top queries
                if keyword_data.get('top') is not None and not keyword_data['top'].empty:
                    result['top'] = keyword_data['top']

            return result

        except Exception as e:
            logger.error(f"Error in sync related queries fetch: {e}")
            return {}

    async def get_comprehensive_sentiment(
        self,
        timeframe: str = "now 7-d"
    ) -> Dict:
        """
        Get comprehensive sentiment analysis across all tracked commodities

        Args:
            timeframe: Time period for analysis

        Returns:
            Dictionary with complete sentiment analysis
        """
        logger.info("Generating comprehensive sentiment analysis")

        try:
            sentiment = {
                'timestamp': datetime.utcnow().isoformat(),
                'timeframe': timeframe,
                'commodities': {},
                'spikes': []
            }

            # Analyze each commodity
            for commodity in self.KEYWORDS.keys():
                # Get interest score
                score = await self.calculate_interest_score(commodity, timeframe)

                # Detect spikes
                spike = await self.detect_interest_spike(commodity, timeframe)

                if score:
                    sentiment['commodities'][commodity] = {
                        'score': score,
                        'spike': spike
                    }

                    # Track spikes separately
                    if spike.get('is_spike'):
                        sentiment['spikes'].append({
                            'commodity': commodity,
                            'current_interest': spike['current_interest'],
                            'z_score': spike['z_score']
                        })

                # Delay between commodities
                await asyncio.sleep(2)

            # Summary statistics
            if sentiment['commodities']:
                all_scores = [
                    data['score']['current_score']
                    for data in sentiment['commodities'].values()
                    if 'score' in data
                ]

                if all_scores:
                    sentiment['summary'] = {
                        'avg_interest': float(np.mean(all_scores)),
                        'max_interest': float(np.max(all_scores)),
                        'total_spikes': len(sentiment['spikes']),
                        'sentiment_level': self._categorize_sentiment(np.mean(all_scores))
                    }

            logger.success(
                f"Generated sentiment analysis for {len(sentiment['commodities'])} commodities. "
                f"Detected {len(sentiment['spikes'])} spikes."
            )

            return sentiment

        except Exception as e:
            logger.error(f"Error generating comprehensive sentiment: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}

    def _categorize_sentiment(self, avg_score: float) -> str:
        """
        Categorize sentiment level based on average interest score

        Args:
            avg_score: Average interest score (0-100)

        Returns:
            Sentiment category string
        """
        if avg_score >= 75:
            return 'very_high'
        elif avg_score >= 50:
            return 'high'
        elif avg_score >= 25:
            return 'moderate'
        else:
            return 'low'


# Singleton instance
google_trends_collector = GoogleTrendsCollector()
