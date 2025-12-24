"""Run batch calculations now.

Uses run_batch_with_backfill to include:
- Phase 1: Market Data Collection
- Phase 1.5: Symbol Factor Calculation (universe-level)
- Phase 1.75: Symbol Metrics Calculation (returns, valuations)
- Phases 0, 2-6: Portfolio processing
"""
import asyncio
import os
import time
from datetime import date

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway'
os.environ['AI_DATABASE_URL'] = 'postgresql+asyncpg://postgres:yaao16yhdsn4jad38lfnkfnbqmqmzysn@metro.proxy.rlwy.net:31246/railway'


async def main():
    from app.batch.batch_orchestrator import batch_orchestrator

    calculation_date = date(2025, 12, 22)
    print(f"Starting FULL batch run for {calculation_date}...")
    print("(Includes Phase 1.5 Symbol Factors and Phase 1.75 Symbol Metrics)")
    print()

    start_time = time.time()

    # Use run_batch_with_backfill with same start/end date to get full processing
    # This includes Phase 1.5 (Symbol Factors) and Phase 1.75 (Symbol Metrics)
    result = await batch_orchestrator.run_daily_batch_with_backfill(
        start_date=calculation_date,
        end_date=calculation_date
    )

    elapsed = time.time() - start_time

    print()
    print(f"=== Batch Complete ===")
    print(f"Duration: {elapsed:.1f} seconds")
    print(f"Success: {result.get('success', False)}")
    print(f"Dates processed: {result.get('dates_processed', 0)}")

    if result.get('phase_1_5'):
        p15 = result['phase_1_5']
        print(f"Phase 1.5 (Symbol Factors): {p15.get('symbols_processed', 0)} symbols")

    if result.get('phase_1_75'):
        p175 = result['phase_1_75']
        print(f"Phase 1.75 (Symbol Metrics): {p175.get('symbols_updated', 0)} symbols")

    if result.get('errors'):
        print(f"Errors: {result['errors']}")


if __name__ == '__main__':
    asyncio.run(main())
