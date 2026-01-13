#!/usr/bin/env python3
"""
Clear V2 calculation data for a SPECIFIC date (keeps market data).

Use this to re-run Phase 3+ without re-fetching market data.

Clears:
- symbol_factor_exposures (V2 symbol-level factors)
- portfolio_snapshots (P&L snapshots)
- factor_exposures (portfolio-level aggregated factors)
- correlation_calculations + pairwise_correlations
- stress_test_results
- position_greeks
- position_factor_exposures (V1 position-level factors)

Does NOT clear:
- market_data_cache (historical prices) - preserved for faster re-runs
- company_profiles (valuation data)

Usage:
    # Railway SSH
    python scripts/maintenance/clear_calcs_for_date.py 2026-01-12

    # Dry run (show what would be deleted)
    python scripts/maintenance/clear_calcs_for_date.py 2026-01-12 --dry-run

    # Local
    uv run python scripts/maintenance/clear_calcs_for_date.py 2026-01-12
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.database import get_async_session


# Tables to clear with their date column names
# Format: (table_name, date_column, use_date_cast)
# use_date_cast=True for DateTime columns that need DATE() cast
CALC_TABLES = [
    ("symbol_factor_exposures", "calculation_date", False),      # V2 symbol-level factors
    ("portfolio_snapshots", "snapshot_date", False),             # P&L snapshots
    ("factor_exposures", "calculation_date", False),             # Portfolio-level factors
    ("correlation_calculations", "calculation_date", True),      # DateTime column - needs DATE() cast
    ("pairwise_correlations", "calculation_date", True),         # DateTime column - needs DATE() cast
    ("stress_test_results", "calculation_date", False),          # Stress test results
    ("position_greeks", "calculation_date", False),              # Options greeks
    ("position_factor_exposures", "calculation_date", False),    # V1 position-level factors
    ("position_market_betas", "calc_date", False),               # Market betas
    ("position_interest_rate_betas", "calculation_date", False), # IR betas
    ("position_volatility", "calculation_date", False),          # Volatility metrics (singular!)
    ("market_risk_scenarios", "calculation_date", False),        # Risk scenarios
    ("factor_correlations", "calculation_date", False),          # Factor correlations
]


async def clear_calcs_for_date(target_date: date, dry_run: bool = False):
    """Clear all V2 calculation data for a specific date."""

    print("=" * 60)
    print(f"  CLEAR CALCULATIONS FOR: {target_date}")
    print(f"  Mode: {'DRY RUN (no changes)' if dry_run else 'DELETE'}")
    print("=" * 60)
    print()

    total_deleted = 0
    results = {}

    async with get_async_session() as db:
        for table_name, date_column, use_date_cast in CALC_TABLES:
            try:
                # Build WHERE clause - use DATE() cast for DateTime columns
                if use_date_cast:
                    where_clause = f"DATE({date_column}) = :target_date"
                else:
                    where_clause = f"{date_column} = :target_date"

                # Count rows to delete
                count_sql = text(f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}")
                count_result = await db.execute(count_sql, {"target_date": target_date})
                count = count_result.scalar() or 0

                if count == 0:
                    print(f"  [SKIP] {table_name}: No rows for {target_date}")
                    results[table_name] = 0
                    continue

                if dry_run:
                    print(f"  [DRY]  {table_name}: Would delete {count} rows")
                    results[table_name] = count
                else:
                    # Delete rows for the specific date
                    delete_sql = text(f"DELETE FROM {table_name} WHERE {where_clause}")
                    await db.execute(delete_sql, {"target_date": target_date})
                    print(f"  [OK]   {table_name}: Deleted {count} rows")
                    results[table_name] = count
                    total_deleted += count

            except Exception as e:
                error_msg = str(e)
                # Handle table not existing (common for unused V1 tables)
                if "does not exist" in error_msg or "relation" in error_msg.lower():
                    print(f"  [SKIP] {table_name}: Table does not exist")
                else:
                    print(f"  [ERR]  {table_name}: {error_msg}")
                results[table_name] = 0

        # Commit all deletions
        if not dry_run:
            await db.commit()

    # Summary
    print()
    print("=" * 60)
    if dry_run:
        would_delete = sum(results.values())
        print(f"  DRY RUN COMPLETE")
        print(f"  Would delete: {would_delete} total rows")
    else:
        print(f"  DELETE COMPLETE")
        print(f"  Deleted: {total_deleted} total rows")
    print()
    print("  Market data (prices) PRESERVED")
    print("  Run Phase 3+ to regenerate calculations")
    print("=" * 60)

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Clear V2 calculation data for a specific date (keeps market data)"
    )
    parser.add_argument(
        "date",
        help="Date to clear (YYYY-MM-DD format)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting"
    )
    args = parser.parse_args()

    # Parse and validate date
    try:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD.")
        sys.exit(1)

    # Run
    asyncio.run(clear_calcs_for_date(target_date, dry_run=args.dry_run))
