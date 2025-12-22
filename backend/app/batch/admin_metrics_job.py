"""
Admin Metrics Aggregation and Cleanup Job

Phase 7 Admin Dashboard Implementation:
- Aggregates raw events to daily_metrics table
- Cleans up data older than 30 days (retention policy)

Runs daily at 1 AM UTC (8 PM ET) via Railway cron.

Created: December 22, 2025
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, Any, Optional, List
from uuid import UUID
import json

from sqlalchemy import select, func, delete, and_, or_, distinct, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.admin import (
    UserActivityEvent,
    AIRequestMetrics,
    BatchRunHistory,
    DailyMetrics,
    AdminSession
)
from app.core.logging import get_logger

logger = get_logger(__name__)


# Retention policy (days)
RETENTION_DAYS = 30
SESSION_RETENTION_DAYS = 7


async def aggregate_user_activity_metrics(
    db: AsyncSession,
    target_date: date
) -> Dict[str, int]:
    """
    Aggregate user activity events for a specific date.

    Metrics aggregated:
    - user_registrations: Count of onboarding.register_complete events
    - user_logins: Count of onboarding.login_success events
    - portfolio_created: Count of onboarding.portfolio_complete events
    - chat_sessions: Count of chat.session_start events
    - feedback_given: Count of chat.feedback_given events
    - registration_errors: Count of onboarding.register_error events
    - login_errors: Count of onboarding.login_error events
    - total_events: Count of all events
    """
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    metrics = {}

    # Event type to metric name mapping
    event_metrics = {
        'onboarding.register_complete': 'user_registrations',
        'onboarding.login_success': 'user_logins',
        'onboarding.portfolio_complete': 'portfolios_created',
        'chat.session_start': 'chat_sessions',
        'chat.feedback_given': 'feedback_given',
        'onboarding.register_error': 'registration_errors',
        'onboarding.login_error': 'login_errors',
    }

    for event_type, metric_name in event_metrics.items():
        result = await db.execute(
            select(func.count(UserActivityEvent.id))
            .where(
                and_(
                    UserActivityEvent.event_type == event_type,
                    UserActivityEvent.created_at >= start_of_day,
                    UserActivityEvent.created_at < end_of_day
                )
            )
        )
        metrics[metric_name] = result.scalar() or 0

    # Total events count
    result = await db.execute(
        select(func.count(UserActivityEvent.id))
        .where(
            and_(
                UserActivityEvent.created_at >= start_of_day,
                UserActivityEvent.created_at < end_of_day
            )
        )
    )
    metrics['total_activity_events'] = result.scalar() or 0

    # Unique users count
    result = await db.execute(
        select(func.count(distinct(UserActivityEvent.user_id)))
        .where(
            and_(
                UserActivityEvent.user_id.isnot(None),
                UserActivityEvent.created_at >= start_of_day,
                UserActivityEvent.created_at < end_of_day
            )
        )
    )
    metrics['unique_users'] = result.scalar() or 0

    return metrics


async def aggregate_ai_request_metrics(
    db: AsyncSession,
    target_date: date
) -> Dict[str, Any]:
    """
    Aggregate AI request metrics for a specific date.

    Metrics aggregated:
    - ai_requests: Count of all requests
    - ai_requests_with_errors: Count of requests with errors
    - avg_latency_ms: Average total latency
    - avg_first_token_ms: Average time to first token
    - total_input_tokens: Sum of input tokens
    - total_output_tokens: Sum of output tokens
    - total_tokens: Sum of all tokens
    - avg_tool_calls: Average tool calls per request
    - latency_p50, p75, p90, p95, p99: Latency percentiles
    """
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    metrics = {}

    # Basic counts
    result = await db.execute(
        select(func.count(AIRequestMetrics.id))
        .where(
            and_(
                AIRequestMetrics.created_at >= start_of_day,
                AIRequestMetrics.created_at < end_of_day
            )
        )
    )
    metrics['ai_requests'] = result.scalar() or 0

    # Error count
    result = await db.execute(
        select(func.count(AIRequestMetrics.id))
        .where(
            and_(
                AIRequestMetrics.created_at >= start_of_day,
                AIRequestMetrics.created_at < end_of_day,
                AIRequestMetrics.error_type.isnot(None)
            )
        )
    )
    metrics['ai_requests_with_errors'] = result.scalar() or 0

    # Averages and sums
    result = await db.execute(
        select(
            func.avg(AIRequestMetrics.total_latency_ms),
            func.avg(AIRequestMetrics.first_token_ms),
            func.sum(AIRequestMetrics.input_tokens),
            func.sum(AIRequestMetrics.output_tokens),
            func.sum(AIRequestMetrics.total_tokens),
            func.avg(AIRequestMetrics.tool_calls_count)
        )
        .where(
            and_(
                AIRequestMetrics.created_at >= start_of_day,
                AIRequestMetrics.created_at < end_of_day
            )
        )
    )
    row = result.one()
    metrics['avg_latency_ms'] = float(row[0]) if row[0] else 0
    metrics['avg_first_token_ms'] = float(row[1]) if row[1] else 0
    metrics['total_input_tokens'] = int(row[2]) if row[2] else 0
    metrics['total_output_tokens'] = int(row[3]) if row[3] else 0
    metrics['total_tokens'] = int(row[4]) if row[4] else 0
    metrics['avg_tool_calls'] = float(row[5]) if row[5] else 0

    # Latency percentiles (using PostgreSQL percentile_cont)
    if metrics['ai_requests'] > 0:
        for percentile, name in [(0.50, 'p50'), (0.75, 'p75'), (0.90, 'p90'), (0.95, 'p95'), (0.99, 'p99')]:
            result = await db.execute(
                text(f"""
                    SELECT percentile_cont(:percentile) WITHIN GROUP (ORDER BY total_latency_ms)
                    FROM ai_request_metrics
                    WHERE created_at >= :start_of_day AND created_at < :end_of_day
                    AND total_latency_ms IS NOT NULL
                """),
                {'percentile': percentile, 'start_of_day': start_of_day, 'end_of_day': end_of_day}
            )
            value = result.scalar()
            metrics[f'latency_{name}'] = float(value) if value else 0
    else:
        for name in ['p50', 'p75', 'p90', 'p95', 'p99']:
            metrics[f'latency_{name}'] = 0

    # Model breakdown
    result = await db.execute(
        select(
            AIRequestMetrics.model,
            func.count(AIRequestMetrics.id)
        )
        .where(
            and_(
                AIRequestMetrics.created_at >= start_of_day,
                AIRequestMetrics.created_at < end_of_day
            )
        )
        .group_by(AIRequestMetrics.model)
    )
    model_counts = {row[0]: row[1] for row in result.all()}
    metrics['model_breakdown'] = model_counts

    return metrics


async def aggregate_batch_metrics(
    db: AsyncSession,
    target_date: date
) -> Dict[str, Any]:
    """
    Aggregate batch processing metrics for a specific date.

    Metrics aggregated:
    - batch_runs: Count of all runs
    - batch_completed: Count of completed runs
    - batch_failed: Count of failed runs
    - batch_partial: Count of partial runs
    - avg_duration_minutes: Average run duration
    - total_jobs: Sum of all jobs
    - total_completed_jobs: Sum of completed jobs
    - total_failed_jobs: Sum of failed jobs
    """
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    metrics = {}

    # Total runs
    result = await db.execute(
        select(func.count(BatchRunHistory.id))
        .where(
            and_(
                BatchRunHistory.started_at >= start_of_day,
                BatchRunHistory.started_at < end_of_day
            )
        )
    )
    metrics['batch_runs'] = result.scalar() or 0

    # Status breakdown
    for status in ['completed', 'failed', 'partial']:
        result = await db.execute(
            select(func.count(BatchRunHistory.id))
            .where(
                and_(
                    BatchRunHistory.started_at >= start_of_day,
                    BatchRunHistory.started_at < end_of_day,
                    BatchRunHistory.status == status
                )
            )
        )
        metrics[f'batch_{status}'] = result.scalar() or 0

    # Average duration (in minutes)
    result = await db.execute(
        select(
            func.avg(
                func.extract('epoch', BatchRunHistory.completed_at - BatchRunHistory.started_at) / 60
            )
        )
        .where(
            and_(
                BatchRunHistory.started_at >= start_of_day,
                BatchRunHistory.started_at < end_of_day,
                BatchRunHistory.completed_at.isnot(None)
            )
        )
    )
    metrics['avg_duration_minutes'] = float(result.scalar() or 0)

    # Job counts
    result = await db.execute(
        select(
            func.sum(BatchRunHistory.total_jobs),
            func.sum(BatchRunHistory.completed_jobs),
            func.sum(BatchRunHistory.failed_jobs)
        )
        .where(
            and_(
                BatchRunHistory.started_at >= start_of_day,
                BatchRunHistory.started_at < end_of_day
            )
        )
    )
    row = result.one()
    metrics['total_jobs'] = int(row[0]) if row[0] else 0
    metrics['total_completed_jobs'] = int(row[1]) if row[1] else 0
    metrics['total_failed_jobs'] = int(row[2]) if row[2] else 0

    return metrics


async def save_daily_metrics(
    db: AsyncSession,
    target_date: date,
    metrics: Dict[str, Any],
    category: str
) -> int:
    """
    Save aggregated metrics to daily_metrics table.
    Uses upsert to handle re-runs.

    Returns number of metrics saved.
    """
    saved_count = 0

    for metric_name, value in metrics.items():
        # Handle nested dicts (like model_breakdown) with dimensions
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                # Upsert metric
                stmt = pg_insert(DailyMetrics).values(
                    date=target_date,
                    metric_type=f"{category}.{metric_name}",
                    metric_value=Decimal(str(sub_value)),
                    dimensions={'key': sub_key}
                )
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_daily_metrics_date_type_dims',
                    set_={'metric_value': stmt.excluded.metric_value}
                )
                await db.execute(stmt)
                saved_count += 1
        else:
            # Convert to Decimal for storage
            if isinstance(value, (int, float)):
                decimal_value = Decimal(str(value))
            else:
                continue  # Skip non-numeric values

            # Upsert metric
            stmt = pg_insert(DailyMetrics).values(
                date=target_date,
                metric_type=f"{category}.{metric_name}",
                metric_value=decimal_value,
                dimensions={}
            )
            stmt = stmt.on_conflict_do_update(
                constraint='uq_daily_metrics_date_type_dims',
                set_={'metric_value': stmt.excluded.metric_value}
            )
            await db.execute(stmt)
            saved_count += 1

    return saved_count


async def aggregate_daily_metrics(
    db: AsyncSession,
    target_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Aggregate all metrics for a specific date (defaults to yesterday).

    Returns summary of aggregation results.
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    logger.info(f"Aggregating metrics for {target_date}")

    results = {
        'date': target_date.isoformat(),
        'metrics_saved': 0,
        'categories': {}
    }

    # Aggregate user activity
    user_metrics = await aggregate_user_activity_metrics(db, target_date)
    saved = await save_daily_metrics(db, target_date, user_metrics, 'user_activity')
    results['categories']['user_activity'] = {'metrics': len(user_metrics), 'saved': saved}
    results['metrics_saved'] += saved

    # Aggregate AI requests
    ai_metrics = await aggregate_ai_request_metrics(db, target_date)
    saved = await save_daily_metrics(db, target_date, ai_metrics, 'ai_requests')
    results['categories']['ai_requests'] = {'metrics': len(ai_metrics), 'saved': saved}
    results['metrics_saved'] += saved

    # Aggregate batch processing
    batch_metrics = await aggregate_batch_metrics(db, target_date)
    saved = await save_daily_metrics(db, target_date, batch_metrics, 'batch')
    results['categories']['batch'] = {'metrics': len(batch_metrics), 'saved': saved}
    results['metrics_saved'] += saved

    await db.commit()

    logger.info(f"Aggregation complete: {results['metrics_saved']} metrics saved")
    return results


async def cleanup_old_data(db: AsyncSession) -> Dict[str, int]:
    """
    Delete data older than retention period.

    Retention policy:
    - user_activity_events: 30 days
    - ai_request_metrics: 30 days
    - batch_run_history: 30 days
    - admin_sessions (expired): 7 days past expiration

    Returns count of deleted records per table.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    session_cutoff = datetime.utcnow() - timedelta(days=SESSION_RETENTION_DAYS)

    deleted = {}

    logger.info(f"Cleaning up data older than {cutoff_date.date()} ({RETENTION_DAYS} days)")

    # Clean user_activity_events
    result = await db.execute(
        delete(UserActivityEvent)
        .where(UserActivityEvent.created_at < cutoff_date)
    )
    deleted['user_activity_events'] = result.rowcount
    logger.info(f"Deleted {result.rowcount} user_activity_events")

    # Clean ai_request_metrics
    result = await db.execute(
        delete(AIRequestMetrics)
        .where(AIRequestMetrics.created_at < cutoff_date)
    )
    deleted['ai_request_metrics'] = result.rowcount
    logger.info(f"Deleted {result.rowcount} ai_request_metrics")

    # Clean batch_run_history
    result = await db.execute(
        delete(BatchRunHistory)
        .where(BatchRunHistory.created_at < cutoff_date)
    )
    deleted['batch_run_history'] = result.rowcount
    logger.info(f"Deleted {result.rowcount} batch_run_history")

    # Clean expired admin_sessions (7 days past expiration)
    result = await db.execute(
        delete(AdminSession)
        .where(AdminSession.expires_at < session_cutoff)
    )
    deleted['admin_sessions'] = result.rowcount
    logger.info(f"Deleted {result.rowcount} expired admin_sessions")

    await db.commit()

    total_deleted = sum(deleted.values())
    logger.info(f"Cleanup complete: {total_deleted} total records deleted")

    return deleted


