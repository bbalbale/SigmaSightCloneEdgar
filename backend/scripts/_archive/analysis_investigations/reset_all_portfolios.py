"""Reset all three demo portfolios and delete their snapshots"""
import asyncio
from sqlalchemy import select, delete
from app.database import AsyncSessionLocal
from app.models.snapshots import PortfolioSnapshot
from app.models.users import Portfolio
from uuid import UUID

async def reset_all():
    # Portfolio IDs and starting equities from Ben Mock Portfolios.md
    portfolios = {
        UUID('1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe'): {
            'name': 'Balanced Individual Investor',
            'equity': 485000.00
        },
        UUID('a7d66e7f-c04d-8b12-2c44-9e75d87f5c5e'): {
            'name': 'Sophisticated High Net Worth',
            'equity': 2850000.00
        },
        UUID('3a5d7c8e-4f6b-9a2d-1e3c-8b7f6a5d4c3b'): {
            'name': 'Long/Short Equity Hedge Fund Style',
            'equity': 3200000.00
        }
    }

    async with AsyncSessionLocal() as db:
        print("=" * 80)
        print("RESETTING ALL DEMO PORTFOLIOS")
        print("=" * 80)
        print()

        for portfolio_id, info in portfolios.items():
            print(f"Portfolio: {info['name']}")
            print(f"  ID: {portfolio_id}")

            # Delete snapshots
            delete_result = await db.execute(
                delete(PortfolioSnapshot).where(PortfolioSnapshot.portfolio_id == portfolio_id)
            )
            print(f"  ✓ Deleted {delete_result.rowcount} snapshots")

            # Reset equity_balance
            portfolio_result = await db.execute(
                select(Portfolio).where(Portfolio.id == portfolio_id)
            )
            portfolio = portfolio_result.scalar_one_or_none()

            if portfolio:
                portfolio.equity_balance = info['equity']
                print(f"  ✓ Reset equity to ${info['equity']:,.2f}")
            else:
                print(f"  ❌ Portfolio not found!")

            print()

        await db.commit()

        print("=" * 80)
        print("RESET COMPLETE!")
        print()
        print("Next: Run batch calculations to rebuild snapshots with correct P&L")
        print("=" * 80)

asyncio.run(reset_all())
