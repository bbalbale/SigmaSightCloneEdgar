#!/usr/bin/env python3
"""
⚠️ DEPRECATED: Use run_batch_with_reports.py instead.
This script is kept for backwards compatibility only.

For new usage:
  uv run python scripts/run_batch_with_reports.py --skip-reports
  
Or for specific portfolio:
  uv run python scripts/run_batch_with_reports.py --portfolio <UUID> --skip-reports

================================================================================
Legacy documentation:
Run batch calculations for demo portfolios
This script executes all calculation engines for the three demo portfolios
to populate Greeks, Factor Analysis, Correlations, Snapshots, etc.
"""
import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Configure UTF-8 output handling for Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2
from app.core.logging import get_logger

logger = get_logger(__name__)


# Demo portfolio IDs (updated with correct IDs from database)
DEMO_PORTFOLIOS = [
    {
        'id': '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe',
        'name': 'Demo Individual Investor Portfolio',
        'email': 'demo_individual@sigmasight.com'
    },
    {
        'id': 'e23ab931-a033-edfe-ed4f-9d02474780b4',
        'name': 'Demo High Net Worth Investor Portfolio',
        'email': 'demo_hnw@sigmasight.com'
    },
    {
        'id': 'fcd71196-e93e-f000-5a74-31a9eead3118',
        'name': 'Demo Hedge Fund Style Investor Portfolio',
        'email': 'demo_hedgefundstyle@sigmasight.com'
    }
]


async def run_batch_for_demo_portfolios(specific_portfolio_id=None):
    """
    Run batch calculations for demo portfolios
    
    Args:
        specific_portfolio_id: Optional - run for specific portfolio only
    """
    start_time = datetime.now()
    print("=" * 80)
    print("🚀 Running Batch Calculations for Demo Portfolios")
    print("=" * 80)
    print(f"Started at: {start_time}")
    print()
    
    # Filter portfolios if specific one requested
    portfolios_to_process = DEMO_PORTFOLIOS
    if specific_portfolio_id:
        portfolios_to_process = [p for p in DEMO_PORTFOLIOS if p['id'] == specific_portfolio_id]
        if not portfolios_to_process:
            print(f"❌ Portfolio ID {specific_portfolio_id} not found in demo portfolios")
            return
    
    # Track overall results
    all_results = []
    portfolio_summaries = []
    
    for idx, portfolio in enumerate(portfolios_to_process, 1):
        print(f"📊 [{idx}/{len(portfolios_to_process)}] Processing: {portfolio['name']}")
        print(f"   Email: {portfolio['email']}")
        print(f"   ID: {portfolio['id']}")
        print("-" * 40)
        
        try:
            # Run batch sequence for this portfolio
            results = await batch_orchestrator_v2.run_daily_batch_sequence(
                portfolio_id=portfolio['id']
            )
            
            # Count successful vs failed jobs
            successful_jobs = sum(1 for r in results if r.get('status') == 'completed')
            failed_jobs = sum(1 for r in results if r.get('status') == 'failed')
            total_jobs = len(results)
            
            # Store results
            all_results.extend(results)
            portfolio_summaries.append({
                'portfolio': portfolio['name'],
                'successful': successful_jobs,
                'failed': failed_jobs,
                'total': total_jobs,
                'success_rate': (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
            })
            
            # Print job details
            print(f"   ✅ Successful: {successful_jobs}/{total_jobs} jobs")
            if failed_jobs > 0:
                print(f"   ❌ Failed: {failed_jobs} jobs")
                # Show which jobs failed
                for job in results:
                    if job.get('status') == 'failed':
                        job_name = job.get('job_name', 'unknown').split('_')[0]
                        error = job.get('error', 'Unknown error')[:100]
                        print(f"      - {job_name}: {error}...")
            
            print()
            
        except Exception as e:
            logger.error(f"Portfolio {portfolio['id']} batch failed: {str(e)}")
            print(f"   ❌ Portfolio batch failed: {str(e)}")
            portfolio_summaries.append({
                'portfolio': portfolio['name'],
                'successful': 0,
                'failed': 0,
                'total': 0,
                'success_rate': 0,
                'error': str(e)
            })
            print()
    
    # Print summary
    duration = datetime.now() - start_time
    print("=" * 80)
    print("📋 BATCH PROCESSING SUMMARY")
    print("=" * 80)
    
    for summary in portfolio_summaries:
        status_icon = "✅" if summary['success_rate'] == 100 else "⚠️" if summary['success_rate'] > 0 else "❌"
        print(f"{status_icon} {summary['portfolio']}:")
        print(f"   Success Rate: {summary['success_rate']:.1f}% ({summary['successful']}/{summary['total']} jobs)")
        if 'error' in summary:
            print(f"   Error: {summary['error']}")
    
    print()
    print(f"⏱️ Total Duration: {duration.total_seconds():.2f} seconds")
    print(f"🏁 Completed at: {datetime.now()}")
    
    # Overall success rate
    total_successful = sum(s['successful'] for s in portfolio_summaries)
    total_jobs = sum(s['total'] for s in portfolio_summaries)
    overall_rate = (total_successful / total_jobs * 100) if total_jobs > 0 else 0
    
    print()
    if overall_rate == 100:
        print(f"🎉 PERFECT! All {total_jobs} jobs completed successfully!")
    elif overall_rate >= 80:
        print(f"✅ GOOD: {overall_rate:.1f}% success rate ({total_successful}/{total_jobs} jobs)")
    elif overall_rate >= 50:
        print(f"⚠️ PARTIAL: {overall_rate:.1f}% success rate ({total_successful}/{total_jobs} jobs)")
    else:
        print(f"❌ POOR: {overall_rate:.1f}% success rate ({total_successful}/{total_jobs} jobs)")
    
    print()
    print("💡 Next Step: Run 'uv run python scripts/verify_demo_portfolios.py' to check calculation engine coverage")
    print("=" * 80)
    
    return all_results


def main():
    """Main entry point with command line argument support"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Run batch calculations for demo portfolios'
    )
    parser.add_argument(
        '--portfolio-id',
        help='Run for specific portfolio ID only',
        default=None
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available demo portfolios and exit'
    )
    
    args = parser.parse_args()
    
    # List portfolios if requested
    if args.list:
        print("Available Demo Portfolios:")
        print("-" * 60)
        for portfolio in DEMO_PORTFOLIOS:
            print(f"ID: {portfolio['id']}")
            print(f"   Name: {portfolio['name']}")
            print(f"   Email: {portfolio['email']}")
            print()
        return
    
    # Run batch calculations
    asyncio.run(run_batch_for_demo_portfolios(args.portfolio_id))


if __name__ == "__main__":
    main()