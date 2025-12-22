"""
Admin Onboarding Analytics Endpoints

Provides analytics for the admin dashboard to track:
- Onboarding funnel conversion rates
- Error breakdown by code
- Daily trends

Data source: user_activity_events table (30-day rolling retention)

Created: December 22, 2025 (Admin Dashboard Phase 3)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text, case
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID

from app.database import get_db
from app.models.admin import UserActivityEvent
from app.api.v1.admin.auth import get_current_admin, CurrentAdmin
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/onboarding", tags=["Admin - Onboarding Analytics"])


# ==============================================================================
# Response Schemas
# ==============================================================================

class FunnelStep(BaseModel):
    """A single step in the onboarding funnel."""
    step: str
    event_type: str
    count: int
    conversion_rate: float  # Percentage relative to first step


class FunnelResponse(BaseModel):
    """Complete funnel analytics."""
    date_range: Dict[str, str]
    total_register_starts: int
    total_portfolio_completes: int
    overall_conversion_rate: float
    steps: List[FunnelStep]


class ErrorBreakdown(BaseModel):
    """Error breakdown by code."""
    error_code: str
    event_type: str
    count: int
    percentage: float
    sample_messages: List[str]  # Up to 3 sample error messages


class ErrorsResponse(BaseModel):
    """Error analytics response."""
    date_range: Dict[str, str]
    total_errors: int
    breakdown: List[ErrorBreakdown]


class DailyMetric(BaseModel):
    """Daily metrics for a single day."""
    date: str
    register_starts: int
    register_completes: int
    login_successes: int
    login_errors: int
    portfolio_starts: int
    portfolio_completes: int


class DailyTrendsResponse(BaseModel):
    """Daily trends response."""
    date_range: Dict[str, str]
    metrics: List[DailyMetric]


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_date_range(days: int) -> tuple:
    """Get start and end datetime for the given number of days."""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("/funnel", response_model=FunnelResponse)
async def get_onboarding_funnel(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to analyze"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> FunnelResponse:
    """
    Get onboarding funnel analytics.

    Shows conversion rates through the onboarding steps:
    1. Registration start
    2. Registration complete
    3. Login success
    4. Portfolio start
    5. Portfolio complete

    Args:
        days: Number of days to analyze (default 30)
        admin_user: Authenticated admin user
        db: Database session

    Returns:
        Funnel conversion analytics
    """
    start_date, end_date = get_date_range(days)

    # Define funnel steps
    funnel_events = [
        ("Registration Start", "onboarding.register_start"),
        ("Registration Complete", "onboarding.register_complete"),
        ("Login Success", "onboarding.login_success"),
        ("Portfolio Start", "onboarding.portfolio_start"),
        ("Portfolio Complete", "onboarding.portfolio_complete"),
    ]

    # Count each step
    steps = []
    first_count = 0

    for step_name, event_type in funnel_events:
        result = await db.execute(
            select(func.count(UserActivityEvent.id))
            .where(
                and_(
                    UserActivityEvent.event_type == event_type,
                    UserActivityEvent.created_at >= start_date,
                    UserActivityEvent.created_at <= end_date,
                )
            )
        )
        count = result.scalar() or 0

        if step_name == "Registration Start":
            first_count = count

        conversion_rate = (count / first_count * 100) if first_count > 0 else 0

        steps.append(FunnelStep(
            step=step_name,
            event_type=event_type,
            count=count,
            conversion_rate=round(conversion_rate, 1),
        ))

    # Get overall conversion rate
    register_starts = steps[0].count if steps else 0
    portfolio_completes = steps[4].count if len(steps) > 4 else 0
    overall_rate = (portfolio_completes / register_starts * 100) if register_starts > 0 else 0

    return FunnelResponse(
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        total_register_starts=register_starts,
        total_portfolio_completes=portfolio_completes,
        overall_conversion_rate=round(overall_rate, 1),
        steps=steps,
    )


@router.get("/errors", response_model=ErrorsResponse)
async def get_onboarding_errors(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to analyze"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ErrorsResponse:
    """
    Get error breakdown for onboarding events.

    Shows errors grouped by error code with sample messages.

    Args:
        days: Number of days to analyze (default 30)
        admin_user: Authenticated admin user
        db: Database session

    Returns:
        Error breakdown analytics
    """
    start_date, end_date = get_date_range(days)

    # Get error counts by code
    result = await db.execute(
        select(
            UserActivityEvent.error_code,
            UserActivityEvent.event_type,
            func.count(UserActivityEvent.id).label("count"),
        )
        .where(
            and_(
                UserActivityEvent.error_code.isnot(None),
                UserActivityEvent.created_at >= start_date,
                UserActivityEvent.created_at <= end_date,
            )
        )
        .group_by(UserActivityEvent.error_code, UserActivityEvent.event_type)
        .order_by(func.count(UserActivityEvent.id).desc())
    )
    error_counts = result.all()

    # Calculate total errors
    total_errors = sum(row.count for row in error_counts)

    # Build breakdown with sample messages
    breakdown = []
    for row in error_counts:
        # Get sample error messages for this code
        sample_result = await db.execute(
            select(UserActivityEvent.error_message)
            .where(
                and_(
                    UserActivityEvent.error_code == row.error_code,
                    UserActivityEvent.error_message.isnot(None),
                    UserActivityEvent.created_at >= start_date,
                    UserActivityEvent.created_at <= end_date,
                )
            )
            .limit(3)
        )
        samples = [r[0] for r in sample_result.all() if r[0]]

        percentage = (row.count / total_errors * 100) if total_errors > 0 else 0

        breakdown.append(ErrorBreakdown(
            error_code=row.error_code,
            event_type=row.event_type,
            count=row.count,
            percentage=round(percentage, 1),
            sample_messages=samples,
        ))

    return ErrorsResponse(
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        total_errors=total_errors,
        breakdown=breakdown,
    )


@router.get("/daily", response_model=DailyTrendsResponse)
async def get_daily_trends(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to analyze"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> DailyTrendsResponse:
    """
    Get daily onboarding trends.

    Shows day-by-day metrics for key onboarding events.

    Args:
        days: Number of days to analyze (default 30)
        admin_user: Authenticated admin user
        db: Database session

    Returns:
        Daily trends analytics
    """
    start_date, end_date = get_date_range(days)

    # Get daily counts for each event type
    result = await db.execute(
        select(
            func.date(UserActivityEvent.created_at).label("date"),
            func.count(UserActivityEvent.id).filter(
                UserActivityEvent.event_type == "onboarding.register_start"
            ).label("register_starts"),
            func.count(UserActivityEvent.id).filter(
                UserActivityEvent.event_type == "onboarding.register_complete"
            ).label("register_completes"),
            func.count(UserActivityEvent.id).filter(
                UserActivityEvent.event_type == "onboarding.login_success"
            ).label("login_successes"),
            func.count(UserActivityEvent.id).filter(
                UserActivityEvent.event_type == "onboarding.login_error"
            ).label("login_errors"),
            func.count(UserActivityEvent.id).filter(
                UserActivityEvent.event_type == "onboarding.portfolio_start"
            ).label("portfolio_starts"),
            func.count(UserActivityEvent.id).filter(
                UserActivityEvent.event_type == "onboarding.portfolio_complete"
            ).label("portfolio_completes"),
        )
        .where(
            and_(
                UserActivityEvent.created_at >= start_date,
                UserActivityEvent.created_at <= end_date,
            )
        )
        .group_by(func.date(UserActivityEvent.created_at))
        .order_by(func.date(UserActivityEvent.created_at))
    )
    daily_data = result.all()

    metrics = [
        DailyMetric(
            date=str(row.date),
            register_starts=row.register_starts or 0,
            register_completes=row.register_completes or 0,
            login_successes=row.login_successes or 0,
            login_errors=row.login_errors or 0,
            portfolio_starts=row.portfolio_starts or 0,
            portfolio_completes=row.portfolio_completes or 0,
        )
        for row in daily_data
    ]

    return DailyTrendsResponse(
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        metrics=metrics,
    )


@router.get("/events")
async def get_recent_events(
    limit: int = Query(default=50, ge=1, le=200, description="Number of events to return"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
    error_only: bool = Query(default=False, description="Only show error events"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get recent activity events for debugging and monitoring.

    Args:
        limit: Number of events to return
        event_type: Optional filter by event type
        error_only: Only show events with error codes
        admin_user: Authenticated admin user
        db: Database session

    Returns:
        List of recent events
    """
    query = select(UserActivityEvent).order_by(UserActivityEvent.created_at.desc())

    if event_type:
        query = query.where(UserActivityEvent.event_type == event_type)

    if error_only:
        query = query.where(UserActivityEvent.error_code.isnot(None))

    query = query.limit(limit)

    result = await db.execute(query)
    events = result.scalars().all()

    return {
        "total": len(events),
        "events": [
            {
                "id": str(event.id),
                "user_id": str(event.user_id) if event.user_id else None,
                "session_id": event.session_id,
                "event_type": event.event_type,
                "event_category": event.event_category,
                "event_data": event.event_data,
                "error_code": event.error_code,
                "error_message": event.error_message,
                "ip_address": event.ip_address,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in events
        ],
    }
