"""
Onboarding Status API Endpoint (Phase 7.1 + 7.2)

Provides real-time batch processing status for onboarding portfolios.
This endpoint allows the frontend to poll for progress updates during
the 15-20 minute portfolio setup process.

Key design decisions:
1. NOT admin-only - uses regular user auth (portfolio owner)
2. Returns activity log for real-time progress display
3. Handles "not_found" status when batch is not running for this portfolio
4. Uses existing batch_run_tracker singleton for status

Endpoints:
- GET /api/v1/onboarding/status/{portfolio_id} - Get batch processing status
- GET /api/v1/onboarding/status/{portfolio_id}/logs - Download complete activity log

Created: 2026-01-09 (Phase 7.1)
Updated: 2026-01-10 (Phase 7.2 - Log download endpoint)
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.core.clerk_auth import get_current_user_clerk
from app.models.users import User, Portfolio
from app.batch.batch_run_tracker import batch_run_tracker
from app.core.logging import get_logger
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)

# Create router - this will be added to existing onboarding router
router = APIRouter(tags=["onboarding"])


# ==============================================================================
# Response Schemas
# ==============================================================================

class ActivityLogEntryResponse(BaseModel):
    """Single activity log entry"""
    timestamp: str  # ISO format
    message: str
    level: str  # "info", "warning", "error"


class CurrentPhaseProgressResponse(BaseModel):
    """Progress detail for current phase"""
    current: int
    total: int
    unit: str  # "symbols", "dates", etc.


class OverallProgressResponse(BaseModel):
    """Overall batch progress"""
    current_phase: Optional[str]
    current_phase_name: Optional[str]
    phases_completed: int
    phases_total: int
    percent_complete: int


class PhaseDetailResponse(BaseModel):
    """Detail for a single phase"""
    phase_id: str
    phase_name: str
    status: str  # "pending", "running", "completed", "failed"
    current: int
    total: int
    unit: str
    duration_seconds: Optional[int]


class OnboardingStatusResponse(BaseModel):
    """Full onboarding status response"""
    portfolio_id: str
    status: str  # "running", "completed", "failed", "not_found"
    started_at: Optional[str]  # ISO format, None if not running
    elapsed_seconds: int
    overall_progress: Optional[OverallProgressResponse]
    current_phase_progress: Optional[CurrentPhaseProgressResponse]
    activity_log: List[ActivityLogEntryResponse]
    phases: Optional[List[PhaseDetailResponse]]


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get(
    "/status/{portfolio_id}",
    response_model=OnboardingStatusResponse,
    summary="Get portfolio onboarding status",
    description="""
Get real-time batch processing status for a portfolio during onboarding.

This endpoint is designed for frontend polling to display progress during
the 15-20 minute portfolio setup process. It returns:

- Current phase and overall progress percentage
- Activity log entries showing what's happening in real-time
- Phase-by-phase status and duration

**Status values:**
- `running`: Batch is currently processing this portfolio
- `completed`: Batch finished (will clear shortly after completion)
- `not_found`: No batch is running for this portfolio

**Polling recommendation:** Poll every 2 seconds during onboarding.

