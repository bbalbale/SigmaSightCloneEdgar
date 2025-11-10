#!/usr/bin/env python
"""
Adjust entry prices to achieve exact target equity with whole number shares.

This script rounds quantities to whole numbers and adjusts entry prices
proportionally so that (quantity × entry_price) equals the target portfolio value.
"""

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from app.database import get_async_session
from app.models.positions import Position
from app.models.users import Portfolio

# Target portfolio values from Ben Mock Portfolios.md
TARGET_VALUES = {
    "Demo Individual Investor Portfolio": Decimal("485000.00"),
    "Demo High Net Worth Investor Portfolio": Decimal("2850000.00"),
    "Demo Hedge Fund Style Investor Portfolio": Decimal("3200000.00"),
    "Demo Family Office Public Growth": Decimal("1250000.00"),
    "Demo Family Office Private Opportunities": Decimal("950000.00"),
}


async def adjust_prices_for_exact_equity():
    """Adjust entry prices to match target values with whole shares."""

    async with get_async_session() as db:
        print("=" * 80)
        print("ADJUSTING ENTRY PRICES FOR EXACT EQUITY MATCH")
        print("=" * 80)
        print()

        # Get all portfolios with their positions
        result = await db.execute(
            select(Portfolio)
            .where(Portfolio.name.in_(list(TARGET_VALUES.keys())))
        )
        portfolios = result.scalars().all()

        for portfolio in portfolios:
            target_value = TARGET_VALUES[portfolio.name]

            # Get all positions for this portfolio
            pos_result = await db.execute(
                select(Position)
                .where(Position.portfolio_id == portfolio.id)
                .order_by(Position.symbol)
            )
            positions = pos_result.scalars().all()

            print(f"\n{portfolio.name}")
            print(f"  Target Value: ${target_value:,.2f}")
            print(f"  Positions: {len(positions)}")
            print()

            # Round all quantities to whole numbers first
            for pos in positions:
                # For SHORT positions (negative quantity), round away from zero
                if pos.quantity < 0:
                    pos.quantity = pos.quantity.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                else:
                    pos.quantity = pos.quantity.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

                # Keep private investments at 1.0 or whole numbers
                if pos.investment_class == 'PRIVATE':
                    pos.quantity = Decimal("1.00")

            # Calculate current total with whole shares
            current_value = sum(
                pos.quantity * pos.entry_price
                for pos in positions
            )

            # Calculate price adjustment factor
            if current_value > 0:
                price_scale = target_value / current_value
            else:
                price_scale = Decimal("1.0")

            print(f"  Current Value (whole shares): ${current_value:,.2f}")
            print(f"  Price Scale Factor: {price_scale:.8f}")
            print()
            print(f"  {'Symbol':10} {'Qty':>8} {'Old Price':>12} {'New Price':>12} {'Position Value':>15}")
            print("  " + "-" * 68)

            # Adjust entry prices
            for pos in positions:
                old_price = pos.entry_price
                new_price = (old_price * price_scale).quantize(Decimal("0.01"))

                pos.entry_price = new_price
                db.add(pos)

                position_value = pos.quantity * new_price

                print(f"  {pos.symbol[:10]:10} {pos.quantity:>8.0f} "
                      f"${old_price:>10,.2f} ${new_price:>10,.2f} ${position_value:>13,.2f}")

            # Verify new total
            new_total = sum(
                pos.quantity * pos.entry_price
                for pos in positions
            )

            print("  " + "-" * 68)
            print(f"  New Total Value: ${new_total:,.2f}")
            difference = abs(new_total - target_value)
            print(f"  Difference from target: ${difference:,.2f}")

            if difference > Decimal("0.01"):
                print(f"  [WARNING] Difference exceeds $0.01")

        print("\n" + "=" * 80)
        response = input("Apply these changes? (yes/no): ")

        if response.lower() == 'yes':
            await db.commit()
            print("[OK] Changes committed to database")
        else:
            await db.rollback()
            print("[CANCELLED] Changes rolled back")


if __name__ == "__main__":
    asyncio.run(adjust_prices_for_exact_equity())
