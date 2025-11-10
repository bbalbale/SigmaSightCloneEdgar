#!/usr/bin/env python
"""
Fine-tune entry prices for EXACT equity match.

This script adjusts the LARGEST position's entry price in each portfolio
to achieve an exact match to the target equity value.

For the hedge fund portfolio, respects the 100% long / 50% short constraint.
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
from app.models.users import Portfolio

# Target portfolio values from Ben Mock Portfolios.md
TARGET_VALUES = {
    "Demo Individual Investor Portfolio": Decimal("485000.00"),
    "Demo High Net Worth Investor Portfolio": Decimal("2850000.00"),
    "Demo Hedge Fund Style Investor Portfolio": Decimal("3200000.00"),
    "Demo Family Office Public Growth": Decimal("1250000.00"),
    "Demo Family Office Private Opportunities": Decimal("950000.00"),
}


async def fine_tune_for_exact_match():
    """Fine-tune prices to get exact equity match."""

    async with get_async_session() as db:
        print("=" * 80)
        print("FINE-TUNING FOR EXACT EQUITY MATCH")
        print("=" * 80)
        print()

        result = await db.execute(
            select(Portfolio)
            .where(Portfolio.name.in_(list(TARGET_VALUES.keys())))
        )
        portfolios = result.scalars().all()

        for portfolio in portfolios:
            target_value = TARGET_VALUES[portfolio.name]

            # Get all positions
            pos_result = await db.execute(
                select(Position)
                .where(Position.portfolio_id == portfolio.id)
                .order_by(Position.symbol)
            )
            positions = list(pos_result.scalars().all())

            # Calculate current total
            current_value = sum(pos.quantity * pos.entry_price for pos in positions)
            difference = target_value - current_value

            print(f"\n{portfolio.name}")
            print(f"  Target: ${target_value:,.2f}")
            print(f"  Current: ${current_value:,.2f}")
            print(f"  Difference: ${difference:,.2f}")

            if abs(difference) < Decimal("0.01"):
                print("  Already at target!")
                continue

            # Special handling for hedge fund (need to respect long/short constraints)
            if "Hedge Fund" in portfolio.name:
                # Separate long and short positions
                long_positions = [p for p in positions if p.quantity > 0 and p.investment_class == 'PUBLIC']
                short_positions = [p for p in positions if p.quantity < 0]

                # Find largest long position by absolute value
                largest_long = max(long_positions, key=lambda p: abs(p.quantity * p.entry_price))

                # Calculate iteratively to handle rounding
                old_price = largest_long.entry_price
                old_value = largest_long.quantity * old_price

                # Try adjusting the price to hit the target
                attempts = 0
                max_attempts = 10
                best_price = old_price
                best_diff = abs(difference)

                for price_delta in [difference / largest_long.quantity,
                                   difference / largest_long.quantity + Decimal("0.01"),
                                   difference / largest_long.quantity - Decimal("0.01")]:
                    test_price = (old_price + price_delta).quantize(Decimal("0.01"))
                    test_value = largest_long.quantity * test_price
                    test_total = sum(pos.quantity * pos.entry_price for pos in positions if pos.id != largest_long.id) + test_value
                    test_diff = abs(test_total - target_value)

                    if test_diff < best_diff:
                        best_diff = test_diff
                        best_price = test_price

                    if test_diff < Decimal("0.01"):
                        break

                new_price = best_price
                new_value = largest_long.quantity * new_price

                largest_long.entry_price = new_price
                db.add(largest_long)

                print(f"  Adjusting {largest_long.symbol}:")
                print(f"    Price: ${old_price:,.2f} -> ${new_price:,.2f}")
                print(f"    Position value: ${old_value:,.2f} -> ${new_value:,.2f}")

            else:
                # For other portfolios, adjust the largest position
                # Find largest position by absolute value (excluding options with $0 price)
                valid_positions = [p for p in positions if p.entry_price > 0]

                if not valid_positions:
                    print("  No valid positions to adjust!")
                    continue

                largest_pos = max(valid_positions, key=lambda p: abs(p.quantity * p.entry_price))

                old_price = largest_pos.entry_price
                old_value = largest_pos.quantity * old_price

                # Calculate iteratively to handle rounding
                best_price = old_price
                best_diff = abs(difference)

                for price_delta in [difference / largest_pos.quantity,
                                   difference / largest_pos.quantity + Decimal("0.01"),
                                   difference / largest_pos.quantity - Decimal("0.01"),
                                   difference / largest_pos.quantity + Decimal("0.02"),
                                   difference / largest_pos.quantity - Decimal("0.02")]:
                    test_price = (old_price + price_delta).quantize(Decimal("0.01"))
                    test_value = largest_pos.quantity * test_price
                    test_total = sum(pos.quantity * pos.entry_price for pos in positions if pos.id != largest_pos.id) + test_value
                    test_diff = abs(test_total - target_value)

                    if test_diff < best_diff:
                        best_diff = test_diff
                        best_price = test_price

                    if test_diff < Decimal("0.01"):
                        break

                new_price = best_price
                new_value = largest_pos.quantity * new_price

                largest_pos.entry_price = new_price
                db.add(largest_pos)

                print(f"  Adjusting {largest_pos.symbol}:")
                print(f"    Quantity: {largest_pos.quantity}")
                print(f"    Price: ${old_price:,.2f} -> ${new_price:,.2f}")
                print(f"    Position value: ${old_value:,.2f} -> ${new_value:,.2f}")

            # Verify new total
            new_total = sum(pos.quantity * pos.entry_price for pos in positions)
            final_diff = abs(new_total - target_value)

            print(f"  New Total: ${new_total:,.2f}")
            print(f"  Final Difference: ${final_diff:,.2f}")

            if final_diff > Decimal("0.01"):
                print("  [WARNING] Still not exact!")

        print("\n" + "=" * 80)
        response = input("Apply these changes? (yes/no): ")

        if response.lower() == 'yes':
            await db.commit()
            print("[OK] Changes committed")

            # Print summary
            print("\n" + "=" * 80)
            print("FINAL VERIFICATION")
            print("=" * 80)

            result = await db.execute(
                select(Portfolio)
                .where(Portfolio.name.in_(list(TARGET_VALUES.keys())))
            )
            portfolios = result.scalars().all()

            for portfolio in portfolios:
                pos_result = await db.execute(
                    select(Position)
                    .where(Position.portfolio_id == portfolio.id)
                )
                positions = list(pos_result.scalars().all())

                total = sum(pos.quantity * pos.entry_price for pos in positions)
                target = TARGET_VALUES[portfolio.name]
                diff = total - target

                status = "EXACT" if abs(diff) < Decimal("0.01") else "OFF"
                print(f"{portfolio.name[:50]:50} ${total:>14,.2f}  [{status}]")

        else:
            await db.rollback()
            print("[CANCELLED] Changes rolled back")


if __name__ == "__main__":
    asyncio.run(fine_tune_for_exact_match())