**Authentication:** Requires Clerk JWT. User must own the portfolio.
"""
)
async def get_onboarding_status(
    portfolio_id: str,
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
) -> OnboardingStatusResponse:
    """
    Get batch processing status for a specific portfolio.

    Returns real-time progress for the onboarding batch process, including
    phase progress and activity log entries for display in the UI.
    """
    # Validate portfolio_id format
    try:
        portfolio_uuid = UUID(portfolio_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_portfolio_id", "message": "Invalid portfolio ID format"}
        )

    # Verify user owns this portfolio
    portfolio_result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_uuid,
            Portfolio.user_id == current_user.id
        )
    )
    portfolio = portfolio_result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "portfolio_not_found",
                "message": "Portfolio not found or you don't have access"
            }
        )

    # Get status from batch_run_tracker
    status_data = batch_run_tracker.get_onboarding_status(portfolio_id)

    if status_data is None:
        # No batch running for this portfolio
        logger.debug(f"No batch running for portfolio {portfolio_id}")
        return OnboardingStatusResponse(
            portfolio_id=portfolio_id,
            status="not_found",
            started_at=None,
            elapsed_seconds=0,
            overall_progress=None,
            current_phase_progress=None,
            activity_log=[],
            phases=None
        )

    # Build response from status_data
    overall_progress = None
    if status_data.get("overall_progress"):
        op = status_data["overall_progress"]
        overall_progress = OverallProgressResponse(
            current_phase=op.get("current_phase"),
            current_phase_name=op.get("current_phase_name"),
            phases_completed=op.get("phases_completed", 0),
            phases_total=op.get("phases_total", 0),
            percent_complete=op.get("percent_complete", 0)
        )

    current_phase_progress = None
    if status_data.get("current_phase_progress"):
        cpp = status_data["current_phase_progress"]
        current_phase_progress = CurrentPhaseProgressResponse(
            current=cpp.get("current", 0),
            total=cpp.get("total", 0),
            unit=cpp.get("unit", "items")
        )

    # Convert activity log entries
    activity_log = [
        ActivityLogEntryResponse(
            timestamp=entry.get("timestamp", ""),
            message=entry.get("message", ""),
            level=entry.get("level", "info")
        )
        for entry in status_data.get("activity_log", [])
    ]

    # Get phase details from tracker (portfolio-scoped to prevent cross-portfolio leaks)
    phase_progress = batch_run_tracker.get_phase_progress_for_portfolio(portfolio_id)
    phases = None
    if phase_progress.get("phases"):
        phases = [
            PhaseDetailResponse(
                phase_id=p.get("phase_id", ""),
                phase_name=p.get("phase_name", ""),
                status=p.get("status", "pending"),
                current=p.get("current", 0),
                total=p.get("total", 0),
                unit=p.get("unit", "items"),
                duration_seconds=p.get("duration_seconds")
            )
            for p in phase_progress["phases"]
        ]

    return OnboardingStatusResponse(
        portfolio_id=portfolio_id,
        status=status_data.get("status", "running"),
        started_at=status_data.get("started_at"),
        elapsed_seconds=status_data.get("elapsed_seconds", 0),
        overall_progress=overall_progress,
        current_phase_progress=current_phase_progress,
        activity_log=activity_log,
        phases=phases
    )


# ==============================================================================
# Log Download Endpoint (Phase 7.2)
# ==============================================================================

def _format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration (e.g., '14m 32s')."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    if minutes < 60:
        return f"{minutes}m {remaining_seconds}s"
    hours = minutes // 60
    remaining_minutes = minutes % 60
    return f"{hours}h {remaining_minutes}m {remaining_seconds}s"


def _build_txt_log(
    portfolio_id: str,
    portfolio_name: str,
    status_data: Dict[str, Any],
    activity_log: List[Dict[str, Any]]
) -> str:
    """Build formatted TXT log file content."""
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append("SIGMASIGHT PORTFOLIO SETUP LOG")
    lines.append("=" * 80)
    lines.append(f"Portfolio ID: {portfolio_id}")
    lines.append(f"Portfolio Name: {portfolio_name}")
    lines.append(f"Started: {status_data.get('started_at', 'N/A')}")

    final_status = status_data.get("status", "unknown")
    elapsed = status_data.get("elapsed_seconds", 0)
    lines.append(f"Total Duration: {_format_duration(elapsed)}")
    lines.append(f"Final Status: {final_status}")
    lines.append("")

    # Summary
    lines.append("=" * 80)
    lines.append("SUMMARY")
    lines.append("=" * 80)

    overall = status_data.get("overall_progress", {})
    phases_completed = overall.get("phases_completed", 0)
    phases_total = overall.get("phases_total", 0)
    lines.append(f"Phases Completed: {phases_completed}/{phases_total}")
    lines.append("")

    # Phase Details
    lines.append("=" * 80)
    lines.append("PHASE DETAILS")
    lines.append("=" * 80)

    phases = status_data.get("phases", [])
    if phases:
        for phase in phases:
            phase_name = phase.get("phase_name", "Unknown")
            phase_status = phase.get("status", "unknown")
            duration = phase.get("duration_seconds")
            current = phase.get("current", 0)
            total = phase.get("total", 0)
            unit = phase.get("unit", "items")

            lines.append(f"Phase: {phase_name}")
            lines.append(f"  Status: {phase_status}")
            if duration is not None:
                lines.append(f"  Duration: {_format_duration(duration)}")
            if total > 0:
                lines.append(f"  Progress: {current}/{total} {unit}")
            lines.append("")
    else:
        lines.append("No phase data available.")
        lines.append("")

    # Activity Log
    lines.append("=" * 80)
    lines.append("ACTIVITY LOG")
    lines.append("=" * 80)

    if activity_log:
        for entry in activity_log:
            timestamp = entry.get("timestamp", "")
            # Format timestamp for readability
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, AttributeError):
                    pass

            level = entry.get("level", "INFO").upper()
            message = entry.get("message", "")
            lines.append(f"{timestamp} [{level}] {message}")
    else:
        lines.append("No activity log entries available.")

    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF LOG")
    lines.append("=" * 80)

    return "\n".join(lines)


@router.get(
    "/status/{portfolio_id}/logs",
    summary="Download portfolio onboarding logs",
    description="""
