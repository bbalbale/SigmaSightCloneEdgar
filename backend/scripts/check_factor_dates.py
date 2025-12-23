"""Check factor exposure dates in Railway database."""
import asyncio
import os

# Set DATABASE_URL for Railway Core DB
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway'


async def check():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(os.environ['DATABASE_URL'])
    async with engine.connect() as conn:
        # Check symbol_factor_exposures dates
        result = await conn.execute(text("""
            SELECT calculation_date, COUNT(*) as cnt
            FROM symbol_factor_exposures
            GROUP BY calculation_date
            ORDER BY calculation_date DESC
            LIMIT 10
        """))
        rows = result.fetchall()
        print('symbol_factor_exposures calculation dates:')
        for dt, cnt in rows:
            print(f'  {dt}: {cnt} records')

        # Check symbol_daily_metrics dates
        result = await conn.execute(text("""
            SELECT metrics_date, COUNT(*) as cnt
            FROM symbol_daily_metrics
            GROUP BY metrics_date
            ORDER BY metrics_date DESC
            LIMIT 5
        """))
        rows = result.fetchall()
        print('\nsymbol_daily_metrics dates:')
        for dt, cnt in rows:
            print(f'  {dt}: {cnt} records')

        # Check batch_run_tracking last run
        result = await conn.execute(text("""
            SELECT target_date, started_at, completed_at
            FROM batch_run_tracking
            ORDER BY started_at DESC
            LIMIT 5
        """))
        rows = result.fetchall()
        print('\nbatch_run_tracking recent runs:')
        for target, started, completed in rows:
            print(f'  target={target}, started={started}, completed={completed}')

    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(check())
