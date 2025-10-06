#!/usr/bin/env python3
"""
Trigger batch processing on Railway deployment
Run with: railway run python scripts/trigger_batch_railway.py
"""
import asyncio
import os

# Fix Railway DATABASE_URL format (postgresql:// -> postgresql+asyncpg://)
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print(f"✅ Converted DATABASE_URL to use asyncpg driver")

from app.batch.batch_orchestrator_v2 import batch_orchestrator_v2


async def main():
    print("🚀 Starting Railway batch processing...")
    print("=" * 60)

    try:
        # Run the daily batch sequence
        await batch_orchestrator_v2.run_daily_batch_sequence()
        print("\n✅ Batch processing completed successfully!")

    except Exception as e:
        print(f"\n❌ Batch processing failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
