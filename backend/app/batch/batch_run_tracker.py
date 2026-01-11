"""
Minimal in-memory tracker for batch processing runs.
Tracks only the CURRENT batch run for real-time progress monitoring.

Phase 7.1 Enhancement (2026-01-09):
- Added activity_log for real-time status updates during onboarding
- Added portfolio_id tracking for per-portfolio status queries
- Added phase progress tracking with phase names and progress counters

Phase 7.3 Enhancement (2026-01-11):
- Added persistent log storage to database (BatchRunHistory.activity_log)
- Logs are persisted at each phase completion for crash recovery
- TTL increased to 2 hours for longer user sessions
- Added database fallback for get_full_activity_log

Phase 7.4 Enhancement (2026-01-11):
- Added BatchActivityLogHandler to capture existing INFO/WARNING logs
- Logs from calculation engines are automatically forwarded to activity log
- Provides Railway-level debugging detail in downloadable logs
"""
import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.core.datetime_utils import utc_now

logger = logging.getLogger(__name__)


# Maximum activity log entries to keep for UI (prevents memory growth)
MAX_ACTIVITY_LOG_ENTRIES = 50

# Maximum full log entries to keep for download (allows complete history)
MAX_FULL_LOG_ENTRIES = 5000

# How long to retain completed run status (seconds)
# Phase 7.3: Increased from 300s (5 min) to 7200s (2 hours) for longer user sessions
COMPLETED_RUN_TTL_SECONDS = 7200

# Logger prefixes to capture for activity log (batch and calculation engines)
CAPTURED_LOGGER_PREFIXES = (
    'app.batch',
    'app.calculations',
    'app.services.market_data',
    'app.services.company_profile',
)

# Fixed phase ordering for consistent UI display
# Phase 7.4 Fix: Ensures phases appear in execution order regardless of when they're created
PHASE_ORDER = [
    'phase_1',      # Market Data Collection
    'phase_1_5',    # Factor Analysis
    'phase_1_75',   # Symbol Metrics
    'phase_0',      # Company Profile Sync (only on current date)
    'phase_2',      # Fundamental Data Collection (only on current date)
    'phase_3',      # P&L Calculation & Snapshots
    'phase_4',      # Position Market Value Updates
    'phase_5',      # Sector Tag Restoration (only on current date)
    'phase_6',      # Risk Analytics
]


