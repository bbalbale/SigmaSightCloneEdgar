#!/usr/bin/env python
"""
Reset portfolio equity_balance to match sum of position entry values.

This should be run before clearing calculations to ensure starting equity is correct.
"""
import asyncio
import sys
from pathlib import Path
from decimal import Decimal

project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.positions import Position


async def reset_equity():
    async with get_async_session() as db:
        # Get all portfolios
        portfolios = (await db.execute(
            select(Portfolio).where(Portfolio.deleted_at.is_(None))
        )).scalars().all()

        print("Resetting portfolio equity to match position entry values...")
        print()

        for portfolio in portfolios:
            # Get all positions
            positions = (await db.execute(
                select(Position).where(
                    Position.portfolio_id == portfolio.id,
                    Position.deleted_at.is_(None)
                )
            )).scalars().all()

            if not positions:
                print(f"  {portfolio.name}: No positions, skipping")
                continue

            # Calculate sum of position entry values
            total_entry_value = sum(pos.quantity * pos.entry_price for pos in positions)

            old_equity = portfolio.equity_balance
            difference = total_entry_value - old_equity

            portfolio.equity_balance = total_entry_value

            print(f"  {portfolio.name}:")
            print(f"    Old equity: ${old_equity:,.2f}")
            print(f"    New equity: ${total_entry_value:,.2f}")
            print(f"    Change:     ${difference:+,.2f}")
            print()

        print("Committing changes...")
        await db.commit()
        print("Done!")


if __name__ == "__main__":
    asyncio.run(reset_equity())
