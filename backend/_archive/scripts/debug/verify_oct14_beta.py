"""
Verify Oct 14 snapshot has beta data
"""
import asyncio
from datetime import date
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.snapshots import PortfolioSnapshot


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
        print("VERIFYING OCT 14 SNAPSHOT BETA DATA")
        print("=" * 80)
        print()
        print(f"Portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")
        print()

        # Query for Oct 14 snapshot
        snapshot_date = date(2025, 10, 14)
        result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .where(PortfolioSnapshot.snapshot_date == snapshot_date)
        )
        snapshot = result.scalar_one_or_none()

        if snapshot:
            print(f"FOUND Oct 14 snapshot:")
            print(f"  Date: {snapshot.snapshot_date}")
            print(f"  Market Beta: {float(snapshot.market_beta_weighted) if snapshot.market_beta_weighted else 0:.6f}")
            print(f"  R-squared: {float(snapshot.market_beta_r_squared) if snapshot.market_beta_r_squared else 0:.6f}")
            print(f"  Observations: {snapshot.market_beta_observations if snapshot.market_beta_observations else 0}")
            print(f"  Equity: ${float(snapshot.equity_balance):,.2f}")
            print()

            if snapshot.market_beta_weighted and float(snapshot.market_beta_weighted) > 0:
                print("SUCCESS: Beta data is populated correctly!")
            else:
                print("WARNING: Beta is 0 or null")
        else:
            print("NOT FOUND: Oct 14 snapshot does not exist")
            print()
            print("Checking all snapshots for this portfolio:")
            result = await db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
            )
            snapshots = result.scalars().all()
            print(f"Found {len(snapshots)} total snapshots")
            for s in snapshots:
                beta = float(s.market_beta_weighted) if s.market_beta_weighted else 0
                print(f"  {s.snapshot_date}: Beta = {beta:.6f}")


if __name__ == "__main__":
    asyncio.run(main())
