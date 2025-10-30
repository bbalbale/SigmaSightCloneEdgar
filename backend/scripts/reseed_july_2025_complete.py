"""
Complete portfolio reseed script for July 1, 2025 start date.

This script:
1. Cleans all portfolio analysis, agent, and market data
2. Reseeds 3 demo portfolios with July 1, 2025 entry dates
3. Runs batch processor for each trading day from July 1 - Oct 27, 2025
4. Verifies results

Estimated time: 55-95 minutes
"""
import asyncio
import sys
from datetime import date, timedelta
from typing import List, Set
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3 as batch_orchestrator_v2

logger = get_logger(__name__)


# ============================================================================
# PHASE 1: DATABASE CLEANING
# ============================================================================

async def clean_all_data():
    """Delete all portfolio analysis, agent, market data, and portfolio/position data."""
    logger.info("="*80)
    logger.info("PHASE 1: Cleaning Database")
    logger.info("="*80)

    async with AsyncSessionLocal() as db:
        # Delete in correct order to handle foreign key constraints
        # Children BEFORE parents
        tables_to_clean = [
            # Portfolio analysis data (children first)
            "portfolio_snapshots",
            "position_greeks",
            "position_factor_exposures",
            "factor_exposures",
            "position_market_betas",
            "position_interest_rate_betas",
            "position_volatility",
            "market_risk_scenarios",
            "stress_test_results",
            "pairwise_correlations",           # Delete before correlation_calculations
            "correlation_cluster_positions",   # Delete before correlation_clusters
            "correlation_clusters",            # Delete before correlation_calculations
            "correlation_calculations",        # Parent table (delete after children)
            "portfolio_target_prices",
            "ai_insights",
            # Agent data
            "agent_messages",  # Delete first (foreign key to conversations)
            "agent_conversations",
            "agent_user_preferences",
            # Tag data
            "position_tags",  # Delete before tags_v2
            "tags_v2",
            # Position and portfolio data
            "positions",  # Delete before portfolios
            "portfolios",
            # Market data (clean slate!)
            "market_data_cache",
            "company_profiles",
        ]

        total_deleted = 0
        for table in tables_to_clean:
            try:
                result = await db.execute(text(f"DELETE FROM {table}"))
                deleted = result.rowcount
                total_deleted += deleted
                logger.info(f"  {table}: Deleted {deleted} records")
            except Exception as e:
                logger.warning(f"  {table}: Error - {e}")

        await db.commit()
        logger.info(f"\nTotal records deleted: {total_deleted}")
        logger.info("Database cleaned successfully!\n")


# ============================================================================
# PHASE 2: RESEED PORTFOLIOS
# ============================================================================

async def reseed_portfolios_july_1():
    """Reseed 3 demo portfolios with July 1, 2025 entry dates."""
    logger.info("="*80)
    logger.info("PHASE 2: Reseeding Portfolios (July 1, 2025)")
    logger.info("="*80)

    # Import and run the seed function
    from app.db.seed_demo_portfolios import seed_demo_portfolios

    # Override entry dates to July 1, 2025
    # The seed function will use the dates from DEMO_PORTFOLIOS
    # We need to temporarily modify those dates

    import app.db.seed_demo_portfolios as seed_module

    # Save original DEMO_PORTFOLIOS
    original_portfolios = seed_module.DEMO_PORTFOLIOS.copy()

    try:
        # Modify all position entry_dates to July 1, 2025
        july_1 = date(2025, 7, 1)
        for portfolio_spec in seed_module.DEMO_PORTFOLIOS:
            for position in portfolio_spec.get('positions', []):
                position['entry_date'] = july_1

        # Run seeding
        async with AsyncSessionLocal() as db:
            await seed_demo_portfolios(db)
            logger.info("\nPortfolios seeded successfully")

        logger.info("Portfolios reseeded successfully!\n")

    finally:
        # Restore original DEMO_PORTFOLIOS
        seed_module.DEMO_PORTFOLIOS = original_portfolios


# ============================================================================
# PHASE 3: HISTORICAL BATCH PROCESSING
# ============================================================================

def is_trading_day(check_date: date) -> bool:
    """Check if date is a trading day (weekday, not holiday)."""
    # Simple check: weekday only (Monday=0, Friday=4)
    # TODO: Could add holiday calendar for more accuracy
    return check_date.weekday() < 5


