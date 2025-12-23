"""Clear Dec 22 calculations to allow re-testing batch speed and accuracy."""
import asyncio
import os
from datetime import date

# Set DATABASE_URL for Railway Core DB
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway'


async def clear():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    target_date = date(2025, 12, 22)

    engine = create_async_engine(os.environ['DATABASE_URL'])
    async with engine.begin() as conn:
        print(f"Clearing calculations for {target_date}...")

        # 1. Delete symbol_factor_exposures for Dec 22
        result = await conn.execute(text("""
            DELETE FROM symbol_factor_exposures
            WHERE calculation_date = :target_date
        """), {'target_date': target_date})
        print(f"  Deleted {result.rowcount} symbol_factor_exposures records")

        # 2. Clear symbol_daily_metrics (truncate since it's one row per symbol)
        result = await conn.execute(text("DELETE FROM symbol_daily_metrics"))
        print(f"  Deleted {result.rowcount} symbol_daily_metrics records")

        # 3. Delete portfolio snapshots for Dec 22
        result = await conn.execute(text("""
            DELETE FROM portfolio_snapshots
            WHERE snapshot_date = :target_date
        """), {'target_date': target_date})
        print(f"  Deleted {result.rowcount} portfolio_snapshots records")

        # 4. Reset batch tracking for Dec 22
        result = await conn.execute(text("""
            DELETE FROM batch_run_tracking
            WHERE DATE(started_at) >= :target_date
        """), {'target_date': target_date})
        print(f"  Deleted {result.rowcount} batch_run_tracking records")

        # 5. Check what's left
        print("\nRemaining counts:")

        result = await conn.execute(text("""
            SELECT calculation_date, COUNT(*)
            FROM symbol_factor_exposures
            GROUP BY calculation_date
            ORDER BY calculation_date DESC
            LIMIT 3
        """))
        rows = result.fetchall()
        print("  symbol_factor_exposures by date:")
        for dt, cnt in rows:
            print(f"    {dt}: {cnt}")

        result = await conn.execute(text("SELECT COUNT(*) FROM symbol_daily_metrics"))
        print(f"  symbol_daily_metrics: {result.scalar()}")

        result = await conn.execute(text("""
            SELECT snapshot_date, COUNT(*)
            FROM portfolio_snapshots
            GROUP BY snapshot_date
            ORDER BY snapshot_date DESC
            LIMIT 3
        """))
        rows = result.fetchall()
        print("  portfolio_snapshots by date:")
        for dt, cnt in rows:
            print(f"    {dt}: {cnt}")

    await engine.dispose()
    print("\n✅ Calculations cleared! Ready for re-run.")


if __name__ == '__main__':
    asyncio.run(clear())
