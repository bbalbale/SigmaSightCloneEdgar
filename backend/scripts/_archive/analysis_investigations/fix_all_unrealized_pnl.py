"""
FIX ALL UNREALIZED P&L VALUES
Recalculate correct unrealized_pnl for ALL positions across ALL portfolios
"""
import asyncio
from decimal import Decimal
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.positions import Position

async def fix_all_pnl():
    async with AsyncSessionLocal() as db:
        # Get ALL positions
        result = await db.execute(select(Position))
        all_positions = result.scalars().all()

        print("=" * 100)
        print("FIXING UNREALIZED P&L FOR ALL POSITIONS")
        print("=" * 100)
        print()
        print(f"Total positions to fix: {len(all_positions)}")
        print()

        fixed_count = 0
        total_error_before = Decimal('0')
        total_error_after = Decimal('0')

        for pos in all_positions:
            # Calculate CORRECT unrealized P&L
            # Formula: (last_price - entry_price) × quantity
            if pos.last_price and pos.entry_price:
                correct_pnl = (pos.last_price - pos.entry_price) * pos.quantity

                # Calculate error
                old_pnl = pos.unrealized_pnl if pos.unrealized_pnl else Decimal('0')
                error = old_pnl - correct_pnl

                total_error_before += abs(error)

                # Update the position
                pos.unrealized_pnl = correct_pnl

                fixed_count += 1

                if abs(error) > Decimal('0.01'):
                    print(f"  {pos.symbol:<10} Old: ${float(old_pnl):>12,.2f}  →  Correct: ${float(correct_pnl):>12,.2f}  (Error: ${float(error):>12,.2f})")
            else:
                print(f"  {pos.symbol:<10} SKIPPED - missing price data")

        print()
        print("=" * 100)
        print(f"Fixed {fixed_count} positions")
        print(f"Total absolute error corrected: ${float(total_error_before):,.2f}")
        print()
        print("Committing changes to database...")

        await db.commit()

        print("✅ COMPLETE! All unrealized P&L values have been corrected.")
        print("=" * 100)

asyncio.run(fix_all_pnl())
