"""
Quick check of equity status for all portfolios
"""
import asyncio
from datetime import date
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot


async def check_all():
    async with get_async_session() as db:
        print("\n" + "=" * 100)
        print("EQUITY BALANCE STATUS - ALL PORTFOLIOS")
        print("=" * 100)

        # Get all portfolios
        portfolios_query = select(Portfolio).where(Portfolio.deleted_at.is_(None))
        portfolios_result = await db.execute(portfolios_query)
        portfolios = portfolios_result.scalars().all()

        today = date(2025, 11, 3)

        summary = []

        for portfolio in portfolios:
            # Get Nov 3 snapshot
            nov3_query = select(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio.id,
                    PortfolioSnapshot.snapshot_date == today
                )
            )
            nov3_result = await db.execute(nov3_query)
            nov3_snap = nov3_result.scalar_one_or_none()

            # Get most recent snapshot before Nov 3
            prev_query = select(PortfolioSnapshot).where(
                and_(
                    PortfolioSnapshot.portfolio_id == portfolio.id,
                    PortfolioSnapshot.snapshot_date < today
                )
            ).order_by(PortfolioSnapshot.snapshot_date.desc()).limit(1)
            prev_result = await db.execute(prev_query)
            prev_snap = prev_result.scalar_one_or_none()

            # Check if reset
            is_reset = False
            if nov3_snap and abs(nov3_snap.equity_balance - portfolio.equity_balance) < 1.0:
                is_reset = True

            summary.append({
                'name': portfolio.name,
                'initial_equity': portfolio.equity_balance,
                'prev_date': prev_snap.snapshot_date if prev_snap else None,
                'prev_equity': prev_snap.equity_balance if prev_snap else None,
                'nov3_equity': nov3_snap.equity_balance if nov3_snap else None,
                'is_reset': is_reset
            })

        # Print summary table
        print(f"\n{'Portfolio':<50} {'Initial':<15} {'Previous':<30} {'Nov 3':<15} {'Status':<10}")
        print("=" * 120)

        for s in summary:
            prev_info = f"${s['prev_equity']:,.2f} ({s['prev_date']})" if s['prev_equity'] else "N/A"
            nov3_info = f"${s['nov3_equity']:,.2f}" if s['nov3_equity'] else "N/A"
            status = "RESET!" if s['is_reset'] else "OK" if s['nov3_equity'] else "MISSING"

            print(f"{s['name']:<50} ${s['initial_equity']:>13,.2f} {prev_info:<30} {nov3_info:<15} {status:<10}")

        print("=" * 120)

        # Count issues
        reset_count = sum(1 for s in summary if s['is_reset'])
        missing_count = sum(1 for s in summary if s['nov3_equity'] is None)

        print(f"\nTotal Portfolios: {len(summary)}")
        print(f"Reset to Initial: {reset_count}")
        print(f"Missing Nov 3:    {missing_count}")
        print(f"OK:               {len(summary) - reset_count - missing_count}")
        print()


if __name__ == "__main__":
    asyncio.run(check_all())
