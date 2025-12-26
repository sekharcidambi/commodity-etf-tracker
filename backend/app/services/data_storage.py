"""Data storage service for saving collected data to database"""

import pandas as pd
from datetime import datetime
from typing import List
from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from loguru import logger

from app.models import ETFPrice, CommodityPrice, Ticker
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


# Singleton instance
data_storage = DataStorageService()