class BatchActivityLogHandler(logging.Handler):
    """
    Custom logging handler that forwards log messages to batch_run_tracker.

    Phase 7.4: Captures existing INFO/WARNING/ERROR logs from calculation engines
    and adds them to the activity log for debugging visibility.

    Only captures logs from specific prefixes (batch, calculations, market data)
    to avoid noise from unrelated modules.

    Usage:
        handler = BatchActivityLogHandler(batch_run_tracker)
        handler.attach()  # Start capturing
        # ... run batch processing ...
        handler.detach()  # Stop capturing
    """

    def __init__(self, tracker: 'BatchRunTracker'):
        super().__init__()
        self.tracker = tracker
        self.setLevel(logging.INFO)
        # Format: just the message, no timestamp (tracker adds its own)
        self.setFormatter(logging.Formatter('%(name)s: %(message)s'))
        self._attached = False

    def emit(self, record: logging.LogRecord) -> None:
        """Forward log record to activity log if batch is running."""
        # Only capture if batch is running
        if not self.tracker._current:
            return

        # Only capture from specific logger prefixes
        if not record.name.startswith(CAPTURED_LOGGER_PREFIXES):
            return

        try:
            msg = self.format(record)
            # Map log level
            if record.levelno >= logging.ERROR:
                level = "error"
            elif record.levelno >= logging.WARNING:
                level = "warning"
            else:
                level = "info"

            self.tracker.add_activity(msg, level=level)
        except Exception:
            # Don't let logging errors break the batch
            pass

    def attach(self) -> None:
        """Attach handler to root logger to start capturing.

        Phase 7.4 Fix (Round 2): Removes any existing BatchActivityLogHandler
        instances before attaching to prevent duplicate logging from leaked
        handlers (e.g., if a previous batch failed mid-run).
        """
        if self._attached:
            return

        root_logger = logging.getLogger()

        # Remove any existing BatchActivityLogHandler instances to prevent duplicates
        # This handles the case where a previous batch failed and leaked its handler
        existing_handlers = [
            h for h in root_logger.handlers
            if isinstance(h, BatchActivityLogHandler)
        ]
        for h in existing_handlers:
            root_logger.removeHandler(h)
            h._attached = False

        root_logger.addHandler(self)
        self._attached = True

    def detach(self) -> None:
        """Detach handler from root logger to stop capturing."""
        if self._attached:
            logging.getLogger().removeHandler(self)
            self._attached = False

    def __enter__(self) -> 'BatchActivityLogHandler':
        """Context manager entry - attach handler."""
        self.attach()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - always detach handler, even on exception."""
        self.detach()
        # Don't suppress exceptions (return None/False)


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
    # Phase 7.3 Fix: Preserve full activity log for download after completion
    full_activity_log: List[Dict[str, Any]] = field(default_factory=list)
    # Security Fix: Preserve phase details for completed runs to avoid cross-portfolio leaks
    phases: List[Dict[str, Any]] = field(default_factory=list)


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
            portfolio_id = self._current.portfolio_id
            try:
                # Build final status before clearing
                final_status = self._build_status_dict(portfolio_id)
                if final_status:
                    final_status["status"] = "completed" if success else "failed"
                    final_status["overall_progress"]["percent_complete"] = 100 if success else final_status["overall_progress"].get("percent_complete", 0)

                    # Phase 7.3 Fix: Preserve full activity log for download after completion
                    full_log = [
                        {
                            "timestamp": entry.timestamp.isoformat(),
                            "message": entry.message,
                            "level": entry.level
                        }
                        for entry in self._current.full_activity_log
                    ]

                    # Security Fix: Preserve phase details before clearing _current
                    phase_progress = self.get_phase_progress()
                    phases_list = phase_progress.get("phases", [])

                    # Store in completed runs with TTL
                    self._completed_runs[portfolio_id] = CompletedRunStatus(
                        status_data=final_status,
                        completed_at=utc_now(),
                        success=success,
                        full_activity_log=full_log,
                        phases=phases_list
                    )
                else:
                    logger.warning(
                        f"Failed to build status dict for portfolio {portfolio_id} - "
                        "completed run status will not be retained"
                    )
            except Exception as e:
                logger.error(
                    f"Error preserving completed run status for portfolio {portfolio_id}: {e}",
                    exc_info=True
                )

        # Phase 7.3.1 Fix: Persist logs BEFORE clearing _current
        # Capture data now since _current will be None after this
        if self._current:
            batch_run_id = self._current.batch_run_id
            portfolio_id = self._current.portfolio_id
            logs_data = [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "message": entry.message,
                    "level": entry.level
                }
                for entry in self._current.full_activity_log
            ]
            triggered_by = self._current.triggered_by
            started_at = self._current.started_at
            total_jobs = self._current.total_jobs
            completed_jobs = self._current.completed_jobs
            failed_jobs = self._current.failed_jobs

            # Schedule persistence with captured data (won't depend on _current)
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._persist_logs_with_data(
                    batch_run_id, portfolio_id, logs_data,
                    triggered_by, started_at, total_jobs, completed_jobs, failed_jobs
                ))
            except RuntimeError:
                asyncio.run(self._persist_logs_with_data(
                    batch_run_id, portfolio_id, logs_data,
                    triggered_by, started_at, total_jobs, completed_jobs, failed_jobs
                ))

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

    def get_full_activity_log(self, portfolio_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get complete activity log for download (up to 5000 entries).

        Security Fix: Only returns logs for the specified portfolio_id to prevent
        cross-portfolio data leaks when multiple batches are running.

        Note: This is the synchronous version for backward compatibility.
        For database fallback, use get_full_activity_log_async().

        Args:
            portfolio_id: Portfolio ID to get logs for (required for security)

        Returns:
            List of all activity log entries as dicts
        """
        # Security: Only return current run logs if portfolio_id matches
        if self._current and portfolio_id and self._current.portfolio_id == portfolio_id:
            return [
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "message": entry.message,
                    "level": entry.level
                }
                for entry in self._current.full_activity_log
            ]

        # Check completed runs if portfolio_id provided
        if portfolio_id:
            self._cleanup_old_completed()
            if portfolio_id in self._completed_runs:
                return self._completed_runs[portfolio_id].full_activity_log

        return []

    async def get_full_activity_log_async(self, portfolio_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get complete activity log with database fallback (up to 5000 entries).

        Phase 7.3 Enhancement: Falls back to database if logs not in memory.
        This allows log retrieval even after TTL expiry or service restart.

        Security Fix: Only returns logs for the specified portfolio_id to prevent
        cross-portfolio data leaks when multiple batches are running.

        Args:
            portfolio_id: Portfolio ID to get logs for (required for security)

        Returns:
            List of all activity log entries as dicts
        """
        # First try in-memory (most recent, most accurate)
        in_memory_logs = self.get_full_activity_log(portfolio_id)
        if in_memory_logs:
            return in_memory_logs

        # Fall back to database if not in memory
        if portfolio_id:
            try:
                from app.database import AsyncSessionLocal
                from app.models.admin import BatchRunHistory
                from sqlalchemy import select

                async with AsyncSessionLocal() as db:
                    # Find most recent batch run for this portfolio
                    stmt = (
                        select(BatchRunHistory.activity_log)
                        .where(BatchRunHistory.portfolio_id == UUID(portfolio_id))
                        .order_by(BatchRunHistory.started_at.desc())
                        .limit(1)
                    )
                    result = await db.execute(stmt)
                    row = result.scalar_one_or_none()

                    if row and isinstance(row, list):
                        logger.debug(
                            f"Retrieved {len(row)} log entries from database for portfolio {portfolio_id}"
                        )
                        return row

            except Exception as e:
                logger.warning(f"Failed to retrieve logs from database: {e}")

        return []

    async def get_batch_status_from_db_async(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        """
        Get batch run status from database for a portfolio.

        Phase 7.3.1 Enhancement: Returns actual batch status from BatchRunHistory
        instead of assuming completed. This provides accurate status for failed
        or partial runs.

        Args:
            portfolio_id: Portfolio ID to get status for

        Returns:
            Dict with status info or None if not found:
            - status: "running", "completed", "failed", "partial"
            - started_at: ISO timestamp
            - completed_at: ISO timestamp or None
            - total_jobs, completed_jobs, failed_jobs
            - phase_durations: dict of phase timings
        """
        try:
            from app.database import AsyncSessionLocal
            from app.models.admin import BatchRunHistory
            from sqlalchemy import select

            async with AsyncSessionLocal() as db:
                # Find most recent batch run for this portfolio
                stmt = (
                    select(BatchRunHistory)
                    .where(BatchRunHistory.portfolio_id == UUID(portfolio_id))
                    .order_by(BatchRunHistory.started_at.desc())
                    .limit(1)
                )
                result = await db.execute(stmt)
                row = result.scalar_one_or_none()

                if row:
                    return {
                        "batch_run_id": row.batch_run_id,
                        "status": row.status,
                        "started_at": row.started_at.isoformat() if row.started_at else None,
                        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                        "total_jobs": row.total_jobs,
                        "completed_jobs": row.completed_jobs,
                        "failed_jobs": row.failed_jobs,
                        "phase_durations": row.phase_durations or {},
                        "error_summary": row.error_summary,
                    }

        except Exception as e:
            logger.warning(f"Failed to retrieve batch status from database: {e}")

        return None

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

    async def persist_logs_to_db(self) -> None:
        """
        Persist current activity logs to database for crash recovery.

        Phase 7.3 Enhancement: Called at each phase completion to ensure logs
        are saved even if a later phase fails or the service crashes.

        Phase 7.3.1 Fix: Uses conditional UPDATE to prevent race conditions.
        Only updates if new log count >= existing count, preventing older
        fire-and-forget tasks from overwriting newer logs.

        Phase 7.3.1 Fix 2: If no record exists (UPDATE rowcount=0), creates
        a minimal BatchRunHistory record to ensure logs are not lost when
        batch fails before batch_history_service creates the record.

        Updates BatchRunHistory.activity_log with current full_activity_log.
        """
        if not self._current:
            return

        batch_run_id = self._current.batch_run_id
        portfolio_id = self._current.portfolio_id

        # Convert logs to serializable format
        logs_data = [
            {
                "timestamp": entry.timestamp.isoformat(),
                "message": entry.message,
                "level": entry.level
            }
            for entry in self._current.full_activity_log
        ]
        new_log_count = len(logs_data)

        try:
            from app.database import AsyncSessionLocal
            from app.models.admin import BatchRunHistory
            from sqlalchemy import update, or_, func, text, select
            from sqlalchemy.dialects.postgresql import JSONB
            from datetime import datetime

            async with AsyncSessionLocal() as db:
                # Conditional UPDATE: only write if new log count >= existing
                # This prevents older fire-and-forget tasks from overwriting newer logs
                # Uses PostgreSQL jsonb_array_length() to check existing log count
                stmt = (
                    update(BatchRunHistory)
                    .where(BatchRunHistory.batch_run_id == batch_run_id)
                    .where(
                        or_(
                            # Condition 1: No existing logs (NULL or empty)
                            BatchRunHistory.activity_log.is_(None),
                            # Condition 2: New logs have more or equal entries
                            func.jsonb_array_length(
                                func.coalesce(
                                    BatchRunHistory.activity_log,
                                    text("'[]'::jsonb")
                                )
                            ) <= new_log_count
                        )
                    )
                    .values(
                        activity_log=logs_data,
                        portfolio_id=UUID(portfolio_id) if portfolio_id else None
                    )
                )
                result = await db.execute(stmt)

                if result.rowcount == 0:
                    # Check if record exists (might have newer logs) or doesn't exist at all
                    check_stmt = select(BatchRunHistory.id).where(
                        BatchRunHistory.batch_run_id == batch_run_id
                    )
                    check_result = await db.execute(check_stmt)
                    exists = check_result.scalar_one_or_none()

                    if exists:
                        # Record exists with newer logs - skip
                        logger.debug(
                            f"Log persistence skipped for {batch_run_id} - "
                            f"newer logs already saved"
                        )
                    else:
                        # Record doesn't exist yet - create minimal record with logs
                        # This ensures logs are saved even if batch fails early
                        logger.info(
                            f"Creating BatchRunHistory record for {batch_run_id} - "
                            f"record not yet created by batch_history_service"
                        )
                        new_record = BatchRunHistory(
                            batch_run_id=batch_run_id,
                            triggered_by=self._current.triggered_by or "unknown",
                            started_at=self._current.started_at or datetime.utcnow(),
                            status="running",
                            total_jobs=self._current.total_jobs,
                            completed_jobs=self._current.completed_jobs,
                            failed_jobs=self._current.failed_jobs,
                            phase_durations={},
                            activity_log=logs_data,
                            portfolio_id=UUID(portfolio_id) if portfolio_id else None,
                        )
                        db.add(new_record)
                        logger.debug(
                            f"Created BatchRunHistory with {new_log_count} log entries for {batch_run_id}"
                        )
                else:
                    logger.debug(
                        f"Persisted {new_log_count} log entries for batch {batch_run_id}"
                    )

                await db.commit()

        except Exception as e:
            # Don't fail the batch if log persistence fails
            logger.warning(f"Failed to persist logs to database: {e}")

    async def _persist_logs_with_data(
        self,
        batch_run_id: str,
        portfolio_id: Optional[str],
        logs_data: List[Dict[str, Any]],
        triggered_by: Optional[str],
        started_at: Optional[datetime],
        total_jobs: int,
        completed_jobs: int,
        failed_jobs: int
    ) -> None:
        """
        Persist logs with pre-captured data (doesn't rely on self._current).

        Phase 7.3.1 Fix: This method is used in complete() to avoid race conditions
        where _current is cleared before fire-and-forget persist tasks run.
        """
        new_log_count = len(logs_data)

        try:
            from app.database import AsyncSessionLocal
            from app.models.admin import BatchRunHistory
            from sqlalchemy import update, or_, func, text, select
            from datetime import datetime as dt

            async with AsyncSessionLocal() as db:
                # Conditional UPDATE: only write if new log count >= existing
                stmt = (
                    update(BatchRunHistory)
                    .where(BatchRunHistory.batch_run_id == batch_run_id)
                    .where(
                        or_(
                            BatchRunHistory.activity_log.is_(None),
                            func.jsonb_array_length(
                                func.coalesce(
                                    BatchRunHistory.activity_log,
                                    text("'[]'::jsonb")
                                )
                            ) <= new_log_count
                        )
                    )
                    .values(
                        activity_log=logs_data,
                        portfolio_id=UUID(portfolio_id) if portfolio_id else None
                    )
                )
                result = await db.execute(stmt)

                if result.rowcount == 0:
                    # Check if record exists or doesn't exist at all
                    check_stmt = select(BatchRunHistory.id).where(
                        BatchRunHistory.batch_run_id == batch_run_id
                    )
                    check_result = await db.execute(check_stmt)
                    exists = check_result.scalar_one_or_none()

                    if exists:
                        logger.debug(
                            f"Log persistence skipped for {batch_run_id} - "
                            f"newer logs already saved"
                        )
                    else:
                        # Create minimal record with logs
                        logger.info(
                            f"Creating BatchRunHistory record for {batch_run_id} - "
                            f"record not yet created by batch_history_service"
                        )
                        new_record = BatchRunHistory(
                            batch_run_id=batch_run_id,
                            triggered_by=triggered_by or "unknown",
                            started_at=started_at or dt.utcnow(),
                            status="running",
                            total_jobs=total_jobs,
                            completed_jobs=completed_jobs,
                            failed_jobs=failed_jobs,
                            phase_durations={},
                            activity_log=logs_data,
                            portfolio_id=UUID(portfolio_id) if portfolio_id else None,
                        )
                        db.add(new_record)
                        logger.debug(
                            f"Created BatchRunHistory with {new_log_count} log entries for {batch_run_id}"
                        )
                else:
                    logger.debug(
                        f"Persisted {new_log_count} log entries for batch {batch_run_id}"
                    )

                await db.commit()

        except Exception as e:
            logger.warning(f"Failed to persist logs to database: {e}")

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

            # Phase 7.3: Persist logs to database after each phase completion
            # This ensures logs are saved even if a later phase fails
            import asyncio
            try:
                # Check if we're in an async context
                loop = asyncio.get_running_loop()
                # We're in async context, create a task
                asyncio.create_task(self.persist_logs_to_db())
            except RuntimeError:
                # No running loop, run synchronously
                asyncio.run(self.persist_logs_to_db())

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

        # Phase 7.4 Fix: Sort phases by fixed execution order for consistent UI display
        phase_order_map = {pid: idx for idx, pid in enumerate(PHASE_ORDER)}
        phases_list.sort(key=lambda p: phase_order_map.get(p["phase_id"], 999))

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

    def get_phase_progress_for_portfolio(self, portfolio_id: str) -> Dict[str, Any]:
        """
        Get phase progress for a specific portfolio only.

        Security Fix: Prevents cross-portfolio data leaks by only returning phase
        data for the specified portfolio, checking both current and completed runs.

        Args:
            portfolio_id: Portfolio ID to get phases for

        Returns:
            Dict with phases list, or empty dict if not found
        """
        # Only return current run phases if portfolio_id matches
        if self._current and self._current.portfolio_id == portfolio_id:
            return self.get_phase_progress()

        # Check completed runs
        self._cleanup_old_completed()
        if portfolio_id in self._completed_runs:
            return {"phases": self._completed_runs[portfolio_id].phases}

        return {}

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
            # Return a deep copy to prevent mutation of cached data
            # (e.g., download endpoint modifies response with phases)
            return copy.deepcopy(completed.status_data)

        # Check if currently running
        return self._build_status_dict(portfolio_id)


# Global singleton instance
batch_run_tracker = BatchRunTracker()