Download the complete activity log for a portfolio's onboarding batch process.

This endpoint provides a downloadable log file useful for:
- Debugging issues during onboarding
- Support tickets
- User peace of mind ("I can see everything that happened")

**Formats:**
- `txt`: Human-readable text file (default)
- `json`: Machine-readable JSON

**Authentication:** Requires Clerk JWT. User must own the portfolio.
"""
)
async def download_onboarding_logs(
    portfolio_id: str,
    output_format: str = Query(default="txt", alias="format", description="Output format: 'txt' or 'json'"),
    current_user: User = Depends(get_current_user_clerk),
    db: AsyncSession = Depends(get_db),
):
    """
    Download complete activity log for portfolio setup.

    Returns the full log as either a text file or JSON, depending on format parameter.
    """
    # Validate portfolio_id format
    try:
        portfolio_uuid = UUID(portfolio_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_portfolio_id", "message": "Invalid portfolio ID format"}
        )

    # Verify user owns this portfolio
    portfolio_result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_uuid,
            Portfolio.user_id == current_user.id
        )
    )
    portfolio = portfolio_result.scalar_one_or_none()

    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "portfolio_not_found",
                "message": "Portfolio not found or you don't have access"
            }
        )

    # Get status from batch_run_tracker
    status_data = batch_run_tracker.get_onboarding_status(portfolio_id)

    # Get full activity log (up to 5000 entries)
    # Phase 7.3: Use async version with database fallback
    # Security Fix: Pass portfolio_id to ensure we only get this portfolio's logs
    activity_log = await batch_run_tracker.get_full_activity_log_async(portfolio_id=portfolio_id)

    # If no status in memory but logs exist in DB, create minimal status
    if status_data is None:
        if activity_log:
            # Logs found in database - create minimal status for response
            status_data = {
                "portfolio_id": portfolio_id,
                "status": "completed",  # Assume completed if we have DB logs
                "started_at": None,
                "elapsed_seconds": 0,
                "overall_progress": {
                    "current_phase": None,
                    "current_phase_name": None,
                    "phases_completed": 0,
                    "phases_total": 0,
                    "percent_complete": 100
                },
                "current_phase_progress": None,
                "activity_log": []
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "no_logs_available",
                    "message": "No onboarding logs available for this portfolio"
                }
            )

    # Build phase details from status (portfolio-scoped to prevent cross-portfolio leaks)
    phase_progress = batch_run_tracker.get_phase_progress_for_portfolio(portfolio_id)
    status_data["phases"] = phase_progress.get("phases", [])

    # Generate timestamp for filename
    timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
    filename_base = f"portfolio_setup_log_{portfolio_id[:8]}_{timestamp}"

    if output_format.lower() == "json":
        # JSON format
        json_response = {
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name,
            "started_at": status_data.get("started_at"),
            "elapsed_seconds": status_data.get("elapsed_seconds", 0),
            "final_status": status_data.get("status", "unknown"),
            "overall_progress": status_data.get("overall_progress", {}),
            "phases": status_data.get("phases", []),
            "activity_log": activity_log,
            "generated_at": utc_now().isoformat()
        }

        return JSONResponse(
            content=json_response,
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.json"'
            }
        )
    else:
        # TXT format (default)
        txt_content = _build_txt_log(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio.name,
            status_data=status_data,
            activity_log=activity_log
        )

        return PlainTextResponse(
            content=txt_content,
            headers={
                "Content-Disposition": f'attachment; filename="{filename_base}.txt"'
            }
        )
