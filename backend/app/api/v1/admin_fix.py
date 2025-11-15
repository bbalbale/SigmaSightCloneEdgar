"""
Admin Fix Endpoint - Railway Production Data Fix
Provides HTTP endpoint to trigger data fix operations on Railway
"""
import asyncio
import uuid
from typing import Optional
from datetime import date as date_type
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.core.dependencies import get_current_user
from app.models.users import User, Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.db.seed_demo_portfolios import create_demo_users, seed_demo_portfolios
from app.batch.batch_orchestrator import batch_orchestrator
from app.core.logging import get_logger
from app.services.admin_fix_service import clear_calculations_comprehensive
from app.services.background_job_tracker import job_tracker

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/fix", tags=["admin-fix"])


async def _run_fix_all_background(
    job_id: str,
    start_date: Optional[date_type] = None,
    end_date: Optional[date_type] = None
):
    """Background task to run the complete fix workflow"""
    try:
        job_tracker.start_job(job_id)
        logger.info(f"[Job {job_id}] Starting background fix")

        async with AsyncSessionLocal() as db:
            # Step 1: Clear calculations
            logger.info(f"[Job {job_id}] Step 1/3: Clearing analytics tables...")
            job_tracker.update_progress(job_id, "Clearing analytics tables...")

            clear_results = await clear_calculations_comprehensive(db)
            await db.commit()

            step1_cleared = (
                clear_results.get("grand_total_deleted")
                or clear_results.get("total_deleted")
                or clear_results.get("total_cleared")
                or 0
            )
            logger.info(f"[Job {job_id}] ✓ Cleared {step1_cleared} calculation records")

            # Step 2: Seed portfolios
            logger.info(f"[Job {job_id}] Step 2/3: Seeding portfolios...")
            job_tracker.update_progress(job_id, "Seeding portfolios...")

            await create_demo_users(db)
            await seed_demo_portfolios(db)
            await db.commit()

            portfolio_count = await db.execute(select(func.count(Portfolio.id)))
            total_portfolios = portfolio_count.scalar()
            logger.info(f"[Job {job_id}] ✓ Seeded {total_portfolios} portfolios")

            # Step 3: Run batch processing
            logger.info(f"[Job {job_id}] Step 3/3: Running batch processing...")
            job_tracker.update_progress(job_id, "Running batch processing...")

            batch_result = await batch_orchestrator.run_daily_batch_with_backfill(
                start_date=start_date,
                end_date=end_date
            )

            logger.info(f"[Job {job_id}] ✓ Batch complete")

            # Mark job as complete
            result = {
                "step1_clear": {
                    "total_cleared": step1_cleared
                },
                "step2_seed": {
                    "total_portfolios": total_portfolios
                },
                "step3_batch": batch_result
            }
            job_tracker.complete_job(job_id, result)
            logger.info(f"[Job {job_id}] Complete fix finished successfully")

    except Exception as e:
        logger.error(f"[Job {job_id}] Error during fix: {e}", exc_info=True)
        job_tracker.fail_job(job_id, str(e))



@router.post("/clear-calculations")
async def clear_calculations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clear all derived analytics tables (snapshots, Greeks, factor exposures,
    betas, volatility, scenarios, correlations) without touching raw market data.
    """
    try:
        logger.info("Starting comprehensive calculation clearing...")
        results = await clear_calculations_comprehensive(db)
        await db.commit()

        total_cleared = (
            results.get("grand_total_deleted")
            or results.get("total_deleted")
            or results.get("total_cleared")
            or 0
        )
        logger.info(f"✓ Cleared {total_cleared} calculation records")

        payload = {
            "success": True,
            "message": f"Cleared {total_cleared} calculation records (including cleanup)",
            "details": results,
        }
        return JSONResponse(content=jsonable_encoder(payload))

    except Exception as e:
        await db.rollback()
        logger.error(f"Error clearing calculations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear calculations: {str(e)}")


@router.post("/seed-portfolios")
async def seed_portfolios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Seed demo portfolios with corrected June 30, 2025 market data
    Smart seeding - won't duplicate existing positions
    """
    try:
        logger.info("Seeding demo portfolios...")

        # Create demo users
        await create_demo_users(db)

        # Seed portfolios
        await seed_demo_portfolios(db)

        await db.commit()

        # Count portfolios
        portfolio_count = await db.execute(select(func.count(Portfolio.id)))
        total_portfolios = portfolio_count.scalar()

        logger.info(f"✓ Seeded {total_portfolios} portfolios")

        return {
            "success": True,
            "message": f"Seeded {total_portfolios} portfolios with corrected data",
            "details": {
                "total_portfolios": total_portfolios,
                "expected_positions": {
                    "demo_individual": 16,
                    "demo_hnw": 39,
                    "demo_hedgefund": 30,
                    "demo_familyoffice_public": 12,
                    "demo_familyoffice_private": 9
                }
            }
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error seeding portfolios: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to seed portfolios: {str(e)}")


@router.post("/run-batch")
async def run_batch(
    current_user: User = Depends(get_current_user)
):
    """
    Run batch processing with automatic backfill
    7-phase processing: company profiles, market data, fundamentals, P&L, market values, sector tags, analytics
    """
    try:
        logger.info("Running batch processing with backfill...")

        # Run batch orchestrator
        result = await batch_orchestrator.run_daily_batch_with_backfill()

        logger.info(f"✓ Batch processing completed: {result.get('message', 'Success')}")

        return {
            "success": True,
            "message": "Batch processing completed",
            "details": result
        }

    except Exception as e:
        logger.error(f"Error running batch processing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run batch processing: {str(e)}")


@router.post("/fix-all")
async def fix_all(
    background_tasks: BackgroundTasks,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Complete fix: clear calculations, seed portfolios, run batch processing

    Returns immediately with a job_id. Poll /admin/fix/jobs/{job_id} for status.

    Args:
        start_date: Optional start date for batch backfill (YYYY-MM-DD)
        end_date: Optional end date for batch processing (YYYY-MM-DD), defaults to today

    Returns:
        {
            "job_id": "uuid",
            "message": "Fix job started",
            "status_url": "/api/v1/admin/fix/jobs/{job_id}"
        }
    """
    # Parse optional date parameters
    parsed_start_date = None
    parsed_end_date = None

    if start_date:
        try:
            parsed_start_date = date_type.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid start_date format: {start_date}. Use YYYY-MM-DD")

    if end_date:
        try:
            parsed_end_date = date_type.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid end_date format: {end_date}. Use YYYY-MM-DD")

    # Create job
    job_id = str(uuid.uuid4())
    job_tracker.create_job(
        job_id=job_id,
        job_type="fix-all",
        params={
            "start_date": start_date,
            "end_date": end_date
        }
    )

    # Start background task
    background_tasks.add_task(
        _run_fix_all_background,
        job_id=job_id,
        start_date=parsed_start_date,
        end_date=parsed_end_date
    )

    logger.info(f"Started fix-all job {job_id} (start_date={start_date}, end_date={end_date})")

    return JSONResponse(content={
        "success": True,
        "job_id": job_id,
        "message": "Fix job started in background",
        "status_url": f"/api/v1/admin/fix/jobs/{job_id}"
    })


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of a background fix job

    Returns:
        {
            "job_id": "uuid",
            "status": "pending|running|completed|failed",
            "progress": "Current step description",
            "result": {...},  # Only if completed
            "error": "...",   # Only if failed
            "created_at": "ISO timestamp",
            "started_at": "ISO timestamp",
            "completed_at": "ISO timestamp"
        }
    """
    job = job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JSONResponse(content=jsonable_encoder(job))
