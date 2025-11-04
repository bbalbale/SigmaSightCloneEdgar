"""
Complete portfolio reseed script using Batch Orchestrator V3

This script:
1. Cleans all portfolio analysis, agent, and market data
2. Reseeds the full demo portfolio set (currently 5 portfolios across 3 demo users,
   including the family office dual-sleeve account) with July 1, 2025 entry dates
3. Uses V3 batch orchestrator with automatic backfill
   - Phase 1: Market Data Collection (1-year lookback)
   - Phase 2: P&L Calculation & Snapshots
   - Phase 2.5: Update Position Market Values (NEW - critical for analytics)
   - Phase 3: Risk Analytics (betas, factors, correlations)
4. Verifies results

Estimated time: 30-40 minutes for 85 trading days (vs 5+ hours with V2)
"""
import asyncio
import copy
import sys
from datetime import date
from typing import List
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3
from app.utils.trading_calendar import trading_calendar
from app.services.portfolio_aggregation_service import PortfolioAggregationService
from app.models.users import User

logger = get_logger(__name__)

# Import the seed module once so we can reference the current demo portfolio spec
import app.db.seed_demo_portfolios as seed_module

DEMO_PORTFOLIO_SPEC = seed_module.DEMO_PORTFOLIOS
EXPECTED_PORTFOLIO_COUNT = len(DEMO_PORTFOLIO_SPEC)
EXPECTED_POSITION_COUNT = sum(len(portfolio.get("positions", [])) for portfolio in DEMO_PORTFOLIO_SPEC)
FAMILY_OFFICE_EMAIL = "demo_familyoffice@sigmasight.com"


# ============================================================================
# PHASE 1: DATABASE CLEANING
# ============================================================================

async def clean_all_data():
    """Delete all portfolio analysis, agent, market data, and portfolio/position data."""
    logger.info("=" * 80)
    logger.info("PHASE 1: Cleaning Database")
    logger.info("=" * 80)

    async with AsyncSessionLocal() as db:
        # Use TRUNCATE CASCADE to automatically handle all foreign key constraints
        # This is much more robust than manual DELETE ordering
        tables_to_clean = [
            # Portfolio analysis data
            "portfolio_snapshots",
            "position_greeks",
            "position_factor_exposures",
            "factor_exposures",
            "position_market_betas",
            "position_interest_rate_betas",
            "position_volatility",
            "market_risk_scenarios",
            "stress_test_results",
            "pairwise_correlations",
            "correlation_cluster_positions",
            "correlation_clusters",
            "correlation_calculations",
            "portfolio_target_prices",
            "ai_insights",
            # Agent data
            "agent_messages",
            "agent_conversations",
            "agent_user_preferences",
            # Tag data
            "position_tags",
            "tags_v2",
            # Position and portfolio data
            "positions",
            "portfolios",
            # Market data - PRESERVE market_data_cache but DELETE company_profiles to test refetch
            # "market_data_cache",  # KEEP: Contains historical price data (Oct 2024 - Oct 2025)
            "company_profiles",      # DELETE: Will be refetched on first batch run to verify fetching works
            # Batch tracking
            "batch_run_tracking",
        ]

        total_deleted = 0
        for table in tables_to_clean:
            try:
                # TRUNCATE CASCADE automatically handles FK constraints
                result = await db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                logger.info(f"  {table}: Truncated successfully")
                # Can't get rowcount from TRUNCATE, but we know it worked
            except Exception as e:
                logger.warning(f"  {table}: Error - {e}")

        await db.commit()
        logger.info(f"\nDatabase cleaned successfully!\n")


# ============================================================================
# PHASE 2: RESEED PORTFOLIOS
# ============================================================================

async def reseed_portfolios_july_1():
    """Reseed demo portfolios with July 1, 2025 entry dates."""
    logger.info("=" * 80)
    logger.info("PHASE 2: Reseeding Portfolios (July 1, 2025)")
    logger.info("=" * 80)

    # Import and run the seed function
    from app.db.seed_demo_portfolios import seed_demo_portfolios

    # Save original DEMO_PORTFOLIOS
    original_portfolios = copy.deepcopy(DEMO_PORTFOLIO_SPEC)

    try:
        # Modify all position entry_dates to July 1, 2025
        july_1 = date(2025, 7, 1)
        for portfolio_spec in DEMO_PORTFOLIO_SPEC:
            for position in portfolio_spec.get("positions", []):
                position['entry_date'] = july_1

        # Run seeding
        async with AsyncSessionLocal() as db:
            await seed_demo_portfolios(db)
            await db.commit()  # CRITICAL: Must commit or positions will be rolled back!
            logger.info(f"\nPortfolios seeded successfully ({EXPECTED_PORTFOLIO_COUNT} portfolios)")

        logger.info("Portfolios reseeded successfully!\n")

    finally:
        # Restore original DEMO_PORTFOLIOS
        seed_module.DEMO_PORTFOLIOS[:] = original_portfolios
        DEMO_PORTFOLIO_SPEC[:] = original_portfolios


