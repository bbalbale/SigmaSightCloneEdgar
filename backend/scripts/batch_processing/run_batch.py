#!/usr/bin/env python
"""
Run batch calculations for portfolios.

This script executes the full batch-processing workflow, including market data
collection, fundamentals, P&L roll-forward, position mark updates, sector tags,
and risk analytics. It is a thin wrapper around the batch orchestrator with
better console output for operators.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Configure UTF-8 output handling for Windows terminals
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")  # type: ignore[attr-defined]
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")  # type: ignore[attr-defined]

# Ensure backend package is importable when invoked directly
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.batch.batch_orchestrator import batch_orchestrator  # noqa: E402
from app.core.logging import get_logger  # noqa: E402


logger = get_logger(__name__)
BANNER = "=" * 60


class BatchRunner:
    """Batch processing runner for portfolio calculations."""

    def __init__(self) -> None:
        self.start_time = datetime.now()
        self.results: Dict[str, Any] = {}

    async def run_batch_processing(
        self,
        portfolio_id: Optional[str] = None,
        run_correlations: bool = False,
    ) -> Dict[str, Any]:
        """
        Run batch calculations for portfolio(s).

        Args:
            portfolio_id: Optional UUID string for a specific portfolio.
            run_correlations: Kept for CLI compatibility (currently handled
                inside Phase 3).
        """
        print(f"\n{BANNER}")
        print("SigmaSight Batch Processing")
        print(BANNER)

        try:
            if run_correlations:
                logger.info("Correlation calculations requested - handled during Phase 3 analytics.")

            if portfolio_id:
                print(f"Running batch for portfolio: {portfolio_id}")
            else:
                print("Running batch for all portfolios")

            batch_start = datetime.now()
            portfolio_ids_list = [portfolio_id] if portfolio_id else None

            results = await batch_orchestrator.run_daily_batch_with_backfill(
                target_date=None,
                portfolio_ids=portfolio_ids_list,
            )

            batch_duration = (datetime.now() - batch_start).total_seconds()

            # Backfill summary response (batch orchestrator v3 primary output)
            if isinstance(results, dict) and "dates_processed" in results:
                print(f"\nBatch processing completed in {batch_duration:.2f} seconds")
                print(f"Dates processed: {results.get('dates_processed', 0)}")
                return results

            # Legacy list output (kept for completeness)
            job_summary: Dict[str, Dict[str, Any]] = {}
            for result in results if isinstance(results, list) else []:
                job_name = result.get("job_name", "unknown")
                status = result.get("status", "unknown")
                portfolio_name = result.get("portfolio_name", "unknown")

                clean_name = job_name.split("_")[0] if "_" in job_name else job_name

                summary = job_summary.setdefault(
                    portfolio_name,
                    {"success": 0, "failed": 0, "jobs": []},
                )

                if status == "completed":
                    summary["success"] += 1
                else:
                    summary["failed"] += 1

                summary["jobs"].append(
                    {
                        "name": clean_name,
                        "status": status,
                        "duration": result.get("duration_seconds", 0),
                    }
                )

            print(f"\nBatch processing completed in {batch_duration:.2f} seconds")
            print("\nJob Summary by Portfolio:")
            print("-" * 40)

            for portfolio, summary in job_summary.items():
                success = summary["success"]
                failed = summary["failed"]
                total = success + failed
                status_label = "OK" if failed == 0 else "WARN" if failed < total / 2 else "FAIL"
                print(f"{status_label} {portfolio}: {success}/{total} succeeded")

                if failed > 0:
                    failed_jobs = [
                        job["name"]
                        for job in summary["jobs"]
                        if job["status"] != "completed"
                    ]
                    print(f"   Failed: {', '.join(failed_jobs)}")

            return {
                "duration": batch_duration,
                "results": results,
                "summary": job_summary,
            }

        except Exception as exc:  # pragma: no cover - CLI feedback path
            logger.error("Batch processing failed: %s", exc, exc_info=True)
            print(f"ERROR Batch processing failed: {exc}")
            return {
                "error": str(exc),
                "duration": 0,
                "results": [],
            }

    async def run(
        self,
        portfolio_id: Optional[str] = None,
        run_correlations: bool = False,
        emit_json: bool = False,
    ) -> Dict[str, Any]:
        """Run batch processing workflow and print final summary."""
        print(f"\n{BANNER}")
        print("SigmaSight Batch Processing")
        print(BANNER)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        self.results = await self.run_batch_processing(
            portfolio_id=portfolio_id,
            run_correlations=run_correlations,
        )

        total_duration = (datetime.now() - self.start_time).total_seconds()

        print(f"\n{BANNER}")
        print("Batch Processing Complete")
        print(BANNER)
        print(f"Total duration: {total_duration:.2f} seconds")

        if "error" not in self.results:
            executed = len(self.results.get("results", []))
            print(f"Calculation engines: {executed} jobs executed")

        self.results["total_duration"] = total_duration
        self.results["completed_at"] = datetime.now().isoformat()

        if emit_json:
            try:
                summary_json = json.dumps(self.results, default=str, indent=2)
                print("\nJSON Summary:\n" + summary_json)
            except TypeError as exc:  # pragma: no cover - defensive
                logger.error("Failed to serialize batch results: %s", exc, exc_info=True)

        return self.results


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run batch calculations for portfolios",
    )
    parser.add_argument(
        "--portfolio",
        type=str,
        help="Portfolio UUID (runs all if not specified)",
    )
    parser.add_argument(
        "--correlations",
        action="store_true",
        help="Include correlation calculations (normally Tuesday only)",
    )
    parser.add_argument(
        "--summary-json",
        action="store_true",
        help="Print a JSON summary of batch results for automation consumers.",
    )
    args = parser.parse_args()

    runner = BatchRunner()

    try:
        results = asyncio.run(
            runner.run(
                portfolio_id=args.portfolio,
                run_correlations=args.correlations,
                emit_json=args.summary_json,
            )
        )
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as exc:  # pragma: no cover - CLI feedback path
        print(f"ERROR Unexpected error: {exc}")
        logger.error("Batch processing failed: %s", exc, exc_info=True)
        sys.exit(1)

    if "error" in results:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
