import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.market_data import StressTestResult

async def check():
    async with get_async_session() as db:
        count = await db.execute(select(func.count(StressTestResult.id)))
        total = count.scalar()
        print(f'Total StressTestResult records: {total}')

        if total > 0:
            stmt = select(StressTestResult).limit(5)
            result = await db.execute(stmt)
            results = result.scalars().all()
            print(f'\nSample stress test results:')
            for r in results:
                pnl = float(r.correlated_pnl) if r.correlated_pnl else 0
                print(f'  Scenario ID: {r.scenario_id}, P&L: ${pnl:,.2f}')

asyncio.run(check())
