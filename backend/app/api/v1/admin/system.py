"""
Admin System Endpoints

Phase 7 Admin Dashboard Implementation:
- System health status
- Manual cleanup trigger
- Aggregation status and triggers

Created: December 22, 2025
"""
from datetime import date, datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from app.database import get_db
from app.models.admin import (
    AdminUser,
    UserActivityEvent,
    AIRequestMetrics,
    BatchRunHistory,
    DailyMetrics
)
from app.core.admin_dependencies import get_current_admin, require_super_admin
from app.core.logging import get_logger
from app.batch.admin_metrics_job import (
    run_admin_metrics_batch,
    aggregate_daily_metrics,
    cleanup_old_data,
    get_aggregation_status,
    get_retention_status,
    RETENTION_DAYS
)

logger = get_logger(__name__)

router = APIRouter(prefix="/system", tags=["admin-system"])


@router.get("/health")
async def get_system_health(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Get system health status.

    Returns status of key system components:
    - Database connectivity
    - Table row counts
    - Recent activity
    - Retention compliance
    """
    logger.info(f"Admin {admin.email} checking system health")

    health = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'database': {
            'connected': True,
            'tables': {}
        },
        'activity': {},
        'retention': {}
    }

    try:
        # Check database connectivity and get table counts
        tables = [
            ('user_activity_events', UserActivityEvent),
            ('ai_request_metrics', AIRequestMetrics),
            ('batch_run_history', BatchRunHistory),
            ('daily_metrics', DailyMetrics)
        ]

        for table_name, model in tables:
            try:
                result = await db.execute(select(func.count(model.id)))
                health['database']['tables'][table_name] = result.scalar() or 0
            except Exception as e:
                health['database']['tables'][table_name] = f"error: {str(e)}"
                health['status'] = 'degraded'

        # Check recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)

        result = await db.execute(
            select(func.count(UserActivityEvent.id))
            .where(UserActivityEvent.created_at >= yesterday)
        )
        health['activity']['events_24h'] = result.scalar() or 0

        result = await db.execute(
            select(func.count(AIRequestMetrics.id))
            .where(AIRequestMetrics.created_at >= yesterday)
        )
        health['activity']['ai_requests_24h'] = result.scalar() or 0

        result = await db.execute(
            select(func.count(BatchRunHistory.id))
            .where(BatchRunHistory.started_at >= yesterday)
        )
        health['activity']['batch_runs_24h'] = result.scalar() or 0

        # Check retention status
        retention_status = await get_retention_status()
        health['retention'] = {
            'retention_days': RETENTION_DAYS,
            'all_compliant': retention_status['all_compliant'],
            'tables': {
                name: info.get('compliant', True)
                for name, info in retention_status['tables'].items()
            }
        }

        if not retention_status['all_compliant']:
            health['status'] = 'needs_cleanup'

    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        health['status'] = 'unhealthy'
        health['error'] = str(e)

    return health


@router.get("/aggregation/status")
async def get_aggregation_status_endpoint(
    days: int = Query(default=7, ge=1, le=30, description="Days to check"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Get status of daily metrics aggregation.

    Shows which dates have been aggregated and identifies gaps.
    """
    logger.info(f"Admin {admin.email} checking aggregation status")

    try:
        status = await get_aggregation_status(days)
        return status
    except Exception as e:
        logger.error(f"Failed to get aggregation status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retention/status")
async def get_retention_status_endpoint(
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Get status of data retention compliance.

    Shows oldest records and counts of data past retention period.
    """
    logger.info(f"Admin {admin.email} checking retention status")

    try:
        status = await get_retention_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get retention status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def trigger_cleanup(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin)
):
    """
    Manually trigger data cleanup.

    Deletes data older than retention period:
    - user_activity_events: 30 days
    - ai_request_metrics: 30 days
    - batch_run_history: 30 days
    - admin_sessions (expired): 7 days

    Requires super_admin role.
    """
    logger.info(f"Super admin {admin.email} triggering manual cleanup")

    try:
        # Run cleanup synchronously to return results
        result = await cleanup_old_data(db)

        return {
            'success': True,
            'triggered_by': admin.email,
            'timestamp': datetime.utcnow().isoformat(),
            'deleted': result,
            'total_deleted': sum(result.values())
        }
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/aggregate")
async def trigger_aggregation(
    target_date: Optional[date] = Query(default=None, description="Date to aggregate (defaults to yesterday)"),
    days: int = Query(default=1, ge=1, le=7, description="Number of days to aggregate"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin)
):
    """
    Manually trigger metrics aggregation.

    Aggregates raw events to daily_metrics table.
    Defaults to yesterday, can specify date or number of days.

    Requires super_admin role.
    """
    logger.info(f"Super admin {admin.email} triggering manual aggregation for {days} days")

    try:
        results = []

        for days_ago in range(days):
            if target_date and days_ago == 0:
                agg_date = target_date
            else:
                agg_date = date.today() - timedelta(days=days_ago + 1)

            result = await aggregate_daily_metrics(db, agg_date)
            results.append(result)

        return {
            'success': True,
            'triggered_by': admin.email,
            'timestamp': datetime.utcnow().isoformat(),
            'aggregations': results,
            'total_metrics_saved': sum(r['metrics_saved'] for r in results)
        }
    except Exception as e:
        logger.error(f"Aggregation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-batch")
async def trigger_admin_metrics_batch(
    aggregate_days: int = Query(default=1, ge=1, le=7, description="Days to aggregate"),
    run_cleanup: bool = Query(default=True, description="Run cleanup after aggregation"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin)
):
    """
    Manually trigger the full admin metrics batch job.

    Runs both aggregation and cleanup (same as scheduled cron job).

    Requires super_admin role.
    """
    logger.info(
        f"Super admin {admin.email} triggering admin metrics batch: "
        f"aggregate_days={aggregate_days}, run_cleanup={run_cleanup}"
    )

    try:
        result = await run_admin_metrics_batch(
            aggregate_days=aggregate_days,
            run_cleanup=run_cleanup
        )

        return {
            'success': result['success'],
            'triggered_by': admin.email,
            'result': result
        }
    except Exception as e:
        logger.error(f"Admin metrics batch failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-metrics")
async def get_daily_metrics(
    days: int = Query(default=7, ge=1, le=90, description="Days of history"),
    metric_type: Optional[str] = Query(default=None, description="Filter by metric type prefix"),
    db: AsyncSession = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin)
):
    """
    Get aggregated daily metrics.

    Returns pre-computed metrics from daily_metrics table.
    Optionally filter by metric type prefix (e.g., 'user_activity', 'ai_requests', 'batch').
    """
    logger.info(f"Admin {admin.email} fetching daily metrics for {days} days")

    cutoff_date = date.today() - timedelta(days=days)

    query = (
        select(DailyMetrics)
        .where(DailyMetrics.date >= cutoff_date)
        .order_by(DailyMetrics.date.desc(), DailyMetrics.metric_type)
    )

    if metric_type:
        query = query.where(DailyMetrics.metric_type.startswith(metric_type))

    result = await db.execute(query)
    metrics = result.scalars().all()

    # Group by date
    grouped = {}
    for m in metrics:
        date_str = m.date.isoformat()
        if date_str not in grouped:
            grouped[date_str] = {}

        # Handle dimensions
        if m.dimensions:
            key = f"{m.metric_type}:{m.dimensions.get('key', '')}"
        else:
            key = m.metric_type

        grouped[date_str][key] = float(m.metric_value)

    return {
        'days': days,
        'metric_type_filter': metric_type,
        'dates_count': len(grouped),
        'metrics_count': len(metrics),
        'data': grouped
    }
