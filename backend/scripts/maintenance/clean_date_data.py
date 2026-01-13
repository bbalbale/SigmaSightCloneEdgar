#!/usr/bin/env python3
"""
Clean all calculation data for a specific date to allow fresh cron run.

Deletes:
- market_data_cache (prices)
- symbol_factor_exposures (factor calculations)
- portfolio_snapshots (P&L snapshots)
- company_profiles valuation fields (PE, PB, etc.)

Usage:
    python scripts/maintenance/clean_date_data.py 2026-01-12

    # Dry run (show what would be deleted)
    python scripts/maintenance/clean_date_data.py 2026-01-12 --dry-run
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.database import get_async_session


async def clean_date_data(target_date: date, dry_run: bool = False):
    """Clean all calculation data for a specific date."""

    print("=" * 60)
    print(f"  CLEAN DATA FOR: {target_date}")
    print(f"  Mode: {'DRY RUN' if dry_run else 'DELETE'}")
    print("=" * 60)

    # Tables with date column
    tables_with_date = [
        ("market_data_cache", "date"),
        ("symbol_factor_exposures", "calculation_date"),
        ("portfolio_snapshots", "snapshot_date"),
    ]

    total_deleted = 0

    for table, date_column in tables_with_date:
        async with get_async_session() as db:
            try:
                # Count rows to delete
                count_result = await db.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE {date_column} = :target_date"),
                    {"target_date": target_date}
                )
                count = count_result.scalar() or 0

                if count == 0:
                    print(f"  [SKIP] {table}: No rows for {target_date}")
                    continue

                if dry_run:
                    print(f"  [DRY RUN] {table}: Would delete {count} rows")
                else:
                    await db.execute(
                        text(f"DELETE FROM {table} WHERE {date_column} = :target_date"),
                        {"target_date": target_date}
                    )
                    await db.commit()
                    print(f"  [OK] {table}: Deleted {count} rows")
                    total_deleted += count

            except Exception as e:
                await db.rollback()
                print(f"  [ERROR] {table}: {e}")

    # Reset company_profiles valuation fields (updated_at based)
    async with get_async_session() as db:
        try:
            # Count profiles updated today
            count_result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM company_profiles
                    WHERE DATE(updated_at) = :target_date
                    AND (pe_ratio IS NOT NULL OR pb_ratio IS NOT NULL)
                """),
                {"target_date": target_date}
            )
            count = count_result.scalar() or 0

            if count == 0:
                print(f"  [SKIP] company_profiles: No valuations updated on {target_date}")
            elif dry_run:
                print(f"  [DRY RUN] company_profiles: Would reset valuations for {count} profiles")
            else:
                # Reset valuation fields to NULL for profiles updated today
                await db.execute(
                    text("""
                        UPDATE company_profiles
                        SET pe_ratio = NULL,
                            pb_ratio = NULL,
                            ps_ratio = NULL,
                            peg_ratio = NULL,
                            enterprise_value = NULL,
                            ev_to_ebitda = NULL,
                            ev_to_revenue = NULL,
                            price_to_book = NULL,
                            price_to_sales = NULL
                        WHERE DATE(updated_at) = :target_date
                    """),
                    {"target_date": target_date}
                )
                await db.commit()
                print(f"  [OK] company_profiles: Reset valuations for {count} profiles")

        except Exception as e:
            await db.rollback()
            print(f"  [ERROR] company_profiles: {e}")

    print("=" * 60)
    if dry_run:
        print("  DRY RUN COMPLETE - No data was deleted")
    else:
        print(f"  COMPLETE - Deleted {total_deleted} total rows")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean calculation data for a specific date")
    parser.add_argument("date", help="Date to clean (YYYY-MM-DD format)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    args = parser.parse_args()

    # Parse and validate date format
    try:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD format.")
        sys.exit(1)

    asyncio.run(clean_date_data(target_date, dry_run=args.dry_run))
