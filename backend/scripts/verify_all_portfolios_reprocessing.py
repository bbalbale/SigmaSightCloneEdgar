"""Verify reprocessing results for all three portfolios"""
import asyncio
from sqlalchemy import select, desc, func
from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot
from uuid import UUID


async def main():
    portfolios = [
        {"id": "e23ab931-a033-edfe-ed4f-9d02474780b4", "name": "High Net Worth"},
        {"id": "1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe", "name": "Individual Investor"},
        {"id": "fcd71196-e93e-f000-5a74-31a9eead3118", "name": "Hedge Fund Style"},
    ]

    print("=" * 80)
    print("ALL PORTFOLIOS REPROCESSING VERIFICATION")
    print("=" * 80)
    print()

    async with get_async_session() as db:
        for portfolio in portfolios:
            portfolio_id = UUID(portfolio["id"])
            portfolio_name = portfolio["name"]

            print(f"PORTFOLIO: {portfolio_name}")
            print("-" * 80)

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
                print(f"  Cumulative P&L: ${float(latest_snapshot.cumulative_pnl):,.2f}")
            else:
                print("  [ERROR] No snapshots found!")

            # Count total snapshots
            count_result = await db.execute(
                select(func.count(PortfolioSnapshot.id)).where(
                    PortfolioSnapshot.portfolio_id == portfolio_id
                )
            )
            snapshot_count = count_result.scalar()
            print(f"  Total Snapshots: {snapshot_count}")

            # Count snapshots with volatility
            vol_count_result = await db.execute(
                select(func.count(PortfolioSnapshot.id)).where(
                    PortfolioSnapshot.portfolio_id == portfolio_id,
                    PortfolioSnapshot.realized_volatility_21d.isnot(None)
                )
            )
            vol_count = vol_count_result.scalar()
            print(f"  Snapshots with Volatility: {vol_count}")

            print()

    print("=" * 80)
    print("[COMPLETE] All portfolios verified")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
