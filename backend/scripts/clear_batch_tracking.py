"""Clear batch tracking to allow re-run."""
import asyncio
import os
from datetime import date

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway'

async def clear():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(os.environ['DATABASE_URL'])
    async with engine.begin() as conn:
        # Clear batch tracking for Dec 22 (column is run_date, not started_at)
        result = await conn.execute(text("DELETE FROM batch_run_tracking WHERE run_date >= '2025-12-22'"))
        print(f'Deleted {result.rowcount} batch_run_tracking records')

        # Clear snapshots for Dec 22
        result = await conn.execute(text("DELETE FROM portfolio_snapshots WHERE snapshot_date = '2025-12-22'"))
        print(f'Deleted {result.rowcount} portfolio_snapshots records')

        print('Ready for re-run!')
    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(clear())
