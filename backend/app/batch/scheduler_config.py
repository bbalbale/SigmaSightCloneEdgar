"""
APScheduler Configuration for Batch Processing
Implements the scheduling requirements from Section 1.6
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from datetime import datetime, date
from typing import Any
import pytz

from app.config import settings
from app.core.logging import get_logger
from app.batch.batch_orchestrator import batch_orchestrator

logger = get_logger(__name__)


class BatchScheduler:
    """
    Manages scheduled batch jobs using APScheduler.
    Implements the daily processing sequence at specific times.
    """
    
    def __init__(self):
        # Configure job stores - use memory store to avoid sync/async mixing
        # Note: Jobs are recreated on restart, but this eliminates greenlet context errors
        jobstores = {
            'default': MemoryJobStore()
        }
        
        # Configure executors
        executors = {
            'default': AsyncIOExecutor(),
        }
        
        # Job defaults
        job_defaults = {
            'coalesce': True,  # Coalesce missed jobs
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 3600  # 1 hour grace time for misfired jobs
        }
        
        # Create scheduler
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.timezone('US/Eastern')  # Market hours are in ET
        )
        
        # Add event listeners
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
    
    def initialize_jobs(self):
        """
        Initialize scheduled batch jobs based on V1/V2 mode.

        V1 Mode (BATCH_V2_ENABLED=false): All existing jobs scheduled
        V2 Mode (BATCH_V2_ENABLED=true): Only non-conflicting jobs scheduled
            - Symbol batch and portfolio refresh run via Railway cron (not APScheduler)
            - Market data, correlations, company profiles handled by V2 crons
            - Only feedback_learning and admin_metrics run via APScheduler

        Historical timeline for V1 (Section 1.6):
        - 4:00 PM: Market data update
        - 4:30 PM: Portfolio aggregation and Greeks
        - 5:00 PM: Factor analysis and risk metrics
        - 5:30 PM: Stress testing
        - 6:00 PM: Correlations (Daily)
        - 6:30 PM: Portfolio snapshots
        """
        # Remove existing jobs to avoid duplicates
        self.scheduler.remove_all_jobs()

        if settings.BATCH_V2_ENABLED:
            # =================================================================
            # V2 MODE: Only non-batch jobs run via APScheduler
            # Symbol batch and portfolio refresh run via Railway cron
            # =================================================================
            logger.info("V2 Batch Mode: Skipping batch jobs, using Railway cron")

            # Feedback learning batch job - Daily at 8:00 PM ET (Phase 3 PRD4)
            # Non-conflicting: doesn't touch market data or calculations
            self.scheduler.add_job(
                func=self._run_feedback_learning,
                trigger='cron',
                hour=20,  # 8:00 PM
                minute=0,
                id='feedback_learning',
                name='Daily Feedback Learning Analysis',
                replace_existing=True
            )

            # Admin metrics aggregation and cleanup - Daily at 8:30 PM ET
            # Non-conflicting: only aggregates metrics, no market data
            self.scheduler.add_job(
                func=self._run_admin_metrics_batch,
                trigger='cron',
                hour=20,  # 8:30 PM ET
                minute=30,
                id='admin_metrics_batch',
                name='Daily Admin Metrics Aggregation & Cleanup',
                replace_existing=True
            )

            logger.info("V2 Mode: Only feedback_learning and admin_metrics_batch scheduled")
            logger.info("V2 Cron jobs (via Railway): symbol_batch (9 PM), portfolio_refresh (9:30 PM)")

        else:
            # =================================================================
            # V1 MODE: All existing jobs scheduled (unchanged behavior)
            # =================================================================
            self._initialize_v1_jobs()

        logger.info(f"Batch jobs initialized (V2={settings.BATCH_V2_ENABLED})")
        self._log_scheduled_jobs()

    def _initialize_v1_jobs(self):
        """
        Initialize all V1 scheduled batch jobs.

        Separated into its own method for clarity. Called when BATCH_V2_ENABLED=false.
        """
        # Daily batch sequence - runs at 4:00 PM ET after market close
        self.scheduler.add_job(
            func=self._run_daily_batch,
            trigger='cron',
            hour=16,  # 4:00 PM
            minute=0,
            id='daily_batch_sequence',
            name='Daily Batch Processing Sequence',
            replace_existing=True
        )

        # Daily correlation calculation - Every day at 6:00 PM ET
        self.scheduler.add_job(
            func=self._run_daily_correlations,
            trigger='cron',
            hour=18,  # 6:00 PM
            minute=0,
            id='daily_correlations',
            name='Daily Correlation Calculation',
            replace_existing=True
        )

        # Company profile sync - Daily at 7:00 PM ET
        self.scheduler.add_job(
            func=self._sync_company_profiles,
            trigger='cron',
            hour=19,  # 7:00 PM
            minute=0,
            id='company_profile_sync',
            name='Daily Company Profile Sync',
            replace_existing=True
        )

        # Market data quality check - Daily at 7:30 PM ET
        self.scheduler.add_job(
            func=self._verify_market_data,
            trigger='cron',
            hour=19,  # 7:30 PM
            minute=30,
            id='market_data_verification',
            name='Daily Market Data Quality Check',
            replace_existing=True
        )

        # Historical data backfill - Weekly on Sunday at 2:00 AM ET
        self.scheduler.add_job(
            func=self._backfill_historical_data,
            trigger='cron',
            day_of_week='sun',
            hour=2,
            minute=0,
            id='historical_backfill',
            name='Weekly Historical Data Backfill',
            replace_existing=True
        )

        # Feedback learning batch job - Daily at 8:00 PM ET (Phase 3 PRD4)
        self.scheduler.add_job(
            func=self._run_feedback_learning,
            trigger='cron',
            hour=20,  # 8:00 PM
            minute=0,
            id='feedback_learning',
            name='Daily Feedback Learning Analysis',
            replace_existing=True
        )

        # Admin metrics aggregation and cleanup - Daily at 8:30 PM ET
        self.scheduler.add_job(
            func=self._run_admin_metrics_batch,
            trigger='cron',
            hour=20,  # 8:30 PM ET
            minute=30,
            id='admin_metrics_batch',
            name='Daily Admin Metrics Aggregation & Cleanup',
            replace_existing=True
        )
    
    async def _run_daily_batch(self):
        """Execute the daily batch processing sequence with automatic backfill."""
        logger.info("Starting scheduled daily batch processing")

        try:
            # V3: Use run_daily_batch_with_backfill for automatic gap detection
            result = await batch_orchestrator.run_daily_batch_with_backfill()

            logger.info(f"Daily batch completed: processed {result.get('dates_processed', 0)} dates")

            # Alert if there were errors
            if not result.get('success') or result.get('errors'):
                await self._send_batch_alert(
                    f"Daily batch completed with {len(result.get('errors', []))} errors",
                    result
                )

        except Exception as e:
            logger.error(f"Daily batch failed with exception: {str(e)}")
            await self._send_batch_alert(f"Daily batch failed: {str(e)}", None)
            raise
    
    async def _run_daily_correlations(self):
        """Execute daily correlation calculations."""
        logger.info("Starting scheduled daily correlation calculation")

        try:
            # V3: Correlations run automatically in Phase 3 analytics
            # Fixed: Added required calculation_date parameter (pre-existing bug)
            result = await batch_orchestrator.run_daily_batch_sequence(
                date.today()  # calculation_date - required parameter
            )

            logger.info(f"Daily correlations completed: {result.get('success')}")

        except Exception as e:
            logger.error(f"Daily correlation calculation failed: {str(e)}")
            await self._send_batch_alert(f"Correlation calculation failed: {str(e)}", None)
            raise
    
    async def _sync_company_profiles(self):
        """Sync company profiles for all portfolio symbols."""
        from app.batch.market_data_sync import sync_company_profiles

        logger.info("Starting scheduled company profile sync")

        try:
            result = await sync_company_profiles()

            logger.info(
                f"Company profile sync completed: {result['successful']}/{result['total']} successful"
            )

            # Alert if failure rate is high (>20%)
            if result['total'] > 0:
                failure_rate = result['failed'] / result['total']
                if failure_rate > 0.2:
                    await self._send_batch_alert(
                        f"Company profile sync: {result['failed']}/{result['total']} failures ({failure_rate*100:.1f}%)",
                        result
                    )

        except Exception as e:
            logger.error(f"Company profile sync failed: {str(e)}")
            await self._send_batch_alert(f"Company profile sync failed: {str(e)}", None)
            raise

    async def _verify_market_data(self):
        """Verify market data quality and completeness."""
        from app.batch.market_data_sync import verify_market_data_quality

        logger.info("Starting market data quality verification")

        try:
            result = await verify_market_data_quality()

            if result['stale_symbols'] > 0:
                logger.warning(
                    f"Found {result['stale_symbols']} symbols with stale data"
                )
                await self._send_batch_alert(
                    f"Market data quality check: {result['stale_symbols']} stale symbols",
                    result
                )
            else:
                logger.info("Market data quality check passed")

        except Exception as e:
            logger.error(f"Market data verification failed: {str(e)}")
            raise
    
    async def _backfill_historical_data(self):
        """Backfill missing historical market data."""
        from app.batch.market_data_sync import fetch_missing_historical_data

        logger.info("Starting weekly historical data backfill")

        try:
            result = await fetch_missing_historical_data(days_back=90)
            logger.info(f"Historical backfill completed: {result}")

        except Exception as e:
            logger.error(f"Historical backfill failed: {str(e)}")
            await self._send_batch_alert(f"Historical backfill failed: {str(e)}", None)
            raise

    async def _run_feedback_learning(self):
        """Execute daily feedback learning analysis (Phase 3 PRD4)."""
        from app.batch.feedback_learning_job import run_feedback_learning_batch

        logger.info("Starting scheduled feedback learning analysis")

        try:
            result = await run_feedback_learning_batch(
                min_confidence=0.7,
                days_lookback=30,
                min_feedback_per_user=3
            )

            logger.info(
                f"Feedback learning completed: "
                f"processed {result.get('users_processed', 0)} users, "
                f"created {result.get('total_rules_created', 0)} rules"
            )

            # Alert if errors occurred
            if result.get('errors'):
                await self._send_batch_alert(
                    f"Feedback learning: {len(result['errors'])} errors",
                    result
                )

        except Exception as e:
            logger.error(f"Feedback learning failed: {str(e)}")
            await self._send_batch_alert(f"Feedback learning failed: {str(e)}", None)
            raise

    async def _run_admin_metrics_batch(self):
        """Execute daily admin metrics aggregation and cleanup (Phase 7)."""
        from app.batch.admin_metrics_job import run_admin_metrics_batch

        logger.info("Starting scheduled admin metrics batch")

        try:
            result = await run_admin_metrics_batch(
                aggregate_days=1,  # Yesterday only
                run_cleanup=True   # Clean up old data
            )

            logger.info(
                f"Admin metrics batch completed: "
                f"aggregations={len(result.get('aggregation', []))}, "
                f"cleanup={result.get('cleanup', {})}"
            )

            # Alert if errors occurred
            if result.get('errors'):
                await self._send_batch_alert(
                    f"Admin metrics batch: {len(result['errors'])} errors",
                    result
                )

        except Exception as e:
            logger.error(f"Admin metrics batch failed: {str(e)}")
            await self._send_batch_alert(f"Admin metrics batch failed: {str(e)}", None)
            raise

    def _job_executed(self, event):
        """Log successful job execution."""
        logger.info(
            f"Job {event.job_id} executed successfully at {event.scheduled_run_time}"
        )
    
    def _job_error(self, event):
        """Log and alert on job errors."""
        logger.error(
            f"Job {event.job_id} crashed at {event.scheduled_run_time}: "
            f"{event.exception}"
        )
    
    async def _send_batch_alert(self, message: str, details: Any):
        """Send alert for batch job issues."""
        # TODO: Implement actual alerting (email, Slack, etc.)
        logger.warning(f"BATCH ALERT: {message}")
        if details:
            logger.warning(f"Details: {details}")
    
    def _log_scheduled_jobs(self):
        """Log all scheduled jobs for verification."""
        jobs = self.scheduler.get_jobs()
        logger.info(f"Scheduled {len(jobs)} batch jobs:")
        for job in jobs:
            logger.info(f"  - {job.id}: {job.name} @ {job.trigger}")
    
    def start(self):
        """Start the scheduler."""
        self.initialize_jobs()
        self.scheduler.start()
        logger.info("Batch scheduler started successfully")
    
    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        self.scheduler.shutdown(wait=True)
        logger.info("Batch scheduler shut down")
    
    # Manual trigger methods for admin endpoints
    
    async def trigger_daily_batch(self, portfolio_id: str = None):
        """Manually trigger daily batch processing."""
        logger.info(f"Manual trigger: daily batch for portfolio {portfolio_id or 'all'}")
        # V3: portfolio_ids is a list
        return await batch_orchestrator.run_daily_batch_sequence(
            portfolio_ids=[portfolio_id] if portfolio_id else None
        )

    async def trigger_market_data_update(self):
        """Manually trigger market data update."""
        from app.batch.market_data_collector import market_data_collector
        from app.database import AsyncSessionLocal
        logger.info("Manual trigger: market data update")
        async with AsyncSessionLocal() as db:
            return await market_data_collector.collect_all_market_data(db)

    async def trigger_portfolio_calculations(self, portfolio_id: str):
        """Manually trigger calculations for a specific portfolio."""
        logger.info(f"Manual trigger: calculations for portfolio {portfolio_id}")
        # V3: portfolio_ids is a list
        return await batch_orchestrator.run_daily_batch_sequence(
            portfolio_ids=[portfolio_id]
        )

    async def trigger_correlations(self, portfolio_id: str = None):
        """Manually trigger correlation calculations."""
        logger.info(f"Manual trigger: correlations for portfolio {portfolio_id or 'all'}")
        # V3: Correlations run automatically in Phase 3
        return await batch_orchestrator.run_daily_batch_sequence(
            portfolio_ids=[portfolio_id] if portfolio_id else None
        )

    async def trigger_company_profile_sync(self):
        """Manually trigger company profile sync."""
        from app.batch.market_data_sync import sync_company_profiles
        logger.info("Manual trigger: company profile sync")
        return await sync_company_profiles()


# Create singleton instance
batch_scheduler = BatchScheduler()


# FastAPI lifespan events integration
async def start_batch_scheduler():
    """Start the batch scheduler on application startup."""
    batch_scheduler.start()


async def stop_batch_scheduler():
    """Stop the batch scheduler on application shutdown."""
    batch_scheduler.shutdown()
