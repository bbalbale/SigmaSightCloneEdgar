#!/usr/bin/env python
"""
Profile a single date batch run to identify bottlenecks
"""
import asyncio
import time
from datetime import date
from app.batch.batch_orchestrator import batch_orchestrator

async def profile_single_date():
    """Profile one date to see where time is spent"""

    test_date = date(2025, 7, 2)  # Use July 2 (July 1 might have special logic)

    print(f"Profiling batch processing for {test_date}")
    print("=" * 80)

    start = time.time()

    result = await batch_orchestrator.run_daily_batch_sequence(
        calculation_date=test_date,
        portfolio_ids=None  # All portfolios
    )

    elapsed = time.time() - start

    print("\n" + "=" * 80)
    print(f"TOTAL TIME: {elapsed:.1f} seconds ({elapsed/60:.2f} minutes)")
    print("=" * 80)

    if result:
        print("\nPhase breakdown:")
        for phase_key in ['phase_1', 'phase_2', 'phase_3', 'phase_4', 'phase_5', 'phase_6']:
            if phase_key in result:
                phase_data = result[phase_key]
                if isinstance(phase_data, dict) and 'duration_seconds' in phase_data:
                    duration = phase_data['duration_seconds']
                    pct = (duration / elapsed * 100) if elapsed > 0 else 0
                    print(f"  {phase_key}: {duration:.1f}s ({pct:.1f}%)")

if __name__ == '__main__':
    asyncio.run(profile_single_date())
