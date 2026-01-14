"""
APScheduler Configuration for Batch Processing

Schedules non-batch background jobs. The main nightly batch processing
(symbol batch + portfolio refresh) runs via Railway cron, not APScheduler.

Jobs scheduled here:
- feedback_learning: Daily at 8:00 PM ET - Analyzes feedback patterns
- admin_metrics_batch: Daily at 8:30 PM ET - Aggregates metrics, cleanup
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from datetime import date
from typing import Any
import pytz

from app.core.logging import get_logger
from app.batch.batch_orchestrator import batch_orchestrator

logger = get_logger(__name__)


class BatchScheduler:
    """
    Manages scheduled batch jobs using APScheduler.

    Note: The main nightly batch (symbol batch + portfolio refresh) runs via
    Railway cron at 9 PM / 9:30 PM ET. APScheduler only handles non-conflicting
    background jobs that don't overlap with the main batch.
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
        Initialize scheduled background jobs.

        Only schedules non-batch jobs that don't conflict with the Railway cron:
        - feedback_learning: 8:00 PM ET
        - admin_metrics_batch: 8:30 PM ET

        The main batch jobs (symbol batch + portfolio refresh) run via Railway cron:
        - Symbol batch: 9:00 PM ET (scripts/automation/railway_daily_batch.py)
        - Portfolio refresh: Part of the same cron job
        """
        # Remove existing jobs to avoid duplicates
        self.scheduler.remove_all_jobs()

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

        logger.info("Background jobs initialized (feedback_learning, admin_metrics_batch)")
        logger.info("Main batch jobs run via Railway cron (9:00 PM ET)")
        self._log_scheduled_jobs()

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
        logger.info(f"Scheduled {len(jobs)} background jobs:")
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
        """Manually trigger daily batch processing via batch_orchestrator."""
        logger.info(f"Manual trigger: daily batch for portfolio {portfolio_id or 'all'}")
        return await batch_orchestrator.run_daily_batch_with_backfill(
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
        return await batch_orchestrator.run_daily_batch_with_backfill(
            portfolio_ids=[portfolio_id]
        )

    async def trigger_correlations(self, portfolio_id: str = None):
        """Manually trigger correlation calculations."""
        logger.info(f"Manual trigger: correlations for portfolio {portfolio_id or 'all'}")
        return await batch_orchestrator.run_daily_batch_with_backfill(
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
