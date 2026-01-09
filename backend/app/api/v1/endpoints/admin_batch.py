"""
Admin API endpoints for batch processing control
Simplified real-time monitoring endpoints
"""
from typing import Optional, Dict, Any
from datetime import timedelta, date
from uuid import uuid4
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_db
from app.core.admin_dependencies import get_current_admin, CurrentAdmin
from app.core.trading_calendar import get_most_recent_trading_day
from app.database import AsyncSessionLocal
from app.batch.batch_orchestrator import batch_orchestrator
from app.batch.batch_run_tracker import batch_run_tracker, CurrentBatchRun
from app.batch.market_data_collector import market_data_collector
from app.core.logging import get_logger
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/batch", tags=["Admin - Batch Processing"])


async def _run_market_data_refresh_with_session():
    """
    Helper function to run market data refresh with its own database session.
    Required because BackgroundTasks closes the request's db session before task runs.
    """
    async with AsyncSessionLocal() as session:
        try:
            # V3: Use market_data_collector directly
            await market_data_collector.collect_all_market_data(session)
            logger.info("Background market data refresh completed successfully")
        except Exception as e:
            logger.error(f"Background market data refresh failed: {e}", exc_info=True)
            await session.rollback()
        finally:
            await session.close()


async def _run_admin_batch_with_tracker_cleanup(
    start_date: Optional[date],
    end_date: Optional[date],
    portfolio_ids: Optional[list],
    portfolio_id: Optional[str],
    force_rerun: bool,
):
    """
    Wrapper to run batch processing with guaranteed batch_run_tracker cleanup.

    CRITICAL: The caller (admin endpoint) calls batch_run_tracker.start(),
    so we MUST call batch_run_tracker.complete() in a finally block to prevent
    the tracker from being stuck "running" forever.
    """
    try:
        result = await batch_orchestrator.run_daily_batch_with_backfill(
            start_date=start_date,
            end_date=end_date,
            portfolio_ids=portfolio_ids,
            portfolio_id=portfolio_id,
            source="admin",
            force_rerun=force_rerun,
        )
        logger.info(f"Admin batch completed: {result.get('dates_processed', 0)} dates processed")
        return result
    except Exception as e:
        logger.error(f"Admin batch failed: {e}", exc_info=True)
        raise
    finally:
        # CRITICAL: Always clear batch_run_tracker, even on exception
        batch_run_tracker.complete()
        logger.debug("Batch run tracker cleared (admin batch wrapper)")


