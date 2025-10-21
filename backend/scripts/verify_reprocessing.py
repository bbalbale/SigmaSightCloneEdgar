"""Verify reprocessing results"""
import asyncio
from sqlalchemy import select, desc, func, text
from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot
from uuid import UUID


async def main():
    portfolio_id = UUID('e23ab931-a033-edfe-ed4f-9d02474780b4')

    print("=" * 80)
    print("REPROCESSING VERIFICATION")
    print("=" * 80)
    print()

    async with get_async_session() as db:
        # Check latest snapshot
        latest_snapshot_stmt = select(PortfolioSnapshot).where(
            PortfolioSnapshot.portfolio_id == portfolio_id
        ).order_by(desc(PortfolioSnapshot.snapshot_date)).limit(1)

        snapshot_result = await db.execute(latest_snapshot_stmt)
        latest_snapshot = snapshot_result.scalar_one_or_none()

        if latest_snapshot:
            print(f"Latest Snapshot: {latest_snapshot.snapshot_date}")
            print(f"  Equity Balance: ${float(latest_snapshot.equity_balance):,.2f}")
            print(f"  Total Value: ${float(latest_snapshot.total_value):,.2f}")
            print(f"  Daily P&L: ${float(latest_snapshot.daily_pnl):,.2f}")
            print(f"  Cumulative P&L: ${float(latest_snapshot.cumulative_pnl):,.2f}")
        else:
            print("No snapshots found!")

        print()

        # Check snapshot count
        count_result = await db.execute(
            select(func.count(PortfolioSnapshot.id)).where(
                PortfolioSnapshot.portfolio_id == portfolio_id
            )
        )
        snapshot_count = count_result.scalar()
        print(f"Total Snapshots: {snapshot_count}")
        print()

        # Check volatility data
        vol_count_result = await db.execute(
            select(func.count(PortfolioSnapshot.id)).where(
                PortfolioSnapshot.portfolio_id == portfolio_id,
                PortfolioSnapshot.realized_volatility_21d.isnot(None)
            )
        )
        vol_count = vol_count_result.scalar()
        print(f"Snapshots with Volatility Data: {vol_count}")
        print()

        # Check spread factors
        spread_factors_result = await db.execute(text("""
            SELECT DISTINCT fd.name
            FROM position_factor_exposures pfe
            JOIN factor_definitions fd ON pfe.factor_id = fd.id
            JOIN positions p ON pfe.position_id = p.id
            WHERE p.portfolio_id = :portfolio_id
            AND fd.name LIKE '%Spread%'
            ORDER BY fd.name
        """), {"portfolio_id": str(portfolio_id)})

        spread_factors = spread_factors_result.fetchall()
        print("Spread Factors Found:")
        if spread_factors:
            for factor in spread_factors:
                print(f"  - {factor[0]}")
        else:
            print("  (none)")

        # Check total factor exposures
        total_factors_result = await db.execute(text("""
            SELECT COUNT(DISTINCT pfe.id)
            FROM position_factor_exposures pfe
            JOIN positions p ON pfe.position_id = p.id
            WHERE p.portfolio_id = :portfolio_id
        """), {"portfolio_id": str(portfolio_id)})
        total_factors = total_factors_result.scalar()
        print(f"\nTotal Factor Exposures: {total_factors}")

        print()
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
