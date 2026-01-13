#!/usr/bin/env python3
"""
Run Phase 3 (Factor Calculations) Only

Use this when Phase 1 (market data) already succeeded but Phase 3 failed.
Skips Phase 0 (valuations) and Phase 1 (prices).

Usage:
    # Railway SSH
    python scripts/maintenance/run_phase3_only.py

    # Local
    uv run python scripts/maintenance/run_phase3_only.py
"""

import asyncio
import sys
import os
from datetime import date

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.batch.v2.symbol_batch_runner import (
    _run_phase_3_factors,
    _collect_symbols_to_process,
    ensure_factor_definitions,
)


async def run_phase3_only(calc_date: date = None):
    """Run only Phase 3 factor calculations."""

    if calc_date is None:
        calc_date = date.today()

    print("=" * 60)
    print("  PHASE 3 ONLY - Factor Calculations")
    print("=" * 60)
    print(f"Calculation Date: {calc_date}")
    print()

    # Step 1: Collect symbols
    print("[1/3] Collecting symbols to process...")
    sys.stdout.flush()
    symbols = await _collect_symbols_to_process()
    print(f"      Found {len(symbols)} symbols")
    sys.stdout.flush()

    # Step 2: Ensure factor definitions exist
    print("[2/3] Ensuring factor definitions...")
    sys.stdout.flush()
    await ensure_factor_definitions()
    print("      Factor definitions verified")
    sys.stdout.flush()

    # Step 3: Run Phase 3
    print("[3/3] Running Phase 3 factor calculations...")
    sys.stdout.flush()

    try:
        result = await _run_phase_3_factors(symbols, calc_date)

        print("\n" + "=" * 60)
        print("  PHASE 3 COMPLETE")
        print("=" * 60)
        print(f"Calculated: {result.get('calculated', 0)}")
        print(f"Cached:     {result.get('cached', 0)}")
        print(f"Failed:     {result.get('failed', 0)}")

        ridge = result.get('ridge_results', {})
        spread = result.get('spread_results', {})
        print(f"\nRidge:  calc={ridge.get('calculated', 0)}, cached={ridge.get('cached', 0)}, fail={ridge.get('failed', 0)}")
        print(f"Spread: calc={spread.get('calculated', 0)}, cached={spread.get('cached', 0)}, fail={spread.get('failed', 0)}")

        errors = result.get('errors', [])
        if errors:
            print(f"\nErrors ({len(errors)} total):")
            for err in errors[:5]:
                print(f"  - {err}")
            if len(errors) > 5:
                print(f"  ... and {len(errors) - 5} more")

        print("=" * 60)
        return result

    except Exception as e:
        print(f"\n[ERROR] Phase 3 failed: {e}")
        sys.stdout.flush()
        raise


if __name__ == "__main__":
    # Allow passing a date as argument
    if len(sys.argv) > 1:
        from datetime import datetime
        calc_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        calc_date = date.today()

    asyncio.run(run_phase3_only(calc_date))
