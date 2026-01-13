#!/usr/bin/env python3
"""
Run V2 batch for a specific date.

Usage:
    python scripts/maintenance/run_v2_batch_for_date.py 2026-01-12
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.batch.v2.symbol_batch_runner import run_symbol_batch
from app.batch.v2.portfolio_refresh_runner import run_portfolio_refresh


async def main(target_date):
    """Run V2 batch for a specific date."""

    print("=" * 60)
    print(f"  V2 BATCH FOR: {target_date}")
    print("=" * 60)
    sys.stdout.flush()

    # Phase 1: Symbol Batch
    print("-" * 60)
    print("PHASE 1: SYMBOL BATCH")
    print("-" * 60)
    sys.stdout.flush()

    symbol_result = await run_symbol_batch(
        target_date=target_date,
        backfill=False,  # Only run for this specific date
    )

    print(f"Symbol Batch Result: success={symbol_result.get('success')}")
    if symbol_result.get('errors'):
        print(f"  Errors: {len(symbol_result.get('errors', []))}")
        for err in symbol_result.get('errors', [])[:5]:
            print(f"    - {err}")
    sys.stdout.flush()

    # Phase 2: Portfolio Refresh
    if symbol_result.get('success'):
        print("-" * 60)
        print("PHASE 2: PORTFOLIO REFRESH")
        print("-" * 60)
        sys.stdout.flush()

        portfolio_result = await run_portfolio_refresh(
            target_date=target_date,
            wait_for_symbol_batch=False,
            wait_for_onboarding=False,
        )

        print(f"Portfolio Refresh Result: success={portfolio_result.get('success')}")
        print(f"  Portfolios processed: {portfolio_result.get('portfolios_processed', 0)}")
        print(f"  Snapshots created: {portfolio_result.get('snapshots_created', 0)}")
        if portfolio_result.get('errors'):
            print(f"  Errors:")
            for err in portfolio_result.get('errors', [])[:5]:
                print(f"    - {err}")
    else:
        print("[WARN] Skipping portfolio refresh due to symbol batch failure")
        portfolio_result = None

    sys.stdout.flush()

    # Summary
    print("=" * 60)
    print("  COMPLETE")
    print("=" * 60)
    print(f"Symbol Batch: {'SUCCESS' if symbol_result and symbol_result.get('success') else 'FAILED'}")
    print(f"Portfolio:    {'SUCCESS' if portfolio_result and portfolio_result.get('success') else 'SKIPPED/FAILED'}")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/maintenance/run_v2_batch_for_date.py YYYY-MM-DD")
        sys.exit(1)

    try:
        target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Invalid date format '{sys.argv[1]}'. Use YYYY-MM-DD format.")
        sys.exit(1)

    asyncio.run(main(target_date))
