"""
Non-interactive version of reseed script for automated execution
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date
from DANGEROUS_reseed_with_v3_backfill import (
    clean_all_data,
    reseed_portfolios_july_1,
    run_v3_backfill,
    verify_results
)
from app.core.logging import get_logger
from app.utils.trading_calendar import trading_calendar

logger = get_logger(__name__)

async def main():
    """Execute backfill without interactive prompts"""
    print("\n" + "=" * 80)
    print("SigmaSight Portfolio Reseed - AUTOMATED EXECUTION")
    print("=" * 80)
    print("\n[!] EXECUTING WITHOUT CONFIRMATION - USER APPROVED")
    print("\nThis will:")
    print("  1. Delete ALL portfolio, market data, and agent data")
    print("  2. Reseed demo portfolios with July 1, 2025 entry dates")
    print("  3. Run V3 batch orchestrator from July 1, 2025 through the latest trading day")
    print("  4. Verify results (including multi-portfolio aggregation)")
    print("\n" + "=" * 80 + "\n")

    try:
        # Phase 1: Clean
        print("\n[Phase 1] Cleaning database...")
        await clean_all_data()

        # Phase 2: Reseed
        print("\n[Phase 2] Reseeding portfolios...")
        await reseed_portfolios_july_1()

        # Phase 3: V3 Backfill
        print("\n[Phase 3] Running V3 batch backfill...")
        target_date = date.today()
        if not trading_calendar.is_trading_day(target_date):
            previous = trading_calendar.get_previous_trading_day(target_date)
            if previous:
                target_date = previous
        logger.info(f"Backfilling through {target_date} (most recent trading day)")
        backfill_result = await run_v3_backfill(target_date)

        # Phase 4: Verify
        print("\n[Phase 4] Verifying results...")
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
        logger.error(f"\n❌ Reseed failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
