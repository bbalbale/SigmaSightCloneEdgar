"""
Check what beta calculation dates we have vs snapshot dates
"""

import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.snapshots import PortfolioSnapshot
from app.models.market_data import PositionMarketBeta


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
        print("BETA CALCULATION DATES vs SNAPSHOT DATES")
        print("=" * 80)
        print()
        print(f"Portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")
        print()

        # Get snapshot dates
        result = await db.execute(
            select(PortfolioSnapshot.snapshot_date)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
        )
        snapshot_dates = [row[0] for row in result.all()]

        print(f"Snapshot dates ({len(snapshot_dates)}):")
        for date in snapshot_dates:
            print(f"  {date}")
        print()

        # Get beta calculation dates
        result = await db.execute(
            select(PositionMarketBeta.calc_date)
            .where(PositionMarketBeta.portfolio_id == portfolio.id)
            .distinct()
            .order_by(PositionMarketBeta.calc_date.desc())
        )
        beta_dates = [row[0] for row in result.all()]

        print(f"Beta calculation dates ({len(beta_dates)}):")
        for date in beta_dates:
            print(f"  {date}")
        print()

        # Check overlaps
        overlap = set(snapshot_dates) & set(beta_dates)
        print(f"Overlapping dates ({len(overlap)}):")
        for date in sorted(overlap, reverse=True):
            print(f"  {date}")
        print()

        if not overlap:
            print("[ISSUE] No overlapping dates!")
            print("Snapshots were created but beta calculations don't exist for those dates.")
            print()
            print("To fix:")
            print("1. Run batch calculations for snapshot dates, OR")
            print("2. Recreate snapshots for beta calculation dates")


if __name__ == "__main__":
    asyncio.run(main())
