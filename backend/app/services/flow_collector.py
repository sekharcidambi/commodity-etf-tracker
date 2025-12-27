"""Flow data collection orchestrator"""

from datetime import datetime, date, timedelta
from typing import Dict, List
from loguru import logger

from app.services.etfdb_scraper import etfdb_scraper
from app.services.sec_scraper import sec_scraper
from app.services.yfinance_institutional import yfinance_institutional
from app.services.data_storage import data_storage
from app.core.config import settings


class FlowCollector:
    """Orchestrates collection of ETF flow data from various sources"""

    def __init__(self):
        self.etfdb = etfdb_scraper
        self.sec = sec_scraper
        self.storage = data_storage

    async def collect_etfdb_flows(self, tickers: List[str] = None) -> Dict:
        """
        Collect ETF flow data from ETFdb.com

        Args:
            tickers: List of ticker symbols, defaults to PRIMARY_TICKERS

        Returns:
            Collection statistics
        """
        if tickers is None:
            tickers = settings.PRIMARY_TICKERS

        logger.info(f"Collecting ETFdb flow data for {len(tickers)} tickers")

        # Fetch data from ETFdb.com
        flow_data = await self.etfdb.fetch_multiple_tickers(tickers)

        if not flow_data:
            logger.warning("No flow data collected from ETFdb")
            return {'status': 'no_data', 'tickers_processed': 0, 'records_saved': 0}

        # Transform scraped data to database format
        flow_records = []
        for ticker, data in flow_data.items():
            # ETFdb doesn't provide weekly flows directly, so we estimate
            # using AUM changes. This is a placeholder - actual implementation
            # would need historical AUM data to calculate flows

            record = {
                'week_ending': self._get_latest_week_end(),
                'ticker': ticker,
                'net_flow': None,  # Would calculate from AUM change
                'aum': data.get('aum'),
                'shares_outstanding': None,
                'premium_discount': None,
                'source': 'ETFdb.com'
            }
            flow_records.append(record)

        # Save to database
        saved_count = await self.storage.save_etf_flows(flow_records)

        logger.success(f"Collected ETFdb flows: {len(flow_data)} tickers, {saved_count} records saved")

        return {
            'status': 'success',
            'source': 'ETFdb.com',
            'tickers_processed': len(flow_data),
            'records_saved': saved_count
        }

    async def collect_institutional_holdings(
        self,
        ticker: str,
        institutions: Dict[str, str] = None
    ) -> Dict:
        """
        Collect institutional holdings using yfinance

        Args:
            ticker: Ticker symbol
            institutions: Not used (kept for compatibility)

        Returns:
            Collection statistics
        """
        logger.info(f"Collecting institutional holdings for {ticker} using yfinance")

        # Fetch holdings using yfinance
        holdings_records = yfinance_institutional.fetch_institutional_holders(ticker)

        if not holdings_records:
            logger.warning(f"No institutional holdings found for {ticker}")
            return {'status': 'no_data', 'institutions_processed': 0, 'records_saved': 0}

        # Save to database
        saved_count = await self.storage.save_institutional_holdings(holdings_records)

        logger.success(f"Collected institutional holdings: {len(holdings_records)} institutions, {saved_count} records saved")

        return {
            'status': 'success',
            'source': 'Yahoo Finance',
            'ticker': ticker,
            'institutions_processed': len(holdings_records),
            'records_saved': saved_count
        }

    async def collect_all_flow_data(self) -> Dict:
        """
        Collect all flow data from all sources

        Returns:
            Aggregated collection statistics
        """
        logger.info("=" * 60)
        logger.info("COLLECTING ALL FLOW DATA")
        logger.info("=" * 60)

        stats = {
            'etfdb_flows': {},
            'institutional_holdings': {},
            'total_records': 0
        }

        # Collect ETFdb flows
        logger.info("\n1. Collecting ETFdb.com flow data...")
        etfdb_stats = await self.collect_etfdb_flows()
        stats['etfdb_flows'] = etfdb_stats
        stats['total_records'] += etfdb_stats.get('records_saved', 0)

        # Collect institutional holdings for primary tickers
        logger.info("\n2. Collecting SEC 13F institutional holdings...")
        for ticker in settings.PRIMARY_TICKERS:
            holdings_stats = await self.collect_institutional_holdings(ticker)
            stats['institutional_holdings'][ticker] = holdings_stats
            stats['total_records'] += holdings_stats.get('records_saved', 0)

        logger.info("\n" + "=" * 60)
        logger.success(f"FLOW COLLECTION COMPLETE - {stats['total_records']} total records saved")
        logger.info("=" * 60)

        return stats

    async def estimate_segment_flows(self, ticker: str, week_ending: date) -> Dict:
        """
        Estimate investor segment flows (placeholder for future enhancement)

        This would analyze:
        - Korean retail flows (from ETFGI data when available)
        - US retail flows (estimated from total - institutional)
        - Institutional flows (from 13F data)
        - Sovereign funds (from known sovereign CIKs)

        Args:
            ticker: Ticker symbol
            week_ending: Week ending date

        Returns:
            Estimated segment flows
        """
        logger.info(f"Estimating segment flows for {ticker} week ending {week_ending}")

        # Placeholder implementation
        # Actual implementation would:
        # 1. Get total flows from ETFdb
        # 2. Get institutional holdings from 13F
        # 3. Estimate retail as residual
        # 4. Parse Korean flows from ETFGI reports (web scraping)

        segment_flows = []

        # Example placeholder data
        segments = ['KOREAN_RETAIL', 'US_RETAIL', 'INSTITUTIONAL', 'SOVEREIGN']

        for segment in segments:
            segment_flows.append({
                'week_ending': week_ending,
                'segment': segment,
                'ticker': ticker,
                'net_flow': None,  # Would calculate from various sources
                'estimated_aum': None
            })

        if segment_flows:
            saved_count = await self.storage.save_investor_segment_flows(segment_flows)
            logger.info(f"Saved {saved_count} segment flow records")

        return {
            'ticker': ticker,
            'week_ending': week_ending.isoformat(),
            'segments_estimated': len(segments),
            'records_saved': len(segment_flows)
        }

    def _get_latest_week_end(self) -> date:
        """Get the most recent Friday (week ending date)"""
        today = date.today()
        # Find the most recent Friday
        days_since_friday = (today.weekday() - 4) % 7
        friday = today - timedelta(days=days_since_friday)
        return friday


# Singleton instance
flow_collector = FlowCollector()
