"""Run snapshot backfill for HNW portfolio."""
import asyncio
from app.database import get_async_session
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2


async def main():
    print("="*80)
    print("Running Snapshot Backfill for HNW Portfolio")
    print("="*80)
    print()

    portfolio_id = "e23ab931-a033-edfe-ed4f-9d02474780b4"

    # Run the snapshot job which now includes backfill logic
    async with get_async_session() as db:
        result = await batch_orchestrator_v2._create_snapshot(db, portfolio_id)

    print(f"Result:")
    print(f"  Snapshots created: {result.get('snapshots_created', 0)}")
    print(f"  Snapshots failed: {result.get('snapshots_failed', 0)}")
    print(f"  Total dates: {result.get('total_dates', 0)}")
    print()

    if result.get('snapshots_created', 0) > 0:
        print("SUCCESS: Snapshots created")
    elif result.get('total_dates', 0) == 0:
        print("INFO: No missing snapshots to create")
    else:
        print("WARNING: Some snapshots failed")


if __name__ == "__main__":
    asyncio.run(main())