async def run_admin_metrics_batch(
    aggregate_days: int = 1,
    run_cleanup: bool = True
) -> Dict[str, Any]:
    """
    Main entry point for admin metrics batch job.

    Args:
        aggregate_days: Number of days to aggregate (default: 1 = yesterday only)
        run_cleanup: Whether to run cleanup after aggregation (default: True)

    Returns:
        Summary of all operations performed.
    """
    logger.info("Starting admin metrics batch job")
    started_at = datetime.utcnow()

    result = {
        'started_at': started_at.isoformat(),
        'completed_at': None,
        'success': False,
        'aggregation': [],
        'cleanup': None,
        'errors': []
    }

    try:
        async with get_async_session() as db:
            # Aggregate metrics for specified days
            for days_ago in range(1, aggregate_days + 1):
                target_date = date.today() - timedelta(days=days_ago)
                try:
                    agg_result = await aggregate_daily_metrics(db, target_date)
                    result['aggregation'].append(agg_result)
                except Exception as e:
                    error_msg = f"Aggregation failed for {target_date}: {str(e)}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)

            # Run cleanup if requested
            if run_cleanup:
                try:
                    cleanup_result = await cleanup_old_data(db)
                    result['cleanup'] = cleanup_result
                except Exception as e:
                    error_msg = f"Cleanup failed: {str(e)}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)

            result['success'] = len(result['errors']) == 0

    except Exception as e:
        error_msg = f"Admin metrics batch job failed: {str(e)}"
        logger.error(error_msg)
        result['errors'].append(error_msg)

    completed_at = datetime.utcnow()
    result['completed_at'] = completed_at.isoformat()
    result['duration_seconds'] = (completed_at - started_at).total_seconds()

    logger.info(
        f"Admin metrics batch job completed in {result['duration_seconds']:.1f}s, "
        f"success={result['success']}, errors={len(result['errors'])}"
    )

    return result


