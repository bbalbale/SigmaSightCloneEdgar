"""
Debug script for October 21 correlation calculation hang
"""
import asyncio
import logging
from datetime import date

from app.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3 as batch_orchestrator

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = get_logger(__name__)


async def main():
    """Debug October 21 correlation calculation with detailed logging"""
    print("\n" + "="*80)
    print("DEBUG: October 21, 2025 Correlation Calculation")
    print("="*80)
    print("\nRunning with DEBUG-level logging to identify hang location...")
    print("Watch for:")
    print("  - 🔍 Detecting correlation clusters")
    print("  - 🔍 Generating nickname for cluster")
    print("  - Querying sector for symbol X/Y")
    print("="*80 + "\n")

    calculation_date = date(2025, 10, 21)

    try:
        logger.info("="*80)
        logger.info(f"Starting batch processing for {calculation_date}")
        logger.info("="*80)

        # Run batch for Oct 21 with all debug logging
        result = await batch_orchestrator.run_daily_batch_sequence(
            calculation_date=calculation_date
        )

        logger.info(f"✅ Completed {calculation_date}")

        # Check if snapshots were created
        async with AsyncSessionLocal() as db:
            from sqlalchemy import text
            result = await db.execute(text("""
                SELECT COUNT(*)
                FROM portfolio_snapshots
                WHERE snapshot_date = :date
            """), {"date": calculation_date})
            count = result.scalar()
            print(f"\n✅ SUCCESS: Created {count} snapshots for {calculation_date}")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

        print("\n" + "="*80)
        print("ERROR OCCURRED - Check logs above for last debug message")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
