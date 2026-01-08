#!/usr/bin/env python
"""
Manual Catch-Up Batch Script

Runs batch processing with explicit start/end dates to catch up portfolios
that have fallen behind due to the global watermark bug.

Usage (from Railway shell):
    python scripts/manual_catchup_batch.py

Or with custom dates:
    python scripts/manual_catchup_batch.py --start 2026-01-06 --end 2026-01-08

Created: 2026-01-08
Issue: TESTSCOTTY_BATCH_PROCESSING_DEBUG_AND_FIX_PLAN.md
"""

import asyncio
import argparse
from datetime import date, datetime
import sys
import os

# Add backend to path if running from scripts directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def run_catchup(start_date: date, end_date: date, dry_run: bool = False):
    """Run catch-up batch processing."""
    from app.batch.batch_orchestrator import batch_orchestrator
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    print("=" * 60)
    print("MANUAL CATCH-UP BATCH")
    print("=" * 60)
    print(f"Start Date: {start_date}")
    print(f"End Date:   {end_date}")
    print(f"Dry Run:    {dry_run}")
    print("=" * 60)

    if dry_run:
        print("\nDRY RUN MODE - No changes will be made")
        print("Remove --dry-run flag to execute")
        return

    print("\nStarting batch processing...")
    print("This may take several minutes.\n")

    try:
        result = await batch_orchestrator.run_daily_batch_with_backfill(
            start_date=start_date,
            end_date=end_date,
            portfolio_ids=None  # All portfolios
        )

        print("\n" + "=" * 60)
        print("BATCH COMPLETE")
        print("=" * 60)
        print(f"Success:         {result.get('success')}")
        print(f"Dates Processed: {result.get('dates_processed', 0)}")

        if result.get('errors'):
            print(f"\nErrors ({len(result['errors'])}):")
            for err in result['errors'][:10]:  # Show first 10
                print(f"  - {err}")
            if len(result['errors']) > 10:
                print(f"  ... and {len(result['errors']) - 10} more")
        else:
            print("\nNo errors!")

        return result

    except Exception as e:
        print(f"\nERROR: {e}")
        logger.exception("Catch-up batch failed")
        raise


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def main():
    parser = argparse.ArgumentParser(
        description="Run catch-up batch processing for all portfolios"
    )
    parser.add_argument(
        "--start",
        type=parse_date,
        default=date(2026, 1, 6),
        help="Start date (YYYY-MM-DD). Default: 2026-01-06"
    )
    parser.add_argument(
        "--end",
        type=parse_date,
        default=date.today(),
        help="End date (YYYY-MM-DD). Default: today"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )

    args = parser.parse_args()

    # Validate dates
    if args.start > args.end:
        print(f"ERROR: Start date ({args.start}) must be before end date ({args.end})")
        sys.exit(1)

    if args.end > date.today():
        print(f"WARNING: End date ({args.end}) is in the future, using today ({date.today()})")
        args.end = date.today()

    # Run the catch-up
    asyncio.run(run_catchup(args.start, args.end, args.dry_run))


if __name__ == "__main__":
    main()
