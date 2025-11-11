"""
Run batch process with real-time monitoring and detailed logging

This script runs the full batch orchestrator v3 sequence including:
- Phase 1: Market Data Collection
- Phase 1.5: Fundamental Data Collection (NEW)
- Phase 2: P&L Calculation
- Phase 2.5: Position Market Value Updates
- Phase 3: Risk Analytics

With enhanced logging for Phase 1.5 fundamentals collection.
"""
import asyncio
import logging
from datetime import date
from app.database import AsyncSessionLocal
from app.batch.batch_orchestrator import batch_orchestrator
from app.core.logging import get_logger

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = get_logger(__name__)


async def run_batch_with_monitoring():
    """Run batch process with real-time monitoring"""

    print("\n" + "=" * 80)
    print("  BATCH PROCESS EXECUTION - FULL 5-PHASE SEQUENCE")
    print("=" * 80)
    print()
    print("Phases to execute:")
    print("  • Phase 1: Market Data Collection (1-year lookback)")
    print("  • Phase 1.5: Fundamental Data Collection ⭐ (FIRST RUN - will fetch all)")
    print("  • Phase 2: P&L Calculation & Snapshots")
    print("  • Phase 2.5: Position Market Value Updates")
    print("  • Phase 2.75: Sector Tag Restoration")
    print("  • Phase 3: Risk Analytics")
    print()
    print("=" * 80)
    print()

    # Get calculation date (today)
    calc_date = date.today()
    print(f"📅 Calculation Date: {calc_date}")
    print()

    # Run batch sequence
    try:
        print("🚀 Starting batch orchestrator v3...")
        print()

        result = await batch_orchestrator.run_daily_batch_sequence(
            calculation_date=calc_date
        )

        # Display results
        print("\n" + "=" * 80)
        print("  BATCH PROCESS COMPLETE")
        print("=" * 80)
        print()

        print(f"✅ Success: {result['success']}")
        print(f"📅 Date: {result['calculation_date']}")
        print()

        # Phase 1 Results
        phase1 = result.get('phase_1', {})
        print("📊 Phase 1 - Market Data Collection:")
        print(f"   Symbols fetched: {phase1.get('symbols_fetched', 0)}")
        print(f"   Data coverage: {phase1.get('data_coverage_pct', 0):.1f}%")
        print(f"   Duration: {phase1.get('duration_seconds', 0)}s")
        print()

        # Phase 1.5 Results (FUNDAMENTALS)
        phase15 = result.get('phase_1_5', {})
        if phase15:
            print("📈 Phase 1.5 - Fundamental Data Collection:")
            print(f"   Symbols evaluated: {phase15.get('symbols_evaluated', 0)}")
            print(f"   Symbols fetched: {phase15.get('symbols_fetched', 0)}")
            print(f"   Symbols skipped: {phase15.get('symbols_skipped', 0)}")
            if phase15.get('errors'):
                print(f"   ⚠️  Errors: {len(phase15['errors'])}")
                for error in phase15['errors'][:5]:  # Show first 5 errors
                    print(f"      - {error}")
            print()

        # Phase 2 Results
        phase2 = result.get('phase_2', {})
        if phase2:
            print("💰 Phase 2 - P&L Calculation:")
            print(f"   Portfolios processed: {phase2.get('portfolios_processed', 0)}")
            print(f"   Duration: {phase2.get('duration_seconds', 0)}s")
            print()

        # Phase 2.5 Results
        phase25 = result.get('phase_2_5', {})
        if phase25:
            print("💵 Phase 2.5 - Position Market Values:")
            print(f"   Positions updated: {phase25.get('positions_updated', 0)}")
            print(f"   Positions skipped: {phase25.get('positions_skipped', 0)}")
            print()

        # Phase 2.75 Results
        phase275 = result.get('phase_2_75', {})
        if phase275:
            print("🏷️  Phase 2.75 - Sector Tags:")
            print(f"   Positions tagged: {phase275.get('positions_tagged', 0)}")
            print(f"   Tags created: {phase275.get('tags_created', 0)}")
            print()

        # Phase 3 Results
        phase3 = result.get('phase_3', {})
        if phase3:
            print("📊 Phase 3 - Risk Analytics:")
            print(f"   Portfolios processed: {phase3.get('portfolios_processed', 0)}")
            print(f"   Duration: {phase3.get('duration_seconds', 0)}s")
            print()

        # Errors
        if result.get('errors'):
            print("⚠️  Errors encountered:")
            for error in result['errors']:
                print(f"   - {error}")
            print()

        print("=" * 80)

        # Show data summary
        print("\n📊 Verifying fundamental data stored...")
        await verify_fundamentals_data()

        return result

    except Exception as e:
        print(f"\n❌ Error running batch process: {e}")
        import traceback
        traceback.print_exc()
        return None


async def verify_fundamentals_data():
    """Verify fundamental data was stored correctly"""
    from sqlalchemy import select, func
    from app.models.fundamentals import IncomeStatement, BalanceSheet, CashFlow
    from app.models.market_data import CompanyProfile

    try:
        async with AsyncSessionLocal() as db:
            # Count income statements
            income_count = await db.execute(select(func.count(IncomeStatement.id)))
            income_total = income_count.scalar()

            # Count balance sheets
            balance_count = await db.execute(select(func.count(BalanceSheet.id)))
            balance_total = balance_count.scalar()

            # Count cash flows
            cash_count = await db.execute(select(func.count(CashFlow.id)))
            cash_total = cash_count.scalar()

            # Count company profiles with fundamentals
            profiles_count = await db.execute(
                select(func.count(CompanyProfile.symbol)).where(
                    CompanyProfile.fundamentals_last_fetched.isnot(None)
                )
            )
            profiles_total = profiles_count.scalar()

            print(f"\n📋 Fundamental Data Summary:")
            print(f"   Income statements: {income_total} records")
            print(f"   Balance sheets: {balance_total} records")
            print(f"   Cash flows: {cash_total} records")
            print(f"   Company profiles with fundamentals: {profiles_total} symbols")

            # Show sample symbols with data
            if income_total > 0:
                sample_query = select(IncomeStatement.symbol).distinct().limit(10)
                sample_result = await db.execute(sample_query)
                symbols = [row[0] for row in sample_result.fetchall()]
                print(f"\n   Sample symbols with fundamental data:")
                print(f"   {', '.join(symbols)}")

    except Exception as e:
        print(f"   Error verifying data: {e}")


if __name__ == "__main__":
    print("\n" + "🚀" * 40)
    print()
    asyncio.run(run_batch_with_monitoring())
    print()
    print("🏁" * 40)
    print()
