"""Backtesting service for evaluating historical signal performance"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from loguru import logger

from app.models import Signal, BacktestRun, SignalPerformance, ETFPrice
from app.db.database import AsyncSessionLocal
from app.services.data_storage import DataStorageService


class BacktestingService:
    """Service for backtesting trading signals and evaluating performance"""

    def __init__(self):
        self.data_storage = DataStorageService()

    async def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        tickers: List[str],
        signal_types: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main backtest runner - simulates trading based on historical signals

        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            tickers: List of tickers to test
            signal_types: List of signal types to test (None = all)
            config: Backtest configuration with keys:
                - initial_capital: Starting capital (default: 100000)
                - position_size_pct: % of capital per trade (default: 10)
                - stop_loss_pct: Stop loss percentage (optional)
                - take_profit_pct: Take profit percentage (optional)
                - max_holding_days: Maximum days to hold (default: 14)

        Returns:
            Dictionary with comprehensive performance metrics
        """
        # Set default configuration
        default_config = {
            'initial_capital': 100000,
            'position_size_pct': 10,
            'stop_loss_pct': None,
            'take_profit_pct': None,
            'max_holding_days': 14
        }
        if config:
            default_config.update(config)
        config = default_config

        logger.info(f"Starting backtest: {start_date.date()} to {end_date.date()}")
        logger.info(f"Tickers: {tickers}, Signal types: {signal_types}")
        logger.info(f"Config: {config}")

        try:
            # Create backtest run record
            run_id = await self._create_backtest_run(
                start_date, end_date, tickers, signal_types, config
            )

            # Get all historical signals in the date range
            signals = await self._get_historical_signals(
                start_date, end_date, tickers, signal_types
            )

            if not signals:
                logger.warning("No signals found in the specified date range")
                await self._update_backtest_status(run_id, 'COMPLETED', error_message="No signals found")
                return {
                    'run_id': run_id,
                    'total_trades': 0,
                    'message': 'No signals found in date range'
                }

            logger.info(f"Found {len(signals)} signals to backtest")

            # Fetch historical price data for all tickers
            price_data = await self._fetch_price_data(tickers, start_date, end_date)

            # Simulate trades for each signal
            trades = []
            for signal in signals:
                trade = await self._simulate_trade(signal, price_data, config)
                if trade:
                    trades.append(trade)

            logger.info(f"Simulated {len(trades)} trades")

            # Calculate performance metrics
            metrics = self.calculate_metrics(trades)

            # Calculate per-signal-type performance
            signal_type_results = self._calculate_signal_type_metrics(trades)

            # Save individual trade results to signal_performance table
            await self._save_signal_performances(trades)

            # Update backtest run with results
            await self.save_backtest_results(run_id, {
                **metrics,
                'signal_type_results': signal_type_results,
                'total_trades': len(trades)
            })

            logger.success(f"Backtest completed: {len(trades)} trades, {metrics.get('win_rate', 0):.1f}% win rate")

            return {
                'run_id': run_id,
                'config': config,
                'total_trades': len(trades),
                'metrics': metrics,
                'signal_type_results': signal_type_results,
                'trades': trades[:10]  # Return first 10 trades as sample
            }

        except Exception as e:
            logger.error(f"Backtest failed: {e}", exc_info=True)
            if 'run_id' in locals():
                await self._update_backtest_status(run_id, 'FAILED', error_message=str(e))
            raise

    async def evaluate_signal(
        self,
        signal: Dict[str, Any],
        historical_prices: pd.DataFrame
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluate a single signal against historical prices

        Args:
            signal: Signal dictionary with keys: id, ticker, signal_type, direction,
                   generated_at, strength, expires_at
            historical_prices: DataFrame with columns: timestamp, open, high, low, close

        Returns:
            Dictionary with evaluation results:
            - return_pct: Return percentage if signal was followed
            - max_drawdown_pct: Maximum adverse excursion
            - max_profit_pct: Maximum favorable excursion
            - is_winner: True if profitable
            - entry_price, exit_price, entry_timestamp, exit_timestamp, exit_reason
        """
        try:
            ticker = signal['ticker']
            signal_time = signal['generated_at']
            direction = signal['direction']

            # Filter prices after signal generation
            future_prices = historical_prices[
                historical_prices['timestamp'] > signal_time
            ].sort_values('timestamp')

            if future_prices.empty:
                logger.debug(f"No future prices available for signal {signal.get('id')}")
                return None

            # Entry: Use next available open price
            entry_row = future_prices.iloc[0]
            entry_price = float(entry_row['open'])
            entry_timestamp = entry_row['timestamp']

            # Track price action and determine exit
            exit_info = self._determine_exit(
                future_prices,
                entry_price,
                entry_timestamp,
                direction,
                signal.get('expires_at')
            )

            if not exit_info:
                return None

            # Calculate return
            if direction == 'BUY':
                return_pct = ((exit_info['exit_price'] - entry_price) / entry_price) * 100
            elif direction == 'SELL':
                return_pct = ((entry_price - exit_info['exit_price']) / entry_price) * 100
            else:  # WATCH or other
                return None

            # Calculate max adverse/favorable excursion
            holding_prices = future_prices[
                (future_prices['timestamp'] >= entry_timestamp) &
                (future_prices['timestamp'] <= exit_info['exit_timestamp'])
            ]

            if direction == 'BUY':
                max_profit_pct = ((holding_prices['high'].max() - entry_price) / entry_price) * 100
                max_drawdown_pct = ((holding_prices['low'].min() - entry_price) / entry_price) * 100
            else:  # SELL
                max_profit_pct = ((entry_price - holding_prices['low'].min()) / entry_price) * 100
                max_drawdown_pct = ((entry_price - holding_prices['high'].max()) / entry_price) * 100

            # Calculate holding period
            holding_period = exit_info['exit_timestamp'] - entry_timestamp
            holding_hours = holding_period.total_seconds() / 3600

            return {
                'signal_id': signal.get('id'),
                'ticker': ticker,
                'signal_type': signal['signal_type'],
                'direction': direction,
                'signal_generated_at': signal_time,
                'signal_strength': signal.get('strength'),
                'entry_price': entry_price,
                'entry_timestamp': entry_timestamp,
                'exit_price': exit_info['exit_price'],
                'exit_timestamp': exit_info['exit_timestamp'],
                'exit_reason': exit_info['exit_reason'],
                'return_pct': return_pct,
                'holding_period_hours': holding_hours,
                'max_drawdown_pct': max_drawdown_pct,
                'max_profit_pct': max_profit_pct,
                'is_winner': return_pct > 0
            }

        except Exception as e:
            logger.error(f"Error evaluating signal: {e}", exc_info=True)
            return None

    def calculate_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate performance metrics from a list of trades

        Args:
            trades: List of trade dictionaries from evaluate_signal

        Returns:
            Dictionary with metrics:
            - win_rate: Percentage of winning trades
            - avg_return: Average return per trade
            - avg_win: Average winning trade return
            - avg_loss: Average losing trade return
            - sharpe_ratio: Risk-adjusted return metric
            - max_drawdown: Maximum drawdown percentage
            - profit_factor: Ratio of gross profit to gross loss
            - total_return_pct: Total cumulative return
            - annualized_return_pct: Annualized return
        """
        if not trades:
            return {
                'win_rate': 0,
                'avg_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'profit_factor': 0
            }

        returns = [t['return_pct'] for t in trades if t.get('return_pct') is not None]

        if not returns:
            return {'win_rate': 0, 'avg_return': 0}

        # Win rate
        winners = [r for r in returns if r > 0]
        losers = [r for r in returns if r < 0]
        win_rate = (len(winners) / len(returns)) * 100 if returns else 0

        # Average returns
        avg_return = np.mean(returns)
        avg_win = np.mean(winners) if winners else 0
        avg_loss = np.mean(losers) if losers else 0

        # Sharpe ratio (annualized, assuming 252 trading days)
        if len(returns) > 1:
            std_return = np.std(returns, ddof=1)
            sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0

        # Maximum drawdown
        cumulative_returns = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = cumulative_returns - running_max
        max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0

        # Profit factor
        gross_profit = sum(winners) if winners else 0
        gross_loss = abs(sum(losers)) if losers else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Total and annualized returns
        total_return_pct = sum(returns)

        # Calculate time span for annualization
        if trades and trades[0].get('entry_timestamp') and trades[-1].get('exit_timestamp'):
            start_date = min(t['entry_timestamp'] for t in trades if t.get('entry_timestamp'))
            end_date = max(t['exit_timestamp'] for t in trades if t.get('exit_timestamp'))
            days = (end_date - start_date).days
            years = days / 365.25 if days > 0 else 1
            annualized_return_pct = (total_return_pct / years) if years > 0 else total_return_pct
        else:
            annualized_return_pct = total_return_pct

        return {
            'win_rate': round(win_rate, 2),
            'winning_trades': len(winners),
            'losing_trades': len(losers),
            'avg_return': round(avg_return, 4),
            'avg_win': round(avg_win, 4),
            'avg_loss': round(avg_loss, 4),
            'sharpe_ratio': round(sharpe_ratio, 3),
            'max_drawdown_pct': round(max_drawdown, 4),
            'profit_factor': round(profit_factor, 2),
            'total_return_pct': round(total_return_pct, 4),
            'annualized_return_pct': round(annualized_return_pct, 4)
        }

    async def get_signal_type_performance(
        self,
        signal_type: str,
        ticker: Optional[str] = None,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        Get performance statistics for a specific signal type

        Args:
            signal_type: Type of signal (e.g., 'EXTREME_FLOW')
            ticker: Optional ticker filter
            days: Number of days to look back

        Returns:
            Dictionary with aggregated performance stats
        """
        try:
            async with AsyncSessionLocal() as session:
                # Build query
                cutoff_date = datetime.utcnow() - timedelta(days=days)

                stmt = select(SignalPerformance).where(
                    and_(
                        SignalPerformance.signal_type == signal_type,
                        SignalPerformance.signal_generated_at >= cutoff_date
                    )
                )

                if ticker:
                    stmt = stmt.where(SignalPerformance.ticker == ticker)

                result = await session.execute(stmt)
                performances = result.scalars().all()

                if not performances:
                    return {
                        'signal_type': signal_type,
                        'ticker': ticker,
                        'total_signals': 0,
                        'message': 'No performance data found'
                    }

                # Convert to list of dicts for metrics calculation
                trades = []
                for perf in performances:
                    if perf.return_pct is not None:
                        trades.append({
                            'return_pct': float(perf.return_pct),
                            'is_winner': perf.is_winner,
                            'entry_timestamp': perf.entry_timestamp,
                            'exit_timestamp': perf.exit_timestamp,
                            'holding_period_hours': float(perf.holding_period_hours) if perf.holding_period_hours else 0
                        })

                metrics = self.calculate_metrics(trades)

                return {
                    'signal_type': signal_type,
                    'ticker': ticker,
                    'days_lookback': days,
                    'total_signals': len(performances),
                    **metrics
                }

        except Exception as e:
            logger.error(f"Error getting signal type performance: {e}")
            return {'error': str(e)}

    async def save_backtest_results(
        self,
        run_id: int,
        results: Dict[str, Any]
    ) -> bool:
        """
        Persist backtest results to database

        Args:
            run_id: Backtest run ID
            results: Dictionary with performance metrics

        Returns:
            True if successful
        """
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(BacktestRun).where(BacktestRun.id == run_id)
                result = await session.execute(stmt)
                backtest_run = result.scalar_one_or_none()

                if not backtest_run:
                    logger.error(f"Backtest run {run_id} not found")
                    return False

                # Update with results
                backtest_run.status = 'COMPLETED'
                backtest_run.completed_at = datetime.utcnow()
                backtest_run.total_trades = results.get('total_trades', 0)
                backtest_run.winning_trades = results.get('winning_trades', 0)
                backtest_run.losing_trades = results.get('losing_trades', 0)
                backtest_run.win_rate = Decimal(str(results.get('win_rate', 0)))
                backtest_run.total_return_pct = Decimal(str(results.get('total_return_pct', 0)))
                backtest_run.annualized_return_pct = Decimal(str(results.get('annualized_return_pct', 0)))
                backtest_run.max_drawdown_pct = Decimal(str(results.get('max_drawdown_pct', 0)))
                backtest_run.sharpe_ratio = Decimal(str(results.get('sharpe_ratio', 0)))
                backtest_run.signal_type_results = results.get('signal_type_results')

                await session.commit()
                logger.success(f"Saved backtest results for run {run_id}")
                return True

        except Exception as e:
            logger.error(f"Error saving backtest results: {e}")
            return False

    # ==================== Private Helper Methods ====================

    async def _create_backtest_run(
        self,
        start_date: datetime,
        end_date: datetime,
        tickers: List[str],
        signal_types: Optional[List[str]],
        config: Dict[str, Any]
    ) -> int:
        """Create a new backtest run record"""
        try:
            async with AsyncSessionLocal() as session:
                run = BacktestRun(
                    run_name=f"Backtest {datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    start_date=start_date.date(),
                    end_date=end_date.date(),
                    tickers=tickers,
                    signal_types=signal_types,
                    initial_capital=Decimal(str(config['initial_capital'])),
                    position_size_pct=Decimal(str(config['position_size_pct'])),
                    stop_loss_pct=Decimal(str(config['stop_loss_pct'])) if config.get('stop_loss_pct') else None,
                    take_profit_pct=Decimal(str(config['take_profit_pct'])) if config.get('take_profit_pct') else None,
                    max_holding_days=config['max_holding_days'],
                    status='RUNNING',
                    started_at=datetime.utcnow()
                )
                session.add(run)
                await session.commit()
                await session.refresh(run)
                return run.id
        except Exception as e:
            logger.error(f"Error creating backtest run: {e}")
            raise

    async def _update_backtest_status(
        self,
        run_id: int,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """Update backtest run status"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(BacktestRun).where(BacktestRun.id == run_id)
                result = await session.execute(stmt)
                run = result.scalar_one_or_none()
                if run:
                    run.status = status
                    run.completed_at = datetime.utcnow()
                    if error_message:
                        run.error_message = error_message
                    await session.commit()
        except Exception as e:
            logger.error(f"Error updating backtest status: {e}")

    async def _get_historical_signals(
        self,
        start_date: datetime,
        end_date: datetime,
        tickers: List[str],
        signal_types: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """Fetch historical signals from database"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(Signal).where(
                    and_(
                        Signal.generated_at >= start_date,
                        Signal.generated_at <= end_date,
                        Signal.ticker.in_(tickers)
                    )
                )

                if signal_types:
                    stmt = stmt.where(Signal.signal_type.in_(signal_types))

                stmt = stmt.order_by(Signal.generated_at)

                result = await session.execute(stmt)
                signals = result.scalars().all()

                return [
                    {
                        'id': s.id,
                        'generated_at': s.generated_at,
                        'ticker': s.ticker,
                        'signal_type': s.signal_type,
                        'direction': s.direction,
                        'strength': float(s.strength) if s.strength else None,
                        'expires_at': s.expires_at
                    }
                    for s in signals
                ]

        except Exception as e:
            logger.error(f"Error fetching historical signals: {e}")
            return []

    async def _fetch_price_data(
        self,
        tickers: List[str],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, pd.DataFrame]:
        """Fetch historical price data for all tickers"""
        price_data = {}

        for ticker in tickers:
            try:
                prices = await self.data_storage.get_price_data(
                    ticker=ticker,
                    start_date=start_date - timedelta(days=1),  # Get one day before
                    end_date=end_date + timedelta(days=30),  # Get extra days for exits
                    limit=10000
                )

                if prices:
                    df = pd.DataFrame(prices)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp')
                    price_data[ticker] = df
                    logger.debug(f"Loaded {len(df)} price records for {ticker}")

            except Exception as e:
                logger.error(f"Error fetching price data for {ticker}: {e}")

        return price_data

    async def _simulate_trade(
        self,
        signal: Dict[str, Any],
        price_data: Dict[str, pd.DataFrame],
        config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Simulate a single trade based on a signal"""
        ticker = signal['ticker']

        if ticker not in price_data:
            logger.debug(f"No price data for {ticker}")
            return None

        return await self.evaluate_signal(signal, price_data[ticker])

    def _determine_exit(
        self,
        future_prices: pd.DataFrame,
        entry_price: float,
        entry_timestamp: datetime,
        direction: str,
        expires_at: Optional[datetime]
    ) -> Optional[Dict[str, Any]]:
        """
        Determine exit point based on price action and exit rules

        Returns dict with exit_price, exit_timestamp, exit_reason or None
        """
        # Default max holding period if expires_at not set
        if expires_at:
            max_exit_time = expires_at
        else:
            max_exit_time = entry_timestamp + timedelta(days=14)

        # Filter to holding period
        holding_period = future_prices[
            (future_prices['timestamp'] > entry_timestamp) &
            (future_prices['timestamp'] <= max_exit_time)
        ]

        if holding_period.empty:
            return None

        # Default stop loss and take profit percentages (can be made configurable)
        stop_loss_pct = 5.0  # 5% stop loss
        take_profit_pct = 10.0  # 10% take profit

        # Check each day for exit conditions
        for idx, row in holding_period.iterrows():
            timestamp = row['timestamp']
            high = float(row['high'])
            low = float(row['low'])
            close = float(row['close'])

            # For BUY signals
            if direction == 'BUY':
                # Check stop loss - if low goes below entry by stop_loss_pct
                stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
                if low <= stop_loss_price:
                    return {
                        'exit_price': stop_loss_price,
                        'exit_timestamp': timestamp,
                        'exit_reason': 'STOP_LOSS'
                    }

                # Check take profit - if high exceeds target by take_profit_pct
                take_profit_price = entry_price * (1 + take_profit_pct / 100)
                if high >= take_profit_price:
                    return {
                        'exit_price': take_profit_price,
                        'exit_timestamp': timestamp,
                        'exit_reason': 'TAKE_PROFIT'
                    }

            # For SELL signals (short positions)
            elif direction == 'SELL':
                # Check stop loss - if high goes above entry by stop_loss_pct
                stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
                if high >= stop_loss_price:
                    return {
                        'exit_price': stop_loss_price,
                        'exit_timestamp': timestamp,
                        'exit_reason': 'STOP_LOSS'
                    }

                # Check take profit - if low drops below entry by take_profit_pct
                take_profit_price = entry_price * (1 - take_profit_pct / 100)
                if low <= take_profit_price:
                    return {
                        'exit_price': take_profit_price,
                        'exit_timestamp': timestamp,
                        'exit_reason': 'TAKE_PROFIT'
                    }

        # If we get here, exit at end of holding period (expired)
        last_row = holding_period.iloc[-1]
        return {
            'exit_price': float(last_row['close']),
            'exit_timestamp': last_row['timestamp'],
            'exit_reason': 'EXPIRED'
        }

    def _calculate_signal_type_metrics(
        self,
        trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate metrics grouped by signal type"""
        signal_type_results = {}

        # Group trades by signal type
        trades_by_type = {}
        for trade in trades:
            signal_type = trade.get('signal_type')
            if signal_type:
                if signal_type not in trades_by_type:
                    trades_by_type[signal_type] = []
                trades_by_type[signal_type].append(trade)

        # Calculate metrics for each signal type
        for signal_type, type_trades in trades_by_type.items():
            metrics = self.calculate_metrics(type_trades)
            signal_type_results[signal_type] = {
                'total_signals': len(type_trades),
                **metrics
            }

        return signal_type_results

    async def _save_signal_performances(
        self,
        trades: List[Dict[str, Any]]
    ) -> int:
        """Save individual trade performances to signal_performance table"""
        if not trades:
            return 0

        try:
            async with AsyncSessionLocal() as session:
                for trade in trades:
                    perf = SignalPerformance(
                        signal_id=trade.get('signal_id'),
                        ticker=trade.get('ticker'),
                        signal_type=trade.get('signal_type'),
                        direction=trade.get('direction'),
                        signal_generated_at=trade.get('signal_generated_at'),
                        signal_strength=Decimal(str(trade['signal_strength'])) if trade.get('signal_strength') else None,
                        entry_price=Decimal(str(trade['entry_price'])) if trade.get('entry_price') else None,
                        entry_timestamp=trade.get('entry_timestamp'),
                        exit_price=Decimal(str(trade['exit_price'])) if trade.get('exit_price') else None,
                        exit_timestamp=trade.get('exit_timestamp'),
                        exit_reason=trade.get('exit_reason'),
                        return_pct=Decimal(str(trade['return_pct'])) if trade.get('return_pct') is not None else None,
                        holding_period_hours=Decimal(str(trade['holding_period_hours'])) if trade.get('holding_period_hours') else None,
                        max_drawdown_pct=Decimal(str(trade['max_drawdown_pct'])) if trade.get('max_drawdown_pct') is not None else None,
                        max_profit_pct=Decimal(str(trade['max_profit_pct'])) if trade.get('max_profit_pct') is not None else None,
                        is_winner=trade.get('is_winner', False)
                    )
                    session.add(perf)

                await session.commit()
                logger.success(f"Saved {len(trades)} signal performance records")
                return len(trades)

        except Exception as e:
            logger.error(f"Error saving signal performances: {e}")
            return 0


# Singleton instance
backtesting_service = BacktestingService()
