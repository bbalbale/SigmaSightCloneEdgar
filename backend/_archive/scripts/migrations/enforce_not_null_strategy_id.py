"""
Enforce NOT NULL on positions.strategy_id with a direct DDL if safe.

This is a pragmatic safeguard when Alembic cannot be run due to local script issues.
The corresponding Alembic revision exists and can be run later without conflict.
"""
import asyncio
from sqlalchemy import text

from app.database import engine


async def main():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT COUNT(1) FROM positions WHERE strategy_id IS NULL"))
        cnt = res.scalar() or 0
        print(f"NULL strategy_id rows: {cnt}")
        if cnt > 0:
            raise RuntimeError("Cannot enforce NOT NULL: there are rows with NULL strategy_id. Run backfill first.")

        print("Altering column to SET NOT NULL...")
        await conn.execute(text("ALTER TABLE positions ALTER COLUMN strategy_id SET NOT NULL"))
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())

