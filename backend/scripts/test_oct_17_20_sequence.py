"""
Test running Oct 17-20 in sequence to see where it hangs
"""
import asyncio
import gc
from datetime import date, timedelta

from app.core.logging import get_logger
from app.batch.batch_orchestrator_v3 import batch_orchestrator_v3 as batch_orchestrator

logger = get_logger(__name__)


def is_trading_day(check_date: date) -> bool:
    return check_date.weekday() < 5


async def main():
    """Run Oct 17-20 in sequence"""
    print("\n" + "="*80)
    print("Testing Oct 17-20 Sequence with 10-min timeout per day")
    print("="*80 + "\n")

    dates_to_test = [
        date(2025, 10, 17),
        # Oct 18-19 are weekend
        date(2025, 10, 20),
    ]

    for i, test_date in enumerate(dates_to_test):
        print(f"\n{'='*80}")
        print(f"Day {i+1}/{len(dates_to_test)}: {test_date}")
        print(f"{'='*80}")

        try:
            # 10-minute timeout per day
            result = await asyncio.wait_for(
                batch_orchestrator.run_daily_batch_sequence(
                    calculation_date=test_date
                ),
                timeout=600
            )
            print(f"[OK] {test_date} completed")

            # Force garbage collection between days
            gc.collect()
            print(f"   Garbage collected")

        except asyncio.TimeoutError:
            print(f"\n[TIMEOUT] TIMEOUT on {test_date}!")
            print(f"   This was day {i+1} in sequence")
            break

        except Exception as e:
            print(f"\n[ERROR] ERROR on {test_date}: {e}")
            break

    print("\n" + "="*80)
    print("Test complete")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
