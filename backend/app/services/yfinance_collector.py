"""yfinance data collector service"""

import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from loguru import logger


class YFinanceCollector:
    """Collect price data using yfinance"""

    def __init__(self):
        self.session = None

    def fetch_etf_data(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: str = "1mo"
    ) -> pd.DataFrame:
        """
        Fetch ETF price data from Yahoo Finance

        Args:
            ticker: ETF ticker symbol (e.g., 'AGQ', 'UGL')
            start_date: Start date for historical data
            end_date: End date for historical data
            period: Period if not using dates ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'max')

        Returns:
            DataFrame with OHLCV data
        """
        try:
            logger.info(f"Fetching data for {ticker}...")

            stock = yf.Ticker(ticker)

            if start_date and end_date:
                data = stock.history(start=start_date, end=end_date)
            else:
                data = stock.history(period=period)

            if data.empty:
                logger.warning(f"No data returned for {ticker}")
                return pd.DataFrame()

            # Reset index to get date as column
            data = data.reset_index()

            # Rename columns to match our schema
            data = data.rename(columns={
                'Date': 'timestamp',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            # Add ticker column
            data['ticker'] = ticker

            # Calculate adjusted close if not present
            if 'adj_close' not in data.columns:
                data['adj_close'] = data['close']

            # Select only needed columns
            data = data[['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume', 'adj_close']]

            logger.success(f"Fetched {len(data)} records for {ticker}")
            return data

        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return pd.DataFrame()

    def fetch_futures_data(
        self,
        symbol: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: str = "1mo"
    ) -> pd.DataFrame:
        """
        Fetch futures price data

        Args:
            symbol: Futures symbol (e.g., 'GC=F' for gold, 'SI=F' for silver)
            start_date: Start date
            end_date: End date
            period: Period string

        Returns:
            DataFrame with OHLCV data
        """
        try:
            logger.info(f"Fetching futures data for {symbol}...")

            futures = yf.Ticker(symbol)

            if start_date and end_date:
                data = futures.history(start=start_date, end=end_date)
            else:
                data = futures.history(period=period)

            if data.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()

            data = data.reset_index()

            # Map symbol to commodity name
            symbol_map = {
                'GC=F': 'XAU',  # Gold
                'SI=F': 'XAG',  # Silver
                'PL=F': 'XPT',  # Platinum
            }

            commodity_symbol = symbol_map.get(symbol, symbol)

            data = data.rename(columns={
                'Date': 'timestamp',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })

            data['symbol'] = commodity_symbol
            data['instrument_type'] = 'FUTURES'
            data['open_interest'] = None  # yfinance doesn't provide OI

            data = data[['timestamp', 'symbol', 'instrument_type', 'open', 'high', 'low', 'close', 'volume', 'open_interest']]

            logger.success(f"Fetched {len(data)} records for {symbol}")
            return data

        except Exception as e:
            logger.error(f"Error fetching futures data for {symbol}: {e}")
            return pd.DataFrame()

    def fetch_multiple_tickers(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        period: str = "1mo"
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple tickers

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date
            period: Period string

        Returns:
            Dictionary mapping ticker to DataFrame
        """
        results = {}

        for ticker in tickers:
            if ticker.endswith('=F'):
                # It's a futures contract
                data = self.fetch_futures_data(ticker, start_date, end_date, period)
            else:
                # It's an ETF/stock
                data = self.fetch_etf_data(ticker, start_date, end_date, period)

            if not data.empty:
                results[ticker] = data

        logger.info(f"Fetched data for {len(results)}/{len(tickers)} tickers")
        return results

    def get_realtime_quote(self, ticker: str) -> Dict:
        """
        Get real-time quote for a ticker

        Args:
            ticker: Ticker symbol

        Returns:
            Dictionary with quote data
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            return {
                'ticker': ticker,
                'last_price': info.get('currentPrice') or info.get('regularMarketPrice'),
                'bid': info.get('bid'),
                'ask': info.get('ask'),
                'volume': info.get('volume'),
                'market_cap': info.get('marketCap'),
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching realtime quote for {ticker}: {e}")
            return {}

    def get_ticker_info(self, ticker: str) -> Dict:
        """
        Get detailed ticker information

        Args:
            ticker: Ticker symbol

        Returns:
            Dictionary with ticker metadata
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            return {
                'ticker': ticker,
                'name': info.get('longName') or info.get('shortName'),
                'category': info.get('category'),
                'total_assets': info.get('totalAssets'),
                'ytd_return': info.get('ytdReturn'),
                'three_year_return': info.get('threeYearAverageReturn'),
                'five_year_return': info.get('fiveYearAverageReturn'),
                'expense_ratio': info.get('annualReportExpenseRatio'),
            }

        except Exception as e:
            logger.error(f"Error fetching ticker info for {ticker}: {e}")
            return {}


# Singleton instance
yfinance_collector = YFinanceCollector()
