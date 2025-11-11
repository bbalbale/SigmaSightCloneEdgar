"""Check if TLT is in market data cache for recent dates"""
import asyncio
from sqlalchemy import select
from app.database import get_async_session
from app.models.market_data import MarketDataCache
from datetime import date

async def check_tlt_cache():
    async with get_async_session() as db:
        # Check TLT in market data cache for November 10 and November 11
        for check_date in [date(2025, 11, 10), date(2025, 11, 11)]:
            result = (await db.execute(
                select(MarketDataCache)
                .where(MarketDataCache.symbol == 'TLT')
                .where(MarketDataCache.date == check_date)
            )).scalar_one_or_none()

            if result:
                print(f'{check_date}: TLT data FOUND (close: ${result.close})')
            else:
                print(f'{check_date}: TLT data MISSING')

        # Also check what symbols DO exist for November 11
        symbols = (await db.execute(
            select(MarketDataCache.symbol)
            .where(MarketDataCache.date == date(2025, 11, 11))
            .distinct()
        )).scalars().all()

        print(f'\nSymbols in cache for 2025-11-11: {len(symbols)} total')
        if 'TLT' in symbols:
            print('  - TLT is IN the cache')
        else:
            print('  - TLT is NOT in the cache')

if __name__ == '__main__':
    asyncio.run(check_tlt_cache())
