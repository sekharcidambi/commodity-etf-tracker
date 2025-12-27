"""yfinance data collector service"""

import yfinance as yf
import pandas_datareader as pdr
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
from loguru import logger
import time
import requests


class YFinanceCollector:
    """Collect price data using yfinance"""

    def __init__(self):
        # Create a requests session with headers to avoid rate limiting
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

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

            # Add small delay to avoid rate limiting
            time.sleep(2)

            # Try yfinance first
            try:
                if start_date and end_date:
                    data = yf.download(
                        ticker,
                        start=start_date,
                        end=end_date,
                        progress=False,
                        session=self.session
                    )
                else:
                    data = yf.download(
                        ticker,
                        period=period,
                        progress=False,
                        session=self.session
                    )
            except Exception as e:
                logger.warning(f"yfinance failed for {ticker}: {e}")
                data = pd.DataFrame()

            # Fallback to Stooq if yfinance fails or returns empty data
            if data.empty:
                logger.info(f"Falling back to Stooq for {ticker}...")
                try:
                    # Stooq requires .US suffix for US stocks
                    stooq_ticker = f"{ticker}.US"

                    if start_date and end_date:
                        data = pdr.DataReader(stooq_ticker, 'stooq', start_date, end_date)
                    else:
                        # Convert period to date range for Stooq
                        end = datetime.now()
                        period_days = {
                            '1d': 1, '5d': 5, '1mo': 30, '3mo': 90,
                            '6mo': 180, '1y': 365, '2y': 730, '5y': 1825
                        }
                        days = period_days.get(period, 30)
                        start = end - timedelta(days=days)
                        data = pdr.DataReader(stooq_ticker, 'stooq', start, end)

                    # Reverse the data (Stooq returns newest first)
                    data = data.sort_index()

                    logger.success(f"Successfully fetched {len(data)} records from Stooq for {ticker}")
                except Exception as e:
                    logger.error(f"Stooq also failed for {ticker}: {e}")
                    return pd.DataFrame()

            if data.empty:
                logger.warning(f"No data returned for {ticker}")
                return pd.DataFrame()

            # Reset index to get date as column (if not already reset)
            if 'Date' not in data.columns and data.index.name in ['Date', None]:
                data = data.reset_index()

            # Rename columns to match our schema (handle both yfinance and Stooq formats)
            column_mapping = {}
            for col in data.columns:
                if col == 'Date':
                    column_mapping[col] = 'timestamp'
                elif col.lower() == 'open':
                    column_mapping[col] = 'open'
                elif col.lower() == 'high':
                    column_mapping[col] = 'high'
                elif col.lower() == 'low':
                    column_mapping[col] = 'low'
                elif col.lower() == 'close':
                    column_mapping[col] = 'close'
                elif col.lower() == 'volume':
                    column_mapping[col] = 'volume'
                elif col == 'Adj Close':
                    column_mapping[col] = 'adj_close'

            data = data.rename(columns=column_mapping)

            # Add ticker column
            data['ticker'] = ticker

            # Ensure adj_close exists (Stooq doesn't provide it)
            if 'adj_close' not in data.columns:
                data['adj_close'] = data['close']

            # Ensure timestamp is timezone-aware (database requires it)
            if pd.api.types.is_datetime64_any_dtype(data['timestamp']):
                if data['timestamp'].dt.tz is None:
                    # Localize to UTC if timezone-naive
                    data['timestamp'] = pd.to_datetime(data['timestamp']).dt.tz_localize('UTC')
            else:
                # Convert to datetime and localize to UTC
                data['timestamp'] = pd.to_datetime(data['timestamp']).dt.tz_localize('UTC')

            # Select only needed columns
            data = data[['timestamp', 'ticker', 'open', 'high', 'low', 'close', 'volume', 'adj_close']]

            logger.success(f"Fetched {len(data)} records for {ticker}")
            return data

        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            import traceback
            logger.error(traceback.format_exc())
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

            # Add small delay to avoid rate limiting
            time.sleep(2)

            # Use yf.download with custom session
            if start_date and end_date:
                data = yf.download(
                    symbol,
                    start=start_date,
                    end=end_date,
                    progress=False,
                    session=self.session
                )
            else:
                data = yf.download(
                    symbol,
                    period=period,
                    progress=False,
                    session=self.session
                )

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
            # Add delay to avoid rate limiting
            time.sleep(2)

            stock = yf.Ticker(ticker, session=self.session)
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
            # Add delay to avoid rate limiting
            time.sleep(2)

            stock = yf.Ticker(ticker, session=self.session)
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
