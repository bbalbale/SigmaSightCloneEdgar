"""
Create portfolio snapshot for Oct 17, 2025 (when beta data exists)
"""

import asyncio
from datetime import date
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import User, Portfolio
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
        print("CREATING SNAPSHOT FOR OCTOBER 17, 2025")
        print("=" * 80)
        print()
        print(f"Portfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")
        print()

        # Create snapshot for Oct 17
        snapshot_date = date(2025, 10, 17)
        print(f"Creating snapshot for {snapshot_date}...")
        print()

        result = await create_portfolio_snapshot(
            db=db,
            portfolio_id=portfolio.id,
            calculation_date=snapshot_date
        )

        if result['success']:
            print(f"✅ Snapshot created successfully!")
            print()
            print(f"Statistics:")
            stats = result.get('statistics', {})
            for key, value in stats.items():
                print(f"  {key}: {value}")

            # Check the beta value
            snapshot = result.get('snapshot')
            if snapshot and snapshot.market_beta_weighted:
                print()
                print(f"✅ Market Beta Weighted: {float(snapshot.market_beta_weighted):.6f}")
                print(f"   R²: {float(snapshot.market_beta_r_squared):.4f}" if snapshot.market_beta_r_squared else "   R²: None")
                print(f"   Observations: {snapshot.market_beta_observations}")
        else:
            print(f"❌ Snapshot creation failed: {result.get('message')}")


if __name__ == "__main__":
    asyncio.run(main())
