"""Scheduler service for automated data collection jobs using APScheduler"""

import asyncio
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job
from sqlalchemy import select, desc

from app.db.database import AsyncSessionLocal
from app.models.data_jobs import DataJob
from app.core.config import settings

# Import data collectors
from app.services.data_collector import data_collector
from app.services.flow_collector import flow_collector
from app.services.cot_collector import cot_collector
from app.services.comex_inventory_collector import comex_inventory_collector
from app.services.google_trends_collector import google_trends_collector
from app.services.reddit_sentiment_collector import reddit_sentiment_collector
from app.services.signal_generator import SignalGeneratorService
from app.services.data_storage import data_storage


class SchedulerService:
    """
    Manages automated data collection jobs using APScheduler

    Scheduled Jobs:
    1. Daily price collection (5 PM ET after market close)
    2. Weekly flow collection (Friday 6 PM ET)
    3. Weekly COT collection (Friday 5 PM ET after CFTC release)
    4. Daily COMEX inventory (6 PM ET)
    5. Hourly Google Trends
    6. Reddit sentiment (every 4 hours)
    7. Signal generation (7 PM ET after all data collected)
    """

    def __init__(self):
        """Initialize the scheduler service"""
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.is_running = False
        self.signal_generator = SignalGeneratorService()

        # Job registry for tracking
        self.job_registry: Dict[str, Dict[str, Any]] = {}

    def start_scheduler(self) -> None:
        """
        Start the APScheduler instance and schedule all jobs
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        try:
            logger.info("=" * 60)
            logger.info("STARTING SCHEDULER SERVICE")
            logger.info("=" * 60)

            # Create AsyncIOScheduler instance
            self.scheduler = AsyncIOScheduler(
                timezone='America/New_York',  # Eastern Time for market hours
                job_defaults={
                    'coalesce': True,  # Combine multiple pending executions into one
                    'max_instances': 1,  # Prevent overlapping executions
                    'misfire_grace_time': 300  # 5 minutes grace period
                }
            )

            # Schedule all jobs
            self._schedule_all_jobs()

            # Start the scheduler
            self.scheduler.start()
            self.is_running = True

            logger.success("Scheduler started successfully")
            logger.info(f"Scheduled {len(self.scheduler.get_jobs())} jobs")
            self._log_scheduled_jobs()

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            logger.error(traceback.format_exc())
            raise

    def stop_scheduler(self, wait: bool = True) -> None:
        """
        Stop the scheduler gracefully

        Args:
            wait: Wait for running jobs to complete before stopping
        """
        if not self.is_running or not self.scheduler:
            logger.warning("Scheduler is not running")
            return

        try:
            logger.info("Stopping scheduler...")
            self.scheduler.shutdown(wait=wait)
            self.is_running = False
            logger.success("Scheduler stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
            raise

    def _schedule_all_jobs(self) -> None:
        """Schedule all automated data collection jobs"""

        # 1. Daily price collection - Every day at 5 PM ET (after market close at 4 PM)
        self.add_job(
            job_name='daily_price_collection',
            func=self._job_wrapper(self._collect_daily_prices, 'PRICE'),
            trigger=CronTrigger(hour=17, minute=0, timezone='America/New_York'),
            job_id='daily_price_collection',
            name='Daily Price Collection',
            description='Collect ETF and futures prices after market close'
        )

        # 2. Weekly flow collection - Every Friday at 6 PM ET
        self.add_job(
            job_name='weekly_flow_collection',
            func=self._job_wrapper(self._collect_weekly_flows, 'FLOW'),
            trigger=CronTrigger(day_of_week='fri', hour=18, minute=0, timezone='America/New_York'),
            job_id='weekly_flow_collection',
            name='Weekly Flow Collection',
            description='Collect ETF flow data every Friday'
        )

        # 3. Weekly COT collection - Every Friday at 5 PM ET (CFTC releases Friday afternoon)
        self.add_job(
            job_name='weekly_cot_collection',
            func=self._job_wrapper(self._collect_cot_data, 'COT'),
            trigger=CronTrigger(day_of_week='fri', hour=17, minute=0, timezone='America/New_York'),
            job_id='weekly_cot_collection',
            name='Weekly COT Collection',
            description='Collect CFTC Commitment of Traders data'
        )

        # 4. Daily COMEX inventory - Every day at 6 PM ET
        self.add_job(
            job_name='daily_comex_inventory',
            func=self._job_wrapper(self._collect_comex_inventory, 'INVENTORY'),
            trigger=CronTrigger(hour=18, minute=0, timezone='America/New_York'),
            job_id='daily_comex_inventory',
            name='Daily COMEX Inventory',
            description='Collect COMEX warehouse inventory data'
        )

        # 5. Hourly Google Trends - Every hour
        self.add_job(
            job_name='hourly_google_trends',
            func=self._job_wrapper(self._collect_google_trends, 'TRENDS'),
            trigger=IntervalTrigger(hours=1),
            job_id='hourly_google_trends',
            name='Hourly Google Trends',
            description='Collect Google search interest data'
        )

        # 6. Reddit sentiment - Every 4 hours
        self.add_job(
            job_name='reddit_sentiment_collection',
            func=self._job_wrapper(self._collect_reddit_sentiment, 'SENTIMENT'),
            trigger=IntervalTrigger(hours=4),
            job_id='reddit_sentiment_collection',
            name='Reddit Sentiment Collection',
            description='Collect Reddit sentiment data'
        )

        # 7. Signal generation - Every day at 7 PM ET (after all data collected)
        self.add_job(
            job_name='daily_signal_generation',
            func=self._job_wrapper(self._generate_signals, 'SIGNAL'),
            trigger=CronTrigger(hour=19, minute=0, timezone='America/New_York'),
            job_id='daily_signal_generation',
            name='Daily Signal Generation',
            description='Generate trading signals from collected data'
        )

        logger.info("All jobs scheduled successfully")

    def add_job(
        self,
        job_name: str,
        func: Callable,
        trigger,
        job_id: Optional[str] = None,
        **kwargs
    ) -> Optional[Job]:
        """
        Add a job to the scheduler

        Args:
            job_name: Unique name for the job
            func: Function to execute
            trigger: APScheduler trigger (CronTrigger, IntervalTrigger, etc.)
            job_id: Optional job ID (defaults to job_name)
            **kwargs: Additional job parameters (name, description, etc.)

        Returns:
            APScheduler Job instance or None if failed
        """
        if not self.scheduler:
            logger.error("Scheduler not initialized")
            return None

        try:
            job_id = job_id or job_name

            job = self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                replace_existing=True,
                **kwargs
            )

            # Track in registry
            self.job_registry[job_id] = {
                'job_name': job_name,
                'trigger': str(trigger),
                'added_at': datetime.utcnow(),
                'metadata': kwargs
            }

            logger.info(f"Added job: {job_name} (ID: {job_id})")
            return job

        except Exception as e:
            logger.error(f"Failed to add job {job_name}: {e}")
            return None

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a job from the scheduler

        Args:
            job_id: Job ID to remove

        Returns:
            True if removed successfully, False otherwise
        """
        if not self.scheduler:
            logger.error("Scheduler not initialized")
            return False

        try:
            self.scheduler.remove_job(job_id)

            # Remove from registry
            if job_id in self.job_registry:
                del self.job_registry[job_id]

            logger.info(f"Removed job: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}")
            return False

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """
        Get list of all scheduled jobs

        Returns:
            List of job dictionaries with details
        """
        if not self.scheduler:
            logger.warning("Scheduler not initialized")
            return []

        jobs_list = []

        for job in self.scheduler.get_jobs():
            job_info = {
                'job_id': job.id,
                'job_name': job.name or job.id,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
                'is_paused': job.next_run_time is None
            }

            # Add registry metadata if available
            if job.id in self.job_registry:
                job_info.update(self.job_registry[job.id])

            jobs_list.append(job_info)

        return jobs_list

    async def get_job_history(
        self,
        job_name: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get execution history for jobs

        Args:
            job_name: Filter by specific job name (None for all jobs)
            limit: Maximum number of records to return

        Returns:
            List of job execution records
        """
        try:
            async with AsyncSessionLocal() as session:
                # Build query
                query = select(DataJob)

                if job_name:
                    query = query.where(DataJob.job_name == job_name)

                query = query.order_by(desc(DataJob.started_at)).limit(limit)

                result = await session.execute(query)
                jobs = result.scalars().all()

                # Convert to dictionaries
                history = []
                for job in jobs:
                    history.append({
                        'id': job.id,
                        'job_name': job.job_name,
                        'job_type': job.job_type,
                        'status': job.status,
                        'started_at': job.started_at.isoformat() if job.started_at else None,
                        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                        'duration_seconds': job.duration_seconds,
                        'records_processed': job.records_processed,
                        'records_saved': job.records_saved,
                        'errors_count': job.errors_count,
                        'triggered_by': job.triggered_by,
                        'error_message': job.error_message,
                        'retry_count': job.retry_count
                    })

                return history

        except Exception as e:
            logger.error(f"Error fetching job history: {e}")
            return []

    async def trigger_job(
        self,
        job_name: str,
        triggered_by: str = 'MANUAL'
    ) -> Dict[str, Any]:
        """
        Manually trigger a job execution

        Args:
            job_name: Name of the job to trigger
            triggered_by: Who/what triggered the job (MANUAL, API, etc.)

        Returns:
            Execution result dictionary
        """
        logger.info(f"Manually triggering job: {job_name}")

        # Map job names to their functions
        job_functions = {
            'daily_price_collection': (self._collect_daily_prices, 'PRICE'),
            'weekly_flow_collection': (self._collect_weekly_flows, 'FLOW'),
            'weekly_cot_collection': (self._collect_cot_data, 'COT'),
            'daily_comex_inventory': (self._collect_comex_inventory, 'INVENTORY'),
            'hourly_google_trends': (self._collect_google_trends, 'TRENDS'),
            'reddit_sentiment_collection': (self._collect_reddit_sentiment, 'SENTIMENT'),
            'daily_signal_generation': (self._generate_signals, 'SIGNAL'),
        }

        if job_name not in job_functions:
            logger.error(f"Unknown job name: {job_name}")
            return {
                'success': False,
                'error': f'Unknown job: {job_name}'
            }

        try:
            func, job_type = job_functions[job_name]

            # Execute the job with wrapper
            wrapped_func = self._job_wrapper(func, job_type, triggered_by=triggered_by)
            result = await wrapped_func()

            return {
                'success': True,
                'job_name': job_name,
                'result': result
            }

        except Exception as e:
            logger.error(f"Error triggering job {job_name}: {e}")
            return {
                'success': False,
                'job_name': job_name,
                'error': str(e)
            }

    def pause_job(self, job_id: str) -> bool:
        """
        Pause a scheduled job

        Args:
            job_id: Job ID to pause

        Returns:
            True if paused successfully
        """
        if not self.scheduler:
            logger.error("Scheduler not initialized")
            return False

        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}")
            return False

    def resume_job(self, job_id: str) -> bool:
        """
        Resume a paused job

        Args:
            job_id: Job ID to resume

        Returns:
            True if resumed successfully
        """
        if not self.scheduler:
            logger.error("Scheduler not initialized")
            return False

        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}")
            return False

    def _job_wrapper(
        self,
        func: Callable,
        job_type: str,
        triggered_by: str = 'SCHEDULER'
    ) -> Callable:
        """
        Wrap a job function with logging, error handling, and database tracking

        Args:
            func: The actual job function to execute
            job_type: Type of job (PRICE, FLOW, etc.)
            triggered_by: How the job was triggered

        Returns:
            Wrapped async function
        """
        async def wrapped():
            job_name = func.__name__
            job_record_id = None
            start_time = datetime.utcnow()

            logger.info("=" * 60)
            logger.info(f"STARTING JOB: {job_name}")
            logger.info(f"Type: {job_type} | Triggered by: {triggered_by}")
            logger.info("=" * 60)

            try:
                # Create job record in database
                async with AsyncSessionLocal() as session:
                    job_record = DataJob(
                        job_name=job_name,
                        job_type=job_type,
                        status='RUNNING',
                        triggered_by=triggered_by,
                        started_at=start_time
                    )
                    session.add(job_record)
                    await session.commit()
                    await session.refresh(job_record)
                    job_record_id = job_record.id

                # Execute the actual job function
                result = await func()

                # Calculate duration
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()

                # Update job record with success
                async with AsyncSessionLocal() as session:
                    job_record = await session.get(DataJob, job_record_id)
                    if job_record:
                        job_record.status = 'COMPLETED'
                        job_record.completed_at = end_time
                        job_record.duration_seconds = int(duration)
                        job_record.result_summary = result

                        # Extract stats from result if available
                        if isinstance(result, dict):
                            job_record.records_processed = result.get('records_processed', 0)
                            job_record.records_saved = result.get('records_saved', 0)
                            job_record.errors_count = result.get('errors', 0)

                        await session.commit()

                logger.success("=" * 60)
                logger.success(f"JOB COMPLETED: {job_name}")
                logger.success(f"Duration: {duration:.2f}s")
                logger.success("=" * 60)

                return result

            except Exception as e:
                # Calculate duration even for failures
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                error_traceback = traceback.format_exc()

                logger.error("=" * 60)
                logger.error(f"JOB FAILED: {job_name}")
                logger.error(f"Error: {e}")
                logger.error(f"Duration: {duration:.2f}s")
                logger.error("=" * 60)
                logger.error(error_traceback)

                # Update job record with failure
                if job_record_id:
                    try:
                        async with AsyncSessionLocal() as session:
                            job_record = await session.get(DataJob, job_record_id)
                            if job_record:
                                job_record.status = 'FAILED'
                                job_record.completed_at = end_time
                                job_record.duration_seconds = int(duration)
                                job_record.error_message = str(e)
                                job_record.error_traceback = error_traceback
                                await session.commit()
                    except Exception as db_error:
                        logger.error(f"Failed to update job record: {db_error}")

                # Check if we should retry
                # (Simple retry logic - can be enhanced)
                return {
                    'success': False,
                    'error': str(e),
                    'duration': duration
                }

        return wrapped

    # ===== Job Implementation Functions =====

    async def _collect_daily_prices(self) -> Dict[str, Any]:
        """Collect daily price data for ETFs and futures"""
        logger.info("Collecting daily prices...")

        stats = await data_collector.collect_all_market_data(period="5d")

        return {
            'records_processed': stats.get('etf_data', {}).get('tickers_processed', 0) +
                               stats.get('futures_data', {}).get('symbols_processed', 0),
            'records_saved': stats.get('total_records', 0),
            'errors': stats.get('total_errors', 0),
            'details': stats
        }

    async def _collect_weekly_flows(self) -> Dict[str, Any]:
        """Collect weekly ETF flow data"""
        logger.info("Collecting weekly flows...")

        stats = await flow_collector.collect_all_flow_data()

        return {
            'records_saved': stats.get('total_records', 0),
            'details': stats
        }

    async def _collect_cot_data(self) -> Dict[str, Any]:
        """Collect CFTC Commitment of Traders data"""
        logger.info("Collecting COT data...")

        # Collect for all precious metals
        commodities = ['gold', 'silver', 'platinum']
        results = {}
        total_records = 0

        for commodity in commodities:
            try:
                positioning = await cot_collector.get_commodity_positioning(commodity)
                if positioning:
                    results[commodity] = positioning
                    total_records += 1
            except Exception as e:
                logger.error(f"Error collecting COT for {commodity}: {e}")

        return {
            'records_saved': total_records,
            'details': results
        }

    async def _collect_comex_inventory(self) -> Dict[str, Any]:
        """Collect COMEX warehouse inventory data"""
        logger.info("Collecting COMEX inventory...")

        # Collect for all commodities
        commodities = ['gold', 'silver', 'platinum', 'palladium']
        results = {}
        total_records = 0

        for commodity in commodities:
            try:
                inventory = await comex_inventory_collector.fetch_comex_inventory(commodity)
                if inventory:
                    results[commodity] = inventory
                    total_records += 1
            except Exception as e:
                logger.error(f"Error collecting inventory for {commodity}: {e}")

        return {
            'records_saved': total_records,
            'details': results
        }

    async def _collect_google_trends(self) -> Dict[str, Any]:
        """Collect Google Trends search interest data"""
        logger.info("Collecting Google Trends data...")

        try:
            sentiment = await google_trends_collector.get_comprehensive_sentiment(timeframe="now 7-d")

            commodities_count = len(sentiment.get('commodities', {}))
            spikes_count = len(sentiment.get('spikes', []))

            return {
                'records_saved': commodities_count,
                'spikes_detected': spikes_count,
                'details': sentiment
            }
        except Exception as e:
            logger.error(f"Error collecting Google Trends: {e}")
            return {
                'records_saved': 0,
                'error': str(e)
            }

    async def _collect_reddit_sentiment(self) -> Dict[str, Any]:
        """Collect Reddit sentiment data"""
        logger.info("Collecting Reddit sentiment...")

        try:
            # Collect for primary tickers
            tickers = settings.PRIMARY_TICKERS
            sentiment_data = await reddit_sentiment_collector.get_multi_ticker_sentiment(
                tickers=tickers,
                hours=4
            )

            total_mentions = sum(
                data.get('mentions', 0)
                for data in sentiment_data.get('tickers', {}).values()
            )

            return {
                'records_saved': len(tickers),
                'total_mentions': total_mentions,
                'details': sentiment_data
            }
        except Exception as e:
            logger.error(f"Error collecting Reddit sentiment: {e}")
            return {
                'records_saved': 0,
                'error': str(e)
            }

    async def _generate_signals(self) -> Dict[str, Any]:
        """Generate trading signals from collected data"""
        logger.info("Generating trading signals...")

        try:
            tickers = settings.PRIMARY_TICKERS
            all_signals = []

            for ticker in tickers:
                try:
                    signals = await self.signal_generator.generate_signals(ticker)
                    all_signals.extend(signals)

                    # Save signals to database
                    if signals:
                        await data_storage.save_signals(signals)

                except Exception as e:
                    logger.error(f"Error generating signals for {ticker}: {e}")

            return {
                'records_saved': len(all_signals),
                'tickers_processed': len(tickers),
                'signals_generated': len(all_signals),
                'details': {
                    'total_signals': len(all_signals),
                    'by_ticker': {
                        ticker: len([s for s in all_signals if s['ticker'] == ticker])
                        for ticker in tickers
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return {
                'records_saved': 0,
                'error': str(e)
            }

    def _log_scheduled_jobs(self) -> None:
        """Log all scheduled jobs for visibility"""
        jobs = self.get_scheduled_jobs()

        logger.info("\nScheduled Jobs:")
        logger.info("-" * 80)

        for job in jobs:
            logger.info(
                f"  {job['job_name']:<40} Next: {job['next_run_time'] or 'PAUSED'}"
            )

        logger.info("-" * 80)


# Singleton instance
scheduler_service = SchedulerService()
