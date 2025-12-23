"""Check market data for today in Railway database."""
import asyncio
import os

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway'


async def check():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(os.environ['DATABASE_URL'])
    async with engine.connect() as conn:
        # Check market_data_cache for recent dates
        result = await conn.execute(text("""
            SELECT date, COUNT(*) as symbols,
                   MIN(close) as min_close,
                   MAX(close) as max_close,
                   ROUND(AVG(close)::numeric, 2) as avg_close
            FROM market_data_cache
            WHERE date >= '2025-12-18'
            GROUP BY date
            ORDER BY date DESC
        """))
        rows = result.fetchall()
        print('Market data by date (recent):')
        print('-' * 70)
        for dt, cnt, min_c, max_c, avg_c in rows:
            print(f'  {dt}: {cnt:4} symbols | close range: ${float(min_c):8.2f} - ${float(max_c):8.2f} | avg: ${float(avg_c):7.2f}')

        # Sample some Dec 22 prices
        result = await conn.execute(text("""
            SELECT symbol, close
            FROM market_data_cache
            WHERE date = '2025-12-22'
            ORDER BY symbol
            LIMIT 15
        """))
        rows = result.fetchall()
        print('\nSample Dec 22 closing prices:')
        print('-' * 30)
        for sym, close in rows:
            print(f'  {sym:6}: ${float(close):10.2f}')

        # Check total distinct symbols
        result = await conn.execute(text("""
            SELECT COUNT(DISTINCT symbol) FROM market_data_cache WHERE date = '2025-12-22'
        """))
        count = result.scalar()
        print(f'\nTotal symbols with Dec 22 data: {count}')

    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(check())
