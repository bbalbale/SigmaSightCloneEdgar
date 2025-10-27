"""
Debug script to compare snapshot total_values with actual position prices.
This will reveal if snapshots are using stale data or if they were all created at once.
"""
import asyncio
from datetime import date
from decimal import Decimal
from sqlalchemy import select
from app.database import get_async_session
from app.models.snapshots import PortfolioSnapshot
from app.models.positions import Position
from app.models.users import Portfolio


async def analyze_snapshot_vs_positions():
    """Compare snapshot values with position market values"""
    async with get_async_session() as db:
        print("\n" + "="*80)
        print("SNAPSHOT VS POSITION PRICE ANALYSIS")
        print("="*80)

        # Get Individual Investor portfolio (the one with clear frozen values)
        portfolio_query = select(Portfolio).where(
            Portfolio.name.ilike("%Individual Investor%")
        )
        portfolio_result = await db.execute(portfolio_query)
        portfolio = portfolio_result.scalar_one_or_none()

        if not portfolio:
            print("Portfolio not found")
            return

        print(f"\nPortfolio: {portfolio.name}")
        print(f"Portfolio ID: {portfolio.id}")

        # Get all positions
        position_query = select(Position).where(Position.portfolio_id == portfolio.id)
        position_result = await db.execute(position_query)
        positions = position_result.scalars().all()

        # Calculate current total from position market_values
        current_total = sum(pos.market_value or Decimal('0') for pos in positions)

        print(f"\nCurrent Position Data (as of {positions[0].updated_at if positions else 'N/A'}):")
        print(f"  Sum of Position.market_value: ${current_total:,.2f}")

        # Get snapshots for this portfolio
        snapshot_query = (
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.portfolio_id == portfolio.id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(10)
        )
        snapshot_result = await db.execute(snapshot_query)
        snapshots = snapshot_result.scalars().all()

        print(f"\n\nSnapshot Analysis (last 10):")
        print(f"{'Snapshot Date':<15} {'Total Value':<18} {'Created At':<25} {'Match?':<10}")
        print("-" * 80)

        for snapshot in snapshots:
            created_str = snapshot.created_at.strftime("%Y-%m-%d %H:%M:%S") if snapshot.created_at else "NULL"
            match = "YES" if abs(snapshot.total_value - current_total) < Decimal('0.01') else "NO"

            print(f"{str(snapshot.snapshot_date):<15} ${snapshot.total_value:>15,.2f} {created_str:<25} {match:<10}")

        # Key insight: Check if all snapshots were created at the same time
        if len(snapshots) > 1:
            creation_times = [s.created_at for s in snapshots if s.created_at]
            unique_creation_times = set(
                ct.strftime("%Y-%m-%d %H:%M") for ct in creation_times
            )

            print(f"\n\nKEY FINDINGS:")
            print(f"1. Current position total: ${current_total:,.2f}")
            print(f"2. Number of unique creation times: {len(unique_creation_times)}")

            if len(unique_creation_times) <= 3:
                print(f"   Creation times: {sorted(unique_creation_times)}")
                print(f"   ⚠️  ISSUE: Most/all snapshots created in batch, not daily!")

            # Check if all recent snapshots have the same total_value
            recent_values = [float(s.total_value) for s in snapshots[:5]]
            if len(set(recent_values)) == 1:
                print(f"3. ⚠️  CRITICAL: Last 5 snapshots ALL have identical total_value: ${recent_values[0]:,.2f}")
                print(f"   This means snapshots are NOT reflecting daily price changes!")
            else:
                print(f"3. ✅ Last 5 snapshots have varying values: {[f'${v:,.2f}' for v in recent_values]}")

        # Now check if prepare_positions_for_aggregation uses historical prices
        print(f"\n\n{'='*80}")
        print("CHECKING SNAPSHOT CALCULATION METHOD")
        print("="*80)

        print("\nLooking at how snapshot calculates total_value...")
        print("From app/calculations/snapshots.py:")
        print("  Line 71: position_data = await _prepare_position_data(db, active_positions, calculation_date)")
        print("  Line 79: aggregations = calculate_portfolio_exposures(positions_list)")
        print("  Line 504: 'total_value': aggregations['gross_exposure']")

        print("\nKey Question: Does _prepare_position_data use historical prices?")
        print("  It calls: prepare_positions_for_aggregation(db, positions)")
        print("  ⚠️  WARNING: This function does NOT take calculation_date as a parameter!")
        print("  This means it uses CURRENT Position.market_value, not historical prices!")

        print("\n\nROOT CAUSE HYPOTHESIS:")
        print("="*80)
        print("Snapshots are created with calculation_date (e.g., Oct 1, Oct 2, etc.)")
        print("BUT they all use the SAME current Position.market_value from the database.")
        print("There is no historical price lookup for past dates.")
        print("")
        print("Result: All snapshots have the same total_value because they're all")
        print("reading the same Position.market_value field, regardless of snapshot_date.")


if __name__ == "__main__":
    asyncio.run(analyze_snapshot_vs_positions())
