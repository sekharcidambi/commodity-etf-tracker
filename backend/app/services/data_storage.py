"""Data storage service for saving collected data to database"""

import pandas as pd
from datetime import datetime
from typing import List
from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from loguru import logger

from app.models import ETFPrice, CommodityPrice, Ticker, ETFFlow, InvestorSegmentFlow, InstitutionalHolding
from app.db.database import AsyncSessionLocal


class DataStorageService:
    """Service for storing data in the database"""

    async def save_etf_prices(self, df: pd.DataFrame) -> int:
        """
        Save ETF price data to database

        Args:
            df: DataFrame with columns: timestamp, ticker, open, high, low, close, volume, adj_close

        Returns:
            Number of records saved
        """
        if df.empty:
            logger.warning("Empty DataFrame, nothing to save")
            return 0

        try:
            async with AsyncSessionLocal() as session:
                # Convert DataFrame to list of dicts
                records = df.to_dict('records')

                # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING for upsert
                stmt = pg_insert(ETFPrice).values(records)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['timestamp', 'ticker']
                )

                await session.execute(stmt)
                await session.commit()

                logger.success(f"Saved {len(records)} ETF price records")
                return len(records)

        except Exception as e:
            logger.error(f"Error saving ETF prices: {e}")
            raise

    async def save_commodity_prices(self, df: pd.DataFrame) -> int:
        """
        Save commodity/futures price data to database

        Args:
            df: DataFrame with columns: timestamp, symbol, instrument_type, open, high, low, close, volume, open_interest

        Returns:
            Number of records saved
        """
        if df.empty:
            logger.warning("Empty DataFrame, nothing to save")
            return 0

        try:
            async with AsyncSessionLocal() as session:
                # Add contract_month column if not present (required for primary key)
                if 'contract_month' not in df.columns:
                    df['contract_month'] = None

                records = df.to_dict('records')

                # Handle None/NULL for contract_month in primary key
                for record in records:
                    if record['contract_month'] is None or pd.isna(record['contract_month']):
                        record['contract_month'] = datetime(1970, 1, 1).date()

                stmt = pg_insert(CommodityPrice).values(records)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['timestamp', 'symbol', 'instrument_type', 'contract_month']
                )

                await session.execute(stmt)
                await session.commit()

                logger.success(f"Saved {len(records)} commodity price records")
                return len(records)

        except Exception as e:
            logger.error(f"Error saving commodity prices: {e}")
            raise

    async def get_latest_price_date(self, ticker: str) -> datetime | None:
        """
        Get the date of the last price record for a ticker

        Args:
            ticker: Ticker symbol

        Returns:
            Latest timestamp or None
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(ETFPrice.timestamp).where(
                    ETFPrice.ticker == ticker
                ).order_by(ETFPrice.timestamp.desc()).limit(1)

                result = await session.execute(stmt)
                latest = result.scalar_one_or_none()

                return latest

        except Exception as e:
            logger.error(f"Error getting latest price date for {ticker}: {e}")
            return None

    async def get_price_data(
        self,
        ticker: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100
    ) -> List[dict]:
        """
        Retrieve price data from database

        Args:
            ticker: Ticker symbol
            start_date: Optional start date
            end_date: Optional end date
            limit: Maximum number of records

        Returns:
            List of price records
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(ETFPrice).where(ETFPrice.ticker == ticker)

                if start_date:
                    stmt = stmt.where(ETFPrice.timestamp >= start_date)
                if end_date:
                    stmt = stmt.where(ETFPrice.timestamp <= end_date)

                stmt = stmt.order_by(ETFPrice.timestamp.desc()).limit(limit)

                result = await session.execute(stmt)
                prices = result.scalars().all()

                # Convert to dict
                return [
                    {
                        'timestamp': p.timestamp.isoformat(),
                        'ticker': p.ticker,
                        'open': float(p.open) if p.open else None,
                        'high': float(p.high) if p.high else None,
                        'low': float(p.low) if p.low else None,
                        'close': float(p.close) if p.close else None,
                        'volume': int(p.volume) if p.volume else None,
                        'adj_close': float(p.adj_close) if p.adj_close else None
                    }
                    for p in prices
                ]

        except Exception as e:
            logger.error(f"Error retrieving price data for {ticker}: {e}")
            return []

    async def update_ticker_info(self, ticker_data: dict) -> bool:
        """
        Update or insert ticker metadata

        Args:
            ticker_data: Dictionary with ticker information

        Returns:
            True if successful
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = pg_insert(Ticker).values(ticker_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['ticker'],
                    set_={
                        'name': stmt.excluded.name,
                        'updated_at': datetime.utcnow()
                    }
                )

                await session.execute(stmt)
                await session.commit()

                logger.success(f"Updated ticker info for {ticker_data.get('ticker')}")
                return True

        except Exception as e:
            logger.error(f"Error updating ticker info: {e}")
            return False

    async def save_etf_flows(self, flows_data: List[dict]) -> int:
        """
        Save ETF flow data to database

        Args:
            flows_data: List of flow records with fields:
                       week_ending, ticker, net_flow, aum, shares_outstanding,
                       premium_discount, source

        Returns:
            Number of records saved
        """
        if not flows_data:
            logger.warning("Empty flow data, nothing to save")
            return 0

        try:
            async with AsyncSessionLocal() as session:
                stmt = pg_insert(ETFFlow).values(flows_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['week_ending', 'ticker'],
                    set_={
                        'net_flow': stmt.excluded.net_flow,
                        'aum': stmt.excluded.aum,
                        'shares_outstanding': stmt.excluded.shares_outstanding,
                        'premium_discount': stmt.excluded.premium_discount,
                        'source': stmt.excluded.source,
                    }
                )

                await session.execute(stmt)
                await session.commit()

                logger.success(f"Saved {len(flows_data)} ETF flow records")
                return len(flows_data)

        except Exception as e:
            logger.error(f"Error saving ETF flows: {e}")
            raise

    async def save_institutional_holdings(self, holdings_data: List[dict]) -> int:
        """
        Save institutional holdings (13F data) to database

        Args:
            holdings_data: List of holdings records with fields:
                          filing_date, cik, institution_name, ticker,
                          shares_held, market_value, weight_pct

        Returns:
            Number of records saved
        """
        if not holdings_data:
            logger.warning("Empty holdings data, nothing to save")
            return 0

        try:
            async with AsyncSessionLocal() as session:
                stmt = pg_insert(InstitutionalHolding).values(holdings_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['filing_date', 'cik', 'ticker'],
                    set_={
                        'institution_name': stmt.excluded.institution_name,
                        'shares_held': stmt.excluded.shares_held,
                        'market_value': stmt.excluded.market_value,
                        'weight_pct': stmt.excluded.weight_pct,
                    }
                )

                await session.execute(stmt)
                await session.commit()

                logger.success(f"Saved {len(holdings_data)} institutional holding records")
                return len(holdings_data)

        except Exception as e:
            logger.error(f"Error saving institutional holdings: {e}")
            raise

    async def save_investor_segment_flows(self, segment_flows: List[dict]) -> int:
        """
        Save investor segment flow data to database

        Args:
            segment_flows: List of segment flow records with fields:
                          week_ending, segment, ticker, net_flow, estimated_aum

        Returns:
            Number of records saved
        """
        if not segment_flows:
            logger.warning("Empty segment flow data, nothing to save")
            return 0

        try:
            async with AsyncSessionLocal() as session:
                stmt = pg_insert(InvestorSegmentFlow).values(segment_flows)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['week_ending', 'segment', 'ticker'],
                    set_={
                        'net_flow': stmt.excluded.net_flow,
                        'estimated_aum': stmt.excluded.estimated_aum,
                    }
                )

                await session.execute(stmt)
                await session.commit()

                logger.success(f"Saved {len(segment_flows)} investor segment flow records")
                return len(segment_flows)

        except Exception as e:
            logger.error(f"Error saving investor segment flows: {e}")
            raise

    async def get_etf_flows(
        self,
        ticker: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 52  # Default 1 year of weekly data
    ) -> List[dict]:
        """
        Retrieve ETF flow data from database

        Args:
            ticker: Ticker symbol
            start_date: Optional start date
            end_date: Optional end date
            limit: Maximum number of records

        Returns:
            List of flow records
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(ETFFlow).where(ETFFlow.ticker == ticker)

                if start_date:
                    stmt = stmt.where(ETFFlow.week_ending >= start_date.date())
                if end_date:
                    stmt = stmt.where(ETFFlow.week_ending <= end_date.date())

                stmt = stmt.order_by(ETFFlow.week_ending.desc()).limit(limit)

                result = await session.execute(stmt)
                flows = result.scalars().all()

                return [
                    {
                        'week_ending': f.week_ending.isoformat(),
                        'ticker': f.ticker,
                        'net_flow': float(f.net_flow) if f.net_flow else None,
                        'aum': float(f.aum) if f.aum else None,
                        'shares_outstanding': int(f.shares_outstanding) if f.shares_outstanding else None,
                        'premium_discount': float(f.premium_discount) if f.premium_discount else None,
                        'source': f.source
                    }
                    for f in flows
                ]

        except Exception as e:
            logger.error(f"Error retrieving ETF flows for {ticker}: {e}")
            return []

    async def get_institutional_holdings(
        self,
        ticker: str,
        start_date: datetime | None = None,
        limit: int = 20
    ) -> List[dict]:
        """
        Retrieve institutional holdings for a ticker

        Args:
            ticker: Ticker symbol
            start_date: Optional start date
            limit: Maximum number of records

        Returns:
            List of holdings records
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(InstitutionalHolding).where(
                    InstitutionalHolding.ticker == ticker
                )

                if start_date:
                    stmt = stmt.where(InstitutionalHolding.filing_date >= start_date.date())

                stmt = stmt.order_by(InstitutionalHolding.filing_date.desc()).limit(limit)

                result = await session.execute(stmt)
                holdings = result.scalars().all()

                return [
                    {
                        'filing_date': h.filing_date.isoformat(),
                        'cik': h.cik,
                        'institution_name': h.institution_name,
                        'ticker': h.ticker,
                        'shares_held': int(h.shares_held) if h.shares_held else None,
                        'market_value': float(h.market_value) if h.market_value else None,
                        'weight_pct': float(h.weight_pct) if h.weight_pct else None
                    }
                    for h in holdings
                ]

        except Exception as e:
            logger.error(f"Error retrieving institutional holdings for {ticker}: {e}")
            return []


# Singleton instance
data_storage = DataStorageService()
