"""
Admin AI Metrics Endpoints

Provides analytics for the admin dashboard to track:
- AI request performance (latency, tokens)
- Error rates and breakdown
- Tool usage frequency

Data source: ai_request_metrics table (30-day rolling retention)

Created: December 22, 2025 (Admin Dashboard Phase 4)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case, desc
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.admin import AIRequestMetrics
from app.api.v1.admin.auth import get_current_admin, CurrentAdmin
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/ai", tags=["Admin - AI Metrics"])


# ==============================================================================
# Response Schemas
# ==============================================================================

class MetricsSummary(BaseModel):
    """Summary of AI request metrics."""
    date_range: Dict[str, str]
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_rate: float  # Percentage
    avg_latency_ms: Optional[float]
    avg_input_tokens: Optional[float]
    avg_output_tokens: Optional[float]
    total_input_tokens: int
    total_output_tokens: int
    total_tool_calls: int


class LatencyPercentiles(BaseModel):
    """Latency percentile metrics."""
    date_range: Dict[str, str]
    sample_count: int
    p50_ms: Optional[float]
    p75_ms: Optional[float]
    p90_ms: Optional[float]
    p95_ms: Optional[float]
    p99_ms: Optional[float]
    avg_ms: Optional[float]
    min_ms: Optional[float]
    max_ms: Optional[float]
    avg_first_token_ms: Optional[float]


class DailyTokenUsage(BaseModel):
    """Daily token usage."""
    date: str
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    request_count: int
    avg_input_tokens: Optional[float]
    avg_output_tokens: Optional[float]


class TokenUsageResponse(BaseModel):
    """Token usage trends response."""
    date_range: Dict[str, str]
    total_input_tokens: int
    total_output_tokens: int
    daily: List[DailyTokenUsage]


class ErrorBreakdown(BaseModel):
    """Error breakdown by type."""
    error_type: str
    count: int
    percentage: float
    sample_messages: List[str]  # Up to 3 sample error messages


class ErrorsResponse(BaseModel):
    """Error analytics response."""
    date_range: Dict[str, str]
    total_errors: int
    error_rate: float
    breakdown: List[ErrorBreakdown]


class ToolUsage(BaseModel):
    """Tool usage statistics."""
    tool_name: str
    call_count: int
    percentage: float


class ToolUsageResponse(BaseModel):
    """Tool usage response."""
    date_range: Dict[str, str]
    total_tool_calls: int
    requests_with_tools: int
    avg_tools_per_request: float
    tools: List[ToolUsage]


class ModelUsage(BaseModel):
    """Model usage statistics."""
    model: str
    request_count: int
    percentage: float
    avg_latency_ms: Optional[float]
    avg_tokens: Optional[float]


class ModelUsageResponse(BaseModel):
    """Model usage response."""
    date_range: Dict[str, str]
    models: List[ModelUsage]


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

@router.get("/metrics", response_model=MetricsSummary)
async def get_metrics_summary(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to analyze"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> MetricsSummary:
    """
    Get summary of AI request metrics.

    Provides overview metrics including:
    - Total requests (successful and failed)
    - Error rate
    - Average latency
    - Token usage

    Args:
        days: Number of days to analyze (default 30)
        admin_user: Authenticated admin user
        db: Database session

    Returns:
        Summary metrics
    """
    start_date, end_date = get_date_range(days)

    # Get aggregate metrics
    result = await db.execute(
        select(
            func.count(AIRequestMetrics.id).label("total"),
            func.count(AIRequestMetrics.id).filter(AIRequestMetrics.error_type.is_(None)).label("successful"),
            func.count(AIRequestMetrics.id).filter(AIRequestMetrics.error_type.isnot(None)).label("failed"),
            func.avg(AIRequestMetrics.total_latency_ms).label("avg_latency"),
            func.avg(AIRequestMetrics.input_tokens).label("avg_input"),
            func.avg(AIRequestMetrics.output_tokens).label("avg_output"),
            func.coalesce(func.sum(AIRequestMetrics.input_tokens), 0).label("total_input"),
            func.coalesce(func.sum(AIRequestMetrics.output_tokens), 0).label("total_output"),
            func.coalesce(func.sum(AIRequestMetrics.tool_calls_count), 0).label("total_tools"),
        )
        .where(
            and_(
                AIRequestMetrics.created_at >= start_date,
                AIRequestMetrics.created_at <= end_date,
            )
        )
    )
    row = result.one()

    total = row.total or 0
    failed = row.failed or 0
    error_rate = (failed / total * 100) if total > 0 else 0

    return MetricsSummary(
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        total_requests=total,
        successful_requests=row.successful or 0,
        failed_requests=failed,
        error_rate=round(error_rate, 2),
        avg_latency_ms=round(row.avg_latency, 1) if row.avg_latency else None,
        avg_input_tokens=round(row.avg_input, 1) if row.avg_input else None,
        avg_output_tokens=round(row.avg_output, 1) if row.avg_output else None,
        total_input_tokens=int(row.total_input),
        total_output_tokens=int(row.total_output),
        total_tool_calls=int(row.total_tools),
    )


@router.get("/latency", response_model=LatencyPercentiles)
async def get_latency_percentiles(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to analyze"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> LatencyPercentiles:
    """
    Get latency percentiles (p50, p75, p90, p95, p99).

    Args:
        days: Number of days to analyze (default 30)
        admin_user: Authenticated admin user
        db: Database session

    Returns:
        Latency percentile metrics
    """
    start_date, end_date = get_date_range(days)

    # Get all latency values for percentile calculation
    result = await db.execute(
        select(
            AIRequestMetrics.total_latency_ms,
            AIRequestMetrics.first_token_ms,
        )
        .where(
            and_(
                AIRequestMetrics.created_at >= start_date,
                AIRequestMetrics.created_at <= end_date,
                AIRequestMetrics.total_latency_ms.isnot(None),
                AIRequestMetrics.error_type.is_(None),  # Only successful requests
            )
        )
        .order_by(AIRequestMetrics.total_latency_ms)
    )
    rows = result.all()

    if not rows:
        return LatencyPercentiles(
            date_range={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            sample_count=0,
            p50_ms=None,
            p75_ms=None,
            p90_ms=None,
            p95_ms=None,
            p99_ms=None,
            avg_ms=None,
            min_ms=None,
            max_ms=None,
            avg_first_token_ms=None,
        )

    latencies = [r.total_latency_ms for r in rows if r.total_latency_ms is not None]
    first_tokens = [r.first_token_ms for r in rows if r.first_token_ms is not None]
    n = len(latencies)

    def percentile(data: List[int], p: float) -> float:
        """Calculate percentile value."""
        if not data:
            return 0
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (k - f) * (data[c] - data[f])

    latencies.sort()

    return LatencyPercentiles(
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        sample_count=n,
        p50_ms=round(percentile(latencies, 50), 1) if latencies else None,
        p75_ms=round(percentile(latencies, 75), 1) if latencies else None,
        p90_ms=round(percentile(latencies, 90), 1) if latencies else None,
        p95_ms=round(percentile(latencies, 95), 1) if latencies else None,
        p99_ms=round(percentile(latencies, 99), 1) if latencies else None,
        avg_ms=round(sum(latencies) / n, 1) if latencies else None,
        min_ms=float(min(latencies)) if latencies else None,
        max_ms=float(max(latencies)) if latencies else None,
        avg_first_token_ms=round(sum(first_tokens) / len(first_tokens), 1) if first_tokens else None,
    )


@router.get("/tokens", response_model=TokenUsageResponse)
async def get_token_usage(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to analyze"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> TokenUsageResponse:
    """
    Get token usage trends by day.

    Args:
        days: Number of days to analyze (default 30)
        admin_user: Authenticated admin user
        db: Database session

    Returns:
        Daily token usage trends
    """
    start_date, end_date = get_date_range(days)

    # Get daily token usage
    result = await db.execute(
        select(
            func.date(AIRequestMetrics.created_at).label("date"),
            func.coalesce(func.sum(AIRequestMetrics.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(AIRequestMetrics.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(AIRequestMetrics.total_tokens), 0).label("total_tokens"),
            func.count(AIRequestMetrics.id).label("request_count"),
            func.avg(AIRequestMetrics.input_tokens).label("avg_input"),
            func.avg(AIRequestMetrics.output_tokens).label("avg_output"),
        )
        .where(
            and_(
                AIRequestMetrics.created_at >= start_date,
                AIRequestMetrics.created_at <= end_date,
            )
        )
        .group_by(func.date(AIRequestMetrics.created_at))
        .order_by(func.date(AIRequestMetrics.created_at))
    )
    daily_data = result.all()

    total_input = sum(d.input_tokens for d in daily_data)
    total_output = sum(d.output_tokens for d in daily_data)

    daily = [
        DailyTokenUsage(
            date=str(d.date),
            total_input_tokens=int(d.input_tokens),
            total_output_tokens=int(d.output_tokens),
            total_tokens=int(d.total_tokens),
            request_count=d.request_count,
            avg_input_tokens=round(d.avg_input, 1) if d.avg_input else None,
            avg_output_tokens=round(d.avg_output, 1) if d.avg_output else None,
        )
        for d in daily_data
    ]

    return TokenUsageResponse(
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        total_input_tokens=int(total_input),
        total_output_tokens=int(total_output),
        daily=daily,
    )


@router.get("/errors", response_model=ErrorsResponse)
async def get_error_breakdown(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to analyze"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ErrorsResponse:
    """
    Get error breakdown by type.

    Args:
        days: Number of days to analyze (default 30)
        admin_user: Authenticated admin user
        db: Database session

    Returns:
        Error breakdown analytics
    """
    start_date, end_date = get_date_range(days)

    # Get total request count for error rate
    total_result = await db.execute(
        select(func.count(AIRequestMetrics.id))
        .where(
            and_(
                AIRequestMetrics.created_at >= start_date,
                AIRequestMetrics.created_at <= end_date,
            )
        )
    )
    total_requests = total_result.scalar() or 0

    # Get error counts by type
    result = await db.execute(
        select(
            AIRequestMetrics.error_type,
            func.count(AIRequestMetrics.id).label("count"),
        )
        .where(
            and_(
                AIRequestMetrics.error_type.isnot(None),
                AIRequestMetrics.created_at >= start_date,
                AIRequestMetrics.created_at <= end_date,
            )
        )
        .group_by(AIRequestMetrics.error_type)
        .order_by(desc(func.count(AIRequestMetrics.id)))
    )
    error_counts = result.all()

    total_errors = sum(row.count for row in error_counts)
    error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0

    # Build breakdown with sample messages
    breakdown = []
    for row in error_counts:
        # Get sample error messages
        sample_result = await db.execute(
            select(AIRequestMetrics.error_message)
            .where(
                and_(
                    AIRequestMetrics.error_type == row.error_type,
                    AIRequestMetrics.error_message.isnot(None),
                    AIRequestMetrics.created_at >= start_date,
                    AIRequestMetrics.created_at <= end_date,
                )
            )
            .limit(3)
        )
        samples = [r[0] for r in sample_result.all() if r[0]]

        percentage = (row.count / total_errors * 100) if total_errors > 0 else 0

        breakdown.append(ErrorBreakdown(
            error_type=row.error_type,
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
        error_rate=round(error_rate, 2),
        breakdown=breakdown,
    )


@router.get("/tools", response_model=ToolUsageResponse)
async def get_tool_usage(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to analyze"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ToolUsageResponse:
    """
    Get tool usage frequency.

    Args:
        days: Number of days to analyze (default 30)
        admin_user: Authenticated admin user
        db: Database session

    Returns:
        Tool usage statistics
    """
    start_date, end_date = get_date_range(days)

    # Get aggregate tool stats
    result = await db.execute(
        select(
            func.coalesce(func.sum(AIRequestMetrics.tool_calls_count), 0).label("total_tools"),
            func.count(AIRequestMetrics.id).filter(AIRequestMetrics.tool_calls_count > 0).label("requests_with_tools"),
            func.count(AIRequestMetrics.id).label("total_requests"),
        )
        .where(
            and_(
                AIRequestMetrics.created_at >= start_date,
                AIRequestMetrics.created_at <= end_date,
            )
        )
    )
    stats = result.one()

    total_tool_calls = int(stats.total_tools)
    requests_with_tools = stats.requests_with_tools or 0
    avg_tools = (total_tool_calls / requests_with_tools) if requests_with_tools > 0 else 0

    # Get tool call details from JSONB
    # Query all records with tool_calls to aggregate tool names
    tool_result = await db.execute(
        select(AIRequestMetrics.tool_calls)
        .where(
            and_(
                AIRequestMetrics.created_at >= start_date,
                AIRequestMetrics.created_at <= end_date,
                AIRequestMetrics.tool_calls.isnot(None),
            )
        )
    )
    tool_records = tool_result.all()

    # Count tool usage
    tool_counts: Dict[str, int] = {}
    for record in tool_records:
        tool_calls_json = record[0]
        if tool_calls_json and "tools" in tool_calls_json:
            for tool in tool_calls_json["tools"]:
                name = tool.get("name", "unknown")
                tool_counts[name] = tool_counts.get(name, 0) + 1

    # Build tool usage list
    total_counted = sum(tool_counts.values())
    tools = [
        ToolUsage(
            tool_name=name,
            call_count=count,
            percentage=round((count / total_counted * 100), 1) if total_counted > 0 else 0,
        )
        for name, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
    ]

    return ToolUsageResponse(
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        total_tool_calls=total_tool_calls,
        requests_with_tools=requests_with_tools,
        avg_tools_per_request=round(avg_tools, 2),
        tools=tools,
    )


@router.get("/models", response_model=ModelUsageResponse)
async def get_model_usage(
    days: int = Query(default=30, ge=1, le=90, description="Number of days to analyze"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> ModelUsageResponse:
    """
    Get model usage breakdown.

    Args:
        days: Number of days to analyze (default 30)
        admin_user: Authenticated admin user
        db: Database session

    Returns:
        Model usage statistics
    """
    start_date, end_date = get_date_range(days)

    # Get model usage stats
    result = await db.execute(
        select(
            AIRequestMetrics.model,
            func.count(AIRequestMetrics.id).label("count"),
            func.avg(AIRequestMetrics.total_latency_ms).label("avg_latency"),
            func.avg(AIRequestMetrics.total_tokens).label("avg_tokens"),
        )
        .where(
            and_(
                AIRequestMetrics.created_at >= start_date,
                AIRequestMetrics.created_at <= end_date,
            )
        )
        .group_by(AIRequestMetrics.model)
        .order_by(desc(func.count(AIRequestMetrics.id)))
    )
    model_data = result.all()

    total_requests = sum(m.count for m in model_data)

    models = [
        ModelUsage(
            model=m.model,
            request_count=m.count,
            percentage=round((m.count / total_requests * 100), 1) if total_requests > 0 else 0,
            avg_latency_ms=round(m.avg_latency, 1) if m.avg_latency else None,
            avg_tokens=round(m.avg_tokens, 1) if m.avg_tokens else None,
        )
        for m in model_data
    ]

    return ModelUsageResponse(
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        models=models,
    )
