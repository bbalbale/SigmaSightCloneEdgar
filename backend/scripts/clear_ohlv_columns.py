"""Clear open, high, low columns from market_data_cache - only keep close prices."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

RAILWAY_CORE_DB_URL = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

async def clear_ohlv_columns():
    engine = create_async_engine(RAILWAY_CORE_DB_URL)

    async with engine.begin() as conn:
        # Clear open, high, low columns (keep only close)
        result = await conn.execute(text("""
            UPDATE market_data_cache
            SET open = NULL, high = NULL, low = NULL
        """))
        print(f"Cleared open/high/low from {result.rowcount} rows")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(clear_ohlv_columns())
