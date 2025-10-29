"""
Complete October 17-28, 2025 batch processing
With cluster detection removed (fix validated on Oct 17)
"""
import asyncio
from datetime import date, timedelta
from app.core.logging import get_logger
from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3 as batch_orchestrator

logger = get_logger(__name__)


def is_trading_day(check_date: date) -> bool:
    """Check if date is a weekday (trading day)"""
    return check_date.weekday() < 5


async def main():
    """Process October 17-28, 2025"""
    print("\n" + "="*80)
    print("Completing October 17-28, 2025 Batch Processing")
    print("Cluster detection removed - fix validated on Oct 17")
    print("="*80 + "\n")

    start_date = date(2025, 10, 17)
    end_date = date(2025, 10, 28)

    # Generate trading days
    current_date = start_date
    trading_days = []
    while current_date <= end_date:
        if is_trading_day(current_date):
            trading_days.append(current_date)
        current_date += timedelta(days=1)

    print(f"Trading days to process: {len(trading_days)}")
    for i, d in enumerate(trading_days):
        print(f"  {i+1}. {d.strftime('%Y-%m-%d (%A)')}")
    print("\n" + "="*80 + "\n")

    # Process each day
    completed = []
    failed = []

    for i, calc_date in enumerate(trading_days):
        print(f"\n{'='*80}")
        print(f"Processing {i+1}/{len(trading_days)}: {calc_date}")
        print(f"{'='*80}")

        try:
            result = await batch_orchestrator.run_daily_batch_sequence(
                calculation_date=calc_date
            )
            completed.append(calc_date)
            print(f"[OK] Completed {calc_date}")

        except Exception as e:
            failed.append((calc_date, str(e)))
            print(f"[ERROR] Failed {calc_date}: {e}")
            logger.error(f"Batch failed for {calc_date}", exc_info=True)
            # Continue processing remaining days

    # Summary
    print("\n" + "="*80)
    print("BATCH PROCESSING SUMMARY")
    print("="*80)
    print(f"Total trading days: {len(trading_days)}")
    print(f"Completed: {len(completed)}")
    print(f"Failed: {len(failed)}")

    if completed:
        print("\nCompleted dates:")
        for d in completed:
            print(f"  [OK] {d}")

    if failed:
        print("\nFailed dates:")
        for d, error in failed:
            print(f"  [ERROR] {d}: {error[:100]}")

    print("="*80 + "\n")

    return len(completed), len(failed)


if __name__ == "__main__":
    completed, failed = asyncio.run(main())
    exit(0 if failed == 0 else 1)
