"""
Recreate Oct 14 snapshot to trigger beta population with new logic
"""

import asyncio
from datetime import date
from sqlalchemy import select, delete
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.calculations.snapshots import create_portfolio_snapshot


async def main():
    async with get_async_session() as db:
        # Get hedge fund portfolio
        result = await db.execute(
            select(User).where(User.email == "demo_hedgefundstyle@sigmasight.com")
        )
        user = result.scalar_one_or_none()

        result = await db.execute(
            select(Portfolio).where(Portfolio.user_id == user.id)
        )
        portfolio = result.scalars().first()

        print("=" * 80)
        print("RECREATING OCT 14 SNAPSHOT WITH NEW BETA LOGIC")
        print("=" * 80)
        print()
        print(f"Portfolio: {portfolio.name}")
        print()

        # Delete existing Oct 14 snapshot
        snapshot_date = date(2025, 10, 14)
        print(f"Deleting existing snapshot for {snapshot_date}...")

        delete_stmt = delete(PortfolioSnapshot).where(
            PortfolioSnapshot.portfolio_id == portfolio.id
        ).where(
            PortfolioSnapshot.snapshot_date == snapshot_date
        )
        result = await db.execute(delete_stmt)
        await db.commit()
        print(f"Deleted {result.rowcount} snapshot(s)")
        print()

        # Recreate snapshot
        print(f"Creating new snapshot for {snapshot_date}...")
        result = await create_portfolio_snapshot(
            db=db,
            portfolio_id=portfolio.id,
            calculation_date=snapshot_date
        )

        if result['success']:
            print()
            print("✅ Snapshot created successfully!")

            snapshot = result.get('snapshot')
            if snapshot:
                print()
                print(f"Snapshot Data:")
                print(f"  Date: {snapshot.snapshot_date}")
                print(f"  Equity: ${float(snapshot.equity_balance):,.2f}")
                print(f"  Market Beta: {float(snapshot.market_beta_weighted) if snapshot.market_beta_weighted else 'None'}")
                print(f"  R²: {float(snapshot.market_beta_r_squared) if snapshot.market_beta_r_squared else 'None'}")
                print(f"  Observations: {snapshot.market_beta_observations if snapshot.market_beta_observations else 'None'}")
        else:
            print(f"❌ Failed: {result.get('message')}")


if __name__ == "__main__":
    asyncio.run(main())
