"""
Debug script to show portfolio equity calculations for Individual Investor portfolio.
"""
import asyncio
from decimal import Decimal
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.positions import Position


async def debug_equity_calculation():
    """Show detailed equity calculation breakdown."""
    async with AsyncSessionLocal() as session:
        # Find Individual Investor portfolio
        result = await session.execute(
            select(Portfolio).where(Portfolio.name.ilike("%Individual Investor%"))
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("❌ Individual Investor portfolio not found")
            print("\nSearching for all portfolios...")
            all_result = await session.execute(select(Portfolio))
            all_portfolios = all_result.scalars().all()
            for p in all_portfolios:
                print(f"  - {p.name}")
            return

        print(f"\n{'='*80}")
        print(f"Portfolio: {portfolio.name}")
        print(f"ID: {portfolio.id}")
        print(f"{'='*80}\n")

        # Get all positions
        positions_result = await session.execute(
            select(Position).where(Position.portfolio_id == portfolio.id)
        )
        positions = positions_result.scalars().all()

        print(f"Total Positions: {len(positions)}\n")

        # Calculate equity components
        total_market_value = Decimal('0')
        user_provided_nav = portfolio.equity_balance or Decimal('0')

        print(f"{'Symbol':<10} {'Type':<10} {'Quantity':<12} {'Last Price':<12} {'Market Value':<15}")
        print(f"{'-'*80}")

        for pos in positions:
            # Use fields directly from Position model
            last_price = pos.last_price or Decimal('0')
            quantity = pos.quantity or Decimal('0')
            market_value = pos.market_value or (last_price * quantity)

            print(f"{pos.symbol:<10} {pos.position_type.value:<10} {float(quantity):<12.2f} ${float(last_price):<11.2f} ${float(market_value):<14.2f}")

            total_market_value += market_value

        print(f"{'-'*80}")
        print(f"\nEquity Calculation Breakdown:")
        print(f"  Calculated Market Value (sum of positions): ${float(total_market_value):,.2f}")
        print(f"  User-Provided NAV (equity_balance):         ${float(user_provided_nav):,.2f}")
        print(f"  {'='*60}")
        print(f"  Difference:                                 ${float(user_provided_nav - total_market_value):,.2f}")
        print(f"\n")

        # Also show what the snapshot contains
        print(f"{'='*80}")
        print(f"Portfolio Snapshot Equity Value:")
        print(f"{'='*80}\n")

        from app.models.snapshots import PortfolioSnapshot

        snapshot_result = await session.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(1)
        )
        snapshot = snapshot_result.scalar_one_or_none()

        if snapshot:
            print(f"Latest Snapshot Date: {snapshot.snapshot_date}")
            print(f"\nSnapshot Values:")
            print(f"  Total Value:      ${float(snapshot.total_value):,.2f}  (current market value of all positions)")
            print(f"  Cash Value:       ${float(snapshot.cash_value):,.2f}")
            print(f"  Long Value:       ${float(snapshot.long_value):,.2f}")
            print(f"  Short Value:      ${float(snapshot.short_value):,.2f}")
            print(f"  Equity Balance:   ${float(snapshot.equity_balance):,.2f}  (starting capital + realized P&L)" if snapshot.equity_balance else "  Equity Balance:   None")
            print(f"  Gross Exposure:   ${float(snapshot.gross_exposure):,.2f}")
            print(f"  Net Exposure:     ${float(snapshot.net_exposure):,.2f}")

            # Calculate unrealized P&L
            if snapshot.equity_balance:
                unrealized_pnl = float(snapshot.total_value) - float(snapshot.equity_balance)
                print(f"\nUnrealized P&L Calculation:")
                print(f"  Total Value - Equity Balance = ${unrealized_pnl:,.2f}")
        else:
            print("❌ No snapshot found for this portfolio")

        print(f"\n{'='*80}")
        print(f"SUMMARY - Portfolio Equity Interpretation:")
        print(f"{'='*80}")
        print(f"\n1. TOTAL VALUE (Market Value): ${float(total_market_value):,.2f}")
        print(f"   - This is the current market value of all positions")
        print(f"   - Used in snapshot.total_value")
        print(f"\n2. EQUITY BALANCE (NAV/Book Value): ${float(user_provided_nav):,.2f}")
        print(f"   - Starting capital + realized P&L")
        print(f"   - Stored in portfolio.equity_balance and snapshot.equity_balance")
        print(f"\n3. UNREALIZED P&L: ${float(total_market_value - user_provided_nav):,.2f}")
        print(f"   - Difference between market value and equity balance")
        print(f"   - This is the gain/loss on open positions")
        print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(debug_equity_calculation())