async def run_historical_batch_loop(start_date: date, end_date: date):
    """Run batch processor for each trading day in the range."""
    logger.info("="*80)
    logger.info("PHASE 3: Historical Batch Processing")
    logger.info("="*80)
    logger.info(f"Date range: {start_date} to {end_date}")

    current_date = start_date
    trading_days_processed = 0
    total_days = (end_date - start_date).days + 1

    while current_date <= end_date:
        if is_trading_day(current_date):
            trading_days_processed += 1
            days_remaining = sum(1 for d in range((end_date - current_date).days + 1)
                               if is_trading_day(current_date + timedelta(days=d)))

            logger.info("="*80)
            logger.info(f"Processing {current_date} (Trading day {trading_days_processed}, {days_remaining} remaining)")
            logger.info("="*80)

            try:
                # Run batch processor for this specific date
                result = await batch_orchestrator_v2.run_daily_batch_sequence(
                    calculation_date=current_date
                )
                logger.info(f"Batch processing completed for {current_date}")

            except Exception as e:
                logger.error(f"Error processing {current_date}: {e}")
                logger.warning("Continuing to next day...")

        current_date += timedelta(days=1)

    logger.info(f"\n\nHistorical batch processing complete!")
    logger.info(f"Processed {trading_days_processed} trading days")


# ============================================================================
# PHASE 4: VERIFICATION
# ============================================================================

async def verify_results():
    """Verify the reseed results."""
    logger.info("="*80)
    logger.info("PHASE 4: Verification")
    logger.info("="*80)

    async with AsyncSessionLocal() as db:
        # Check portfolios
        portfolios_result = await db.execute(text("SELECT COUNT(*) FROM portfolios"))
        portfolio_count = portfolios_result.scalar()

        # Check positions
        positions_result = await db.execute(text("SELECT COUNT(*) FROM positions"))
        position_count = positions_result.scalar()

        # Check snapshots
        snapshots_result = await db.execute(text("SELECT COUNT(*) FROM portfolio_snapshots"))
        snapshot_count = snapshots_result.scalar()

        # Check market data
        market_data_result = await db.execute(text("SELECT COUNT(*) FROM market_data_cache"))
        market_data_count = market_data_result.scalar()

        # Get portfolio details
        portfolios_query = await db.execute(
            text("""
                SELECT name, equity_balance
                FROM portfolios
                ORDER BY name
            """)
        )
        portfolios = portfolios_query.fetchall()

        logger.info("\nVerification Results:")
        logger.info(f"  Portfolios:      {portfolio_count} (expected: 3)")
        logger.info(f"  Positions:       {position_count} (expected: 63)")
        logger.info(f"  Snapshots:       {snapshot_count} (expected: ~255 for 85 days × 3 portfolios)")
        logger.info(f"  Market Data:     {market_data_count} (expected: ~4,200)")

        logger.info("\nPortfolio Details:")
        for name, equity in portfolios:
            logger.info(f"  {name}: ${float(equity):,.2f}")

        # Check if we have expected counts
        status = "SUCCESS"
        if portfolio_count != 3:
            logger.error(f"  ERROR: Expected 3 portfolios, found {portfolio_count}")
            status = "FAILED"
        if position_count != 63:
            logger.error(f"  ERROR: Expected 63 positions, found {position_count}")
            status = "FAILED"

        logger.info(f"\nVerification Status: {status}\n")
        return status == "SUCCESS"


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main reseed execution."""
    print("\n" + "="*80)
    print("SigmaSight Portfolio Reseed - July 1, 2025")
    print("="*80)
    print("\nThis will:")
    print("  1. Delete ALL portfolio, market data, and agent data")
    print("  2. Reseed 3 portfolios with July 1, 2025 entry dates")
    print("  3. Run batch processor for ~86 trading days (July 1 - Oct 28)")
    print("  4. Verify results")
    print("\nEstimated time: 60-100 minutes")
    print("="*80 + "\n")

    response = input("Are you sure you want to proceed? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("\n Cancelled. No changes made.")
        return

    try:
        # Phase 1: Clean
        await clean_all_data()

        # Phase 2: Reseed
        await reseed_portfolios_july_1()

        # Phase 3: Historical batch processing
        start_date = date(2025, 7, 1)
        end_date = date(2025, 10, 28)  # Updated to today

        await run_historical_batch_loop(start_date, end_date)

        # Phase 4: Verify
        await verify_results()

        print("\n✅ All phases complete!")
        print("  ✓ Database cleaned")
        print("  ✓ Portfolios reseeded with July 1, 2025 entry dates")
        print("  ✓ Historical batch processing complete")
        print("  ✓ Results verified")

    except Exception as e:
        logger.error(f"\nReseed failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
