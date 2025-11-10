#!/usr/bin/env python
"""
Export current database positions to seed script format.
This generates the corrected position data after all our adjustments.
"""

import asyncio
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


async def export_seed_data():
    async with get_async_session() as db:
        portfolios = [
            'Demo Individual Investor Portfolio',
            'Demo High Net Worth Investor Portfolio',
            'Demo Hedge Fund Style Investor Portfolio',
            'Demo Family Office Public Growth',
            'Demo Family Office Private Opportunities'
        ]

        print("# Corrected seed data - November 10, 2025")
        print("# All positions acquired June 30, 2025 at closing prices")
        print("# Equity balances at or just below target values")
        print()

        for portfolio_name in portfolios:
            portfolio = (await db.execute(
                select(Portfolio).where(Portfolio.name == portfolio_name)
            )).scalar_one()

            positions = list((await db.execute(
                select(Position)
                .where(Position.portfolio_id == portfolio.id)
                .order_by(Position.symbol)
            )).scalars().all())

            total_equity = sum(p.quantity * p.entry_price for p in positions)

            print(f"# {portfolio_name}")
            print(f"# Positions: {len(positions)}")
            print(f"# Equity: ${total_equity:,.2f}")
            print()

            for pos in positions:
                # Format as Python dict for seed script
                pos_type = pos.position_type.value if hasattr(pos.position_type, 'value') else pos.position_type
                inv_class = pos.investment_class.value if hasattr(pos.investment_class, 'value') else (pos.investment_class or "PUBLIC")

                print(f'    {{"symbol": "{pos.symbol}", '
                      f'"position_type": "{pos_type}", '
                      f'"quantity": Decimal("{pos.quantity}"), '
                      f'"entry_price": Decimal("{pos.entry_price}"), '
                      f'"entry_date": date(2025, 6, 30), '
                      f'"investment_class": "{inv_class}"'
                      f'}},')

            print()


if __name__ == "__main__":
    asyncio.run(export_seed_data())
