"""
Test Correlation Calculation Cleanup Logic

This script tests that old correlation calculations are properly cleaned up
to prevent stale data accumulation in the database.
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.users import User, Portfolio
from app.models.correlations import (
    CorrelationCalculation,
    PairwiseCorrelation,
    CorrelationCluster,
    CorrelationClusterPosition
)
from app.services.correlation_service import CorrelationService


async def main():
    async with AsyncSessionLocal() as db:
        # Get test portfolio (use Balanced Individual)
        stmt = select(Portfolio).join(User).where(
            User.email == 'demo_individual@sigmasight.com'
        )
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("[FAIL] Test portfolio not found")
            return

        print(f"[OK] Found portfolio: {portfolio.name}")
        print(f"     ID: {portfolio.id}")

        # Count existing calculations before test
        count_stmt = select(func.count(CorrelationCalculation.id)).where(
            CorrelationCalculation.portfolio_id == portfolio.id
        )
        initial_count = (await db.execute(count_stmt)).scalar()
        print(f"\n[INFO] Initial calculation count: {initial_count}")

        # Create correlation service
        correlation_service = CorrelationService(db)

        # Run 3 calculations with 90-day duration (should replace each other)
        print(f"\n[TEST] Running 3 correlation calculations (90-day duration)...")
        for i in range(3):
            calc_date = datetime.now() - timedelta(days=i)
            print(f"       Calculation {i+1}/3 (date: {calc_date.date()})...", end=" ")

            calculation = await correlation_service.calculate_portfolio_correlations(
                portfolio_id=portfolio.id,
                calculation_date=calc_date,
                force_recalculate=True,
                duration_days=90
            )

            if calculation:
                print(f"[OK] ID: {calculation.id}")
            else:
                print(f"[SKIP] Insufficient data")

        # Count calculations after 90-day runs
        final_count = (await db.execute(count_stmt)).scalar()
        print(f"\n[INFO] Final calculation count: {final_count}")
        print(f"       Expected: 1 (each new calculation replaces the previous)")

        if final_count == 1:
            print(f"\n[PASS] CLEANUP WORKING: Only 1 calculation exists (most recent replaced previous)")
        else:
            print(f"\n[FAIL] CLEANUP NOT WORKING: Found {final_count} calculations (expected 1)")

        # Run 1 calculation with 30-day duration (should coexist with 90-day)
        print(f"\n[TEST] Running 1 correlation calculation (30-day duration)...")
        calculation_30d = await correlation_service.calculate_portfolio_correlations(
            portfolio_id=portfolio.id,
            calculation_date=datetime.now(),
            force_recalculate=True,
            duration_days=30
        )

        if calculation_30d:
            print(f"       [OK] ID: {calculation_30d.id}")

        # Count calculations after adding 30-day
        final_count = (await db.execute(count_stmt)).scalar()
        print(f"\n[INFO] Final calculation count: {final_count}")
        print(f"       Expected: 2 (one 90-day + one 30-day)")

        if final_count == 2:
            print(f"\n[PASS] MULTI-DURATION WORKING: Different durations coexist correctly")
        else:
            print(f"\n[FAIL] MULTI-DURATION FAILED: Found {final_count} calculations (expected 2)")

        # Show remaining calculations
        list_stmt = (
            select(CorrelationCalculation)
            .where(CorrelationCalculation.portfolio_id == portfolio.id)
            .order_by(CorrelationCalculation.calculation_date.desc())
        )
        remaining = (await db.execute(list_stmt)).scalars().all()

        print(f"\n[INFO] Remaining calculations:")
        for i, calc in enumerate(remaining, 1):
            print(f"       {i}. {calc.duration_days}-day duration | {calc.calculation_date.date()} | ID: {calc.id}")

        # Verify cluster cleanup by counting orphaned records
        cluster_stmt = select(func.count(CorrelationCluster.id)).where(
            CorrelationCluster.correlation_calculation_id.not_in([c.id for c in remaining])
        )
        orphaned_clusters = (await db.execute(cluster_stmt)).scalar()

        if orphaned_clusters == 0:
            print(f"\n[PASS] CLUSTER CLEANUP WORKING: No orphaned clusters found")
        else:
            print(f"\n[FAIL] CLUSTER CLEANUP FAILED: Found {orphaned_clusters} orphaned clusters")

        print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
