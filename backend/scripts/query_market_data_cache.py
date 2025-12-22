"""Query Railway market data cache to see tickers and date ranges."""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"

async def query_market_data():
    engine = create_async_engine(DATABASE_URL)

    async with engine.connect() as conn:
        # First, find tables related to market data
        result = await conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND (table_name LIKE '%market%' OR table_name LIKE '%price%' OR table_name LIKE '%stock%' OR table_name LIKE '%daily%')
            ORDER BY table_name
        """))
        tables = result.fetchall()
        print("=== Market Data Related Tables ===")
        for t in tables:
            print(f"  - {t[0]}")

        # Check market_data_cache table structure
        print("\n=== market_data_cache Table Columns ===")
        result = await conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'market_data_cache'
            ORDER BY ordinal_position
        """))
        cols = result.fetchall()
        for c in cols:
            print(f"  {c[0]}: {c[1]}")

        # Get ticker summary with date ranges
        print("\n=== Market Data Cache Summary ===")
        result = await conn.execute(text("""
            SELECT
                symbol,
                COUNT(*) as data_points,
                MIN(date) as earliest_date,
                MAX(date) as latest_date,
                (MAX(date) - MIN(date)) as days_span
            FROM market_data_cache
            GROUP BY symbol
            ORDER BY symbol
        """))
        rows = result.fetchall()

        print(f"\nTotal tickers: {len(rows)}")
        print(f"\n{'Symbol':<10} {'Records':<10} {'Earliest':<12} {'Latest':<12} {'Days':<6}")
        print("-" * 55)
        for row in rows:
            print(f"{row[0]:<10} {row[1]:<10} {str(row[2]):<12} {str(row[3]):<12} {row[4] if row[4] else 0:<6}")

        # Get total record count
        result = await conn.execute(text("SELECT COUNT(*) FROM market_data_cache"))
        total = result.scalar()
        print(f"\n=== Total Records: {total} ===")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(query_market_data())
