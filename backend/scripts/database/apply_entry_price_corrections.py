"""
Apply entry price corrections to the database.

This script reads the corrections plan from analyze_corrections_needed.py
and applies them to the positions table.

IMPORTANT: Run analyze_corrections_needed.py first to generate the corrections plan!
"""

import asyncio
import csv
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select, update
from app.database import get_async_session
from app.models.positions import Position
from app.models.users import Portfolio


async def apply_corrections():
    """Apply all entry price corrections from the plan."""

    # Read corrections plan
    print("\n" + "="*100)
    print("LOADING CORRECTIONS PLAN")
    print("="*100)

    try:
        with open("entry_price_corrections_plan.csv", "r") as f:
            reader = csv.DictReader(f)
            corrections = list(reader)
    except FileNotFoundError:
        print("ERROR: entry_price_corrections_plan.csv not found!")
        print("Run analyze_corrections_needed.py first to generate the plan.")
        return

    print(f"Loaded {len(corrections)} corrections")

    async with get_async_session() as db:
        print("\n" + "="*100)
        print("APPLYING CORRECTIONS")
        print("="*100)

        applied_count = 0
        failed_count = 0

        for i, corr in enumerate(corrections, 1):
            position_id = UUID(corr["position_id"])
            symbol = corr["symbol"]
            old_price = Decimal(corr["old_entry_price"])
            new_price = Decimal(corr["new_entry_price"])
            portfolio = corr["portfolio"]

            try:
                # Update the position
                result = await db.execute(
                    update(Position)
                    .where(Position.id == position_id)
                    .values(entry_price=new_price)
                )

                if result.rowcount == 1:
                    print(f"[{i:3d}/{len(corrections)}] {portfolio:30s} {symbol:20s}: ${old_price:8.2f} -> ${new_price:8.2f} OK")
                    applied_count += 1
                else:
                    print(f"[{i:3d}/{len(corrections)}] {portfolio:30s} {symbol:20s}: FAILED (position not found)")
                    failed_count += 1

            except Exception as e:
                print(f"[{i:3d}/{len(corrections)}] {portfolio:30s} {symbol:20s}: ERROR - {e}")
                failed_count += 1

        # Commit all changes
        if applied_count > 0:
            print("\n" + "="*100)
            print("COMMITTING CHANGES")
            print("="*100)
            await db.commit()
            print(f"Successfully applied {applied_count} corrections")
        else:
            print("\nNo corrections applied - rolling back")
            await db.rollback()

        if failed_count > 0:
            print(f"WARNING: {failed_count} corrections failed")

        # Verify results
        print("\n" + "="*100)
        print("VERIFICATION")
        print("="*100)

        # Check Individual Investor
        individual = await db.execute(
            select(Portfolio).where(Portfolio.name == "Demo Individual Investor Portfolio")
        )
        individual = individual.scalar_one()

        positions = await db.execute(
            select(Position).where(Position.portfolio_id == individual.id)
        )
        positions = positions.scalars().all()

        total_entry = sum(p.entry_price * p.quantity for p in positions)
        print(f"\nIndividual Investor:")
        print(f"  Total Entry Value: ${total_entry:,.2f}")
        print(f"  Target:            $484,925.00")
        print(f"  Match:             {abs(total_entry - Decimal('484925')) < Decimal('0.01')}")

        # Check High Net Worth (public only)
        hnw = await db.execute(
            select(Portfolio).where(Portfolio.name == "Demo High Net Worth Investor Portfolio")
        )
        hnw = hnw.scalar_one()

        positions = await db.execute(
            select(Position).where(Position.portfolio_id == hnw.id)
        )
        positions = positions.scalars().all()

        public_positions = [p for p in positions if p.investment_class == "PUBLIC"]
        total_public_entry = sum(p.entry_price * p.quantity for p in public_positions)

        print(f"\nHigh Net Worth (Public Equities Only):")
        print(f"  Total Entry Value: ${total_public_entry:,.2f}")
        print(f"  Target:            $1,282,500.00")
        print(f"  Difference:        ${abs(total_public_entry - Decimal('1282500')):,.2f}")

        # Check Hedge Fund
        hedge = await db.execute(
            select(Portfolio).where(Portfolio.name == "Demo Hedge Fund Style Investor Portfolio")
        )
        hedge = hedge.scalar_one()

        positions = await db.execute(
            select(Position).where(Portfolio.id == hedge.id)
        )
        positions = positions.scalars().all()

        from app.models.positions import PositionType
        long_stocks = [p for p in positions if p.position_type == PositionType.LONG]
        short_stocks = [p for p in positions if p.position_type == PositionType.SHORT]
        options = [p for p in positions if p.position_type in (PositionType.LC, PositionType.LP, PositionType.SC, PositionType.SP)]

        total_long = sum(p.entry_price * abs(p.quantity) for p in long_stocks)
        total_short = sum(p.entry_price * abs(p.quantity) for p in short_stocks)
        total_options = sum(p.entry_price * abs(p.quantity) for p in options)

        print(f"\nHedge Fund Style:")
        print(f"  Long Stocks Total:  ${total_long:,.2f} (target: $4,960,000.00)")
        print(f"  Short Stocks Total: ${total_short:,.2f} (target: $2,240,000.00)")
        print(f"  Options Total:      ${total_options:,.2f} (target: $0.00)")
        print(f"  Long Match:         {abs(total_long - Decimal('4960000')) < Decimal('100')}")
        print(f"  Short Match:        {abs(total_short - Decimal('2240000')) < Decimal('100')}")
        print(f"  Options Match:      {total_options == Decimal('0')}")


if __name__ == "__main__":
    print("\n" + "#"*100)
    print("# ENTRY PRICE CORRECTION APPLICATION")
    print("#"*100)
    print("\nThis script will apply entry price corrections to fix portfolio discrepancies.")
    print("Make sure you have:")
    print("  1. Run analyze_corrections_needed.py to generate the corrections plan")
    print("  2. Reviewed the corrections plan CSV")
    print("  3. Backed up your database (if needed)")
    print("\n" + "#"*100)

    response = input("\nProceed with corrections? (yes/no): ")
    if response.lower() == "yes":
        asyncio.run(apply_corrections())
    else:
        print("Aborted by user")
