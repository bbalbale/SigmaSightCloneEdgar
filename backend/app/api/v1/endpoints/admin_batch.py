"""
Admin API endpoints for batch processing control
Simplified real-time monitoring endpoints
"""
from typing import Optional, Dict, Any
from datetime import timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_admin
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2 as batch_orchestrator
from app.batch.batch_run_tracker import batch_run_tracker, CurrentBatchRun
from app.batch.data_quality import pre_flight_validation
from app.core.logging import get_logger
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/batch", tags=["Admin - Batch Processing"])


@router.post("/run")
async def run_batch_processing(
    background_tasks: BackgroundTasks,
    admin_user = Depends(require_admin),
    portfolio_id: Optional[str] = Query(None, description="Specific portfolio ID or all"),
    force: bool = Query(False, description="Force run even if batch already running")
):
    """
    Trigger batch processing with real-time tracking.

    Returns batch_run_id for status polling via GET /admin/batch/run/current.
    Prevents concurrent runs unless force=True.
    """
    # Check if batch already running
    if batch_run_tracker.get_current() and not force:
        raise HTTPException(
            status_code=409,
            detail="Batch already running. Use force=true to override."
        )

    # Create new batch run
    batch_run_id = str(uuid4())
    run = CurrentBatchRun(
        batch_run_id=batch_run_id,
        started_at=utc_now(),
        triggered_by=admin_user.email
    )

    batch_run_tracker.start(run)

    logger.info(
        f"Admin {admin_user.email} triggered batch run {batch_run_id} "
        f"for portfolio {portfolio_id or 'all'}"
    )

    # Execute in background with tracking
    background_tasks.add_task(
        batch_orchestrator.run_daily_batch_sequence,
        portfolio_id
    )

    return {
        "status": "started",
        "batch_run_id": batch_run_id,
        "portfolio_id": portfolio_id or "all",
        "triggered_by": admin_user.email,
        "timestamp": utc_now(),
        "poll_url": "/api/v1/admin/batch/run/current"
    }


@router.get("/run/current")
async def get_current_batch_status(
    admin_user = Depends(require_admin)
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
    admin_user = Depends(require_admin)
):
    """
    Manually trigger market data update for all symbols.
    """
    from app.batch.market_data_sync import sync_market_data
    
    logger.info(f"Admin {admin_user.email} triggered market data update")
    
    background_tasks.add_task(sync_market_data)
    
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
    admin_user = Depends(require_admin)
):
    """
    Manually trigger correlation calculations (normally runs weekly on Tuesday).
    """
    logger.info(f"Admin {admin_user.email} triggered correlations for portfolio {portfolio_id or 'all'}")
    
    background_tasks.add_task(
        batch_orchestrator.run_daily_batch_sequence,
        portfolio_id,
        True  # run_correlations=True
    )
    
    return {
        "status": "started",
        "message": f"Correlation calculation started for {'portfolio ' + portfolio_id if portfolio_id else 'all portfolios'}",
        "triggered_by": admin_user.email,
        "timestamp": utc_now()
    }


@router.get("/data-quality")
async def get_data_quality_status(
    portfolio_id: Optional[str] = Query(None, description="Specific portfolio ID or all portfolios"),
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """
    Get data quality status and metrics for portfolios.
    Provides pre-flight validation results without running batch processing.
    """
    logger.info(f"Admin {admin_user.email} requested data quality status for portfolio {portfolio_id or 'all'}")
    
    try:
        # Run data quality validation
        validation_results = await pre_flight_validation(db, portfolio_id)
        
        # Add admin metadata
        validation_results['requested_by'] = admin_user.email
        validation_results['request_timestamp'] = utc_now()
        
        logger.info(
            f"Data quality check completed for admin {admin_user.email}: "
            f"score {validation_results.get('quality_score', 0):.1%}"
        )
        
        return validation_results
        
    except Exception as e:
        logger.error(f"Data quality check failed for admin {admin_user.email}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Data quality validation failed: {str(e)}"
        )


@router.post("/data-quality/refresh")
async def refresh_market_data_for_quality(
    background_tasks: BackgroundTasks,
    portfolio_id: Optional[str] = Query(None, description="Specific portfolio ID or all portfolios"),
    db: AsyncSession = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """
    Refresh market data to improve data quality scores.
    Runs market data sync in the background based on data quality recommendations.
    """
    logger.info(f"Admin {admin_user.email} requested market data refresh for data quality improvement")
    
    # First, check current data quality to identify what needs refreshing
    validation_results = await pre_flight_validation(db, portfolio_id)
    recommendations = validation_results.get('recommendations', [])
    
    if not recommendations or 'within acceptable thresholds' in recommendations[0]:
        return {
            "status": "no_action_needed",
            "message": "Data quality is already within acceptable thresholds",
            "current_quality_score": validation_results.get('quality_score', 0),
            "requested_by": admin_user.email,
            "timestamp": utc_now()
        }
    
    # Run market data sync in background
    background_tasks.add_task(
        batch_orchestrator._update_market_data,
        db
    )
    
    logger.info(
        f"Market data refresh initiated by admin {admin_user.email} "
        f"(current quality: {validation_results.get('quality_score', 0):.1%})"
    )
    
    return {
        "status": "refresh_started",
        "message": "Market data refresh started to improve data quality",
        "current_quality_score": validation_results.get('quality_score', 0),
        "recommendations": recommendations[:3],  # Show top 3 recommendations
        "requested_by": admin_user.email,
        "timestamp": utc_now()
    }