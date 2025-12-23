"""Check which symbols are missing Dec 22 price data."""
import asyncio
import os

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway'


async def check():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(os.environ['DATABASE_URL'])
    async with engine.connect() as conn:
        # Find symbols in universe but missing Dec 22 prices
        result = await conn.execute(text("""
            SELECT su.symbol
            FROM symbol_universe su
            WHERE su.is_active = true
            AND NOT EXISTS (
                SELECT 1 FROM market_data_cache mdc
                WHERE mdc.symbol = su.symbol
                AND mdc.date = '2025-12-22'
            )
            ORDER BY su.symbol
        """))
        rows = result.fetchall()
        print(f'Symbols in universe missing Dec 22 prices: {len(rows)}')
        for row in rows:
            print(f'  - {row[0]}')

        # Also check symbols in market_data_cache (any date) but missing Dec 22
        result = await conn.execute(text("""
            SELECT DISTINCT mdc.symbol
            FROM market_data_cache mdc
            WHERE mdc.date = '2025-12-19'
            AND NOT EXISTS (
                SELECT 1 FROM market_data_cache mdc2
                WHERE mdc2.symbol = mdc.symbol
                AND mdc2.date = '2025-12-22'
            )
            ORDER BY mdc.symbol
        """))
        rows = result.fetchall()
        print(f'\nSymbols with Dec 19 data but missing Dec 22: {len(rows)}')
        for row in rows:
            print(f'  - {row[0]}')

    await engine.dispose()


if __name__ == '__main__':
    asyncio.run(check())
