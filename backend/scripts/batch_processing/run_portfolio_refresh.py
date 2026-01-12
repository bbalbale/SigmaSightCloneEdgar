#!/usr/bin/env python3
"""
V2 Portfolio Refresh Runner - Railway Cron Entry Point

Runs at 9:30 PM ET (30 minutes after symbol batch) to refresh all portfolios:
1. Wait for symbol batch completion
2. Wait for pending symbol onboarding
3. Create snapshots using cached prices/factors

Usage:
  # Normal cron run (waits for symbol batch)
  uv run python scripts/batch_processing/run_portfolio_refresh.py

  # Force run without waiting
  uv run python scripts/batch_processing/run_portfolio_refresh.py --no-wait

  # Specific date
  uv run python scripts/batch_processing/run_portfolio_refresh.py --date 2026-01-10

Environment Variables Required:
  BATCH_V2_ENABLED=true     - Must be enabled for V2 mode
  DATABASE_URL              - PostgreSQL connection string

Railway Cron Configuration:
  Schedule: 30 2 * * 1-5  (9:30 PM ET = 2:30 AM UTC next day)
  Command: python scripts/batch_processing/run_portfolio_refresh.py
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
    If V1 mode, portfolio refresh happens as part of railway_daily_batch.py.
    """
    if not settings.BATCH_V2_ENABLED:
        print("=" * 60)
        print("V2 BATCH MODE NOT ENABLED")
        print("=" * 60)
        print("BATCH_V2_ENABLED=false detected.")
        print("")
        print("To use V2 portfolio refresh, set BATCH_V2_ENABLED=true")
        print("")
        print("For V1 mode, portfolio refresh is part of:")
        print("  python scripts/automation/railway_daily_batch.py")
        print("=" * 60)
        sys.exit(0)  # Exit 0 = graceful skip (not an error)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="V2 Portfolio Refresh Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Target date (YYYY-MM-DD). Defaults to most recent trading day.",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for symbol batch or onboarding (force run).",
    )
    return parser.parse_args()


async def main():
    """Main entry point for V2 portfolio refresh."""
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

    wait_for_symbol_batch = not args.no_wait
    wait_for_onboarding = not args.no_wait

    print("=" * 60)
    print("  V2 PORTFOLIO REFRESH RUNNER - STARTING")
    print("=" * 60)
    print(f"Timestamp:         {job_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target Date:       {target_date or 'auto (most recent trading day)'}")
    print(f"Wait for Batch:    {wait_for_symbol_batch}")
    print(f"Wait for Onboard:  {wait_for_onboarding}")
    print("=" * 60)

    try:
        # Import here to avoid loading before DATABASE_URL fix
        from app.batch.v2.portfolio_refresh_runner import run_portfolio_refresh

        # Run the portfolio refresh
        result = await run_portfolio_refresh(
            target_date=target_date,
            wait_for_symbol_batch=wait_for_symbol_batch,
            wait_for_onboarding=wait_for_onboarding,
        )

        # Calculate duration
        job_end = datetime.now()
        duration = (job_end - job_start).total_seconds()

        # Print results
        print("=" * 60)
        print("  V2 PORTFOLIO REFRESH RUNNER - COMPLETE")
        print("=" * 60)
        print(f"Duration:          {duration:.1f}s ({duration/60:.1f} min)")
        print(f"Success:           {result.get('success', False)}")
        print(f"Portfolios:        {result.get('portfolios_processed', 0)} processed")
        print(f"Snapshots:         {result.get('snapshots_created', 0)} created")

        if result.get('error'):
            print(f"Error:             {result.get('error')}: {result.get('message')}")

        print("=" * 60)

        # Exit with appropriate code
        if result.get('success'):
            print("Portfolio refresh completed successfully")
            sys.exit(0)
        else:
            print("Portfolio refresh completed with errors")
            sys.exit(1)

    except KeyboardInterrupt:
        print("Portfolio refresh interrupted by user (Ctrl+C)")
        sys.exit(130)

    except Exception as e:
        print(f"FATAL ERROR: Portfolio refresh failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
