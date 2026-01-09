"""
Onboarding Status API Endpoint (Phase 7.1)

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

Created: 2026-01-09 (Phase 7.1)
"""
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.core.clerk_auth import get_current_user_clerk
from app.models.users import User, Portfolio
from app.batch.batch_run_tracker import batch_run_tracker
from app.core.logging import get_logger

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

    # Get phase details from tracker
    phase_progress = batch_run_tracker.get_phase_progress()
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
