#!/usr/bin/env python3
"""Test pandas_datareader with Stooq"""

import pandas_datareader as pdr
from datetime import datetime, timedelta
from loguru import logger

logger.info("Testing pandas_datareader with Stooq...")

try:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5)

    logger.info(f"Fetching AGQ from {start_date.date()} to {end_date.date()}...")

    # Stooq uses different ticker format - US stocks need .US suffix
    data = pdr.DataReader('AGQ.US', 'stooq', start_date, end_date)

    logger.info(f"Data shape: {data.shape}")
    logger.info(f"Data:\n{data}")

    if data.empty:
        logger.error("❌ Data is empty!")
    else:
        logger.success(f"✅ Successfully fetched {len(data)} records!")
        logger.info(f"Columns: {data.columns.tolist()}")

except Exception as e:
    logger.error(f"❌ Error: {e}")
    import traceback
    logger.error(traceback.format_exc())
