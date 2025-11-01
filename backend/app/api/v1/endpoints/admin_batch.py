"""
Admin API endpoints for batch processing control
Simplified real-time monitoring endpoints
"""
from typing import Optional, Dict, Any
from datetime import timedelta
from uuid import uuid4
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.dependencies import get_db, require_admin
from app.database import AsyncSessionLocal
from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3 as batch_orchestrator
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
    admin_user = Depends(require_admin)
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
    admin_user = Depends(require_admin)
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
    admin_user = Depends(require_admin),
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


# Note: data-quality endpoints removed - data_quality module was deleted
# V3 batch orchestrator handles data quality internally via market_data_collector