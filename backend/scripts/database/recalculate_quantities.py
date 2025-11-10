#!/usr/bin/env python
"""
Recalculate position quantities to match intended portfolio values.

This script adjusts quantities so that (quantity × entry_price) for all positions
in a portfolio equals the intended total portfolio value from Ben Mock Portfolios.md
"""

import asyncio
from decimal import Decimal
from sqlalchemy import select
from pathlib import Path
import sys

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from app.database import get_async_session
from app.models.positions import Position
from app.models.users import Portfolio, User

# Target portfolio values from Ben Mock Portfolios.md
TARGET_VALUES = {
    "Demo Individual Investor Portfolio": Decimal("485000.00"),
    "Demo High Net Worth Investor Portfolio": Decimal("2850000.00"),
    "Demo Hedge Fund Style Investor Portfolio": Decimal("3200000.00"),
    "Demo Family Office Public Growth": Decimal("1250000.00"),
    "Demo Family Office Private Opportunities": Decimal("950000.00"),
}


async def recalculate_quantities():
    """Recalculate quantities to match target values."""

    async with get_async_session() as db:
        print("=" * 80)
        print("RECALCULATING POSITION QUANTITIES")
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

            # Calculate current total value
            current_value = sum(
                pos.quantity * pos.entry_price
                for pos in positions
            )

            # Calculate scaling factor
            if current_value > 0:
                scale_factor = target_value / current_value
            else:
                scale_factor = Decimal("1.0")

            print(f"\n{portfolio.name}")
            print(f"  Target Value: ${target_value:,.2f}")
            print(f"  Current Value: ${current_value:,.2f}")
            print(f"  Scale Factor: {scale_factor:.6f}")
            print(f"  Positions to adjust: {len(positions)}")

            # Adjust each position quantity
            for pos in positions:
                old_quantity = pos.quantity
                new_quantity = (old_quantity * scale_factor).quantize(Decimal("0.01"))

                pos.quantity = new_quantity
                db.add(pos)

                old_value = old_quantity * pos.entry_price
                new_value = new_quantity * pos.entry_price

                if abs(new_quantity - old_quantity) > Decimal("0.01"):
                    print(f"    {pos.symbol:10} {old_quantity:>10.2f} -> {new_quantity:>10.2f} shares  "
                          f"(${old_value:>12,.2f} -> ${new_value:>12,.2f})")

            # Verify new total
            new_total = sum(
                pos.quantity * pos.entry_price
                for pos in positions
            )

            print(f"  New Total Value: ${new_total:,.2f}")
            print(f"  Difference from target: ${abs(new_total - target_value):,.2f}")

        print("\n" + "=" * 80)
        response = input("Apply these changes? (yes/no): ")

        if response.lower() == 'yes':
            await db.commit()
            print("[OK] Changes committed to database")
        else:
            await db.rollback()
            print("[CANCELLED] Changes rolled back")


if __name__ == "__main__":
    asyncio.run(recalculate_quantities())
