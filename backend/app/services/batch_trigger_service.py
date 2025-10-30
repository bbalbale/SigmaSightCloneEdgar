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
from typing import Optional, Dict, Any
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, BackgroundTasks

from app.core.logging import get_logger
from app.models.users import Portfolio
from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3 as batch_orchestrator
from app.batch.batch_run_tracker import batch_run_tracker, CurrentBatchRun
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class BatchTriggerService:
    """Service for triggering batch processing"""

    @staticmethod
    async def check_batch_running() -> bool:
        """
        Check if a batch is currently running.

        Returns:
            True if batch is running, False otherwise
        """
        current_run = batch_run_tracker.get_current()
        return current_run is not None

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
        db: Optional[AsyncSession] = None
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

        logger.info(
            f"Batch run {batch_run_id} started by {user_email or 'system'} "
            f"for portfolio {portfolio_id or 'all'}"
        )

        # 4. Execute in background
        # Pass calculation_date and portfolio_ids list to orchestrator
        background_tasks.add_task(
            batch_orchestrator.run_daily_batch_sequence,
            date.today(),  # calculation_date
            [portfolio_id] if portfolio_id else None  # portfolio_ids as list or None for all
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
