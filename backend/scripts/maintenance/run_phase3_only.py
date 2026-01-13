#!/usr/bin/env python3
"""
Run Phase 3 + Portfolio Refresh (Phases 3-6)

Use this when Phase 0/1 (valuations/prices) already succeeded but Phase 3 failed.
Runs:
- Phase 3: Factor calculations (Ridge + Spread) for symbols
- Portfolio Refresh:
  - Phase 3: Snapshots and P&L for all portfolios
  - Phase 4: Correlation calculations
  - Phase 5: Factor aggregation (symbol -> portfolio level)
  - Phase 6: Stress test calculations

Usage:
    # Railway SSH
    python scripts/maintenance/run_phase3_only.py

    # With specific date
    python scripts/maintenance/run_phase3_only.py 2026-01-12

    # Local
    uv run python scripts/maintenance/run_phase3_only.py
"""

import asyncio
import sys
import os
from datetime import date, datetime

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.batch.v2.symbol_batch_runner import (
    _run_phase_3_factors,
    _get_symbols_to_process,
    ensure_factor_definitions,
)
from app.batch.v2.portfolio_refresh_runner import run_portfolio_refresh


async def run_phase3_and_portfolio_refresh(calc_date: date = None):
    """Run Phase 3 factor calculations + Portfolio Refresh."""

    if calc_date is None:
        calc_date = date.today()

    print("=" * 60)
    print("  PHASE 3 + PORTFOLIO REFRESH")
    print("=" * 60)
    print(f"Calculation Date: {calc_date}")
    print()

    # =========================================================================
    # PHASE 3: Factor Calculations
    # =========================================================================
    print("[PHASE 3] Factor Calculations")
    print("-" * 60)

    # Step 1: Collect symbols
    print("[1/3] Collecting symbols to process...")
    sys.stdout.flush()
    symbols = await _get_symbols_to_process()
    print(f"      Found {len(symbols)} symbols")
    sys.stdout.flush()

    # Step 2: Ensure factor definitions exist
    print("[2/3] Ensuring factor definitions...")
    sys.stdout.flush()
    await ensure_factor_definitions()
    print("      Factor definitions verified")
    sys.stdout.flush()

    # Step 3: Run Phase 3
    print("[3/3] Running factor calculations...")
    sys.stdout.flush()

    try:
        phase3_result = await _run_phase_3_factors(symbols, calc_date)

        print(f"\n[PHASE 3 COMPLETE]")
        print(f"  Calculated: {phase3_result.get('calculated', 0)}")
        print(f"  Cached:     {phase3_result.get('cached', 0)}")
        print(f"  Failed:     {phase3_result.get('failed', 0)}")

        ridge = phase3_result.get('ridge_results', {})
        spread = phase3_result.get('spread_results', {})
        print(f"  Ridge:  calc={ridge.get('calculated', 0)}, cached={ridge.get('cached', 0)}, fail={ridge.get('failed', 0)}")
        print(f"  Spread: calc={spread.get('calculated', 0)}, cached={spread.get('cached', 0)}, fail={spread.get('failed', 0)}")
        sys.stdout.flush()

        errors = phase3_result.get('errors', [])
        if errors:
            print(f"\n  Errors ({len(errors)} total):")
            for err in errors[:3]:
                print(f"    - {err}")
            if len(errors) > 3:
                print(f"    ... and {len(errors) - 3} more")

    except Exception as e:
        print(f"\n[ERROR] Phase 3 failed: {e}")
        sys.stdout.flush()
        raise

    # =========================================================================
    # PORTFOLIO REFRESH: Phases 3-6
    # =========================================================================
    print("\n" + "=" * 60)
    print("[PORTFOLIO REFRESH] Phases 3-6 (Snapshots, Correlations, Factors, Stress)")
    print("-" * 60)
    sys.stdout.flush()

    try:
        # Run portfolio refresh (skip waiting since we just ran Phase 3)
        portfolio_result = await run_portfolio_refresh(
            target_date=calc_date,
            wait_for_symbol_batch=False,  # We just ran it
            wait_for_onboarding=False,    # Skip waiting
        )

        print(f"\n[PORTFOLIO REFRESH COMPLETE]")
        print(f"  Success:        {portfolio_result.get('success', False)}")
        print(f"  Portfolios:     {portfolio_result.get('portfolios_processed', 0)}")
        print(f"  Total Duration: {portfolio_result.get('duration_seconds', 0):.1f}s")
        print()
        print(f"  Phase Results:")
        print(f"    Phase 3 (Snapshots):    {portfolio_result.get('snapshots_created', 0)} created")
        print(f"    Phase 4 (Correlations): {portfolio_result.get('correlations_calculated', 0)} calculated")
        phase_durations = portfolio_result.get('phase_durations', {})
        phase5_status = "completed" if 'phase_5_factor_aggregation' in phase_durations else "skipped"
        print(f"    Phase 5 (Factors):      {phase5_status}")
        print(f"    Phase 6 (Stress Tests): {portfolio_result.get('stress_tests_calculated', 0)} calculated")

        # Show phase durations if available
        if phase_durations:
            print()
            print(f"  Phase Durations:")
            for phase_name, duration in phase_durations.items():
                print(f"    {phase_name}: {duration:.1f}s")
        sys.stdout.flush()

        if portfolio_result.get('errors'):
            print(f"\n  Errors ({len(portfolio_result['errors'])} total):")
            for err in portfolio_result['errors'][:5]:
                print(f"    - {err}")
            if len(portfolio_result['errors']) > 5:
                print(f"    ... and {len(portfolio_result['errors']) - 5} more")

    except Exception as e:
        print(f"\n[ERROR] Portfolio refresh failed: {e}")
        sys.stdout.flush()
        raise

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 60)
    print("  ALL COMPLETE")
    print("=" * 60)
    print(f"Date:                    {calc_date}")
    print(f"Symbol Phase 3:          {phase3_result.get('calculated', 0)} calculated, {phase3_result.get('failed', 0)} failed")
    print(f"Portfolio Phase 3:       {portfolio_result.get('snapshots_created', 0)} snapshots")
    print(f"Portfolio Phase 4:       {portfolio_result.get('correlations_calculated', 0)} correlations")
    pf_phase_durations = portfolio_result.get('phase_durations', {})
    pf_phase5 = "completed" if 'phase_5_factor_aggregation' in pf_phase_durations else "skipped"
    print(f"Portfolio Phase 5:       {pf_phase5}")
    print(f"Portfolio Phase 6:       {portfolio_result.get('stress_tests_calculated', 0)} stress tests")
    print(f"Total Duration:          {portfolio_result.get('duration_seconds', 0):.1f}s")
    print("=" * 60)

    return {
        "phase3": phase3_result,
        "portfolio_refresh": portfolio_result,
    }


if __name__ == "__main__":
    # Allow passing a date as argument
    if len(sys.argv) > 1:
        calc_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        calc_date = date.today()

    asyncio.run(run_phase3_and_portfolio_refresh(calc_date))
