"""Check symbol tables in Railway database."""
import asyncio
import os

# Set DATABASE_URL for Railway Core DB
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway'


async def check():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(os.environ['DATABASE_URL'])
    async with engine.connect() as conn:
        # Check counts
        print('Table counts:')
        result = await conn.execute(text('SELECT COUNT(*) FROM symbol_universe'))
        print(f'  symbol_universe: {result.scalar()}')

        result = await conn.execute(text('SELECT COUNT(*) FROM symbol_factor_exposures'))
        print(f'  symbol_factor_exposures: {result.scalar()}')

        result = await conn.execute(text('SELECT COUNT(*) FROM symbol_daily_metrics'))
        metrics_count = result.scalar()
        print(f'  symbol_daily_metrics: {metrics_count}')

        result = await conn.execute(text('SELECT COUNT(DISTINCT symbol) FROM market_data_cache'))
        print(f'  market_data_cache (distinct symbols): {result.scalar()}')

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

        # Sample some metrics data
        if metrics_count > 0:
            result = await conn.execute(text("""
                SELECT symbol, metrics_date, return_1d, return_ytd, sector
                FROM symbol_daily_metrics
                ORDER BY symbol
                LIMIT 5
            """))
            rows = result.fetchall()
            print('\nSample metrics:')
            for sym, dt, r1d, rytd, sector in rows:
                print(f'  {sym}: date={dt}, 1d={r1d}, ytd={rytd}, sector={sector}')

    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(check())
