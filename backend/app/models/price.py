"""Price data models"""

from sqlalchemy import Column, String, Numeric, BigInteger, Date, TIMESTAMP
from app.db.database import Base


class ETFPrice(Base):
    """ETF daily price data"""
    __tablename__ = "etf_prices"

    timestamp = Column(TIMESTAMP(timezone=True), primary_key=True)
    ticker = Column(String(10), primary_key=True)
    open = Column(Numeric(12, 4))
    high = Column(Numeric(12, 4))
    low = Column(Numeric(12, 4))
    close = Column(Numeric(12, 4))
    volume = Column(BigInteger)
    adj_close = Column(Numeric(12, 4))
    vwap = Column(Numeric(12, 4))

    def __repr__(self):
        return f"<ETFPrice {self.ticker} @ {self.timestamp}>"


class CommodityPrice(Base):
    """Commodity price data (spot, futures, ETF)"""
    __tablename__ = "commodity_prices"

    timestamp = Column(TIMESTAMP(timezone=True), primary_key=True)
    symbol = Column(String(10), primary_key=True)
    instrument_type = Column(String(20), primary_key=True)
    contract_month = Column(Date, primary_key=True, nullable=True, default='1970-01-01')
    open = Column(Numeric(12, 4))
    high = Column(Numeric(12, 4))
    low = Column(Numeric(12, 4))
    close = Column(Numeric(12, 4))
    volume = Column(BigInteger)
    open_interest = Column(BigInteger)

    def __repr__(self):
        return f"<CommodityPrice {self.symbol} {self.instrument_type} @ {self.timestamp}>"


class IntradayBar(Base):
    """Intraday bar data (1m, 5m, etc.)"""
    __tablename__ = "intraday_bars"

    timestamp = Column(TIMESTAMP(timezone=True), primary_key=True)
    ticker = Column(String(10), primary_key=True)
    interval = Column(String(5), primary_key=True)
    open = Column(Numeric(12, 4))
    high = Column(Numeric(12, 4))
    low = Column(Numeric(12, 4))
    close = Column(Numeric(12, 4))
    volume = Column(BigInteger)
    vwap = Column(Numeric(12, 4))

    def __repr__(self):
        return f"<IntradayBar {self.ticker} {self.interval} @ {self.timestamp}>"
