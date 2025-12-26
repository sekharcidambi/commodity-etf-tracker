"""ETFdb.com flow data scraper"""

import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, Optional
from loguru import logger
import re


class ETFdbScraper:
    """Scraper for ETFdb.com ETF flow data"""

    BASE_URL = "https://etfdb.com/etf"

    def __init__(self):
        self.session = httpx.AsyncClient(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            },
            timeout=30.0,
            follow_redirects=True
        )

    async def fetch_etf_flow_data(self, ticker: str) -> Dict | None:
        """
        Fetch ETF flow data from ETFdb.com

        Args:
            ticker: ETF ticker symbol (e.g., 'AGQ', 'UGL')

        Returns:
            Dictionary with flow data or None if failed
        """
        try:
            url = f"{self.BASE_URL}/{ticker}/"
            logger.info(f"Fetching flow data from {url}")

            response = await self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Parse flow data from the page
            flow_data = self._parse_flow_data(soup, ticker)

            if flow_data:
                logger.success(f"Successfully scraped flow data for {ticker}")
                return flow_data
            else:
                logger.warning(f"No flow data found for {ticker}")
                return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {ticker}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping {ticker}: {e}")
            return None

    def _parse_flow_data(self, soup: BeautifulSoup, ticker: str) -> Dict | None:
        """
        Parse flow data from ETFdb.com page

        Args:
            soup: BeautifulSoup object of the page
            ticker: ETF ticker

        Returns:
            Dictionary with parsed data
        """
        data = {
            'ticker': ticker,
            'aum': None,
            'average_volume': None,
            'expense_ratio': None,
            'inception_date': None,
        }

        try:
            # Look for "Vitals" section which contains key metrics
            # Note: ETFdb.com structure may change, this is a best-effort parser

            # Find AUM (Assets Under Management)
            aum_elem = soup.find(text=re.compile(r'Assets Under Management', re.I))
            if aum_elem:
                aum_parent = aum_elem.find_parent()
                if aum_parent:
                    aum_value = aum_parent.find_next('td')
                    if aum_value:
                        aum_text = aum_value.get_text(strip=True)
                        data['aum'] = self._parse_aum(aum_text)

            # Find Average Volume
            vol_elem = soup.find(text=re.compile(r'Average Volume', re.I))
            if vol_elem:
                vol_parent = vol_elem.find_parent()
                if vol_parent:
                    vol_value = vol_parent.find_next('td')
                    if vol_value:
                        vol_text = vol_value.get_text(strip=True)
                        data['average_volume'] = self._parse_number(vol_text)

            # Find Expense Ratio
            expense_elem = soup.find(text=re.compile(r'Expense Ratio', re.I))
            if expense_elem:
                expense_parent = expense_elem.find_parent()
                if expense_parent:
                    expense_value = expense_parent.find_next('td')
                    if expense_value:
                        expense_text = expense_value.get_text(strip=True)
                        data['expense_ratio'] = self._parse_percentage(expense_text)

            logger.debug(f"Parsed data for {ticker}: {data}")
            return data

        except Exception as e:
            logger.error(f"Error parsing flow data: {e}")
            return None

    def _parse_aum(self, text: str) -> float | None:
        """Parse AUM value from text (e.g., '$245.7M' -> 245.7)"""
        try:
            # Remove currency symbols and whitespace
            text = text.replace('$', '').replace(',', '').strip()

            # Handle B (billions) and M (millions)
            if 'B' in text.upper():
                return float(text.upper().replace('B', '')) * 1000  # Convert to millions
            elif 'M' in text.upper():
                return float(text.upper().replace('M', ''))
            else:
                # Try to parse as is
                return float(text)
        except:
            return None

    def _parse_number(self, text: str) -> int | None:
        """Parse number from text (e.g., '1,234,567' -> 1234567)"""
        try:
            return int(text.replace(',', '').strip())
        except:
            return None

    def _parse_percentage(self, text: str) -> float | None:
        """Parse percentage from text (e.g., '0.95%' -> 0.0095)"""
        try:
            text = text.replace('%', '').strip()
            return float(text) / 100
        except:
            return None

    async def fetch_multiple_tickers(self, tickers: list[str]) -> Dict[str, Dict]:
        """
        Fetch flow data for multiple tickers

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary mapping ticker to flow data
        """
        results = {}

        for ticker in tickers:
            data = await self.fetch_etf_flow_data(ticker)
            if data:
                results[ticker] = data

            # Be polite - add delay between requests
            import asyncio
            await asyncio.sleep(2)  # 2 second delay

        logger.info(f"Fetched data for {len(results)}/{len(tickers)} tickers")
        return results

    async def close(self):
        """Close the HTTP session"""
        await self.session.aclose()


# Singleton instance
etfdb_scraper = ETFdbScraper()
