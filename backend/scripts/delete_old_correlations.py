"""
Delete old incorrect correlation calculations

The diagnostic found these old calculations have incorrect NVDA-META correlation (-0.95):
- 3d5095d9-47b6-462e-9857-6816cfc3086f
- e082a10a-61d7-4086-bd61-c1174d3a52a6

Recent calculations have the correct value (+0.2537).
"""
import asyncio
from uuid import UUID
from sqlalchemy import select, delete
from app.database import AsyncSessionLocal
from app.models.correlations import (
    CorrelationCalculation,
    PairwiseCorrelation,
    CorrelationCluster,
    CorrelationClusterPosition
)

async def main():
    # Old calculation IDs with incorrect data
    old_calculation_ids = [
        UUID('3d5095d9-47b6-462e-9857-6816cfc3086f'),
        UUID('e082a10a-61d7-4086-bd61-c1174d3a52a6')
    ]

    print(f"\n{'='*80}")
    print("DELETING OLD INCORRECT CORRELATION CALCULATIONS")
    print(f"{'='*80}\n")

    async with AsyncSessionLocal() as db:
        for calc_id in old_calculation_ids:
            # Get calculation details
            stmt = select(CorrelationCalculation).where(
                CorrelationCalculation.id == calc_id
            )
            result = await db.execute(stmt)
            calculation = result.scalar_one_or_none()

            if calculation:
                print(f"Found calculation: {calc_id}")
                print(f"  Portfolio ID: {calculation.portfolio_id}")
                print(f"  Calculation date: {calculation.calculation_date}")
                print(f"  Overall correlation: {float(calculation.overall_correlation):.4f}")

                # Get clusters for this calculation
                cluster_stmt = select(CorrelationCluster).where(
                    CorrelationCluster.correlation_calculation_id == calc_id
                )
                cluster_result = await db.execute(cluster_stmt)
                clusters = cluster_result.scalars().all()

                # Delete cluster positions first (innermost foreign key)
                total_positions = 0
                for cluster in clusters:
                    delete_positions_stmt = delete(CorrelationClusterPosition).where(
                        CorrelationClusterPosition.cluster_id == cluster.id
                    )
                    positions_result = await db.execute(delete_positions_stmt)
                    total_positions += positions_result.rowcount

                if total_positions > 0:
                    print(f"  Deleted {total_positions} cluster positions")

                # Delete clusters
                delete_clusters_stmt = delete(CorrelationCluster).where(
                    CorrelationCluster.correlation_calculation_id == calc_id
                )
                clusters_result = await db.execute(delete_clusters_stmt)
                print(f"  Deleted {clusters_result.rowcount} clusters")

                # Delete pairwise correlations
                delete_pairs_stmt = delete(PairwiseCorrelation).where(
                    PairwiseCorrelation.correlation_calculation_id == calc_id
                )
                pairs_result = await db.execute(delete_pairs_stmt)
                print(f"  Deleted {pairs_result.rowcount} pairwise correlations")

                # Delete calculation
                delete_calc_stmt = delete(CorrelationCalculation).where(
                    CorrelationCalculation.id == calc_id
                )
                await db.execute(delete_calc_stmt)
                print(f"  Deleted calculation record")
                print()
            else:
                print(f"Calculation {calc_id} not found (may have been deleted already)")
                print()

        await db.commit()
        print(f"✅ All old incorrect correlation calculations deleted successfully\n")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