async def get_aggregation_status(days: int = 7) -> Dict[str, Any]:
    """
    Get status of daily metrics aggregation.

    Returns:
        Summary of aggregation coverage and gaps.
    """
    async with get_async_session() as db:
        # Check which dates have been aggregated
        result = await db.execute(
            select(distinct(DailyMetrics.date))
            .where(DailyMetrics.date >= date.today() - timedelta(days=days))
            .order_by(DailyMetrics.date.desc())
        )
        aggregated_dates = [row[0] for row in result.all()]

        # Find gaps
        expected_dates = [date.today() - timedelta(days=i) for i in range(1, days + 1)]
        missing_dates = [d for d in expected_dates if d not in aggregated_dates]

        # Get total metric count
        result = await db.execute(
            select(func.count(DailyMetrics.id))
        )
        total_metrics = result.scalar() or 0

        return {
            'total_metrics': total_metrics,
            'days_checked': days,
            'aggregated_dates': [d.isoformat() for d in aggregated_dates],
            'missing_dates': [d.isoformat() for d in missing_dates],
            'coverage_percent': (len(aggregated_dates) / days) * 100 if days > 0 else 0
        }


async def get_retention_status() -> Dict[str, Any]:
    """
    Get status of data retention (oldest records per table).

    Returns:
        Summary of oldest data and retention compliance.
    """
    async with get_async_session() as db:
        cutoff_date = datetime.utcnow() - timedelta(days=RETENTION_DAYS)

        status = {
            'retention_days': RETENTION_DAYS,
            'cutoff_date': cutoff_date.date().isoformat(),
            'tables': {}
        }

        # Check each table
        tables = [
            ('user_activity_events', UserActivityEvent, UserActivityEvent.created_at),
            ('ai_request_metrics', AIRequestMetrics, AIRequestMetrics.created_at),
            ('batch_run_history', BatchRunHistory, BatchRunHistory.created_at),
        ]

        for table_name, model, date_col in tables:
            # Oldest record
            result = await db.execute(
                select(func.min(date_col))
            )
            oldest = result.scalar()

            # Count of records older than cutoff
            result = await db.execute(
                select(func.count(model.id))
                .where(date_col < cutoff_date)
            )
            old_count = result.scalar() or 0

            # Total count
            result = await db.execute(
                select(func.count(model.id))
            )
            total_count = result.scalar() or 0

            status['tables'][table_name] = {
                'oldest_record': oldest.isoformat() if oldest else None,
                'records_past_retention': old_count,
                'total_records': total_count,
                'compliant': old_count == 0
            }

        # Check expired sessions
        session_cutoff = datetime.utcnow() - timedelta(days=SESSION_RETENTION_DAYS)
        result = await db.execute(
            select(func.count(AdminSession.id))
            .where(AdminSession.expires_at < session_cutoff)
        )
        expired_sessions = result.scalar() or 0

        result = await db.execute(
            select(func.count(AdminSession.id))
        )
        total_sessions = result.scalar() or 0

        status['tables']['admin_sessions'] = {
            'expired_sessions': expired_sessions,
            'total_sessions': total_sessions,
            'session_retention_days': SESSION_RETENTION_DAYS,
            'compliant': expired_sessions == 0
        }

        # Overall compliance
        status['all_compliant'] = all(
            t.get('compliant', True) for t in status['tables'].values()
        )

        return status
