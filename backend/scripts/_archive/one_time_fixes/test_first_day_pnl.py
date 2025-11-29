"""
Test first-day P&L calculation after corrections.

This script:
1. Clears portfolio snapshots (preserves market data and entry prices)
2. Resets portfolio equity balances to initial values
3. Runs batch calculations for July 1, 2025
4. Verifies the first-day equity matches expected values

IMPORTANT: Only clears calculation results, NOT market data cache or entry prices!
"""

import asyncio
from decimal import Decimal
from datetime import date
from sqlalchemy import select, delete
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.positions import Position
from app.models.snapshots import PortfolioSnapshot
from app.batch.pnl_calculator import pnl_calculator


# Expected starting values (from requirements)
EXPECTED_VALUES = {
    "Demo Individual Investor Portfolio": {
        "initial_equity": Decimal("485000.00"),
        "invested_capital": Decimal("484925.00"),
        "uninvested_cash": Decimal("75.00"),
        "july1_market_value": Decimal("508522.36"),  # From our earlier analysis
        "expected_july1_equity": Decimal("508597.36"),  # Market value + cash
    },
    "Demo High Net Worth Investor Portfolio": {
        "initial_equity": Decimal("2850000.00"),
        # Public equities only for comparison
        "public_invested": Decimal("1282500.00"),  # After corrections
    },
    "Demo Hedge Fund Style Investor Portfolio": {
        "initial_equity": Decimal("3200000.00"),
        "long_stocks": Decimal("4960000.00"),
        "short_stocks": Decimal("2240000.00"),
        "options": Decimal("0.00"),
    }
}


async def reset_portfolio_equity(portfolio_name: str, initial_equity: Decimal):
    """Reset a portfolio's equity balance to initial value."""

    async with get_async_session() as db:
        result = await db.execute(
            select(Portfolio).where(Portfolio.name == portfolio_name)
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print(f"Portfolio '{portfolio_name}' not found")
            return False

        print(f"\nResetting {portfolio_name}:")
        print(f"  Current equity: ${portfolio.equity_balance:,.2f}")
        print(f"  Initial equity: ${initial_equity:,.2f}")

        portfolio.equity_balance = initial_equity
        await db.commit()

        print(f"  Reset complete: ${portfolio.equity_balance:,.2f}")
        return True


async def clear_portfolio_snapshots(portfolio_name: str):
    """Clear all snapshots for a portfolio."""

    async with get_async_session() as db:
        result = await db.execute(
            select(Portfolio).where(Portfolio.name == portfolio_name)
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print(f"Portfolio '{portfolio_name}' not found")
            return False

        # Count snapshots
        count_result = await db.execute(
            select(PortfolioSnapshot).where(PortfolioSnapshot.portfolio_id == portfolio.id)
        )
        snapshot_count = len(count_result.scalars().all())

        if snapshot_count > 0:
            print(f"  Clearing {snapshot_count} snapshots...")
            await db.execute(
                delete(PortfolioSnapshot).where(PortfolioSnapshot.portfolio_id == portfolio.id)
            )
            await db.commit()
            print(f"  Cleared {snapshot_count} snapshots")
        else:
            print(f"  No snapshots to clear")

        return True


async def verify_entry_values(portfolio_name: str):
    """Verify entry values match expected."""

    async with get_async_session() as db:
        result = await db.execute(
            select(Portfolio).where(Portfolio.name == portfolio_name)
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            return False

        positions_result = await db.execute(
            select(Position).where(Position.portfolio_id == portfolio.id)
        )
        positions = positions_result.scalars().all()

        total_entry = sum(p.entry_price * abs(p.quantity) for p in positions)

        print(f"\nEntry Values for {portfolio_name}:")
        print(f"  Total entry value: ${total_entry:,.2f}")

        expected = EXPECTED_VALUES.get(portfolio_name, {})
        if "invested_capital" in expected:
            print(f"  Expected:          ${expected['invested_capital']:,.2f}")
            match = abs(total_entry - expected['invested_capital']) < Decimal("1.00")
            print(f"  Match:             {match}")
            return match

        return True


async def run_first_day_calc(portfolio_name: str, calc_date: date):
    """Run P&L calculation for first day."""

    async with get_async_session() as db:
        result = await db.execute(
            select(Portfolio).where(Portfolio.name == portfolio_name)
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            return False

        print(f"\nRunning first-day P&L for {portfolio_name} on {calc_date}:")
        print(f"  Starting equity: ${portfolio.equity_balance:,.2f}")

        # Run the calculation
        success = await pnl_calculator.calculate_portfolio_pnl(
            db=db,
            portfolio_id=portfolio.id,
            calculation_date=calc_date
        )

        if success:
            # Refresh portfolio to get updated equity
            await db.refresh(portfolio)
            print(f"  Ending equity:   ${portfolio.equity_balance:,.2f}")

            # Verify against expected
            expected = EXPECTED_VALUES.get(portfolio_name, {})
            if "expected_july1_equity" in expected:
                expected_equity = expected["expected_july1_equity"]
                print(f"  Expected equity: ${expected_equity:,.2f}")
                diff = portfolio.equity_balance - expected_equity
                print(f"  Difference:      ${diff:,.2f}")

                match = abs(diff) < Decimal("1.00")
                print(f"  Match:           {match}")
                return match
        else:
            print(f"  Calculation failed!")
            return False

        return True


async def main():
    """Main test flow."""

    print("="*100)
    print("FIRST-DAY P&L CALCULATION TEST")
    print("="*100)
    print("\nThis test will:")
    print("1. Clear portfolio snapshots (preserves market data and entry prices)")
    print("2. Reset portfolio equity balances to initial values")
    print("3. Run first-day P&L calculation for July 1, 2025")
    print("4. Verify results match expected values")
    print("\n" + "="*100)

    response = input("\nProceed with test? (yes/no): ")
    if response.lower() != "yes":
        print("Test aborted")
        return

    # Test Individual Investor portfolio
    portfolio_name = "Demo Individual Investor Portfolio"
    expected = EXPECTED_VALUES[portfolio_name]

    print("\n" + "="*100)
    print(f"TESTING: {portfolio_name}")
    print("="*100)

    # Step 1: Verify entry values
    await verify_entry_values(portfolio_name)

    # Step 2: Clear snapshots
    await clear_portfolio_snapshots(portfolio_name)

    # Step 3: Reset equity
    await reset_portfolio_equity(portfolio_name, expected["initial_equity"])

    # Step 4: Run first-day calc
    july1 = date(2025, 7, 1)
    success = await run_first_day_calc(portfolio_name, july1)

    print("\n" + "="*100)
    if success:
        print("TEST PASSED!")
    else:
        print("TEST FAILED - Please review output above")
    print("="*100)


if __name__ == "__main__":
    asyncio.run(main())
