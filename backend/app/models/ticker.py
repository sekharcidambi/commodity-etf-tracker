"""Ticker metadata model"""

from sqlalchemy import Column, String, Numeric, Date, Boolean, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.db.database import Base


class Ticker(Base):
    """Ticker metadata"""
    __tablename__ = "tickers"

    ticker = Column(String(10), primary_key=True)
    name = Column(String(200))
    asset_class = Column(String(50))
    leverage_factor = Column(Numeric(4, 2))
    expense_ratio = Column(Numeric(5, 4))
    inception_date = Column(Date)
    is_active = Column(Boolean, default=True)
    last_volume_check = Column(Date)
    avg_daily_volume = Column(Numeric)
    delisted_date = Column(Date)
    notes = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Ticker {self.ticker} - {self.name}>"
