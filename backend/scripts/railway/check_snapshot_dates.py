"""Check what dates snapshots were created for"""
import asyncio
import os

# Fix Railway DATABASE_URL format
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print("✅ Converted DATABASE_URL to use asyncpg driver\n")

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio
from app.models.batch_tracking import BatchRunTracking


async def main():
    async with AsyncSessionLocal() as db:
        # Check batch run tracking
        print("=" * 80)
        print("BATCH RUN TRACKING")
        print("=" * 80)
        batch_runs = await db.execute(
            select(BatchRunTracking).order_by(BatchRunTracking.run_date.desc()).limit(10)
        )
        for run in batch_runs.scalars().all():
            print(f"{run.run_date}: Phase 1: {run.phase_1_status}, Created: {run.created_at}")

        print("\n" + "=" * 80)
        print("PORTFOLIO SNAPSHOTS BY DATE")
        print("=" * 80)

        # Get all portfolios
        portfolios = await db.execute(select(Portfolio))

        for portfolio in portfolios.scalars().all():
            print(f"\n{portfolio.name} (ID: {portfolio.id})")
            print(f"Current equity_balance: ${portfolio.equity_balance:,.2f}")
            print("-" * 80)

            snapshots = await db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.portfolio_id == portfolio.id)
                .order_by(PortfolioSnapshot.snapshot_date)
            )

            for snap in snapshots.scalars().all():
                print(f"  {snap.snapshot_date}: equity=${snap.equity_balance:,.2f}, daily_pnl=${snap.daily_pnl or 0:,.2f}, daily_flow=${snap.daily_capital_flow or 0:,.2f}")

if __name__ == "__main__":
    asyncio.run(main())