@router.post("/run")
async def run_batch_processing(
    background_tasks: BackgroundTasks,
    admin_user: CurrentAdmin = Depends(get_current_admin),
    portfolio_id: Optional[str] = Query(None, description="Specific portfolio ID or all"),
    force: bool = Query(False, description="Force run even if batch already running"),
    force_rerun: bool = Query(False, description="Force reprocess dates even if snapshots exist (repair partial runs)"),
    start_date: Optional[date] = Query(None, description="Start date for reprocessing (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for reprocessing (YYYY-MM-DD, defaults to today)")
):
    """
    Trigger batch processing with real-time tracking.

    Returns batch_run_id for status polling via GET /admin/batch/run/current.
    Prevents concurrent runs unless force=True.

    **Force Rerun Mode (force_rerun=True):**
    Use this to repair partial batch runs where snapshots exist but later phases
    (market values, sector tags, analytics) didn't complete due to crashes/deploys.

    When force_rerun=True:
    - Bypasses snapshot existence checks
    - Reprocesses all dates in the specified range
    - Re-runs ALL phases for each date (Phases 2-6)

    **Date Range:**
    - start_date: Beginning of reprocess range (required for force_rerun)
    - end_date: End of reprocess range (defaults to today)
    """
    # Check if batch already running
    if batch_run_tracker.get_current() and not force:
        raise HTTPException(
            status_code=409,
            detail="Batch already running. Use force=true to override."
        )

    # Validate force_rerun parameters
    if force_rerun and not start_date:
        raise HTTPException(
            status_code=400,
            detail="start_date is required when using force_rerun=true"
        )

    # Validate date parameters are only used with force_rerun
    # Prevents silent ignoring of user-provided dates
    if not force_rerun and (start_date or end_date):
        raise HTTPException(
            status_code=400,
            detail="start_date and end_date are only supported with force_rerun=true. "
                   "Normal batch runs process only the most recent trading day."
        )

    # Create new batch run
    batch_run_id = str(uuid4())
    run = CurrentBatchRun(
        batch_run_id=batch_run_id,
        started_at=utc_now(),
        triggered_by=admin_user.email
    )

    batch_run_tracker.start(run)

    # Get most recent trading day for calculations (handles weekends/holidays)
    calculation_date = get_most_recent_trading_day()

    # Determine effective date range
    # For normal runs (force_rerun=False): default to single-date (most recent trading day)
    # For force_rerun=True: use provided start_date (required) and end_date
    if force_rerun:
        effective_start = start_date
        effective_end = end_date  # None = today
        mode = "FORCE_RERUN"
        logger.warning(
            f"FORCE_RERUN: Reprocessing dates {start_date} to {end_date or 'today'} "
            f"(bypassing snapshot checks)"
        )
    else:
        # Normal mode: single-date processing (most recent trading day)
        effective_start = calculation_date
        effective_end = calculation_date
        mode = "normal (single-date)"

    logger.info(
        f"Admin {admin_user.email} triggered batch run {batch_run_id} "
        f"for portfolio {portfolio_id or 'all'} "
        f"(mode: {mode}, dates: {effective_start} to {effective_end or 'today'})"
    )

    # Execute in background with tracker cleanup wrapper
    background_tasks.add_task(
        _run_admin_batch_with_tracker_cleanup,
        effective_start,  # start_date
        effective_end,    # end_date
        [portfolio_id] if portfolio_id else None,  # portfolio_ids
        portfolio_id if portfolio_id else None,    # portfolio_id (single mode)
        force_rerun,      # force_rerun
    )

    return {
        "status": "started",
        "batch_run_id": batch_run_id,
        "portfolio_id": portfolio_id or "all",
        "force_rerun": force_rerun,
        "date_range": {
            "start": str(effective_start),
            "end": str(effective_end) if effective_end else "today"
        },
        "triggered_by": admin_user.email,
        "timestamp": utc_now(),
        "poll_url": "/api/v1/admin/batch/run/current"
    }


@router.get("/run/current")
async def get_current_batch_status(
    admin_user: CurrentAdmin = Depends(get_current_admin)
):
    """
    Get status of currently running batch process.

    Returns "idle" if no batch running.
    Designed for polling every 2-5 seconds.
    """
    current = batch_run_tracker.get_current()

    if not current:
        return {
            "status": "idle",
            "batch_run_id": None,
            "message": "No batch processing currently running"
        }

    elapsed = (utc_now() - current.started_at).total_seconds()
    progress = (
        (current.completed_jobs / current.total_jobs * 100)
        if current.total_jobs > 0
        else 0
    )

    return {
        "status": "running",
        "batch_run_id": current.batch_run_id,
        "started_at": current.started_at.isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "triggered_by": current.triggered_by,
        "jobs": {
            "total": current.total_jobs,
            "completed": current.completed_jobs,
            "failed": current.failed_jobs,
            "pending": current.total_jobs - current.completed_jobs - current.failed_jobs
        },
        "current_job": current.current_job_name,
        "current_portfolio": current.current_portfolio_name,
        "progress_percent": round(progress, 1)
    }


@router.post("/trigger/market-data")
async def trigger_market_data_update(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    admin_user: CurrentAdmin = Depends(get_current_admin)
):
    """
    Manually trigger market data update for all symbols.
    """
    logger.info(f"Admin {admin_user.email} triggered market data update")

    # V3: Use wrapper function with own session
    background_tasks.add_task(_run_market_data_refresh_with_session)

    return {
        "status": "started",
        "message": "Market data update started",
        "triggered_by": admin_user.email,
        "timestamp": utc_now()
    }


@router.post("/trigger/correlations")
async def trigger_correlation_calculation(
    background_tasks: BackgroundTasks,
    portfolio_id: Optional[str] = Query(None, description="Specific portfolio ID or all"),
    db: AsyncSession = Depends(get_db),
    admin_user: CurrentAdmin = Depends(get_current_admin)
):
    """
    Manually trigger correlation calculations (normally runs as part of batch).
    """
    logger.info(f"Admin {admin_user.email} triggered batch for portfolio {portfolio_id or 'all'}")

    # V3: Correlations run as part of Phase 3 analytics automatically
    background_tasks.add_task(
        batch_orchestrator.run_daily_batch_sequence,
        None,  # calculation_date (None = today)
        [portfolio_id] if portfolio_id else None,  # portfolio_ids list
        db
    )

    return {
        "status": "started",
        "message": f"Batch processing started for {'portfolio ' + portfolio_id if portfolio_id else 'all portfolios'}",
        "triggered_by": admin_user.email,
        "timestamp": utc_now()
    }


