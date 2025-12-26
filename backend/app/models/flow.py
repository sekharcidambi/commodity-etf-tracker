"""ETF flow data models"""

from sqlalchemy import Column, String, Numeric, BigInteger, Date, TIMESTAMP, Text
from sqlalchemy.sql import func
from app.db.database import Base


class ETFFlow(Base):
    """Weekly ETF flow data"""
    __tablename__ = "etf_flows"

    week_ending = Column(Date, primary_key=True)
    ticker = Column(String(10), primary_key=True)
    net_flow = Column(Numeric(16, 2))  # USD millions
    aum = Column(Numeric(16, 2))  # USD millions
    shares_outstanding = Column(BigInteger)
    premium_discount = Column(Numeric(6, 4))  # percentage
    source = Column(String(50))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ETFFlow {self.ticker} week {self.week_ending}: ${self.net_flow}M>"


class InvestorSegmentFlow(Base):
    """Investor segment flow data"""
    __tablename__ = "investor_segment_flows"

    week_ending = Column(Date, primary_key=True)
    ticker = Column(String(10), primary_key=True)
    segment = Column(String(50), primary_key=True)
    estimated_flow = Column(Numeric(16, 2))
    confidence_score = Column(Numeric(3, 2))
    data_source = Column(String(100))
    notes = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<InvestorSegmentFlow {self.ticker} {self.segment} week {self.week_ending}>"
