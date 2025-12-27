"""Collect institutional holdings data using yfinance"""

import yfinance as yf
from datetime import datetime, timedelta, date
from typing import List, Dict
from decimal import Decimal
from loguru import logger
import pandas as pd
import time
import requests


class YFinanceInstitutional:
    """Collect institutional holdings using yfinance"""

    def __init__(self):
        # Create a requests session with headers to avoid rate limiting
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

    def fetch_institutional_holders(self, ticker: str) -> List[Dict]:
        """
        Fetch institutional holders for a ticker from Yahoo Finance

        Args:
            ticker: ETF ticker symbol

        Returns:
            List of institutional holding records
        """
        try:
            logger.info(f"Fetching institutional holders for {ticker}...")
            time.sleep(5)  # Longer delay to avoid rate limiting

            stock = yf.Ticker(ticker, session=self.session)
            holders = stock.institutional_holders

            if holders is None or holders.empty:
                logger.warning(f"No institutional holders data for {ticker}")
                return []

            # Convert to our format
            holdings = []
            # Use most recent quarter end as filing date
            filing_date = self._get_recent_quarter_end()

            for idx, row in holders.iterrows():
                # Calculate change (yfinance doesn't provide historical, so we'll use 0 for now)
                shares = row.get('Shares', 0)
                value = row.get('Value', 0)
                pct_held = row.get('% Out', 0)

                holding = {
                    'filing_date': filing_date,
                    'ticker': ticker,
                    'institution_name': row.get('Holder', 'Unknown'),
                    'shares': int(shares) if pd.notna(shares) else 0,
                    'value_usd': Decimal(str(round(value, 2))) if pd.notna(value) else Decimal('0'),
                    'percent_of_portfolio': Decimal(str(round(pct_held, 4))) if pd.notna(pct_held) else Decimal('0'),
                    'change_shares': 0,  # Would need historical data
                    'change_percent': Decimal('0')
                }
                holdings.append(holding)

            logger.success(f"Fetched {len(holdings)} institutional holders for {ticker}")
            return holdings

        except Exception as e:
            logger.error(f"Error fetching institutional holders for {ticker}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _get_recent_quarter_end(self) -> date:
        """Get the most recent quarter end date"""
        today = datetime.now().date()
        year = today.year

        quarter_ends = [
            date(year, 3, 31),
            date(year, 6, 30),
            date(year, 9, 30),
            date(year, 12, 31),
        ]

        # Find most recent quarter end before today
        for qe in reversed(quarter_ends):
            if today >= qe:
                return qe

        # If we're before Q1 end, use last year's Q4
        return date(year - 1, 12, 31)


# Singleton
yfinance_institutional = YFinanceInstitutional()
