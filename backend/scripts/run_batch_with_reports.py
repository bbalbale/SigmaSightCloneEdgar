#!/usr/bin/env python
"""
Run batch calculations and generate reports for portfolios.

This script combines batch processing with report generation,
providing a complete daily workflow for portfolio analytics.

Usage:
    python scripts/run_batch_with_reports.py                    # Run for all portfolios
    python scripts/run_batch_with_reports.py --portfolio <UUID>  # Run for specific portfolio
    python scripts/run_batch_with_reports.py --skip-batch        # Only generate reports
    python scripts/run_batch_with_reports.py --skip-reports      # Only run batch
"""

import argparse
import asyncio
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import UUID

# Configure UTF-8 output handling for Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_async_session
from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2
from app.reports.portfolio_report_generator import PortfolioReportGenerator
from app.models.users import Portfolio
from app.core.logging import get_logger
from sqlalchemy import select

logger = get_logger(__name__)


class BatchReportRunner:
    """Combined batch processing and report generation runner."""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.results = {
            "batch": {},
            "reports": {},
            "summary": {}
        }
    
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
    
    async def generate_reports(
        self,
        portfolio_id: Optional[str] = None,
        formats: List[str] = None,
        report_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Generate reports for portfolio(s)."""
        print("\n" + "=" * 60)
        print("📊 REPORT GENERATION")
        print("=" * 60)
        
        if not formats:
            formats = ["md", "json", "csv"]
        
        if not report_date:
            report_date = date.today()
        
        report_results = {}
        
        async with get_async_session() as db:
            # Get portfolios to process
            if portfolio_id:
                try:
                    portfolio_uuid = UUID(portfolio_id)
                except ValueError:
                    print(f"❌ Invalid portfolio ID: {portfolio_id}")
                    return {"error": "Invalid portfolio ID"}
                
                stmt = select(Portfolio).where(Portfolio.id == portfolio_uuid)
            else:
                stmt = select(Portfolio).order_by(Portfolio.name)
            
            result = await db.execute(stmt)
            portfolios = result.scalars().all()
            
            if not portfolios:
                print("No portfolios found")
                return {"error": "No portfolios found"}
            
            print(f"Generating reports for {len(portfolios)} portfolio(s)")
            print(f"Formats: {', '.join(formats)}")
            print(f"Date: {report_date}")
            print("-" * 40)
            
            generator = PortfolioReportGenerator(db)
            
            for portfolio in portfolios:
                print(f"\n📁 {portfolio.name}...")
                portfolio_results = {
                    "name": portfolio.name,
                    "id": str(portfolio.id),
                    "formats": {}
                }
                
                for format_type in formats:
                    try:
                        print(f"   {format_type.upper()}...", end=" ")
                        
                        file_path = await generator.generate_report(
                            portfolio_id=portfolio.id,
                            report_date=report_date,
                            format=format_type
                        )
                        
                        portfolio_results["formats"][format_type] = {
                            "status": "success",
                            "path": file_path
                        }
                        print("✅")
                        
                    except Exception as e:
                        logger.error(f"Failed to generate {format_type} for {portfolio.name}: {str(e)}")
                        portfolio_results["formats"][format_type] = {
                            "status": "failed",
                            "error": str(e)
                        }
                        print(f"❌ ({str(e)[:50]}...)")
                
                report_results[str(portfolio.id)] = portfolio_results
        
        # Summary
        total_reports = len(report_results) * len(formats)
        successful = sum(
            1 for p in report_results.values() 
            for f in p["formats"].values() 
            if f["status"] == "success"
        )
        
        print(f"\n✅ Report generation completed")
        print(f"   Generated: {successful}/{total_reports} reports")
        
        if successful < total_reports:
            print("\n⚠️ Some reports failed:")
            for portfolio_data in report_results.values():
                failed_formats = [
                    fmt for fmt, result in portfolio_data["formats"].items()
                    if result["status"] == "failed"
                ]
                if failed_formats:
                    print(f"   {portfolio_data['name']}: {', '.join(failed_formats)}")
        
        return report_results
    
    async def run(
        self,
        portfolio_id: Optional[str] = None,
        skip_batch: bool = False,
        skip_reports: bool = False,
        run_correlations: bool = False,
        report_formats: List[str] = None,
        report_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Run complete workflow: batch processing + report generation."""
        
        print("\n" + "=" * 60)
        print("🚀 SIGMASIGHT DAILY WORKFLOW")
        print("=" * 60)
        print(f"Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run batch processing
        if not skip_batch:
            self.results["batch"] = await self.run_batch_processing(
                portfolio_id=portfolio_id,
                run_correlations=run_correlations
            )
        else:
            print("\n⏭️  Skipping batch processing")
            self.results["batch"] = {"skipped": True}
        
        # Run report generation
        if not skip_reports:
            self.results["reports"] = await self.generate_reports(
                portfolio_id=portfolio_id,
                formats=report_formats,
                report_date=report_date
            )
        else:
            print("\n⏭️  Skipping report generation")
            self.results["reports"] = {"skipped": True}
        
        # Final summary
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("📈 WORKFLOW COMPLETE")
        print("=" * 60)
        print(f"Total duration: {total_duration:.2f} seconds")
        
        if not skip_batch and "error" not in self.results["batch"]:
            batch_data = self.results["batch"]
            print(f"Batch processing: {batch_data.get('duration', 0):.2f} seconds")
        
        if not skip_reports and "error" not in self.results["reports"]:
            report_count = len(self.results["reports"])
            print(f"Reports generated: {report_count} portfolio(s)")
        
        self.results["summary"] = {
            "total_duration": total_duration,
            "completed_at": datetime.now().isoformat()
        }
        
        return self.results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run batch calculations and generate reports"
    )
    
    parser.add_argument(
        "--portfolio",
        type=str,
        help="Portfolio UUID (runs all if not specified)"
    )
    
    parser.add_argument(
        "--skip-batch",
        action="store_true",
        help="Skip batch processing, only generate reports"
    )
    
    parser.add_argument(
        "--skip-reports",
        action="store_true",
        help="Skip report generation, only run batch"
    )
    
    parser.add_argument(
        "--correlations",
        action="store_true",
        help="Include correlation calculations (normally Tuesday only)"
    )
    
    parser.add_argument(
        "--formats",
        type=str,
        default="md,json,csv",
        help="Report formats to generate (comma-separated)"
    )
    
    parser.add_argument(
        "--report-date",
        type=str,
        help="Report date (YYYY-MM-DD format)"
    )
    
    args = parser.parse_args()
    
    # Parse report date if provided
    report_date = None
    if args.report_date:
        try:
            report_date = datetime.strptime(args.report_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"❌ Invalid date format: {args.report_date}")
            sys.exit(1)
    
    # Parse formats
    report_formats = [f.strip() for f in args.formats.split(",")]
    
    # Run workflow
    runner = BatchReportRunner()
    
    try:
        results = asyncio.run(
            runner.run(
                portfolio_id=args.portfolio,
                skip_batch=args.skip_batch,
                skip_reports=args.skip_reports,
                run_correlations=args.correlations,
                report_formats=report_formats,
                report_date=report_date
            )
        )
        
        # Exit with appropriate code
        if "error" in results.get("batch", {}) or "error" in results.get("reports", {}):
            sys.exit(1)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        logger.error(f"Workflow failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()