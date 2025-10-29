"""
Complete batch processing for October 21-28, 2025 with correlation timeout
"""
import asyncio
from datetime import date, timedelta
from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.core.logging import get_logger
from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3 as batch_orchestrator

logger = get_logger(__name__)

# Timeout for correlation calculations (5 minutes)
CORRELATION_TIMEOUT = 300  # seconds


def is_trading_day(check_date: date) -> bool:
    """Check if date is a trading day (weekday, not holiday)."""
    return check_date.weekday() < 5


async def run_batch_with_timeout(calculation_date: date, timeout_seconds: int = 600):
    """
    Run batch processing with a timeout.

    Args:
        calculation_date: Date to process
        timeout_seconds: Maximum time allowed (default 10 minutes)

    Returns:
        True if successful, False if timeout or error
    """
    try:
        # Run batch with timeout
        result = await asyncio.wait_for(
            batch_orchestrator.run_daily_batch_sequence(
                calculation_date=calculation_date
            ),
            timeout=timeout_seconds
        )
        return True

    except asyncio.TimeoutError:
        logger.error(f"⏱️ TIMEOUT after {timeout_seconds}s on {calculation_date}")
        logger.warning(f"Correlation calculation likely hung - skipping {calculation_date}")
        return False

    except Exception as e:
        logger.error(f"❌ Error on {calculation_date}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Complete remaining trading days Oct 21-28 with timeout protection"""
    print("\n" + "="*80)
    print("Completing Batch Processing: October 21-28, 2025 (With Timeout)")
    print("="*80)

    start_date = date(2025, 10, 21)
    end_date = date(2025, 10, 28)

    # Count trading days
    trading_days = sum(1 for d in range((end_date - start_date).days + 1)
                      if is_trading_day(start_date + timedelta(days=d)))

    print(f"\nDate range: {start_date} to {end_date}")
    print(f"Estimated trading days: {trading_days}")
    print(f"Timeout per day: 10 minutes (will skip if correlation hangs)")
    print("="*80 + "\n")

    current_date = start_date
    completed = 0
    skipped = 0
    failed = 0

    while current_date <= end_date:
        if is_trading_day(current_date):
            completed += 1
            remaining = sum(1 for d in range((end_date - current_date).days + 1)
                          if is_trading_day(current_date + timedelta(days=d)))

            logger.info("="*80)
            logger.info(f"Processing {current_date} (Day {completed}/{trading_days}, {remaining} remaining)")
            logger.info("="*80)

            success = await run_batch_with_timeout(current_date, timeout_seconds=600)

            if success:
                logger.info(f"✅ Completed {current_date}")
            else:
                skipped += 1
                logger.warning(f"⚠️ Skipped {current_date} due to timeout/error")

        current_date += timedelta(days=1)

    # Verify completion
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT MIN(snapshot_date), MAX(snapshot_date), COUNT(DISTINCT snapshot_date)
            FROM portfolio_snapshots
        """))
        row = result.fetchone()

        # Count Oct 21-28 snapshots
        oct_result = await db.execute(text("""
            SELECT COUNT(DISTINCT snapshot_date)
            FROM portfolio_snapshots
            WHERE snapshot_date >= '2025-10-21' AND snapshot_date <= '2025-10-28'
        """))
        oct_count = oct_result.scalar()

        print("\n" + "="*80)
        print("COMPLETION SUMMARY")
        print("="*80)
        print(f"Trading days attempted: {completed}")
        print(f"Skipped due to timeout: {skipped}")
        print(f"\nSnapshot date range: {row[0]} to {row[1]}")
        print(f"Total unique snapshot dates: {row[2]}")
        print(f"Oct 21-28 snapshot dates: {oct_count}")
        print(f"Target was: October 28, 2025")

        if row[1] >= date(2025, 10, 28):
            print("\n✅ SUCCESS: Reached October 28, 2025!")
        else:
            print(f"\n⚠️ PARTIAL: Only reached {row[1]}, missing {trading_days - oct_count} days")

        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
