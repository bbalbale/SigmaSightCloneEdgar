#!/usr/bin/env python3
"""
V2 Symbol Batch Runner - Railway Cron Entry Point

Runs at 9:00 PM ET (after market close) to process all symbols:
1. Company profiles sync
2. Market data collection (prices)
3. Fundamental data (earnings-driven)
4. Factor calculations

Usage:
  # Normal cron run (with backfill)
  uv run python scripts/batch_processing/run_symbol_batch.py

  # Specific date without backfill
  uv run python scripts/batch_processing/run_symbol_batch.py --date 2026-01-10 --no-backfill

Environment Variables Required:
  BATCH_V2_ENABLED=true     - Must be enabled for V2 mode
  DATABASE_URL              - PostgreSQL connection string
  POLYGON_API_KEY           - Market data API key
  FMP_API_KEY              - Financial Modeling Prep API key

Railway Cron Configuration:
  Schedule: 0 2 * * 1-5  (9 PM ET = 2 AM UTC next day)
  Command: python scripts/batch_processing/run_symbol_batch.py
"""

import os
import sys
import asyncio
import argparse
from datetime import date, datetime

# Fix Railway DATABASE_URL format BEFORE any imports
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print("Converted DATABASE_URL to use asyncpg driver")

# Add parent directory to path for imports
sys.path.insert(0, '/app')  # Railway container path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def check_v2_enabled():
    """
    Verify V2 batch mode is enabled.

    This script should only run when BATCH_V2_ENABLED=true.
    If V1 mode, the legacy railway_daily_batch.py should be used instead.
    """
    if not settings.BATCH_V2_ENABLED:
        print("=" * 60)
        print("V2 BATCH MODE NOT ENABLED")
        print("=" * 60)
        print("BATCH_V2_ENABLED=false detected.")
        print("")
        print("To use V2 symbol batch, set BATCH_V2_ENABLED=true")
        print("")
        print("For V1 mode, use:")
        print("  python scripts/automation/railway_daily_batch.py")
        print("=" * 60)
        sys.exit(0)  # Exit 0 = graceful skip (not an error)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="V2 Symbol Batch Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Target date (YYYY-MM-DD). Defaults to most recent trading day.",
    )
    parser.add_argument(
        "--no-backfill",
        action="store_true",
        help="Disable backfill mode (only process target date).",
    )
    return parser.parse_args()


async def main():
    """Main entry point for V2 symbol batch."""
    # Check V2 mode is enabled
    check_v2_enabled()

    args = parse_args()
    job_start = datetime.now()

    # Parse target date if provided
    target_date = None
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"Invalid date format: {args.date}. Use YYYY-MM-DD.")
            sys.exit(1)

    backfill = not args.no_backfill

    print("=" * 60)
    print("  V2 SYMBOL BATCH RUNNER - STARTING")
    print("=" * 60)
    print(f"Timestamp:    {job_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Date:  {target_date or 'auto (most recent trading day)'}")
    print(f"Backfill:     {backfill}")
    print("=" * 60)

    try:
        # Import here to avoid loading before DATABASE_URL fix
        from app.batch.v2.symbol_batch_runner import run_symbol_batch

        # Run the symbol batch
        result = await run_symbol_batch(
            target_date=target_date,
            backfill=backfill,
        )

        # Calculate duration
        job_end = datetime.now()
        duration = (job_end - job_start).total_seconds()

        # Print results
        print("=" * 60)
        print("  V2 SYMBOL BATCH RUNNER - COMPLETE")
        print("=" * 60)
        print(f"Duration:     {duration:.1f}s ({duration/60:.1f} min)")
        print(f"Success:      {result.get('success', False)}")
        print(f"Dates:        {result.get('dates_processed', 0)} processed, {result.get('dates_failed', 0)} failed")

        if result.get('error'):
            print(f"Error:        {result.get('error')}: {result.get('message')}")

        print("=" * 60)

        # Exit with appropriate code
        if result.get('success'):
            print("Symbol batch completed successfully")
            sys.exit(0)
        else:
            print("Symbol batch completed with errors")
            sys.exit(1)

    except KeyboardInterrupt:
        print("Symbol batch interrupted by user (Ctrl+C)")
        sys.exit(130)

    except Exception as e:
        print(f"FATAL ERROR: Symbol batch failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