@router.post("/trigger/company-profiles")
async def trigger_company_profile_sync(
    background_tasks: BackgroundTasks,
    admin_user: CurrentAdmin = Depends(get_current_admin)
):
    """
    Manually trigger company profile synchronization (normally runs daily at 7 PM ET).
    Fetches company names, sectors, industries, and revenue/earnings estimates from yfinance + yahooquery.
    """
    from app.batch.scheduler_config import batch_scheduler

    logger.info(f"Admin {admin_user.email} triggered company profile sync")

    background_tasks.add_task(batch_scheduler.trigger_company_profile_sync)

    return {
        "status": "started",
        "message": "Company profile sync started for all portfolio symbols",
        "triggered_by": admin_user.email,
        "timestamp": utc_now(),
        "info": "This will fetch company data from yfinance and yahooquery APIs"
    }


@router.post("/restore-sector-tags")
async def restore_sector_tags(
    background_tasks: BackgroundTasks,
    portfolio_id: Optional[str] = Query(None, description="Specific portfolio ID or all portfolios"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually restore sector tags for all positions based on company profile data.

    This endpoint:
    1. Removes existing sector tags (identified by "Sector:" in description)
    2. Re-applies sector tags based on current company profile sectors
    3. Creates new sector tags as needed with appropriate colors

    Use this when:
    - Company profile data has been updated
    - Sector classifications have changed
    - You want to ensure all positions have current sector tags
    """
    from app.services.sector_tag_service import restore_sector_tags_for_portfolio
    from app.models.users import Portfolio
    from uuid import UUID

    logger.info(
        f"Admin {admin_user.email} triggered sector tag restoration "
        f"for portfolio {portfolio_id or 'all'}"
    )

    try:
        if portfolio_id:
            # Restore tags for specific portfolio
            portfolio_uuid = UUID(portfolio_id)

            # Get portfolio and verify access
            portfolio_result = await db.execute(
                select(Portfolio).where(Portfolio.id == portfolio_uuid)
            )
            portfolio = portfolio_result.scalar_one_or_none()

            if not portfolio:
                raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")

            # Restore sector tags for this portfolio
            result = await restore_sector_tags_for_portfolio(
                db=db,
                portfolio_id=portfolio.id,
                user_id=portfolio.user_id
            )

            return {
                "status": "completed",
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio.name,
                "positions_tagged": result.get('positions_tagged', 0),
                "positions_skipped": result.get('positions_skipped', 0),
                "tags_created": result.get('tags_created', 0),
                "tags_applied": result.get('tags_applied', []),
                "triggered_by": admin_user.email,
                "timestamp": utc_now()
            }

        else:
            # Restore tags for all portfolios
            portfolios_result = await db.execute(
                select(Portfolio).where(Portfolio.deleted_at.is_(None))
            )
            portfolios = portfolios_result.scalars().all()

            total_positions_tagged = 0
            total_positions_skipped = 0
            total_tags_created = 0
            portfolios_processed = 0

            for portfolio in portfolios:
                try:
                    result = await restore_sector_tags_for_portfolio(
                        db=db,
                        portfolio_id=portfolio.id,
                        user_id=portfolio.user_id
                    )

                    total_positions_tagged += result.get('positions_tagged', 0)
                    total_positions_skipped += result.get('positions_skipped', 0)
                    total_tags_created += result.get('tags_created', 0)
                    portfolios_processed += 1

                except Exception as e:
                    logger.error(f"Error restoring sector tags for portfolio {portfolio.name}: {e}")
                    # Continue to next portfolio

            return {
                "status": "completed",
                "portfolios_processed": portfolios_processed,
                "total_portfolios": len(portfolios),
                "positions_tagged": total_positions_tagged,
                "positions_skipped": total_positions_skipped,
                "tags_created": total_tags_created,
                "triggered_by": admin_user.email,
                "timestamp": utc_now()
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring sector tags: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error restoring sector tags: {str(e)}"
        )


@router.post("/cleanup-incomplete")
async def cleanup_incomplete_snapshots_endpoint(
    age_threshold_hours: int = Query(1, description="Delete incomplete snapshots older than this (hours)"),
    portfolio_id: Optional[str] = Query(None, description="Specific portfolio ID or all portfolios"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Clean up incomplete snapshots (Phase 2.10 idempotency fix).

    Removes placeholder snapshots that were created by crashed batch processes.
    These placeholders have is_complete=False and block retries due to unique constraint.

    **Use Cases:**
    - Batch process crashed mid-calculation, leaving placeholder snapshots
    - Need to retry batch processing for a specific date
    - Automated cleanup before batch runs

    **Safety:**
    - Only deletes snapshots with is_complete=False
    - Only deletes snapshots older than age_threshold_hours (default: 1 hour)
    - Logs all deletions for audit trail

    **Example:**
    - `POST /api/v1/admin/batch/cleanup-incomplete?age_threshold_hours=2`
    - Deletes incomplete snapshots older than 2 hours
    """
    from app.calculations.snapshots import cleanup_incomplete_snapshots
    from uuid import UUID

    logger.info(
        f"Admin {admin_user.email} triggered incomplete snapshot cleanup "
        f"(age > {age_threshold_hours}h) for portfolio {portfolio_id or 'all'}"
    )

    try:
        portfolio_uuid = UUID(portfolio_id) if portfolio_id else None

        result = await cleanup_incomplete_snapshots(
            db=db,
            age_threshold_hours=age_threshold_hours,
            portfolio_id=portfolio_uuid
        )

        return {
            "status": "completed",
            "incomplete_found": result['incomplete_found'],
            "incomplete_deleted": result['incomplete_deleted'],
            "deleted_ids": [str(id) for id in result['deleted_ids']],
            "age_threshold_hours": age_threshold_hours,
            "portfolio_id": portfolio_id or "all",
            "triggered_by": admin_user.email,
            "timestamp": utc_now()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid portfolio ID: {str(e)}")
    except Exception as e:
        logger.error(f"Error cleaning up incomplete snapshots: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up incomplete snapshots: {str(e)}"
        )


# Note: data-quality endpoints removed - data_quality module was deleted
# Batch orchestrator handles data quality internally via market_data_collector


# =============================================================================
# Batch History Endpoints (Phase 5 Admin Dashboard)
# =============================================================================

@router.get("/history")
async def get_batch_history(
    days: int = Query(30, ge=1, le=90, description="Number of days of history to return"),
    status: Optional[str] = Query(None, description="Filter by status (completed, failed, partial)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get historical batch processing runs.

    Returns batch run history for the admin dashboard, ordered by most recent first.
    Includes status, job counts, phase durations, and error summaries.

    **Query Parameters:**
    - days: Number of days of history (default: 30, max: 90)
    - status: Filter by status (completed, failed, partial)
    - limit: Maximum records to return (default: 50, max: 200)

    **Use Cases:**
    - View recent batch processing performance
    - Identify failed batch runs
    - Analyze phase timing trends
    """
    from app.models.admin import BatchRunHistory
    from sqlalchemy import desc
    from datetime import datetime, timedelta

    try:
        # Build query
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = select(BatchRunHistory).where(
            BatchRunHistory.created_at >= cutoff_date
        )

        if status:
            query = query.where(BatchRunHistory.status == status)

        query = query.order_by(desc(BatchRunHistory.started_at)).limit(limit)

        result = await db.execute(query)
        runs = result.scalars().all()

        return {
            "success": True,
            "total_count": len(runs),
            "days": days,
            "status_filter": status,
            "runs": [
                {
                    "id": str(run.id),
                    "batch_run_id": run.batch_run_id,
                    "triggered_by": run.triggered_by,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "status": run.status,
                    "total_jobs": run.total_jobs,
                    "completed_jobs": run.completed_jobs,
                    "failed_jobs": run.failed_jobs,
                    "duration_seconds": (
                        (run.completed_at - run.started_at).total_seconds()
                        if run.completed_at and run.started_at
                        else None
                    ),
                    "phase_durations": run.phase_durations,
                    "has_errors": run.error_summary is not None,
                }
                for run in runs
            ]
        }

    except Exception as e:
        logger.error(f"Error fetching batch history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching batch history: {str(e)}"
        )


@router.get("/history/summary")
async def get_batch_history_summary(
    days: int = Query(30, ge=1, le=90, description="Number of days to summarize"),
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary statistics of batch processing history.

    Provides aggregated metrics for the admin dashboard overview:
    - Total runs
    - Success/failure/partial counts
    - Average duration
    - Recent trend

    **Query Parameters:**
    - days: Number of days to summarize (default: 30, max: 90)

    NOTE: This route must be defined BEFORE /history/{batch_run_id} to avoid
    FastAPI matching "summary" as a batch_run_id parameter.
    """
    from app.models.admin import BatchRunHistory
    from sqlalchemy import func
    from datetime import datetime, timedelta

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Get status counts
        status_query = select(
            BatchRunHistory.status,
            func.count(BatchRunHistory.id).label('count')
        ).where(
            BatchRunHistory.created_at >= cutoff_date
        ).group_by(BatchRunHistory.status)

        status_result = await db.execute(status_query)
        status_counts = {row[0]: row[1] for row in status_result.all()}

        # Get average duration for completed runs
        duration_query = select(
            func.avg(
                func.extract('epoch', BatchRunHistory.completed_at - BatchRunHistory.started_at)
            )
        ).where(
            BatchRunHistory.created_at >= cutoff_date,
            BatchRunHistory.completed_at.isnot(None),
            BatchRunHistory.status == 'completed'
        )

        duration_result = await db.execute(duration_query)
        avg_duration = duration_result.scalar_one_or_none()

        # Get most recent run
        recent_query = select(BatchRunHistory).order_by(
            BatchRunHistory.started_at.desc()
        ).limit(1)
        recent_result = await db.execute(recent_query)
        recent_run = recent_result.scalar_one_or_none()

        total_runs = sum(status_counts.values())
        completed_count = status_counts.get('completed', 0)
        success_rate = (
            round(completed_count / total_runs * 100, 1)
            if total_runs > 0
            else 100.0
        )

        return {
            "period_days": days,
            "total_runs": total_runs,
            "status_breakdown": {
                "completed": status_counts.get('completed', 0),
                "failed": status_counts.get('failed', 0),
                "partial": status_counts.get('partial', 0),
                "running": status_counts.get('running', 0),
            },
            "success_rate_percent": success_rate,
            "avg_duration_seconds": round(avg_duration, 1) if avg_duration else None,
            "most_recent": {
                "batch_run_id": recent_run.batch_run_id if recent_run else None,
                "status": recent_run.status if recent_run else None,
                "started_at": recent_run.started_at.isoformat() if recent_run and recent_run.started_at else None,
            } if recent_run else None,
        }

    except Exception as e:
        logger.error(f"Error fetching batch history summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching batch history summary: {str(e)}"
        )


@router.get("/history/{batch_run_id}")
async def get_batch_run_details(
    batch_run_id: str,
    admin_user: CurrentAdmin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific batch run.

    Returns complete information about a batch run including full error details.

    **Path Parameters:**
    - batch_run_id: The batch run identifier (e.g., "batch_20251222_143000")
    """
    from app.models.admin import BatchRunHistory

    try:
        result = await db.execute(
            select(BatchRunHistory).where(
                BatchRunHistory.batch_run_id == batch_run_id
            )
        )
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(
                status_code=404,
                detail=f"Batch run '{batch_run_id}' not found"
            )

        return {
            "id": str(run.id),
            "batch_run_id": run.batch_run_id,
            "triggered_by": run.triggered_by,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "status": run.status,
            "jobs": {
                "total": run.total_jobs,
                "completed": run.completed_jobs,
                "failed": run.failed_jobs,
                "success_rate": (
                    round(run.completed_jobs / run.total_jobs * 100, 1)
                    if run.total_jobs > 0
                    else 100.0
                )
            },
            "duration_seconds": (
                (run.completed_at - run.started_at).total_seconds()
                if run.completed_at and run.started_at
                else None
            ),
            "phase_durations": run.phase_durations,
            "error_summary": run.error_summary,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching batch run details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching batch run details: {str(e)}"
        )
