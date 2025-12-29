"""Alert models"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from app.db.database import Base


class AlertLog(Base):
    """Alert delivery log"""
    __tablename__ = "alert_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sent_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    alert_type = Column(String(50), nullable=False)
    ticker = Column(String(10))
    channel = Column(String(20), nullable=False)
    recipient = Column(String(200))
    message = Column(Text)
    status = Column(String(20), nullable=False, default='PENDING')
    error_message = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<AlertLog {self.id} {self.alert_type} {self.channel} {self.status}>"
