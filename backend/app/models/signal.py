"""Trading signal models"""

from sqlalchemy import Column, Integer, String, Numeric, TIMESTAMP, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base


class Signal(Base):
    """Trading signals generated from flow and price analysis"""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    generated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    ticker = Column(String(10))
    signal_type = Column(String(50), nullable=False)  # EXTREME_FLOW, DIVERGENCE, etc.
    direction = Column(String(10), nullable=False)  # BUY, SELL, WATCH
    strength = Column(Numeric(3, 2))  # 0.0 to 1.0
    trigger_values = Column(JSONB)  # Store calculation details as JSON
    status = Column(String(20), default='ACTIVE')  # ACTIVE, EXPIRED, CLOSED
    expires_at = Column(TIMESTAMP(timezone=True))
    closed_at = Column(TIMESTAMP(timezone=True))
    notes = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Signal {self.id} {self.ticker} {self.signal_type} {self.direction}>"
