"""
Manually apply the Priority 1-3 performance indexes.

This script directly creates the indexes that should have been created
by the Alembic migration j7k8l9m0n1o2.

Run: uv run python scripts/database/apply_performance_indexes.py
"""
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal


async def create_indexes():
    """Create the three priority performance indexes."""
    print("\n" + "="*80)
    print("CREATING PRIORITY PERFORMANCE INDEXES")
    print("="*80)

    async with AsyncSessionLocal() as db:
        # Priority 1: Extended Position Active Lookup
        print("\nCreating Priority 1: idx_positions_active_complete...")
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_positions_active_complete
            ON positions(portfolio_id, deleted_at, exit_date, investment_class)
            WHERE deleted_at IS NULL
        """))
        print("[OK] Created idx_positions_active_complete")

        # Priority 2: Market Data Valid Prices
        print("\nCreating Priority 2: idx_market_data_valid_prices...")
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_market_data_valid_prices
            ON market_data_cache(symbol, date)
            WHERE close > 0
        """))
        print("[OK] Created idx_market_data_valid_prices")

        # Priority 3: Position Symbol Active Filter
        print("\nCreating Priority 3: idx_positions_symbol_active...")
        await db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_positions_symbol_active
            ON positions(deleted_at, symbol, exit_date, expiration_date)
            WHERE deleted_at IS NULL AND symbol IS NOT NULL AND symbol != ''
        """))
        print("[OK] Created idx_positions_symbol_active")

        await db.commit()
        print("\n[SUCCESS] All 3 indexes created successfully!")


async def verify_indexes():
    """Verify the indexes were created."""
    print("\n" + "="*80)
    print("VERIFYING INDEXES")
    print("="*80)

    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename IN ('positions', 'market_data_cache')
            AND indexname IN (
                'idx_positions_active_complete',
                'idx_market_data_valid_prices',
                'idx_positions_symbol_active'
            )
            ORDER BY indexname
        """))

        indexes = [row[0] for row in result.fetchall()]

        expected = [
            'idx_market_data_valid_prices',
            'idx_positions_active_complete',
            'idx_positions_symbol_active'
        ]

        print("\nFound indexes:")
        for idx in indexes:
            print(f"  [OK] {idx}")

        missing = set(expected) - set(indexes)
        if missing:
            print("\nMissing indexes:")
            for idx in missing:
                print(f"  [MISSING] {idx}")
            return False
        else:
            print(f"\n[SUCCESS] All {len(expected)} priority indexes verified!")
            return True


async def main():
    """Create and verify indexes."""
    try:
        await create_indexes()
        success = await verify_indexes()

        if success:
            print("\n" + "="*80)
            print("SUCCESS!")
            print("="*80)
            print("\nPerformance indexes are now in place.")
            print("Your batch processing should be MUCH faster now!")
            print("\nNext steps:")
            print("1. Run the batch processing again")
            print("2. Expect 3-5 minute runtime instead of 30+ minutes")
            print("3. Monitor logs for 'OPTIMIZATION' messages showing cache usage")
        else:
            print("\n[ERROR] Some indexes failed to create. Check the errors above.")

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
