#!/usr/bin/env python3
"""
Railway Daily Automation Script

Runs after market close on trading days to sync data and calculate metrics.

Usage:
  uv run python scripts/automation/railway_daily_batch.py

Environment Variables Required:
  DATABASE_URL - PostgreSQL connection string
  POLYGON_API_KEY - Market data API key
  FMP_API_KEY - Financial Modeling Prep API key
  OPENAI_API_KEY - OpenAI API key for chat features

Workflow:
  The batch orchestrator handles everything:
  - Trading day detection and adjustment
  - Phase 0: Company profile sync (on final date only)
  - Phase 1: Market data collection
  - Phase 2: Fundamental data collection
  - Phase 3: P&L calculation & snapshots
  - Phase 4: Position market value updates
  - Phase 5: Sector tag restoration
  - Phase 6: Risk analytics

Phase 11.1 Change: Simplified to use batch orchestrator directly.
All trading day logic, company profile sync, and batch processing is now
handled by the batch orchestrator's run_daily_batch_with_backfill() method.
This eliminates code duplication and ensures Railway uses the same code path
as local batch processing (scripts/batch_processing/run_batch.py).
"""

import os
import asyncio
import sys
import datetime

# Fix Railway DATABASE_URL format BEFORE any imports
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print("✅ Converted DATABASE_URL to use asyncpg driver")

# Add parent directory to path for imports
sys.path.insert(0, '/app')  # Railway container path
sys.path.insert(0, '.')      # Local development path

from app.config import settings
from app.core.logging import get_logger
from app.batch.batch_orchestrator import batch_orchestrator
from app.database import AsyncSessionLocal
from app.db.seed_factors import seed_factors

logger = get_logger(__name__)


def check_v2_guard():
    """
    V2 Architecture Guard: Redirect to V2 batch when enabled.

    When BATCH_V2_ENABLED=true, this script delegates to the V2 batch runner
    instead of running V1 legacy batch. This allows seamless migration without
    changing Railway cron configuration.
    """
    if settings.BATCH_V2_ENABLED:
        print("=" * 60)
        print("[V2] V2 BATCH MODE ENABLED - DELEGATING TO V2 RUNNER")
        print("=" * 60)
        print("BATCH_V2_ENABLED=true detected.")
        print("Delegating to V2 batch runner...")
        print("=" * 60)

        # Import and run V2 batch
        import subprocess
        import sys

        # Get the path to the V2 script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        v2_script = os.path.join(script_dir, "railway_daily_batch_v2.py")

        # Run V2 script and exit with its exit code
        result = subprocess.run(
            [sys.executable, v2_script],
            cwd=os.path.dirname(script_dir),  # Set cwd to backend/scripts
        )
        sys.exit(result.returncode)


async def ensure_factor_definitions():
    """Ensure factor definitions exist before running batch.

    This is critical because:
    1. Factor definitions must exist for analytics_runner to save exposures
    2. Stress testing needs factor exposures to calculate scenario impacts
    3. seed_factors() is idempotent - won't duplicate existing factors
    """
    logger.info("Verifying factor definitions...")
    async with AsyncSessionLocal() as db:
        await seed_factors(db)
        await db.commit()
    logger.info("✅ Factor definitions verified/seeded")


async def main():
    """Main entry point for daily batch job."""
    # V2 Guard: Exit early if V2 batch mode is enabled
    check_v2_guard()

    job_start = datetime.datetime.now()

    # Use print() for critical messages - logger.info() doesn't show in Railway logs
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║       SIGMASIGHT DAILY BATCH WORKFLOW - STARTING (V1)        ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"Timestamp: {job_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    try:
        # Ensure factor definitions exist before running batch
        await ensure_factor_definitions()

        # Run the batch orchestrator - it handles everything:
        # - Trading day detection and adjustment (to previous trading day if needed)
        # - Phase 0: Company profile sync (on final date only)
        # - Phase 1: Market data collection (1-year lookback)
        # - Phase 2: Fundamental data collection (earnings-driven)
        # - Phase 3: P&L calculation & snapshots (equity rollforward)
        # - Phase 4: Position market value updates (for analytics accuracy)
        # - Phase 5: Sector tag restoration (auto-tag from company profiles)
        # - Phase 6: Risk analytics (betas, factors, volatility, correlations)

        logger.info("Starting batch orchestrator with automatic backfill...")
        results = await batch_orchestrator.run_daily_batch_with_backfill()

        # Calculate total duration
        job_end = datetime.datetime.now()
        total_duration = (job_end - job_start).total_seconds()

        # Print completion summary - use print() for Railway visibility
        print("=" * 60)
        print("DAILY BATCH JOB COMPLETE")
        print("=" * 60)
        print(f"Start Time:    {job_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time:      {job_end.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Runtime: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
        print(f"Results: {results}")
        print("=" * 60)

        # Check for success
        if results.get('success'):
            print("✅ All operations completed successfully")
            sys.exit(0)
        else:
            print(f"⚠️ Job completed with issues: {results.get('message', 'Unknown error')}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("⚠️ Job interrupted by user (Ctrl+C)")
        sys.exit(130)  # Standard exit code for SIGINT

    except Exception as e:
        print(f"❌ FATAL ERROR: Daily batch job failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
