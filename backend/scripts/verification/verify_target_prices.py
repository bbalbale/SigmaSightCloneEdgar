import asyncio
from app.database import AsyncSessionLocal
from app.models.target_prices import TargetPrice
from app.models.users import Portfolio
from sqlalchemy import select, func

async def verify():
    async with AsyncSessionLocal() as db:
        # Count total records
        count = await db.scalar(select(func.count(TargetPrice.id)))
        print(f'✅ Total target price records: {count}')

        # Count by portfolio
        portfolios = await db.execute(select(Portfolio))
        print('\nTarget prices by portfolio:')
        for p in portfolios.scalars():
            p_count = await db.scalar(
                select(func.count(TargetPrice.id)).where(TargetPrice.portfolio_id == p.id)
            )
            print(f'  {p.name}: {p_count} records')

        # Sample records
        sample = await db.execute(select(TargetPrice).limit(5))
        print('\nSample target prices:')
        for tp in sample.scalars():
            if tp.expected_return_eoy:
                print(f'  {tp.symbol}: EOY=${tp.target_price_eoy:.2f}, Return={tp.expected_return_eoy:.2f}%')
            else:
                print(f'  {tp.symbol}: EOY=${tp.target_price_eoy:.2f}, Return=N/A')

asyncio.run(verify())