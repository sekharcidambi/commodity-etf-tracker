"""Test flow data collection from ETFdb and SEC"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.flow_collector import flow_collector
from app.services.etfdb_scraper import etfdb_scraper
from app.services.sec_scraper import sec_scraper
from app.services.data_storage import data_storage
from loguru import logger


async def main():
    """Test flow data collection"""
    logger.info("=" * 60)
    logger.info("TESTING FLOW DATA COLLECTION")
    logger.info("=" * 60)

    # Test 1: ETFdb.com scraper
    logger.info("\n1. Testing ETFdb.com scraper for AGQ and UGL...")
    try:
        etfdb_data = await etfdb_scraper.fetch_multiple_tickers(['AGQ', 'UGL'])
        logger.info(f"ETFdb scraper results: {len(etfdb_data)} tickers")
        for ticker, data in etfdb_data.items():
            logger.info(f"  {ticker}: AUM=${data.get('aum', 'N/A')}M, "
                       f"Avg Vol={data.get('average_volume', 'N/A')}, "
                       f"Expense Ratio={data.get('expense_ratio', 'N/A')}")
    except Exception as e:
        logger.error(f"ETFdb scraper test failed: {e}")

    # Test 2: SEC 13F scraper
    logger.info("\n2. Testing SEC 13F scraper (Blackrock example)...")
    try:
        # Test with Blackrock's CIK for AGQ
        sec_data = await sec_scraper.fetch_13f_holdings('1364742', 'AGQ')
        if sec_data:
            logger.info(f"SEC scraper results:")
            logger.info(f"  Institution: {sec_data.get('institution_name')}")
            logger.info(f"  CIK: {sec_data.get('cik')}")
            logger.info(f"  Holdings count: {len(sec_data.get('holdings', []))}")
            if sec_data.get('holdings'):
                logger.info(f"  Sample filing: {sec_data['holdings'][0]}")
        else:
            logger.warning("No 13F data found (this is expected - not all institutions hold all ETFs)")
    except Exception as e:
        logger.error(f"SEC scraper test failed: {e}")

    # Test 3: Flow collector - ETFdb flows
    logger.info("\n3. Testing flow collector - ETFdb flows...")
    try:
        etfdb_stats = await flow_collector.collect_etfdb_flows(['AGQ', 'UGL'])
        logger.info(f"Flow collection stats: {etfdb_stats}")
    except Exception as e:
        logger.error(f"Flow collector test failed: {e}")

    # Test 4: Retrieve saved flow data
    logger.info("\n4. Retrieving saved flow data from database...")
    try:
        agq_flows = await data_storage.get_etf_flows('AGQ', limit=5)
        logger.info(f"AGQ flows (last 5 records): {len(agq_flows)} records")
        if agq_flows:
            logger.info(f"Sample: {agq_flows[0]}")

        ugl_flows = await data_storage.get_etf_flows('UGL', limit=5)
        logger.info(f"UGL flows (last 5 records): {len(ugl_flows)} records")
        if ugl_flows:
            logger.info(f"Sample: {ugl_flows[0]}")
    except Exception as e:
        logger.error(f"Database retrieval test failed: {e}")

    # Test 5: Institutional holdings collection
    logger.info("\n5. Testing institutional holdings collection...")
    try:
        # Note: This will try to fetch from major institutions
        # Most won't have AGQ, so we expect low hit rate
        holdings_stats = await flow_collector.collect_institutional_holdings('AGQ')
        logger.info(f"Institutional holdings stats: {holdings_stats}")
    except Exception as e:
        logger.error(f"Institutional holdings test failed: {e}")

    # Test 6: Retrieve institutional holdings
    logger.info("\n6. Retrieving institutional holdings from database...")
    try:
        agq_holdings = await data_storage.get_institutional_holdings('AGQ', limit=10)
        logger.info(f"AGQ institutional holdings: {len(agq_holdings)} records")
        if agq_holdings:
            for holding in agq_holdings[:3]:  # Show first 3
                logger.info(f"  {holding['institution_name']}: {holding['filing_date']}")
    except Exception as e:
        logger.error(f"Holdings retrieval test failed: {e}")

    # Cleanup
    logger.info("\n7. Cleaning up HTTP sessions...")
    try:
        await etfdb_scraper.close()
        await sec_scraper.close()
        logger.success("Sessions closed")
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")

    logger.info("\n" + "=" * 60)
    logger.success("✅ FLOW DATA COLLECTION TEST COMPLETE!")
    logger.info("=" * 60)
    logger.info("\nNOTE: Some tests may show 'no data' results due to:")
    logger.info("  - ETFdb.com rate limiting or page structure changes")
    logger.info("  - SEC 13F filings may not include all ETFs")
    logger.info("  - Database may be empty on first run")


if __name__ == "__main__":
    asyncio.run(main())
