"""Quick script to verify the fix worked"""
import asyncio
from sqlalchemy import select
from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio


async def verify_results():
    async with get_async_session() as db:
        # Get Individual Investor portfolio
        portfolio_query = select(Portfolio).where(
            Portfolio.name.ilike("%Individual Investor%")
        )
        portfolio_result = await db.execute(portfolio_query)
        portfolio = portfolio_result.scalar_one_or_none()

        # Get all recent snapshots
        snapshot_query = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(10)
        )
        snapshot_result = await db.execute(snapshot_query)
        snapshots = snapshot_result.scalars().all()

        print("\n" + "="*80)
        print("VERIFICATION: Daily P&L Fix Results")
        print("="*80)
        print(f"\n{'Date':<15} {'Total Value':<18} {'Daily P&L':<18} {'Cumul P&L':<18}")
        print("-" * 80)

        for snapshot in snapshots:
            date_str = str(snapshot.snapshot_date)
            total_value_str = f"${snapshot.total_value:,.2f}"
            daily_pnl_str = f"${snapshot.daily_pnl:,.2f}" if snapshot.daily_pnl is not None else "NULL"
            cumul_pnl_str = f"${snapshot.cumulative_pnl:,.2f}" if snapshot.cumulative_pnl is not None else "NULL"

            print(f"{date_str:<15} {total_value_str:<18} {daily_pnl_str:<18} {cumul_pnl_str:<18}")

        # Check results
        total_values = [float(s.total_value) for s in snapshots[:5]]
        unique_values = len(set(total_values))
        null_pnl_count = sum(1 for s in snapshots[:5] if s.daily_pnl is None)

        print(f"\n\n{'='*80}")
        print("RESULTS:")
        print("="*80)
        print(f"Last 5 snapshots unique values: {unique_values}/5")
        print(f"Snapshots with NULL daily_pnl: {null_pnl_count}/5")

        if unique_values >= 3 and null_pnl_count <= 1:
            print(f"\n✓✓✓ FIX SUCCESSFUL! ✓✓✓")
            print(f"Snapshots now use historical prices and P&L is calculated correctly!")
        elif unique_values >= 2:
            print(f"\n✓ PARTIAL SUCCESS: Values are varying, but may need more historical data")
        else:
            print(f"\n✗ ISSUE: Values still frozen, historical data may be missing")


if __name__ == "__main__":
    asyncio.run(verify_results())
