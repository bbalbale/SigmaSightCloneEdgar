import asyncio
from app.database import get_async_session
from app.models.users import Portfolio
from sqlalchemy import select

async def check_equity():
    async with get_async_session() as db:
        portfolios = await db.scalars(select(Portfolio))
        print('Portfolio Equity Values:')
        print('='*60)
        for p in portfolios.all():
            print(f'Portfolio: {p.name}')
            print(f'  ID: {p.id}')
            if p.equity_balance:
                print(f'  Equity Balance: ${p.equity_balance:,.2f}')
            else:
                print('  Equity Balance: None')
            print()

asyncio.run(check_equity())