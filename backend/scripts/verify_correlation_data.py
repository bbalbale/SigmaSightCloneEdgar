"""Verify correlation data was recreated after reprocessing"""
import asyncio
from sqlalchemy import text
from app.database import get_async_session

async def main():
    print("=" * 80)
    print("VERIFY: Correlation Data After Reprocessing")
    print("=" * 80)
    print()

    async with get_async_session() as db:
        # Check all 3 demo portfolios
        portfolios = [
            ("e23ab931-a033-edfe-ed4f-9d02474780b4", "High Net Worth"),
            ("1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe", "Individual Investor"),
            ("fcd71196-e93e-f000-5a74-31a9eead3118", "Hedge Fund Style"),
        ]

        for portfolio_id, portfolio_name in portfolios:
            print(f"Portfolio: {portfolio_name}")
            print(f"ID: {portfolio_id}")
            print("-" * 80)

            # Count correlation_calculations
            result = await db.execute(text("""
                SELECT COUNT(*) as count
                FROM correlation_calculations
                WHERE portfolio_id = :portfolio_id
            """), {"portfolio_id": portfolio_id})
            calc_count = result.scalar()

            # Count correlation_clusters
            result = await db.execute(text("""
                SELECT COUNT(*) as count
                FROM correlation_clusters cc
                JOIN correlation_calculations calc ON cc.correlation_calculation_id = calc.id
                WHERE calc.portfolio_id = :portfolio_id
            """), {"portfolio_id": portfolio_id})
            cluster_count = result.scalar()

            # Count correlation_cluster_positions
            result = await db.execute(text("""
                SELECT COUNT(*) as count
                FROM correlation_cluster_positions ccp
                JOIN correlation_clusters cc ON ccp.cluster_id = cc.id
                JOIN correlation_calculations calc ON cc.correlation_calculation_id = calc.id
                WHERE calc.portfolio_id = :portfolio_id
            """), {"portfolio_id": portfolio_id})
            cluster_pos_count = result.scalar()

            # Count pairwise_correlations
            result = await db.execute(text("""
                SELECT COUNT(*) as count
                FROM pairwise_correlations pc
                JOIN correlation_calculations calc ON pc.correlation_calculation_id = calc.id
                WHERE calc.portfolio_id = :portfolio_id
            """), {"portfolio_id": portfolio_id})
            pairwise_count = result.scalar()

            # Get latest calculation date
            result = await db.execute(text("""
                SELECT MAX(calculation_date) as latest_date
                FROM correlation_calculations
                WHERE portfolio_id = :portfolio_id
            """), {"portfolio_id": portfolio_id})
            latest_date = result.scalar()

            print(f"  Correlation Calculations: {calc_count}")
            print(f"  Correlation Clusters: {cluster_count}")
            print(f"  Cluster Positions: {cluster_pos_count}")
            print(f"  Pairwise Correlations: {pairwise_count}")
            print(f"  Latest Calculation Date: {latest_date}")

            if calc_count > 0:
                print(f"  Status: OK - Correlation data EXISTS")
            else:
                print(f"  Status: WARNING - NO correlation data")

            print()

        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
