"""
Debug script to trace the equity rollforward calculation and find where it went wrong.
"""
import asyncio
from decimal import Decimal
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.snapshots import PortfolioSnapshot


async def trace_equity_rollforward():
    """Trace the equity balance rollforward over time."""
    async with AsyncSessionLocal() as session:
        # Get Individual Investor portfolio
        result = await session.execute(
            select(Portfolio).where(Portfolio.name.ilike("%Individual Investor%"))
        )
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("ERROR: Portfolio not found")
            return

        print(f"\n{'='*80}")
        print(f"EQUITY ROLLFORWARD TRACE")
        print(f"{'='*80}\n")
        print(f"Portfolio: {portfolio.name}")
        print(f"Expected Starting Equity: $485,000.00")
        print(f"Current Equity in DB: ${float(portfolio.equity_balance):,.2f}")
        print(f"\n")

        # Get all snapshots in chronological order
        snapshots_result = await session.execute(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .order_by(PortfolioSnapshot.snapshot_date.asc())
        )
        snapshots = snapshots_result.scalars().all()

        if not snapshots:
            print("ERROR: No snapshots found")
            return

        print(f"Found {len(snapshots)} snapshots\n")
        print(f"{'Date':<12} {'Total Value':<15} {'Equity Bal':<15} {'Daily P&L':<15} {'Calc Equity':<15} {'Match?':<10}")
        print(f"{'-'*100}")

        expected_equity = Decimal("485000.00")
        previous_value = None

        for i, snap in enumerate(snapshots):
            total_value = snap.total_value
            equity_bal = snap.equity_balance or Decimal('0')

            # Calculate what daily P&L should be
            if previous_value is not None:
                daily_pnl = total_value - previous_value
                calculated_equity = expected_equity + daily_pnl
            else:
                # First snapshot
                daily_pnl = Decimal('0')
                calculated_equity = Decimal("485000.00")

            # Check if snapshot equity matches expected
            match = "OK" if abs(equity_bal - calculated_equity) < Decimal('0.01') else "ERROR"

            print(
                f"{str(snap.snapshot_date):<12} "
                f"${float(total_value):>13,.2f} "
                f"${float(equity_bal):>13,.2f} "
                f"${float(daily_pnl):>13,.2f} "
                f"${float(calculated_equity):>13,.2f} "
                f"{match:<10}"
            )

            # Update for next iteration
            expected_equity = calculated_equity
            previous_value = total_value

        print(f"\n{'='*80}")
        print(f"ANALYSIS:")
        print(f"{'='*80}\n")

        first_snap = snapshots[0]
        last_snap = snapshots[-1]

        print(f"First Snapshot ({first_snap.snapshot_date}):")
        print(f"  Equity Balance: ${float(first_snap.equity_balance):,.2f}" if first_snap.equity_balance else "  Equity Balance: None")
        print(f"  Total Value:    ${float(first_snap.total_value):,.2f}")
        print(f"  Expected:       $485,000.00")

        if first_snap.equity_balance:
            if abs(float(first_snap.equity_balance) - 485000) > 1:
                print(f"  PROBLEM: First snapshot equity is wrong!")
                print(f"     Difference: ${float(first_snap.equity_balance) - 485000:,.2f}")

        print(f"\nLast Snapshot ({last_snap.snapshot_date}):")
        print(f"  Equity Balance: ${float(last_snap.equity_balance):,.2f}" if last_snap.equity_balance else "  Equity Balance: None")
        print(f"  Total Value:    ${float(last_snap.total_value):,.2f}")
        print(f"  Expected:       ${float(expected_equity):,.2f}")

        if last_snap.equity_balance:
            discrepancy = float(last_snap.total_value) - float(last_snap.equity_balance)
            print(f"  Discrepancy:    ${discrepancy:,.2f}")

            if abs(discrepancy) > 100:
                print(f"\n  MAJOR PROBLEM: Equity balance has diverged from total value!")
                print(f"     This means the rollforward calculation is broken.")


if __name__ == "__main__":
    asyncio.run(trace_equity_rollforward())
