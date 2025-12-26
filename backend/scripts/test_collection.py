"""Test data collection"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.data_collector import data_collector
from loguru import logger


async def main():
    """Test data collection"""
    logger.info("=" * 60)
    logger.info("TESTING DATA COLLECTION")
    logger.info("=" * 60)

    # Collect data for primary tickers (5 days of data)
    logger.info("\n1. Collecting 5 days of data for AGQ and UGL...")
    stats = await data_collector.collect_daily_prices(
        tickers=['AGQ', 'UGL'],
        period='5d'
    )
    logger.info(f"ETF Collection Stats: {stats}")

    # Collect futures data
    logger.info("\n2. Collecting 5 days of futures data (gold, silver)...")
    futures_stats = await data_collector.collect_futures_prices(
        symbols=['GC=F', 'SI=F'],
        period='5d'
    )
    logger.info(f"Futures Collection Stats: {futures_stats}")

    # Get sample data back from database
    logger.info("\n3. Retrieving saved data from database...")
    from app.services.data_storage import data_storage

    agq_data = await data_storage.get_price_data('AGQ', limit=5)
    logger.info(f"AGQ data (last 5 records): {len(agq_data)} records")
    if agq_data:
        logger.info(f"Sample: {agq_data[0]}")

    ugl_data = await data_storage.get_price_data('UGL', limit=5)
    logger.info(f"UGL data (last 5 records): {len(ugl_data)} records")
    if ugl_data:
        logger.info(f"Sample: {ugl_data[0]}")

    logger.info("\n" + "=" * 60)
    logger.success("✅ DATA COLLECTION TEST COMPLETE!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
