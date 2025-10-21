"""Verify key tables from migrations exist"""
import asyncio
from sqlalchemy import text
from app.database import get_async_session


async def main():
    key_tables = [
        'position_market_betas',
        'position_interest_rate_betas',
        'position_volatility',
        'ai_insights',
        'benchmarks_sector_weights'
    ]

    async with get_async_session() as db:
        placeholders = ','.join([f"'{t}'" for t in key_tables])
        result = await db.execute(text(f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            AND table_name IN ({placeholders})
            ORDER BY table_name
        """))

        tables = result.fetchall()

        print("=" * 60)
        print("MIGRATION VERIFICATION")
        print("=" * 60)
        print(f"\nKey tables found: {len(tables)}/{len(key_tables)}")
        print()
        for t in tables:
            print(f"  [OK] {t[0]}")

        missing = set(key_tables) - {t[0] for t in tables}
        if missing:
            print("\nMissing tables:")
            for t in missing:
                print(f"  [MISSING] {t}")
        else:
            print("\n[SUCCESS] All key migration tables exist!")
        print()


if __name__ == "__main__":
    asyncio.run(main())
