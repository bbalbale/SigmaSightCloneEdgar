"""
Simple Stress Test Runner - Windows Compatible (No Emojis)
"""
import asyncio
from datetime import date
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.calculations.stress_testing import (
    run_comprehensive_stress_test,
    save_stress_test_results
)
from app.core.logging import get_logger

logger = get_logger(__name__)


async def main():
    """Run stress testing for all demo portfolios and save to database"""

    print("\n" + "="*80)
    print("RUNNING STRESS TESTING FOR ALL DEMO PORTFOLIOS")
    print("="*80)

    async with AsyncSessionLocal() as db:
        # Get all 3 demo portfolios
        stmt = select(Portfolio).join(User).where(
            User.email.in_([
                "demo_individual@sigmasight.com",
                "demo_hnw@sigmasight.com",
                "demo_hedgefundstyle@sigmasight.com"
            ])
        )
        result = await db.execute(stmt)
        portfolios = result.scalars().all()

        print(f"\nFound {len(portfolios)} demo portfolios")

        calculation_date = date.today()
        success_count = 0
        skip_count = 0
        error_count = 0

        for portfolio in portfolios:
            print(f"\n{'='*80}")
            print(f"Portfolio: {portfolio.name}")
            print(f"ID: {portfolio.id}")
            print(f"{'='*80}")

            try:
                # Run comprehensive stress test
                print(f"Running comprehensive stress test...")
                results = await run_comprehensive_stress_test(
                    db=db,
                    portfolio_id=portfolio.id,
                    calculation_date=calculation_date
                )

                # Check if skipped (e.g., all PRIVATE positions)
                if results.get('stress_test_results', {}).get('skipped'):
                    print(f"SKIPPED: {results['stress_test_results'].get('message')}")
                    skip_count += 1
                    continue

                # Display summary
                config_meta = results.get('config_metadata', {})
                summary = results.get('stress_test_results', {}).get('summary_stats', {})

                print(f"\nStress test completed:")
                print(f"  Scenarios tested: {config_meta.get('scenarios_tested', 0)}")
                print(f"  Scenarios skipped: {config_meta.get('scenarios_skipped', 0)}")

                if summary:
                    print(f"\n  Summary Statistics:")
                    print(f"    Worst case P&L: ${summary.get('worst_case_pnl', 0):,.2f}")
                    print(f"    Best case P&L:  ${summary.get('best_case_pnl', 0):,.2f}")
                    print(f"    Mean P&L:       ${summary.get('mean_pnl', 0):,.2f}")
                    print(f"    Median P&L:     ${summary.get('median_pnl', 0):,.2f}")
                    print(f"    Scenarios negative: {summary.get('scenarios_negative', 0)}")
                    print(f"    Scenarios positive: {summary.get('scenarios_positive', 0)}")

                # Save results to database
                print(f"\nSaving results to database...")
                saved_count = await save_stress_test_results(
                    db=db,
                    portfolio_id=portfolio.id,
                    stress_test_results=results
                )

                print(f"SUCCESS: Saved {saved_count} stress test results to database")
                success_count += 1

            except Exception as e:
                print(f"ERROR: {e}")
                logger.error(f"Error running stress test for {portfolio.name}: {e}", exc_info=True)
                error_count += 1

        # Final summary
        print(f"\n{'='*80}")
        print("FINAL SUMMARY")
        print(f"{'='*80}")
        print(f"Total portfolios: {len(portfolios)}")
        print(f"  Success: {success_count}")
        print(f"  Skipped: {skip_count}")
        print(f"  Errors:  {error_count}")

        if success_count > 0:
            print(f"\nStress test results saved to database!")
        else:
            print(f"\nNo stress test results were saved to database")


if __name__ == "__main__":
    asyncio.run(main())
