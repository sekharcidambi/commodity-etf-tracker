"""Data jobs model for tracking scheduled data collection jobs"""

from sqlalchemy import Column, Integer, String, TIMESTAMP, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base


class DataJob(Base):
    """Track execution history and status of scheduled data collection jobs"""
    __tablename__ = "data_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(100), nullable=False, index=True)
    job_type = Column(String(50), nullable=False)  # PRICE, FLOW, COT, INVENTORY, TRENDS, SENTIMENT, SIGNAL
    status = Column(String(20), nullable=False)  # RUNNING, COMPLETED, FAILED, CANCELLED
    started_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True))
    duration_seconds = Column(Integer)

    # Execution details
    records_processed = Column(Integer, default=0)
    records_saved = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)

    # Job metadata
    triggered_by = Column(String(50), default='SCHEDULER')  # SCHEDULER, MANUAL, API
    job_params = Column(JSONB)  # Store job parameters as JSON
    result_summary = Column(JSONB)  # Store execution results as JSON

    # Error tracking
    error_message = Column(Text)
    error_traceback = Column(Text)

    # Retry tracking
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    is_retry = Column(Boolean, default=False)
    parent_job_id = Column(Integer)  # Reference to original job if this is a retry

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<DataJob {self.id} {self.job_name} {self.status}>"
