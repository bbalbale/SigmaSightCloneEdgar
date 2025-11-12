"""
Admin Fix Endpoint - Railway Production Data Fix
Provides HTTP endpoint to trigger data fix operations on Railway
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.users import User, Portfolio
from app.db.seed_demo_portfolios import create_demo_users, seed_demo_portfolios
from app.batch.batch_orchestrator import batch_orchestrator
from app.core.logging import get_logger
from app.services.admin_fix_service import clear_calculations_comprehensive

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/fix", tags=["admin-fix"])


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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Complete fix: clear calculations, seed portfolios, run batch processing
    All-in-one endpoint for Railway production data fix
    """
    try:
        logger.info("=" * 80)
        logger.info("STARTING COMPLETE RAILWAY DATA FIX")
        logger.info("=" * 80)

        results = {}

        # Step 1: Clear calculations
        logger.info("\nStep 1/3: Clearing analytics tables...")
        clear_results = await clear_calculations_comprehensive(db)
        await db.commit()

        results["step1_clear"] = clear_results
        step1_cleared = (
            clear_results.get("grand_total_deleted")
            or clear_results.get("total_deleted")
            or clear_results.get("total_cleared")
            or 0
        )
        logger.info(f"✓ Cleared {step1_cleared} calculation records (including cleanup)")

        # Step 2: Seed portfolios
        logger.info("\nStep 2/3: Seeding portfolios...")
        await create_demo_users(db)
        await seed_demo_portfolios(db)
        await db.commit()

        portfolio_count = await db.execute(select(func.count(Portfolio.id)))
        total_portfolios = portfolio_count.scalar()

        results["step2_seed"] = {
            "total_portfolios": total_portfolios
        }

        # Step 3: Run batch processing
        logger.info("\nStep 3/3: Running batch processing...")
        batch_result = await batch_orchestrator.run_daily_batch_with_backfill()

        results["step3_batch"] = batch_result

        logger.info("=" * 80)
        logger.info("COMPLETE RAILWAY DATA FIX FINISHED")
        logger.info("=" * 80)

        payload = {
            "success": True,
            "message": "Complete data fix finished successfully",
            "details": results,
        }
        return JSONResponse(content=jsonable_encoder(payload))

    except Exception as e:
        await db.rollback()
        logger.error(f"Error during complete fix: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to complete fix: {str(e)}")
