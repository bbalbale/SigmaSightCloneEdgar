"""
Batch Trigger Service

Provides shared batch orchestration logic for triggering batch calculations.

Can be used from:
- User-facing calculate endpoint (with ownership checks)
- Admin batch endpoint (with admin permissions)

Key features:
- Batch already running detection
- Portfolio ownership validation (optional)
- Background task execution with tracking
- Graceful error handling
"""
from uuid import UUID, uuid4
from typing import Optional, Dict, Any, List
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, BackgroundTasks

from app.core.logging import get_logger
from app.core.trading_calendar import get_most_recent_trading_day
from app.models.users import Portfolio
from app.batch.batch_orchestrator import batch_orchestrator
from app.batch.batch_run_tracker import (
    batch_run_tracker,
    CurrentBatchRun,
    BatchJobType,
)
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class BatchTriggerService:
    """Service for triggering batch processing"""

    @staticmethod
    async def check_batch_running(
        job_type: Optional[BatchJobType] = None
    ) -> bool:
        """
        Check if a batch is currently running.

        V2 Enhancement: Can check specific job type or any job.

        Args:
            job_type: Optional specific job type to check.
                     If None, checks V1 legacy batch (backward compatible).

        Returns:
            True if batch is running, False otherwise
        """
        if job_type is not None:
            # V2 mode: Check specific job type
            return batch_run_tracker.is_job_running(job_type)

        # V1 mode: Check legacy current run
        current_run = batch_run_tracker.get_current()
        return current_run is not None

    @staticmethod
    async def check_any_batch_running(
        job_types: Optional[List[BatchJobType]] = None
    ) -> bool:
        """
        Check if any batch job is currently running (V2 multi-job aware).

        Args:
            job_types: Optional list of job types to check.
                      If None, checks all V2 job types AND V1 legacy batch.

        Returns:
            True if any specified batch is running, False otherwise
        """
        # Check V2 jobs
        if batch_run_tracker.is_any_job_running(job_types):
            return True

        # Also check V1 legacy batch (for backward compatibility)
        if job_types is None or BatchJobType.LEGACY_BATCH in job_types:
            current_run = batch_run_tracker.get_current()
            if current_run is not None:
                return True

        return False

    @staticmethod
    async def verify_portfolio_ownership(
        portfolio_id: UUID,
        user_id: UUID,
        db: AsyncSession
    ) -> Portfolio:
        """
        Verify that user owns the portfolio.

        Args:
            portfolio_id: Portfolio UUID
            user_id: User UUID
            db: Database session

        Returns:
            Portfolio object if ownership verified

        Raises:
            HTTPException: 404 if portfolio not found, 403 if not owned
        """
        result = await db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            logger.warning(f"Portfolio {portfolio_id} not found")
            raise HTTPException(status_code=404, detail="Portfolio not found")

        if portfolio.user_id != user_id:
            logger.warning(
                f"User {user_id} attempted to access portfolio {portfolio_id} "
                f"owned by {portfolio.user_id}"
            )
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this portfolio"
            )

        return portfolio

    @staticmethod
    async def trigger_batch(
        background_tasks: BackgroundTasks,
        portfolio_id: Optional[str] = None,
        force: bool = False,
        user_id: Optional[UUID] = None,
        user_email: Optional[str] = None,
        db: Optional[AsyncSession] = None,
        force_onboarding: bool = False
    ) -> Dict[str, Any]:
        """
        Trigger batch processing.

        Shared logic for both admin and user-facing endpoints.

        Args:
            background_tasks: FastAPI background tasks
            portfolio_id: Portfolio ID to process (None = all portfolios)
            force: Force run even if batch already running
            user_id: User ID for ownership validation (optional)
            user_email: User email for audit logging
            db: Database session (required if user_id provided)
            force_onboarding: If True, run all phases even on weekends for onboarding

        Returns:
            Dictionary with batch run details:
            {
                "status": "started",
                "batch_run_id": str,
                "portfolio_id": str,
                "triggered_by": str,
                "timestamp": datetime,
                "poll_url": str
            }

        Raises:
            HTTPException: 409 if batch already running (unless force=True)
            HTTPException: 403 if user doesn't own portfolio
            HTTPException: 404 if portfolio not found
        """
        # 1. Validate portfolio ownership if user_id provided
        if user_id and portfolio_id and db:
            portfolio_uuid = UUID(portfolio_id)
            await BatchTriggerService.verify_portfolio_ownership(
                portfolio_uuid,
                user_id,
                db
            )
            logger.info(f"Portfolio ownership verified: {portfolio_id} for user {user_id}")

        # 2. Check if batch already running
        if not force and await BatchTriggerService.check_batch_running():
            logger.warning("Batch already running, rejecting new request")
            raise HTTPException(
                status_code=409,
                detail="Batch processing already running. Please wait for current run to complete."
            )

        # 3. Create new batch run
        batch_run_id = str(uuid4())
        run = CurrentBatchRun(
            batch_run_id=batch_run_id,
            started_at=utc_now(),
            triggered_by=user_email or "system"
        )

        batch_run_tracker.start(run)

        # Get most recent trading day for calculations (handles weekends/holidays)
        calculation_date = get_most_recent_trading_day()

        logger.info(
            f"Batch run {batch_run_id} started by {user_email or 'system'} "
            f"for portfolio {portfolio_id or 'all'} "
            f"(calculation_date: {calculation_date}, today: {date.today()})"
        )

        # 4. Execute in background
        # Pass calculation_date and portfolio_ids list to orchestrator
        background_tasks.add_task(
            batch_orchestrator.run_daily_batch_sequence,
            calculation_date,  # Use most recent trading day, not today
            [portfolio_id] if portfolio_id else None,  # portfolio_ids as list or None for all
            db,  # Pass through existing db session if available
            None,  # run_sector_analysis (use default)
            None,  # price_cache (use default)
            force_onboarding  # Pass through force_onboarding flag
        )

        # 5. Determine poll URL (admin vs user endpoint)
        if user_id:
            # User-facing endpoint
            poll_url = f"/api/v1/portfolio/{portfolio_id}/batch-status/{batch_run_id}"
        else:
            # Admin endpoint
            poll_url = "/api/v1/admin/batch/run/current"

        return {
            "status": "started",
            "batch_run_id": batch_run_id,
            "portfolio_id": portfolio_id or "all",
            "triggered_by": user_email or "system",
            "timestamp": utc_now(),
            "poll_url": poll_url
        }


# Convenience instance
batch_trigger_service = BatchTriggerService()
