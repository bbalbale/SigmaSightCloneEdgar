"""Check market data table schema."""
import asyncio
import asyncpg

CORE_DB_URL = "postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

async def main():
    conn = await asyncpg.connect(CORE_DB_URL)
    try:
        query = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'market_data_cache'
            ORDER BY ordinal_position
        """
        rows = await conn.fetch(query)
        print("market_data_cache columns:")
        for row in rows:
            print(f"  {row['column_name']}: {row['data_type']}")
    finally:
        await conn.close()

asyncio.run(main())
