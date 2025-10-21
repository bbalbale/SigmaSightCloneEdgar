#!/usr/bin/env python
"""
Update BRK.B ticker to BRK-B in the database

This script updates all occurrences of "BRK.B" to "BRK-B" across all relevant tables.
Many financial APIs (including YFinance) use BRK-B (hyphen) instead of BRK.B (dot).

Tables updated:
- positions (symbol column)
- market_data_cache (symbol column)
- security_master (symbol column) if exists
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.positions import Position
from app.models.market_data import MarketDataCache
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def update_brk_ticker():
    """Update BRK.B to BRK-B across all tables"""

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("=" * 80)
        print("Updating BRK.B Ticker to BRK-B")
        print("=" * 80)
        print()

        old_symbol = "BRK.B"
        new_symbol = "BRK-B"

        # Track results
        total_updated = 0

        # ====================================================================
        # 1. Update Positions table
        # ====================================================================
        print("Checking positions table...")

        # Check count before
        count_query = select(func.count(Position.id)).where(Position.symbol == old_symbol)
        result = await db.execute(count_query)
        positions_count = result.scalar()

        if positions_count > 0:
            print(f"  Found {positions_count} position(s) with symbol '{old_symbol}'")

            # Update
            update_stmt = (
                update(Position)
                .where(Position.symbol == old_symbol)
                .values(symbol=new_symbol)
            )
            await db.execute(update_stmt)

            print(f"  [OK] Updated {positions_count} position(s) to '{new_symbol}'")
            total_updated += positions_count
        else:
            print(f"  [INFO] No positions found with symbol '{old_symbol}'")

        print()

        # ====================================================================
        # 2. Update MarketDataCache table
        # ====================================================================
        print("Checking market_data_cache table...")

        # Check count before
        count_query = select(func.count(MarketDataCache.id)).where(
            MarketDataCache.symbol == old_symbol
        )
        result = await db.execute(count_query)
        market_data_count = result.scalar()

        if market_data_count > 0:
            print(f"  Found {market_data_count} market data record(s) with symbol '{old_symbol}'")

            # Update
            update_stmt = (
                update(MarketDataCache)
                .where(MarketDataCache.symbol == old_symbol)
                .values(symbol=new_symbol)
            )
            await db.execute(update_stmt)

            print(f"  [OK] Updated {market_data_count} market data record(s) to '{new_symbol}'")
            total_updated += market_data_count
        else:
            print(f"  [INFO] No market data found with symbol '{old_symbol}'")

        print()

        # ====================================================================
        # 3. Try to update security_master table (if it exists)
        # ====================================================================
        print("Checking security_master table...")

        try:
            # Check if table exists by trying to query it
            check_query = select(func.count()).select_from(
                db.bind.dialect.get_table_names(db.bind)
            )

            # Try updating security_master
            from app.models.market_data import SecurityMaster

            count_query = select(func.count(SecurityMaster.id)).where(
                SecurityMaster.symbol == old_symbol
            )
            result = await db.execute(count_query)
            security_count = result.scalar()

            if security_count > 0:
                print(f"  Found {security_count} security_master record(s) with symbol '{old_symbol}'")

                # Update
                update_stmt = (
                    update(SecurityMaster)
                    .where(SecurityMaster.symbol == old_symbol)
                    .values(symbol=new_symbol)
                )
                await db.execute(update_stmt)

                print(f"  [OK] Updated {security_count} security_master record(s) to '{new_symbol}'")
                total_updated += security_count
            else:
                print(f"  [INFO] No security_master records found with symbol '{old_symbol}'")

        except Exception as e:
            print(f"  [INFO] Skipping security_master table: {str(e)[:100]}")

        print()

        # ====================================================================
        # Commit all changes
        # ====================================================================
        await db.commit()

        print("=" * 80)
        print("UPDATE COMPLETE")
        print("=" * 80)
        print(f"Total records updated: {total_updated}")
        print(f"Changed: '{old_symbol}' -> '{new_symbol}'")
        print()

        # ====================================================================
        # Verification
        # ====================================================================
        print("=" * 80)
        print("Verification")
        print("=" * 80)
        print()

        # Verify no BRK.B remains
        print(f"Checking for any remaining '{old_symbol}' records...")

        positions_check = await db.execute(
            select(func.count(Position.id)).where(Position.symbol == old_symbol)
        )
        positions_remaining = positions_check.scalar()

        market_data_check = await db.execute(
            select(func.count(MarketDataCache.id)).where(MarketDataCache.symbol == old_symbol)
        )
        market_data_remaining = market_data_check.scalar()

        if positions_remaining == 0 and market_data_remaining == 0:
            print(f"  [OK] No '{old_symbol}' records remaining")
        else:
            print(f"  [WARNING] Found {positions_remaining} position(s) and {market_data_remaining} market data record(s) still with '{old_symbol}'")

        print()

        # Verify BRK-B now exists
        print(f"Checking for '{new_symbol}' records...")

        positions_new = await db.execute(
            select(func.count(Position.id)).where(Position.symbol == new_symbol)
        )
        positions_new_count = positions_new.scalar()

        market_data_new = await db.execute(
            select(func.count(MarketDataCache.id)).where(MarketDataCache.symbol == new_symbol)
        )
        market_data_new_count = market_data_new.scalar()

        print(f"  Positions with '{new_symbol}': {positions_new_count}")
        print(f"  Market data records with '{new_symbol}': {market_data_new_count}")
        print()

        # Show sample market data for BRK-B
        if market_data_new_count > 0:
            print(f"Sample market data for '{new_symbol}':")
            sample_query = (
                select(MarketDataCache)
                .where(MarketDataCache.symbol == new_symbol)
                .order_by(MarketDataCache.date.desc())
                .limit(3)
            )
            result = await db.execute(sample_query)
            sample_records = result.scalars().all()

            for record in sample_records:
                print(f"  {record.date}: Close=${float(record.close):.2f}, Volume={record.volume:,}, Source={record.data_source}")
            print()

    await engine.dispose()


if __name__ == "__main__":
    print("Starting BRK.B to BRK-B ticker update...")
    print()
    asyncio.run(update_brk_ticker())
    print("Done!")
