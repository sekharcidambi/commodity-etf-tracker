#!/usr/bin/env python3
"""
Debug yfinance data collection
"""

import yfinance as yf
import pandas as pd
from loguru import logger


def test_yfinance():
    """Test yfinance directly"""
    logger.info("Testing yfinance...")

    ticker = "AGQ"
    logger.info(f"Fetching data for {ticker}...")

    try:
        stock = yf.Ticker(ticker)
        logger.info(f"Ticker object created: {stock}")

        # Try to get info
        logger.info("Getting ticker info...")
        info = stock.info
        logger.info(f"Ticker info: {info}")

        # Try to get history
        logger.info("Getting 5 days of history...")
        data = stock.history(period="5d")
        logger.info(f"Data shape: {data.shape}")
        logger.info(f"Data:\n{data}")

        if data.empty:
            logger.error("❌ Data is empty!")
        else:
            logger.success(f"✅ Successfully fetched {len(data)} records!")
            logger.info(f"Columns: {data.columns.tolist()}")
            logger.info(f"First row:\n{data.iloc[0]}")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    test_yfinance()
