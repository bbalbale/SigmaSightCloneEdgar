#!/usr/bin/env python
"""
Fix Entry Prices to Match June 30, 2025 Market Prices

This script updates all PUBLIC position entry prices to match the actual
June 30, 2025 closing prices from market_data_cache. This ensures that
portfolios start with accurate baseline values and prevents artificial
gains on the first calculation day (July 1).

Critical for accurate P&L calculations.
"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal
from datetime import date

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from sqlalchemy import select
from app.database import get_async_session
from app.models.users import User, Portfolio
from app.models.positions import Position
from app.models.market_data import MarketDataCache

JUNE_30 = date(2025, 6, 30)


async def fix_entry_prices():
    """Update all PUBLIC position entry prices to match June 30, 2025 market prices"""

    async with get_async_session() as db:
        print("=" * 100)
        print("FIXING ENTRY PRICES TO JUNE 30, 2025 MARKET PRICES")
        print("=" * 100)
        print()

        # Get all portfolios
        portfolios = (await db.execute(
            select(Portfolio).where(Portfolio.deleted_at.is_(None))
        )).scalars().all()

        total_updated = 0
        total_skipped = 0
        total_no_data = 0

        for portfolio in portfolios:
            user = (await db.execute(
                select(User).where(User.id == portfolio.user_id)
            )).scalar_one()

            print(f"Portfolio: {portfolio.name} ({user.email})")
            print("-" * 100)

            # Get PUBLIC positions only
            positions = (await db.execute(
                select(Position).where(
                    Position.portfolio_id == portfolio.id,
                    Position.investment_class == 'PUBLIC',
                    Position.deleted_at.is_(None)
                )
            )).scalars().all()

            if not positions:
                print("  No PUBLIC positions found")
                print()
                continue

            for pos in sorted(positions, key=lambda p: p.symbol):
                # Get June 30 market price
                june30_data = (await db.execute(
                    select(MarketDataCache).where(
                        MarketDataCache.symbol == pos.symbol,
                        MarketDataCache.date == JUNE_30
                    )
                )).scalar_one_or_none()

                if not june30_data:
                    print(f"  [SKIP] {pos.symbol}: No June 30 data found")
                    total_no_data += 1
                    continue

                old_price = pos.entry_price
                new_price = june30_data.close
                diff = new_price - old_price
                diff_pct = (diff / old_price * 100) if old_price else 0

                # Update if difference is more than 1 cent
                if abs(diff) > Decimal('0.01'):
                    pos.entry_price = new_price
                    db.add(pos)
                    print(f"  [UPDATE] {pos.symbol}: {old_price:.2f} -> {new_price:.2f} ({diff:+.2f}, {diff_pct:+.2f}%)")
                    total_updated += 1
                else:
                    print(f"  [OK] {pos.symbol}: {old_price:.2f} (already correct)")
                    total_skipped += 1

            print()

        print("=" * 100)
        print(f"Summary:")
        print(f"  Updated:  {total_updated} positions")
        print(f"  Skipped:  {total_skipped} positions (already correct)")
        print(f"  No Data:  {total_no_data} positions (missing June 30 price)")
        print("=" * 100)
        print()

        if total_updated > 0:
            print("Committing changes...")
            await db.commit()
            print("[DONE] Entry prices updated successfully")
        else:
            print("[DONE] No changes needed")


if __name__ == "__main__":
    asyncio.run(fix_entry_prices())
