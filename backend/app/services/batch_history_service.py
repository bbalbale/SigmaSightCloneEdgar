"""
Batch History Recording Service

Records batch processing history for admin dashboard analytics (Phase 5).
Uses fire-and-forget pattern to avoid impacting batch processing performance.

Created: December 22, 2025 (Phase 5 Admin Dashboard)
"""
import asyncio
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from datetime import datetime

from app.database import get_async_session
from app.models.admin import BatchRunHistory
from app.core.logging import get_logger

logger = get_logger(__name__)


class BatchHistoryService:
    """Service for recording batch processing history."""

    @classmethod
    def record_batch_start(
        cls,
        batch_run_id: str,
        triggered_by: str,
        total_jobs: int = 0,
    ) -> UUID:
        """
        Record the start of a batch run.

        Args:
            batch_run_id: Unique identifier for the batch run
            triggered_by: Who/what triggered the run ("cron", "manual", "admin:email")
            total_jobs: Total number of jobs to process

        Returns:
            UUID of the created history record
        """
        record_id = uuid4()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    cls._record_batch_start_async(
                        record_id=record_id,
                        batch_run_id=batch_run_id,
                        triggered_by=triggered_by,
                        total_jobs=total_jobs,
                    )
                )
            else:
                asyncio.run(
                    cls._record_batch_start_async(
                        record_id=record_id,
                        batch_run_id=batch_run_id,
                        triggered_by=triggered_by,
                        total_jobs=total_jobs,
                    )
                )
        except Exception as e:
            logger.warning(f"[BatchHistory] Failed to schedule start recording: {e}")
        return record_id

    @classmethod
    async def _record_batch_start_async(
        cls,
        record_id: UUID,
        batch_run_id: str,
        triggered_by: str,
        total_jobs: int,
    ):
        """Async implementation of batch start recording."""
        try:
            async with get_async_session() as db:
                history = BatchRunHistory(
                    id=record_id,
                    batch_run_id=batch_run_id,
                    triggered_by=triggered_by,
                    started_at=datetime.utcnow(),
                    status="running",
                    total_jobs=total_jobs,
                    completed_jobs=0,
                    failed_jobs=0,
                    phase_durations={},
                )
                db.add(history)
                await db.commit()
                logger.debug(f"[BatchHistory] Recorded batch start: {batch_run_id}")
        except Exception as e:
            logger.warning(f"[BatchHistory] Failed to record batch start: {e}")

    @classmethod
    def record_batch_complete(
        cls,
        batch_run_id: str,
        status: str,
        completed_jobs: int = 0,
        failed_jobs: int = 0,
        total_jobs: Optional[int] = None,
        phase_durations: Optional[Dict[str, float]] = None,
        error_summary: Optional[Dict[str, Any]] = None,
    ):
        """
        Record the completion of a batch run.

        Args:
            batch_run_id: Unique identifier for the batch run
            status: Final status ("completed", "failed", "partial")
            completed_jobs: Number of successfully completed jobs
            failed_jobs: Number of failed jobs
            total_jobs: Total number of jobs (if None, computed from completed + failed)
            phase_durations: Dict of phase names to duration in seconds
            error_summary: Optional error details
        """
        # Compute total_jobs if not provided
        if total_jobs is None:
            total_jobs = completed_jobs + failed_jobs

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    cls._record_batch_complete_async(
                        batch_run_id=batch_run_id,
                        status=status,
                        completed_jobs=completed_jobs,
                        failed_jobs=failed_jobs,
                        total_jobs=total_jobs,
                        phase_durations=phase_durations or {},
                        error_summary=error_summary,
                    )
                )
            else:
                asyncio.run(
                    cls._record_batch_complete_async(
                        batch_run_id=batch_run_id,
                        status=status,
                        completed_jobs=completed_jobs,
                        failed_jobs=failed_jobs,
                        total_jobs=total_jobs,
                        phase_durations=phase_durations or {},
                        error_summary=error_summary,
                    )
                )
        except Exception as e:
            logger.warning(f"[BatchHistory] Failed to schedule completion recording: {e}")

    @classmethod
    async def _record_batch_complete_async(
        cls,
        batch_run_id: str,
        status: str,
        completed_jobs: int,
        failed_jobs: int,
        total_jobs: int,
        phase_durations: Dict[str, float],
        error_summary: Optional[Dict[str, Any]],
    ):
        """Async implementation of batch completion recording."""
        try:
            from sqlalchemy import update

            async with get_async_session() as db:
                stmt = (
                    update(BatchRunHistory)
                    .where(BatchRunHistory.batch_run_id == batch_run_id)
                    .where(BatchRunHistory.status == "running")
                    .values(
                        status=status,
                        completed_at=datetime.utcnow(),
                        total_jobs=total_jobs,
                        completed_jobs=completed_jobs,
                        failed_jobs=failed_jobs,
                        phase_durations=phase_durations,
                        error_summary=error_summary,
                    )
                )
                result = await db.execute(stmt)
                await db.commit()

                if result.rowcount > 0:
                    logger.debug(
                        f"[BatchHistory] Recorded batch completion: {batch_run_id} "
                        f"status={status} total={total_jobs} completed={completed_jobs} failed={failed_jobs}"
                    )
                else:
                    logger.warning(
                        f"[BatchHistory] No running batch found to complete: {batch_run_id}"
                    )
        except Exception as e:
            logger.warning(f"[BatchHistory] Failed to record batch completion: {e}")

    @classmethod
    def update_batch_progress(
        cls,
        batch_run_id: str,
        completed_jobs: int,
        failed_jobs: int,
    ):
        """
        Update progress of a running batch.

        Args:
            batch_run_id: Unique identifier for the batch run
            completed_jobs: Current count of completed jobs
            failed_jobs: Current count of failed jobs
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    cls._update_batch_progress_async(
                        batch_run_id=batch_run_id,
                        completed_jobs=completed_jobs,
                        failed_jobs=failed_jobs,
                    )
                )
        except Exception as e:
            logger.warning(f"[BatchHistory] Failed to schedule progress update: {e}")

    @classmethod
    async def _update_batch_progress_async(
        cls,
        batch_run_id: str,
        completed_jobs: int,
        failed_jobs: int,
    ):
        """Async implementation of progress update."""
        try:
            from sqlalchemy import update

            async with get_async_session() as db:
                stmt = (
                    update(BatchRunHistory)
                    .where(BatchRunHistory.batch_run_id == batch_run_id)
                    .where(BatchRunHistory.status == "running")
                    .values(
                        completed_jobs=completed_jobs,
                        failed_jobs=failed_jobs,
                    )
                )
                await db.execute(stmt)
                await db.commit()
        except Exception as e:
            logger.warning(f"[BatchHistory] Failed to update progress: {e}")


# Convenience functions for direct import
def record_batch_start(
    batch_run_id: str,
    triggered_by: str,
    total_jobs: int = 0,
) -> UUID:
    """
    Record the start of a batch run.

    Example usage:
        record_id = record_batch_start(
            batch_run_id="batch_20251222_143000",
            triggered_by="cron",
            total_jobs=5,
        )
    """
    return BatchHistoryService.record_batch_start(
        batch_run_id=batch_run_id,
        triggered_by=triggered_by,
        total_jobs=total_jobs,
    )


def record_batch_complete(
    batch_run_id: str,
    status: str,
    completed_jobs: int = 0,
    failed_jobs: int = 0,
    total_jobs: Optional[int] = None,
    phase_durations: Optional[Dict[str, float]] = None,
    error_summary: Optional[Dict[str, Any]] = None,
):
    """
    Record the completion of a batch run.

    Args:
        batch_run_id: Unique identifier for the batch run
        status: Final status ("completed", "failed", "partial")
        completed_jobs: Number of successfully completed jobs
        failed_jobs: Number of failed jobs
        total_jobs: Total number of jobs (if None, computed from completed + failed)
        phase_durations: Dict of phase names to duration in seconds
        error_summary: Optional error details

    Example usage:
        record_batch_complete(
            batch_run_id="batch_20251222_143000",
            status="completed",
            completed_jobs=5,
            failed_jobs=0,
            phase_durations={
                "phase_0_company_profiles": 12.5,
                "phase_1_market_data": 45.2,
                "phase_2_pnl": 8.3,
                "phase_3_analytics": 30.1,
            },
        )
    """
    BatchHistoryService.record_batch_complete(
        batch_run_id=batch_run_id,
        status=status,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        total_jobs=total_jobs,
        phase_durations=phase_durations,
        error_summary=error_summary,
    )


def update_batch_progress(
    batch_run_id: str,
    completed_jobs: int,
    failed_jobs: int,
):
    """
    Update progress of a running batch.

    Example usage:
        update_batch_progress(
            batch_run_id="batch_20251222_143000",
            completed_jobs=3,
            failed_jobs=0,
        )
    """
    BatchHistoryService.update_batch_progress(
        batch_run_id=batch_run_id,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
    )
