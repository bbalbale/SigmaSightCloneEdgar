"""
Minimal in-memory tracker for batch processing runs.
Tracks only the CURRENT batch run for real-time progress monitoring.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.core.datetime_utils import utc_now


@dataclass
class CurrentBatchRun:
    """Minimal state for current batch run"""
    batch_run_id: str
    started_at: datetime
    triggered_by: str

    # Counts
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0

    # Current state
    current_job_name: Optional[str] = None
    current_portfolio_name: Optional[str] = None


class BatchRunTracker:
    """Simple singleton - only tracks CURRENT run"""

    def __init__(self):
        self._current: Optional[CurrentBatchRun] = None

    def start(self, run: CurrentBatchRun):
        """Register new batch run as current"""
        self._current = run

    def get_current(self) -> Optional[CurrentBatchRun]:
        """Get currently running batch"""
        return self._current

    def complete(self):
        """Mark batch run as complete and clear state"""
        self._current = None

    def update(
        self,
        total_jobs: Optional[int] = None,
        completed: Optional[int] = None,
        failed: Optional[int] = None,
        job_name: Optional[str] = None,
        portfolio_name: Optional[str] = None
    ):
        """Update progress for current batch run"""
        if not self._current:
            return

        if total_jobs is not None:
            self._current.total_jobs = total_jobs  # Dynamic update
        if completed is not None:
            self._current.completed_jobs = completed
        if failed is not None:
            self._current.failed_jobs = failed
        if job_name:
            self._current.current_job_name = job_name
        if portfolio_name:
            self._current.current_portfolio_name = portfolio_name


# Global singleton instance
batch_run_tracker = BatchRunTracker()
