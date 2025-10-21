"""
Check what market beta is actually stored in PortfolioSnapshot
"""

import asyncio
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
        print("PORTFOLIO SNAPSHOT BETA CHECK")
        print("=" * 80)
        print()
        print(f"Portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")
        print()

        # Get latest snapshot
        result = await db.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(5)
        )
        snapshots = result.scalars().all()

        print(f"Found {len(snapshots)} recent snapshots")
        print()
        print(f"{'Date':<12} {'Market Beta':>12} {'R²':>8} {'Obs':>5} {'Equity':>15}")
        print("-" * 60)

        for snap in snapshots:
            beta = snap.market_beta_weighted if snap.market_beta_weighted else 0
            r_sq = snap.market_beta_r_squared if snap.market_beta_r_squared else 0
            obs = snap.market_beta_observations if snap.market_beta_observations else 0
            equity = snap.equity_balance if snap.equity_balance else 0

            print(f"{snap.snapshot_date} "
                  f"{float(beta):>12.6f} "
                  f"{float(r_sq):>8.4f} "
                  f"{obs:>5} "
                  f"${float(equity):>14,.2f}")

        print()
        print("If the market_beta_weighted in the snapshot doesn't match our calculation,")
        print("there may be an issue with how snapshots.py is calculating or storing the beta.")


if __name__ == "__main__":
    asyncio.run(main())
