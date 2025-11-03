"""
Quick verification that the fix worked
"""
import asyncio
from datetime import date
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot


async def verify():
    async with get_async_session() as db:
        # Get demo individual portfolio
        portfolio_query = select(Portfolio).where(
            Portfolio.name.like("%Individual%")
        )
        portfolio_result = await db.execute(portfolio_query)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            print("Portfolio not found!")
            return

        print(f"\nPortfolio: {portfolio.name}")
        print(f"Initial Equity: ${portfolio.equity_balance:,.2f}")
        print()

        # Check Nov 3 snapshot
        nov_3_query = select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id == portfolio.id,
                PortfolioSnapshot.snapshot_date == date(2025, 11, 3)
            )
        )
        nov_3_result = await db.execute(nov_3_query)
        nov_3_snapshot = nov_3_result.scalar_one_or_none()

        # Check Oct 29 snapshot
        oct_29_query = select(PortfolioSnapshot).where(
            and_(
                PortfolioSnapshot.portfolio_id == portfolio.id,
                PortfolioSnapshot.snapshot_date == date(2025, 10, 29)
            )
        )
        oct_29_result = await db.execute(oct_29_query)
        oct_29_snapshot = oct_29_result.scalar_one_or_none()

        if nov_3_snapshot and oct_29_snapshot:
            print("Nov 3 Snapshot:")
            print(f"  Equity Balance: ${nov_3_snapshot.equity_balance:,.2f}")
            print(f"  Daily P&L: ${nov_3_snapshot.daily_pnl:,.2f}" if nov_3_snapshot.daily_pnl else "  Daily P&L: NULL")
            print()

            print("Oct 29 Snapshot (last before gap):")
            print(f"  Equity Balance: ${oct_29_snapshot.equity_balance:,.2f}")
            print()

            # Verify fix
            if abs(nov_3_snapshot.equity_balance - portfolio.equity_balance) < 1.0:
                print("❌ FAILED: Equity still reset to initial value ($485,000)!")
                print(f"   Nov 3 Equity: ${nov_3_snapshot.equity_balance:,.2f}")
                print(f"   Should be close to: ${oct_29_snapshot.equity_balance:,.2f}")
            elif nov_3_snapshot.daily_pnl and abs(nov_3_snapshot.equity_balance - (oct_29_snapshot.equity_balance + nov_3_snapshot.daily_pnl)) < 0.01:
                print("✅ SUCCESS: Equity properly rolled forward!")
                print(f"   Oct 29 Equity: ${oct_29_snapshot.equity_balance:,.2f}")
                print(f"   Nov 3 P&L: ${nov_3_snapshot.daily_pnl:,.2f}")
                print(f"   Nov 3 Equity: ${nov_3_snapshot.equity_balance:,.2f}")
                print(f"   Formula: ${oct_29_snapshot.equity_balance:,.2f} + ${nov_3_snapshot.daily_pnl:,.2f} = ${nov_3_snapshot.equity_balance:,.2f}")
            else:
                print("⚠️  Equity didn't reset to initial, but calculation may be off")
                print(f"   Oct 29: ${oct_29_snapshot.equity_balance:,.2f}")
                print(f"   Nov 3: ${nov_3_snapshot.equity_balance:,.2f}")
                print(f"   Daily P&L: ${nov_3_snapshot.daily_pnl or 0:,.2f}")
        else:
            print("Missing snapshot data")


if __name__ == "__main__":
    asyncio.run(verify())
