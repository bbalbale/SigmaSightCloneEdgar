#!/usr/bin/env python
"""
Delete corrupted September 29, 2025 data for all symbols
"""

import asyncio
import sys
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.market_data import MarketDataCache
from app.config import settings


async def delete_sept_29_data():
    """Delete all records for September 29, 2025"""

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("=" * 80)
        print("Deleting September 29, 2025 Data")
        print("=" * 80)
        print()

        target_date = date(2025, 9, 29)

        # Check what we have before deletion
        query = select(MarketDataCache).where(
            MarketDataCache.date == target_date
        )
        result = await db.execute(query)
        records = result.scalars().all()

        print(f"Found {len(records)} records for {target_date}")
        print()

        if records:
            # Show sample of what will be deleted
            print("Sample records to be deleted:")
            for rec in records[:10]:
                print(f"  {rec.symbol}: Close=${float(rec.close):.2f}, Source={rec.data_source}")
            if len(records) > 10:
                print(f"  ... and {len(records) - 10} more")
            print()

            # Delete the records
            delete_stmt = delete(MarketDataCache).where(
                MarketDataCache.date == target_date
            )
            await db.execute(delete_stmt)
            await db.commit()

            print(f"✅ Deleted {len(records)} records for {target_date}")
        else:
            print(f"No records found for {target_date}")

        print()

    await engine.dispose()


if __name__ == "__main__":
    print("Deleting corrupted September 29, 2025 data...")
    print()
    asyncio.run(delete_sept_29_data())
    print("Done!")
