"""
Export corrected entry prices from database to update seed file.

This script reads the current database positions and generates the corrected
seed data entries that can be copied into seed_demo_portfolios.py.
"""

import asyncio
from decimal import Decimal
from sqlalchemy import select, and_
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.positions import Position


async def export_portfolio_positions(portfolio_name: str):
    """Export positions for a specific portfolio."""

    async with get_async_session() as db:
        # Get portfolio
        portfolio_result = await db.execute(
            select(Portfolio).where(Portfolio.name == portfolio_name)
        )
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            print(f"Portfolio '{portfolio_name}' not found")
            return

        # Get positions
        positions_result = await db.execute(
            select(Position).where(
                and_(
                    Position.portfolio_id == portfolio.id,
                    Position.deleted_at.is_(None)
                )
            ).order_by(Position.symbol)
        )
        positions = positions_result.scalars().all()

        print(f"\n{'='*100}")
        print(f"PORTFOLIO: {portfolio_name}")
        print(f"{'='*100}")
        print(f"Total Positions: {len(positions)}")
        print(f"Equity Balance: ${portfolio.equity_balance:,.2f}")

        # Calculate totals
        total_entry_value = sum(p.entry_price * abs(p.quantity) for p in positions)
        print(f"Total Entry Value: ${total_entry_value:,.2f}")
        print(f"Uninvested Cash: ${portfolio.equity_balance - total_entry_value:,.2f}")

        print(f"\nCORRECTED ENTRY PRICES:")
        print(f"{'Symbol':<25} {'Quantity':>12} {'Entry Price':>15} {'Entry Value':>18}")
        print(f"{'-'*25} {'-'*12} {'-'*15} {'-'*18}")

        for p in positions:
            entry_value = p.entry_price * abs(p.quantity)
            print(f"{p.symbol:<25} {float(p.quantity):>12.2f} ${float(p.entry_price):>14.2f} ${float(entry_value):>17,.2f}")


async def export_all_corrected_portfolios():
    """Export all three corrected portfolios."""

    portfolios = [
        "Demo Individual Investor Portfolio",
        "Demo High Net Worth Investor Portfolio",
        "Demo Hedge Fund Style Investor Portfolio"
    ]

    print("\n" + "#"*100)
    print("# EXPORTING CORRECTED ENTRY PRICES FROM DATABASE")
    print("#"*100)

    for portfolio_name in portfolios:
        await export_portfolio_positions(portfolio_name)

    print("\n" + "="*100)
    print("EXPORT COMPLETE")
    print("="*100)
    print("\nNext steps:")
    print("1. Use these values to update seed_demo_portfolios.py")
    print("2. Update Ben Mock Portfolios.md with the corrected entry prices")
    print("3. Test by reseeding the database")


if __name__ == "__main__":
    asyncio.run(export_all_corrected_portfolios())
