#!/usr/bin/env python
"""Get exact position entry values for all portfolios."""
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
from app.models.users import User, Portfolio
from app.models.positions import Position


async def get_exact_values():
    async with get_async_session() as db:
        portfolios_data = [
            ('demo_individual@sigmasight.com', 'Individual Investor'),
            ('demo_hnw@sigmasight.com', 'High Net Worth'),
            ('demo_hedgefundstyle@sigmasight.com', 'Hedge Fund Style'),
            ('demo_familyoffice@sigmasight.com', 'Family Office Public Growth'),
        ]

        for email, name in portfolios_data:
            user = (await db.execute(
                select(User).where(User.email == email)
            )).scalar_one_or_none()

            if not user:
                continue

            portfolios = (await db.execute(
                select(Portfolio).where(
                    Portfolio.user_id == user.id,
                    Portfolio.deleted_at.is_(None)
                )
            )).scalars().all()

            for portfolio in portfolios:
                if 'Private Opportunities' in portfolio.name:
                    continue  # Skip private opportunities

                positions = (await db.execute(
                    select(Position).where(
                        Position.portfolio_id == portfolio.id,
                        Position.deleted_at.is_(None)
                    )
                )).scalars().all()

                long_exposure = Decimal('0')
                short_exposure = Decimal('0')

                for pos in positions:
                    value = pos.quantity * pos.entry_price
                    if pos.quantity < 0:
                        short_exposure += abs(value)
                    else:
                        long_exposure += value

                gross = long_exposure + short_exposure
                net = long_exposure - short_exposure

                print(f'{name}:')
                print(f'- Equity Balance: ${portfolio.equity_balance} (starting capital)')
                print(f'- Long Exposure: ${long_exposure} (position entry values)')
                print(f'- Short Exposure: ${short_exposure}')
                print(f'- Gross Exposure: ${gross}')
                print(f'- Net Exposure: ${net}')
                if short_exposure > 0:
                    leverage = (gross / portfolio.equity_balance) if portfolio.equity_balance else Decimal('0')
                    print(f'- Leverage Ratio: {leverage:.2f}x gross')
                else:
                    print(f'- No leverage')
                print()


if __name__ == "__main__":
    asyncio.run(get_exact_values())
