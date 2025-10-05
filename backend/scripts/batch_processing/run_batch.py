#!/usr/bin/env python
"""
Run batch calculations for portfolios.

This script runs the complete batch processing workflow for portfolio analytics,
including portfolio aggregation, Greeks calculations, factor analysis, market risk,
snapshots, and correlations.

Usage:
    python scripts/batch_processing/run_batch.py                    # Run for all portfolios
    python scripts/batch_processing/run_batch.py --portfolio <UUID>  # Run for specific portfolio
    python scripts/batch_processing/run_batch.py --correlations      # Include correlation calculations
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Configure UTF-8 output handling for Windows
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2
from app.core.logging import get_logger

logger = get_logger(__name__)


class BatchRunner:
    """Batch processing runner for portfolio calculations."""

    def __init__(self):
        self.start_time = datetime.now()
        self.results = {}

    async def run_batch_processing(
        self,
        portfolio_id: Optional[str] = None,
        run_correlations: bool = False
    ) -> Dict[str, Any]:
        """Run batch calculations for portfolio(s)."""
        print("\n" + "=" * 60)
        print("🔄 BATCH PROCESSING")
        print("=" * 60)

        try:
            if portfolio_id:
                print(f"Running batch for portfolio: {portfolio_id}")
            else:
                print("Running batch for all portfolios")

            batch_start = datetime.now()

            results = await batch_orchestrator_v2.run_daily_batch_sequence(
                portfolio_id=portfolio_id,
                run_correlations=run_correlations
            )

            batch_duration = (datetime.now() - batch_start).total_seconds()

            # Analyze results
            job_summary = {}
            for result in results:
                job_name = result.get('job_name', 'unknown')
                status = result.get('status', 'unknown')
                portfolio_name = result.get('portfolio_name', 'unknown')

                # Clean job name
                clean_name = job_name.split('_')[0] if '_' in job_name else job_name

                if portfolio_name not in job_summary:
                    job_summary[portfolio_name] = {"success": 0, "failed": 0, "jobs": []}

                if status == 'completed':
                    job_summary[portfolio_name]["success"] += 1
                else:
                    job_summary[portfolio_name]["failed"] += 1

                job_summary[portfolio_name]["jobs"].append({
                    "name": clean_name,
                    "status": status,
                    "duration": result.get('duration_seconds', 0)
                })

            # Print summary
            print(f"\n✅ Batch processing completed in {batch_duration:.2f} seconds")
            print("\nJob Summary by Portfolio:")
            print("-" * 40)

            for portfolio, summary in job_summary.items():
                success = summary["success"]
                failed = summary["failed"]
                total = success + failed

                emoji = "✅" if failed == 0 else "⚠️" if failed < total/2 else "❌"
                print(f"{emoji} {portfolio}: {success}/{total} succeeded")

                if failed > 0:
                    failed_jobs = [j["name"] for j in summary["jobs"] if j["status"] != "completed"]
                    print(f"   Failed: {', '.join(failed_jobs)}")

            return {
                "duration": batch_duration,
                "results": results,
                "summary": job_summary
            }

        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            print(f"❌ Batch processing failed: {str(e)}")
            return {
                "error": str(e),
                "duration": 0,
                "results": []
            }

    async def run(
        self,
        portfolio_id: Optional[str] = None,
        run_correlations: bool = False
    ) -> Dict[str, Any]:
        """Run batch processing workflow."""

        print("\n" + "=" * 60)
        print("🚀 SIGMASIGHT BATCH PROCESSING")
        print("=" * 60)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Run batch processing
        self.results = await self.run_batch_processing(
            portfolio_id=portfolio_id,
            run_correlations=run_correlations
        )

        # Final summary
        total_duration = (datetime.now() - self.start_time).total_seconds()

        print("\n" + "=" * 60)
        print("📈 BATCH PROCESSING COMPLETE")
        print("=" * 60)
        print(f"Total duration: {total_duration:.2f} seconds")

        if "error" not in self.results:
            print(f"Calculation engines: {len(self.results.get('results', []))} jobs executed")

        self.results["total_duration"] = total_duration
        self.results["completed_at"] = datetime.now().isoformat()

        return self.results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run batch calculations for portfolios"
    )

    parser.add_argument(
        "--portfolio",
        type=str,
        help="Portfolio UUID (runs all if not specified)"
    )

    parser.add_argument(
        "--correlations",
        action="store_true",
        help="Include correlation calculations (normally Tuesday only)"
    )

    args = parser.parse_args()

    # Run batch processing
    runner = BatchRunner()

    try:
        results = asyncio.run(
            runner.run(
                portfolio_id=args.portfolio,
                run_correlations=args.correlations
            )
        )

        # Exit with appropriate code
        if "error" in results:
            sys.exit(1)

        sys.exit(0)

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        logger.error(f"Batch processing failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
