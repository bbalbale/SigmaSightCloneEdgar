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
            print("❌ Test portfolio not found")
            return

        print(f"✅ Found portfolio: {portfolio.name}")
        print(f"   ID: {portfolio.id}")

        # Count existing calculations before test
        count_stmt = select(func.count(CorrelationCalculation.id)).where(
            CorrelationCalculation.portfolio_id == portfolio.id
        )
        initial_count = (await db.execute(count_stmt)).scalar()
        print(f"\n📊 Initial calculation count: {initial_count}")

        # Create correlation service
        correlation_service = CorrelationService(db)

        # Run 8 calculations with different dates (simulating multiple batch runs)
        print(f"\n🔄 Running 8 correlation calculations...")
        for i in range(8):
            calc_date = datetime.now() - timedelta(days=i)
            print(f"   Calculation {i+1}/8 (date: {calc_date.date()})...", end=" ")

            calculation = await correlation_service.calculate_portfolio_correlations(
                portfolio_id=portfolio.id,
                calculation_date=calc_date,
                force_recalculate=True,
                duration_days=90
            )

            if calculation:
                print(f"✅ Done (ID: {calculation.id})")
            else:
                print(f"⚠️  Skipped (insufficient data)")

        # Count calculations after test
        final_count = (await db.execute(count_stmt)).scalar()
        print(f"\n📊 Final calculation count: {final_count}")
        print(f"   Expected: 5 (due to keep_most_recent=5 retention policy)")

        if final_count == 5:
            print(f"\n✅ CLEANUP WORKING: Kept exactly 5 most recent calculations")
        elif final_count < 5:
            print(f"\n⚠️  UNEXPECTED: Only {final_count} calculations found (expected 5)")
        else:
            print(f"\n❌ CLEANUP NOT WORKING: Found {final_count} calculations (expected 5)")

        # Show remaining calculations
        list_stmt = (
            select(CorrelationCalculation)
            .where(CorrelationCalculation.portfolio_id == portfolio.id)
            .order_by(CorrelationCalculation.calculation_date.desc())
        )
        remaining = (await db.execute(list_stmt)).scalars().all()

        print(f"\n📋 Remaining calculations:")
        for i, calc in enumerate(remaining, 1):
            print(f"   {i}. {calc.calculation_date.date()} - ID: {calc.id}")

        # Verify cluster cleanup by counting orphaned records
        cluster_stmt = select(func.count(CorrelationCluster.id)).where(
            CorrelationCluster.correlation_calculation_id.not_in([c.id for c in remaining])
        )
        orphaned_clusters = (await db.execute(cluster_stmt)).scalar()

        if orphaned_clusters == 0:
            print(f"\n✅ CLUSTER CLEANUP WORKING: No orphaned clusters found")
        else:
            print(f"\n❌ CLUSTER CLEANUP FAILED: Found {orphaned_clusters} orphaned clusters")

        print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
