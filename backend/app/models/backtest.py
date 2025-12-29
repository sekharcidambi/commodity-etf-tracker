"""Backtesting models"""

from sqlalchemy import Column, Integer, String, Numeric, TIMESTAMP, Text, Boolean, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.db.database import Base


class BacktestRun(Base):
    """Backtest run configuration and results"""
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_name = Column(String(100))

    # Backtest parameters
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    tickers = Column(JSONB, nullable=False)  # Array of tickers tested
    signal_types = Column(JSONB)  # Array of signal types to test (null = all)

    # Configuration
    initial_capital = Column(Numeric(15, 2), default=100000)
    position_size_pct = Column(Numeric(5, 2), default=10)  # % of capital per trade
    stop_loss_pct = Column(Numeric(5, 2))
    take_profit_pct = Column(Numeric(5, 2))
    max_holding_days = Column(Integer, default=14)

    # Results summary
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Numeric(5, 2))

    # Returns
    total_return_pct = Column(Numeric(10, 4))
    annualized_return_pct = Column(Numeric(10, 4))
    max_drawdown_pct = Column(Numeric(10, 4))
    sharpe_ratio = Column(Numeric(6, 3))

    # Per signal type performance
    signal_type_results = Column(JSONB)

    # Status
    status = Column(String(20), default='PENDING')  # PENDING, RUNNING, COMPLETED, FAILED
    error_message = Column(Text)

    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<BacktestRun {self.id} {self.run_name} {self.status}>"


class SignalPerformance(Base):
    """Individual signal performance tracking"""
    __tablename__ = "signal_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, nullable=False)  # References signals table
    ticker = Column(String(10), nullable=False)
    signal_type = Column(String(50), nullable=False)
    direction = Column(String(10), nullable=False)  # BUY, SELL, WATCH

    # Signal timing
    signal_generated_at = Column(TIMESTAMP(timezone=True), nullable=False)
    signal_strength = Column(Numeric(4, 2))

    # Entry point
    entry_price = Column(Numeric(12, 4))
    entry_timestamp = Column(TIMESTAMP(timezone=True))

    # Exit point
    exit_price = Column(Numeric(12, 4))
    exit_timestamp = Column(TIMESTAMP(timezone=True))
    exit_reason = Column(String(50))  # TARGET_HIT, STOP_LOSS, EXPIRED, MANUAL

    # Performance metrics
    return_pct = Column(Numeric(8, 4))  # (exit - entry) / entry * 100
    holding_period_hours = Column(Numeric(10, 2))

    # Maximum adverse/favorable excursion
    max_drawdown_pct = Column(Numeric(8, 4))
    max_profit_pct = Column(Numeric(8, 4))

    # Win/Loss classification
    is_winner = Column(Boolean)

    # Context at signal time
    market_regime = Column(String(30))
    composite_score_at_signal = Column(Numeric(6, 2))

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<SignalPerformance {self.id} {self.ticker} {self.signal_type} {self.return_pct}%>"
