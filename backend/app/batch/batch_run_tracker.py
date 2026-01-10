"""
Minimal in-memory tracker for batch processing runs.
Tracks only the CURRENT batch run for real-time progress monitoring.

Phase 7.1 Enhancement (2026-01-09):
- Added activity_log for real-time status updates during onboarding
- Added portfolio_id tracking for per-portfolio status queries
- Added phase progress tracking with phase names and progress counters
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.datetime_utils import utc_now


# Maximum activity log entries to keep for UI (prevents memory growth)
MAX_ACTIVITY_LOG_ENTRIES = 50

# Maximum full log entries to keep for download (allows complete history)
MAX_FULL_LOG_ENTRIES = 5000

# How long to retain completed run status (seconds)
COMPLETED_RUN_TTL_SECONDS = 60


@dataclass
class ActivityLogEntry:
    """Single activity log entry for real-time status updates"""
    timestamp: datetime
    message: str
    level: str = "info"  # "info", "warning", "error"


@dataclass
class PhaseProgress:
    """Progress tracking for a single batch phase"""
    phase_id: str           # "phase_1", "phase_1.5", etc.
    phase_name: str         # "Market Data Collection", etc.
    status: str = "pending"  # "pending", "running", "completed", "failed"
    current: int = 0
    total: int = 0
    unit: str = "items"     # "symbols", "dates", "positions"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


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

    # Phase 7.1: Portfolio-specific tracking for onboarding status
    portfolio_id: Optional[str] = None

    # Phase 7.1: Activity log for real-time updates (condensed, last 50)
    activity_log: List[ActivityLogEntry] = field(default_factory=list)

    # Phase 7.2: Full activity log for download (up to 5000 entries)
    full_activity_log: List[ActivityLogEntry] = field(default_factory=list)

    # Phase 7.1: Phase progress tracking
    phases: Dict[str, PhaseProgress] = field(default_factory=dict)
    current_phase: Optional[str] = None


@dataclass
class CompletedRunStatus:
    """Terminal status for a completed batch run (retained for TTL)"""
    status_data: Dict[str, Any]
    completed_at: datetime
    success: bool


class BatchRunTracker:
    """Simple singleton - tracks CURRENT run and recently completed runs"""

    def __init__(self):
        self._current: Optional[CurrentBatchRun] = None
        # Phase 7.1 Fix: Retain completed run status for 60 seconds
        # so frontend can see "completed"/"failed" instead of "not_found"
        self._completed_runs: Dict[str, CompletedRunStatus] = {}

    def start(self, run: CurrentBatchRun):
        """Register new batch run as current"""
        # CODE REVIEW FIX (2026-01-09): Clear any stale completed status for this portfolio
        # If operator retries within 60s TTL, we need to show "running" not the old status
        if run.portfolio_id and run.portfolio_id in self._completed_runs:
            del self._completed_runs[run.portfolio_id]

        self._current = run

    def get_current(self) -> Optional[CurrentBatchRun]:
        """Get currently running batch"""
        return self._current

    def complete(self, success: bool = True):
        """
        Mark batch run as complete, retain terminal status, then clear current state.

        Args:
            success: Whether the batch completed successfully
        """
        if self._current and self._current.portfolio_id:
            # Build final status before clearing
            final_status = self._build_status_dict(self._current.portfolio_id)
            if final_status:
                final_status["status"] = "completed" if success else "failed"
                final_status["overall_progress"]["percent_complete"] = 100 if success else final_status["overall_progress"].get("percent_complete", 0)

                # Store in completed runs with TTL
                self._completed_runs[self._current.portfolio_id] = CompletedRunStatus(
                    status_data=final_status,
                    completed_at=utc_now(),
                    success=success
                )

        self._current = None
        self._cleanup_old_completed()

    def _cleanup_old_completed(self) -> None:
        """Remove completed runs older than TTL"""
        now = utc_now()
        expired = [
            pid for pid, status in self._completed_runs.items()
            if (now - status.completed_at).total_seconds() > COMPLETED_RUN_TTL_SECONDS
        ]
        for pid in expired:
            del self._completed_runs[pid]

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

    # ==========================================================================
    # Phase 7.1: Activity Log Methods
    # ==========================================================================

    def add_activity(
        self,
        message: str,
        level: str = "info"
    ) -> None:
        """
        Add an activity log entry for real-time status updates.

        Args:
            message: User-friendly message to display
            level: "info", "warning", or "error"
        """
        if not self._current:
            return

        entry = ActivityLogEntry(
            timestamp=utc_now(),
            message=message,
            level=level
        )

        # Add to condensed log (for UI polling)
        self._current.activity_log.append(entry)
        if len(self._current.activity_log) > MAX_ACTIVITY_LOG_ENTRIES:
            self._current.activity_log = self._current.activity_log[-MAX_ACTIVITY_LOG_ENTRIES:]

        # Add to full log (for download)
        self._current.full_activity_log.append(entry)
        if len(self._current.full_activity_log) > MAX_FULL_LOG_ENTRIES:
            self._current.full_activity_log = self._current.full_activity_log[-MAX_FULL_LOG_ENTRIES:]

    def get_activity_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get activity log entries as dictionaries for API response.

        Args:
            limit: Maximum entries to return (most recent)

        Returns:
            List of activity log entries as dicts
        """
        if not self._current:
            return []

        entries = self._current.activity_log[-limit:]
        return [
            {
                "timestamp": entry.timestamp.isoformat(),
                "message": entry.message,
                "level": entry.level
            }
            for entry in entries
        ]

    def get_full_activity_log(self) -> List[Dict[str, Any]]:
        """
        Get complete activity log for download (up to 5000 entries).

        Returns:
            List of all activity log entries as dicts
        """
        if not self._current:
            return []

        return [
            {
                "timestamp": entry.timestamp.isoformat(),
                "message": entry.message,
                "level": entry.level
            }
            for entry in self._current.full_activity_log
        ]

    # ==========================================================================
    # Phase 7.1: Phase Progress Methods
    # ==========================================================================

    def set_portfolio_id(self, portfolio_id: str) -> None:
        """Set the portfolio ID for this batch run (for onboarding status queries)"""
        if self._current:
            self._current.portfolio_id = portfolio_id

    def get_portfolio_id(self) -> Optional[str]:
        """Get the portfolio ID for current batch run"""
        if self._current:
            return self._current.portfolio_id
        return None

    def start_phase(
        self,
        phase_id: str,
        phase_name: str,
        total: int = 0,
        unit: str = "items"
    ) -> None:
        """
        Mark a phase as started and set up progress tracking.

        Args:
            phase_id: Internal phase ID (e.g., "phase_1", "phase_1.5")
            phase_name: User-friendly name (e.g., "Market Data Collection")
            total: Total items to process (for progress bar)
            unit: Unit for progress (e.g., "symbols", "dates")
        """
        if not self._current:
            return

        self._current.phases[phase_id] = PhaseProgress(
            phase_id=phase_id,
            phase_name=phase_name,
            status="running",
            current=0,
            total=total,
            unit=unit,
            started_at=utc_now()
        )
        self._current.current_phase = phase_id

        # Add activity log entry
        self.add_activity(f"Starting {phase_name}...")

    def update_phase_progress(
        self,
        phase_id: str,
        current: int,
        total: Optional[int] = None
    ) -> None:
        """
        Update progress for a running phase.

        Args:
            phase_id: Phase to update
            current: Current progress count
            total: Optionally update total count
        """
        if not self._current:
            return

        if phase_id in self._current.phases:
            phase = self._current.phases[phase_id]
            phase.current = current
            if total is not None:
                phase.total = total

    def complete_phase(
        self,
        phase_id: str,
        success: bool = True,
        summary: Optional[str] = None
    ) -> None:
        """
        Mark a phase as completed.

        Args:
            phase_id: Phase to complete
            success: Whether phase succeeded
            summary: Optional summary message for activity log
        """
        if not self._current:
            return

        if phase_id in self._current.phases:
            phase = self._current.phases[phase_id]
            phase.status = "completed" if success else "failed"
            phase.completed_at = utc_now()
            if phase.started_at:
                phase.duration_seconds = int(
                    (phase.completed_at - phase.started_at).total_seconds()
                )

            # Add activity log entry with summary
            if summary:
                level = "info" if success else "warning"
                self.add_activity(f"{phase.phase_name}: {summary}", level)

    def get_phase_progress(self) -> Dict[str, Any]:
        """
        Get current phase progress for API response.

        Returns:
            Dict with overall progress and per-phase details
        """
        if not self._current:
            return {}

        phases_list = []
        completed_count = 0
        total_phases = len(self._current.phases)

        for phase_id, phase in self._current.phases.items():
            if phase.status == "completed":
                completed_count += 1
            phases_list.append({
                "phase_id": phase.phase_id,
                "phase_name": phase.phase_name,
                "status": phase.status,
                "current": phase.current,
                "total": phase.total,
                "unit": phase.unit,
                "duration_seconds": phase.duration_seconds
            })

        # Calculate overall percent (rough estimate based on phases)
        percent_complete = 0
        if total_phases > 0:
            # Give weight to both completed phases and current phase progress
            base_percent = (completed_count / total_phases) * 100

            # Add progress from current running phase
            current_phase = self._current.phases.get(self._current.current_phase)
            if current_phase and current_phase.status == "running" and current_phase.total > 0:
                phase_weight = 100 / total_phases
                phase_progress = (current_phase.current / current_phase.total) * phase_weight
                base_percent += phase_progress

            percent_complete = min(int(base_percent), 99)  # Cap at 99 until truly done

        return {
            "current_phase": self._current.current_phase,
            "current_phase_name": (
                self._current.phases[self._current.current_phase].phase_name
                if self._current.current_phase and self._current.current_phase in self._current.phases
                else None
            ),
            "phases_completed": completed_count,
            "phases_total": total_phases,
            "percent_complete": percent_complete,
            "phases": phases_list
        }

    def _build_status_dict(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        """
        Build status dictionary from current run state.

        Internal helper used by both get_onboarding_status() and complete().
        """
        if not self._current:
            return None

        if self._current.portfolio_id != portfolio_id:
            return None

        elapsed_seconds = 0
        if self._current.started_at:
            elapsed_seconds = int((utc_now() - self._current.started_at).total_seconds())

        phase_progress = self.get_phase_progress()
        current_phase_detail = None

        # Get current phase progress detail
        if self._current.current_phase and self._current.current_phase in self._current.phases:
            phase = self._current.phases[self._current.current_phase]
            current_phase_detail = {
                "current": phase.current,
                "total": phase.total,
                "unit": phase.unit
            }

        return {
            "portfolio_id": portfolio_id,
            "status": "running",
            "started_at": self._current.started_at.isoformat(),
            "elapsed_seconds": elapsed_seconds,
            "overall_progress": {
                "current_phase": phase_progress.get("current_phase"),
                "current_phase_name": phase_progress.get("current_phase_name"),
                "phases_completed": phase_progress.get("phases_completed", 0),
                "phases_total": phase_progress.get("phases_total", 0),
                "percent_complete": phase_progress.get("percent_complete", 0)
            },
            "current_phase_progress": current_phase_detail,
            "activity_log": self.get_activity_log(limit=50)
        }

    def get_onboarding_status(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full onboarding status for a specific portfolio.

        Checks recently completed runs first (within 60s TTL), then current run.

        Args:
            portfolio_id: Portfolio UUID string to check

        Returns:
            Full status dict if this portfolio is/was being processed, None otherwise
        """
        # Phase 7.1 Fix: Check completed runs first (within TTL)
        self._cleanup_old_completed()
        if portfolio_id in self._completed_runs:
            completed = self._completed_runs[portfolio_id]
            # Return the saved terminal status
            return completed.status_data

        # Check if currently running
        return self._build_status_dict(portfolio_id)


# Global singleton instance
batch_run_tracker = BatchRunTracker()
