"""SEC EDGAR 13F filings scraper for institutional holdings"""

import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
import asyncio


class SECScraper:
    """Scraper for SEC EDGAR 13F institutional holdings filings"""

    BASE_URL = "https://data.sec.gov"
    SUBMISSIONS_URL = f"{BASE_URL}/submissions"

    def __init__(self):
        # SEC requires a User-Agent header with contact info
        self.session = httpx.AsyncClient(
            headers={
                'User-Agent': 'Commodity ETF Tracker research@example.com',
                'Accept': 'application/json',
            },
            timeout=30.0,
            follow_redirects=True
        )
        # SEC rate limit: max 10 requests per second
        self.rate_limit_delay = 0.11  # 110ms between requests

    async def fetch_13f_holdings(
        self,
        cik: str,
        ticker: str,
        filing_date: Optional[datetime] = None
    ) -> Dict | None:
        """
        Fetch 13F holdings for a specific institution (CIK) and ticker

        Args:
            cik: Central Index Key (CIK) of the institution (10-digit, zero-padded)
            ticker: ETF ticker symbol to search for in holdings
            filing_date: Optional specific filing date to retrieve

        Returns:
            Dictionary with holdings data or None if failed
        """
        try:
            # Ensure CIK is 10 digits, zero-padded
            cik_padded = cik.zfill(10)

            url = f"{self.SUBMISSIONS_URL}/CIK{cik_padded}.json"
            logger.info(f"Fetching 13F data for CIK {cik_padded}")

            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)

            response = await self.session.get(url)
            response.raise_for_status()

            data = response.json()

            # Parse 13F filings from submission data
            holdings = self._parse_13f_filings(data, ticker, filing_date)

            if holdings:
                logger.success(f"Found {len(holdings)} 13F filings for CIK {cik_padded}")
                return {
                    'cik': cik_padded,
                    'institution_name': data.get('name', 'Unknown'),
                    'ticker': ticker,
                    'holdings': holdings
                }
            else:
                logger.warning(f"No 13F holdings found for {ticker} in CIK {cik_padded}")
                return None

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching CIK {cik}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error scraping CIK {cik}: {e}")
            return None

    def _parse_13f_filings(
        self,
        submission_data: Dict,
        ticker: str,
        filing_date: Optional[datetime] = None
    ) -> List[Dict] | None:
        """
        Parse 13F filings from SEC submission data

        Args:
            submission_data: JSON response from SEC API
            ticker: Ticker to search for
            filing_date: Optional specific filing date

        Returns:
            List of holdings records
        """
        try:
            filings = submission_data.get('filings', {}).get('recent', {})

            if not filings:
                return None

            # Get filing metadata
            forms = filings.get('form', [])
            filing_dates = filings.get('filingDate', [])
            accession_numbers = filings.get('accessionNumber', [])

            holdings = []

            # Filter for 13F-HR forms
            for i, form in enumerate(forms):
                if form in ['13F-HR', '13F-HR/A']:  # Include amendments
                    filing_dt = datetime.strptime(filing_dates[i], '%Y-%m-%d')

                    # If specific filing date requested, filter by date
                    if filing_date and abs((filing_dt - filing_date).days) > 7:
                        continue

                    # Note: Full holdings parsing requires fetching the XML filing
                    # For now, we'll store the filing metadata
                    # In production, you'd fetch and parse the InfoTable.xml file
                    holdings.append({
                        'filing_date': filing_dates[i],
                        'accession_number': accession_numbers[i],
                        'form_type': form,
                        'quarter_end': self._get_quarter_end(filing_dt),
                        # Placeholder - would need to fetch actual XML to get:
                        # 'shares_held': None,
                        # 'market_value': None,
                        # 'position_change': None,
                    })

            return holdings if holdings else None

        except Exception as e:
            logger.error(f"Error parsing 13F filings: {e}")
            return None

    def _get_quarter_end(self, filing_date: datetime) -> str:
        """
        Determine quarter end date from filing date
        13F filings are due 45 days after quarter end
        """
        # Work backwards to find quarter end
        quarter_ends = [
            datetime(filing_date.year, 3, 31),
            datetime(filing_date.year, 6, 30),
            datetime(filing_date.year, 9, 30),
            datetime(filing_date.year, 12, 31),
        ]

        # Find the most recent quarter end before filing date
        for qe in reversed(quarter_ends):
            if filing_date >= qe:
                return qe.strftime('%Y-%m-%d')

        # If filing is in Q1, use previous year Q4
        return datetime(filing_date.year - 1, 12, 31).strftime('%Y-%m-%d')

    async def fetch_major_institutions(self, ticker: str) -> Dict[str, Dict]:
        """
        Fetch 13F holdings from major known institutions for a ticker

        Args:
            ticker: ETF ticker symbol

        Returns:
            Dictionary mapping institution name to holdings data
        """
        # Major hedge funds and institutions (CIKs)
        major_institutions = {
            'Blackrock': '1364742',
            'Vanguard': '102909',
            'State Street': '1548165',
            'JPMorgan': '19617',
            'Goldman Sachs': '886982',
            'Morgan Stanley': '895421',
            'Citadel': '1423053',
            'Renaissance Technologies': '1037389',
            'Two Sigma': '1416463',
            'DE Shaw': '1009207',
        }

        results = {}

        for name, cik in major_institutions.items():
            logger.info(f"Fetching 13F for {name}...")
            data = await self.fetch_13f_holdings(cik, ticker)

            if data:
                results[name] = data

            # Rate limiting - SEC allows max 10 req/sec
            await asyncio.sleep(self.rate_limit_delay)

        logger.info(f"Fetched 13F data from {len(results)}/{len(major_institutions)} institutions")
        return results

    async def fetch_holdings_detail(self, accession_number: str, ticker: str) -> Dict | None:
        """
        Fetch detailed holdings from a specific 13F filing XML

        This would parse the InfoTable.xml to get actual share counts and values

        Args:
            accession_number: SEC accession number (e.g., '0001104659-23-123456')
            ticker: Ticker to search for in the filing

        Returns:
            Detailed holdings data or None
        """
        try:
            # Convert accession number format: 0001104659-23-123456 -> 000110465923123456
            acc_clean = accession_number.replace('-', '')

            # Construct URL to InfoTable.xml
            # Format: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=...
            # This is a simplified placeholder - actual implementation needs to:
            # 1. Fetch the filing index page
            # 2. Find the InfoTable.xml file
            # 3. Parse the XML for the specific ticker

            logger.info(f"Fetching detailed holdings for accession {accession_number}")
            logger.warning("Detailed holdings parsing not yet implemented - would parse InfoTable.xml")

            # Placeholder return
            return {
                'accession_number': accession_number,
                'ticker': ticker,
                'note': 'Detailed parsing requires InfoTable.xml implementation'
            }

        except Exception as e:
            logger.error(f"Error fetching holdings detail: {e}")
            return None

    async def close(self):
        """Close the HTTP session"""
        await self.session.aclose()


# Singleton instance
sec_scraper = SECScraper()
