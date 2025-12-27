"""Institutional holdings models"""

from sqlalchemy import Column, String, Numeric, BigInteger, Date
from app.db.database import Base


class InstitutionalHolding(Base):
    """Institutional holdings from 13F filings"""
    __tablename__ = "institutional_holdings"

    filing_date = Column(Date, primary_key=True)
    ticker = Column(String(10), primary_key=True)
    institution_name = Column(String(200), primary_key=True)
    shares = Column(BigInteger)
    value_usd = Column(Numeric(16, 2))  # in USD
    percent_of_portfolio = Column(Numeric(6, 4))
    change_shares = Column(BigInteger)  # change from previous quarter
    change_percent = Column(Numeric(7, 4))

    def __repr__(self):
        return f"<InstitutionalHolding {self.ticker} {self.institution_name} @ {self.filing_date}>"