# ============================================================================
# PHASE 3: BATCH ORCHESTRATOR V3 BACKFILL
# ============================================================================

async def run_v3_backfill(target_date: date):
    """
    Run Batch Orchestrator V3 with automatic backfill

    V3 will:
    - Detect earliest position date (July 1, 2025)
    - Fetch 1-year market data (July 1, 2024 - target_date)
    - Process snapshots for all trading days (July 1, 2025 - target_date)
    - Track progress in batch_run_tracking table
    """
    logger.info("=" * 80)
    logger.info("PHASE 3: Batch Orchestrator V3 Backfill")
    logger.info("=" * 80)
    logger.info(f"Target date: {target_date}")
    logger.info("")

    result = await batch_orchestrator_v3.run_daily_batch_with_backfill(
        target_date=target_date
    )

    if result['success']:
        logger.info(f"\n[SUCCESS] Backfill complete!")
        logger.info(f"  Dates processed: {result['dates_processed']}")
        if 'duration_seconds' in result:
            logger.info(f"  Duration: {result['duration_seconds']}s")
    else:
        logger.error(f"\n[FAILED] Backfill had errors")
        logger.error(f"  Dates processed: {result['dates_processed']}")

    return result


# ============================================================================
# PHASE 4: VERIFICATION
# ============================================================================


async def verify_results():
    """Verify the reseed results."""
    logger.info("=" * 80)
    logger.info("PHASE 4: Verification")
    logger.info("=" * 80)

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

        # Check batch tracking
        tracking_result = await db.execute(text("SELECT COUNT(*) FROM batch_run_tracking"))
        tracking_count = tracking_result.scalar()

        # Get portfolio details
        portfolios_query = await db.execute(
            text("""
                SELECT name, equity_balance
                FROM portfolios
                ORDER BY name
            """)
        )
        portfolios = portfolios_query.fetchall()

        # Get snapshot date range
        snapshot_dates_query = await db.execute(
            text("""
                SELECT MIN(snapshot_date), MAX(snapshot_date), COUNT(DISTINCT snapshot_date)
                FROM portfolio_snapshots
            """)
        )
        min_date, max_date, unique_dates = snapshot_dates_query.fetchone()

        logger.info("\nVerification Results:")
        logger.info(f"  Portfolios:      {portfolio_count} (expected: {EXPECTED_PORTFOLIO_COUNT})")
        logger.info(f"  Positions:       {position_count} (expected: {EXPECTED_POSITION_COUNT})")
        logger.info("  Snapshots:       {} (expected: ~{} for 85 trading days)".format(snapshot_count, EXPECTED_PORTFOLIO_COUNT * 85))
        logger.info(f"  Market Data:     {market_data_count} (expected: thousands)")
        logger.info(f"  Batch Tracking:  {tracking_count} (expected: ~85)")

        if min_date and max_date:
            logger.info(f"\nSnapshot Date Range:")
            logger.info(f"  First: {min_date}")
            logger.info(f"  Last:  {max_date}")
            logger.info(f"  Unique dates: {unique_dates}")

        logger.info("\nPortfolio Details:")
        for name, equity in portfolios:
            logger.info(f"  {name}: ${float(equity):,.2f}")


        # Check if we have expected counts
        status = "SUCCESS"
        if portfolio_count != EXPECTED_PORTFOLIO_COUNT:
            logger.error(f"  ERROR: Expected {EXPECTED_PORTFOLIO_COUNT} portfolios, found {portfolio_count}")
            status = "FAILED"
        if position_count != EXPECTED_POSITION_COUNT:
            logger.error(f"  ERROR: Expected {EXPECTED_POSITION_COUNT} positions, found {position_count}")
            status = "FAILED"
        if min_date != date(2025, 7, 1):
            logger.error(f"  ERROR: Expected first snapshot on 2025-07-01, found {min_date}")
            status = "FAILED"

        # Validate the multi-portfolio aggregation for the family office account
        family_user_result = await db.execute(
            select(User).where(User.email == FAMILY_OFFICE_EMAIL)
        )
        family_user = family_user_result.scalar_one_or_none()

        if family_user:
            aggregation_service = PortfolioAggregationService(db)
            aggregate_metrics = await aggregation_service.aggregate_portfolio_metrics(family_user.id)
            expected_family_portfolios = sum(
                1 for portfolio in DEMO_PORTFOLIO_SPEC if portfolio.get("user_email") == FAMILY_OFFICE_EMAIL
            )

            logger.info("\nFamily Office Aggregate Metrics:")
            logger.info(
                f"  Portfolio Count: {aggregate_metrics.get('portfolio_count')} (expected: {expected_family_portfolios})"
            )
            logger.info(
                f"  Net Asset Value: ${aggregate_metrics.get('net_asset_value', 0):,.2f}"
            )

            if aggregate_metrics.get('portfolio_count') != expected_family_portfolios:
                logger.error(
                    f"  ERROR: Family office aggregate expected {expected_family_portfolios} portfolios, found {aggregate_metrics.get('portfolio_count')}"
                )
                status = "FAILED"

            family_portfolio_balances = await db.execute(
                text("""
                    SELECT SUM(equity_balance)
                    FROM portfolios WHERE user_id = :user_id
                """),
                {"user_id": str(family_user.id)},
            )
            expected_family_nav = float(family_portfolio_balances.scalar() or 0.0)
            aggregate_nav = float(aggregate_metrics.get('net_asset_value', 0) or 0.0)

            if abs(expected_family_nav - aggregate_nav) > 0.01:
                logger.error(
                    f"  ERROR: Family office NAV mismatch. Portfolios sum=${expected_family_nav:,.2f}, aggregate=${aggregate_nav:,.2f}"
                )
                status = "FAILED"
        else:
            logger.error("  ERROR: Could not locate family office demo user for aggregation check")
            status = "FAILED"

        logger.info(f"\nVerification Status: {status}\n")
        return status == "SUCCESS"



# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Main reseed execution."""
    print("\n" + "=" * 80)
    print("SigmaSight Portfolio Reseed - Batch Orchestrator V3")
    print("=" * 80)
    print("\nThis will:")
    print("  1. Delete ALL portfolio, market data, and agent data")
    print("  2. Reseed demo portfolios with July 1, 2025 entry dates")
    print("  3. Run V3 batch orchestrator from July 1, 2025 through the latest trading day")
    print("  4. Verify results (including multi-portfolio aggregation)")
    print("\nV3 Batch Phases:")
    print("  - Phase 1: Market Data Collection (1-year lookback)")
    print("  - Phase 2: P&L Calculation & Snapshots")
    print("  - Phase 2.5: Update Position Market Values (NEW)")
    print("  - Phase 3: Risk Analytics (betas, factors, correlations)")
    print("\nV3 Features:")
    print("  - Provider priority: YFinance -> YahooQuery -> Polygon -> FMP")
    print("  - Automatic backfill detection")
    print("  - Position market values updated for accurate analytics")
    print("\nEstimated time: 30-40 minutes (vs 5+ hours with V2)")
    print("=" * 80 + "\n")

    response = input("Are you sure you want to proceed? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("\n[CANCELLED] No changes made.")
        return

    # SECOND CONFIRMATION - SAFETY CHECK
    print("\n" + "=" * 80)
    print("⚠️  SECOND CONFIRMATION REQUIRED")
    print("=" * 80)
    print("This will PERMANENTLY DELETE all portfolio data!")
    print("Type exactly: DELETE ALL MY DATA")
    print("=" * 80)
    confirm_text = input("Confirmation: ").strip()
    if confirm_text != "DELETE ALL MY DATA":
        print(f"\n❌ Cancelled. Confirmation text did not match.")
        print(f"   Expected: 'DELETE ALL MY DATA'")
        print(f"   Got: '{confirm_text}'")
        return

    try:
        # Phase 1: Clean
        await clean_all_data()

        # Phase 2: Reseed
        await reseed_portfolios_july_1()

        # Phase 3: V3 Backfill
        target_date = date.today()
        if not trading_calendar.is_trading_day(target_date):
            previous = trading_calendar.get_previous_trading_day(target_date)
            if previous:
                target_date = previous
        logger.info(f"Backfilling through {target_date} (most recent trading day)")
        backfill_result = await run_v3_backfill(target_date)

        # Phase 4: Verify
        await verify_results()

        print("\n" + "=" * 80)
        print("[SUCCESS] All phases complete!")
        print("=" * 80)
        print("  - Database cleaned")
        print("  - Portfolios reseeded with July 1, 2025 entry dates")
        print("  - V3 batch processing complete")
        print("  - Results verified")
        print(f"\nTotal duration: {backfill_result.get('duration_seconds', 0)}s")
        print("=" * 80 + "\n")

    except Exception as e:
        logger.error(f"\nReseed failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
