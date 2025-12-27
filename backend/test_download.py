#!/usr/bin/env python3
"""Test yfinance download method"""

import yfinance as yf
import pandas as pd
from loguru import logger

logger.info("Testing yf.download()...")

try:
    logger.info("Downloading AGQ data for 5 days...")
    data = yf.download(
        "AGQ",
        period="5d",
        progress=False
    )

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
