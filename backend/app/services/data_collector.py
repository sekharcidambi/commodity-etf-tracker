"""Main data collection orchestrator"""

from datetime import datetime, timedelta
from typing import List, Dict
from loguru import logger

from app.core.config import settings
from app.services.yfinance_collector import yfinance_collector
from app.services.data_storage import data_storage


class DataCollector:
    """Orchestrates data collection from various sources"""

    def __init__(self):
        self.yf_collector = yfinance_collector
        self.storage = data_storage

    async def collect_daily_prices(
        self,
        tickers: List[str] | None = None,
        period: str = "5d"
    ) -> Dict[str, int]:
        """
        Collect daily price data for all configured tickers

        Args:
            tickers: List of tickers to collect (uses config if None)
            period: Time period to collect ('1d', '5d', '1mo', etc.)

        Returns:
            Dictionary with collection statistics
        """
        if tickers is None:
            tickers = settings.PRIMARY_TICKERS + settings.EXTENDED_TICKERS

        logger.info(f"Starting daily price collection for {len(tickers)} tickers")

        stats = {
            'tickers_processed': 0,
            'records_saved': 0,
            'errors': 0
        }

        # Collect ETF data
        etf_tickers = [t for t in tickers if not t.endswith('=F')]
        for ticker in etf_tickers:
            try:
                # Fetch data
                df = self.yf_collector.fetch_etf_data(ticker, period=period)

                if not df.empty:
                    # Save to database
                    saved = await self.storage.save_etf_prices(df)
                    stats['records_saved'] += saved
                    stats['tickers_processed'] += 1
                else:
                    logger.warning(f"No data fetched for {ticker}")
                    stats['errors'] += 1

            except Exception as e:
                logger.error(f"Error collecting data for {ticker}: {e}")
                stats['errors'] += 1

        logger.success(
            f"Daily price collection complete: {stats['tickers_processed']} tickers, "
            f"{stats['records_saved']} records saved, {stats['errors']} errors"
        )

        return stats

    async def collect_futures_prices(
        self,
        symbols: List[str] | None = None,
        period: str = "5d"
    ) -> Dict[str, int]:
        """
        Collect futures price data

        Args:
            symbols: List of futures symbols (uses config if None)
            period: Time period to collect

        Returns:
            Dictionary with collection statistics
        """
        if symbols is None:
            symbols = settings.FUTURES_SYMBOLS

        logger.info(f"Starting futures price collection for {len(symbols)} symbols")

        stats = {
            'symbols_processed': 0,
            'records_saved': 0,
            'errors': 0
        }

        for symbol in symbols:
            try:
                # Fetch data
                df = self.yf_collector.fetch_futures_data(symbol, period=period)

                if not df.empty:
                    # Save to database
                    saved = await self.storage.save_commodity_prices(df)
                    stats['records_saved'] += saved
                    stats['symbols_processed'] += 1
                else:
                    logger.warning(f"No data fetched for {symbol}")
                    stats['errors'] += 1

            except Exception as e:
                logger.error(f"Error collecting data for {symbol}: {e}")
                stats['errors'] += 1

        logger.success(
            f"Futures price collection complete: {stats['symbols_processed']} symbols, "
            f"{stats['records_saved']} records saved, {stats['errors']} errors"
        )

        return stats

    async def collect_all_market_data(self, period: str = "5d") -> Dict:
        """
        Collect all market data (ETFs + Futures)

        Args:
            period: Time period to collect

        Returns:
            Combined statistics
        """
        logger.info("=" * 60)
        logger.info("STARTING FULL MARKET DATA COLLECTION")
        logger.info("=" * 60)

        start_time = datetime.utcnow()

        # Collect ETF prices
        etf_stats = await self.collect_daily_prices(period=period)

        # Collect futures prices
        futures_stats = await self.collect_futures_prices(period=period)

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        combined_stats = {
            'started_at': start_time.isoformat(),
            'completed_at': end_time.isoformat(),
            'duration_seconds': duration,
            'etf_data': etf_stats,
            'futures_data': futures_stats,
            'total_records': etf_stats['records_saved'] + futures_stats['records_saved'],
            'total_errors': etf_stats['errors'] + futures_stats['errors']
        }

        logger.info("=" * 60)
        logger.success(f"DATA COLLECTION COMPLETE IN {duration:.2f}s")
        logger.info(f"Total records saved: {combined_stats['total_records']}")
        logger.info(f"Total errors: {combined_stats['total_errors']}")
        logger.info("=" * 60)

        return combined_stats

    async def backfill_historical_data(
        self,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime | None = None
    ) -> Dict:
        """
        Backfill historical data for tickers

        Args:
            tickers: List of tickers to backfill
            start_date: Start date for historical data
            end_date: End date (defaults to today)

        Returns:
            Statistics
        """
        if end_date is None:
            end_date = datetime.utcnow()

        logger.info(
            f"Starting historical backfill from {start_date.date()} to {end_date.date()} "
            f"for {len(tickers)} tickers"
        )

        stats = {
            'tickers_processed': 0,
            'records_saved': 0,
            'errors': 0
        }

        for ticker in tickers:
            try:
                if ticker.endswith('=F'):
                    # Futures
                    df = self.yf_collector.fetch_futures_data(
                        ticker,
                        start_date=start_date,
                        end_date=end_date
                    )
                    if not df.empty:
                        saved = await self.storage.save_commodity_prices(df)
                        stats['records_saved'] += saved
                        stats['tickers_processed'] += 1
                else:
                    # ETF
                    df = self.yf_collector.fetch_etf_data(
                        ticker,
                        start_date=start_date,
                        end_date=end_date
                    )
                    if not df.empty:
                        saved = await self.storage.save_etf_prices(df)
                        stats['records_saved'] += saved
                        stats['tickers_processed'] += 1

            except Exception as e:
                logger.error(f"Error backfilling {ticker}: {e}")
                stats['errors'] += 1

        logger.success(
            f"Historical backfill complete: {stats['records_saved']} records saved"
        )

        return stats


# Singleton instance
data_collector = DataCollector()
