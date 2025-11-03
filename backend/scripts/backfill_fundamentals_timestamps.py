"""
Backfill fundamentals_last_fetched Timestamps

This script updates the fundamentals_last_fetched timestamp for all symbols
that have fundamental data (income statements, balance sheets, or cash flows)
but are missing the timestamp in company_profiles.

Run this once to fix existing data after the timestamp update logic was improved.
"""
import asyncio
from datetime import datetime
from sqlalchemy import select, func, distinct
from app.database import AsyncSessionLocal
from app.models.fundamentals import IncomeStatement, BalanceSheet, CashFlow
from app.models.market_data import CompanyProfile
from app.core.logging import get_logger

logger = get_logger(__name__)


async def backfill_timestamps():
    """Backfill missing fundamentals_last_fetched timestamps"""
    print("\n" + "=" * 80)
    print("  BACKFILL FUNDAMENTALS TIMESTAMPS")
    print("=" * 80)
    print()

    async with AsyncSessionLocal() as db:
        # Step 1: Get all symbols with fundamental data
        income_symbols_query = await db.execute(
            select(distinct(IncomeStatement.symbol))
        )
        income_symbols = set(row[0] for row in income_symbols_query.fetchall())

        balance_symbols_query = await db.execute(
            select(distinct(BalanceSheet.symbol))
        )
        balance_symbols = set(row[0] for row in balance_symbols_query.fetchall())

        cash_symbols_query = await db.execute(
            select(distinct(CashFlow.symbol))
        )
        cash_symbols = set(row[0] for row in cash_symbols_query.fetchall())

        # Combine all symbols with any fundamental data
        all_fundamental_symbols = income_symbols | balance_symbols | cash_symbols

        print(f"📊 Found {len(all_fundamental_symbols)} symbols with fundamental data:")
        print(f"   Income statements: {len(income_symbols)} symbols")
        print(f"   Balance sheets: {len(balance_symbols)} symbols")
        print(f"   Cash flows: {len(cash_symbols)} symbols")
        print()

        # Step 2: Find symbols missing timestamps
        symbols_to_update = []
        for symbol in all_fundamental_symbols:
            profile_query = await db.execute(
                select(CompanyProfile).where(CompanyProfile.symbol == symbol)
            )
            profile = profile_query.scalar_one_or_none()

            if not profile:
                symbols_to_update.append((symbol, "NO_PROFILE"))
            elif not profile.fundamentals_last_fetched:
                symbols_to_update.append((symbol, "NO_TIMESTAMP"))

        print(f"🔧 Symbols needing timestamp updates: {len(symbols_to_update)}")
        if symbols_to_update:
            print(f"   Symbols: {', '.join(s[0] for s in symbols_to_update[:10])}")
            if len(symbols_to_update) > 10:
                print(f"   ... and {len(symbols_to_update) - 10} more")
        print()

        # Step 3: Update timestamps
        updated_count = 0
        created_count = 0
        current_time = datetime.utcnow()

        for symbol, status in symbols_to_update:
            try:
                if status == "NO_PROFILE":
                    # Create new company profile
                    profile = CompanyProfile(
                        symbol=symbol,
                        fundamentals_last_fetched=current_time
                    )
                    db.add(profile)
                    created_count += 1
                    logger.info(f"Created company profile for {symbol}")
                else:
                    # Update existing profile
                    profile_query = await db.execute(
                        select(CompanyProfile).where(CompanyProfile.symbol == symbol)
                    )
                    profile = profile_query.scalar_one()
                    profile.fundamentals_last_fetched = current_time
                    updated_count += 1
                    logger.info(f"Updated fundamentals_last_fetched for {symbol}")

            except Exception as e:
                logger.error(f"Error updating {symbol}: {e}")

        # Commit all changes
        await db.commit()

        print(f"✅ Backfill Complete:")
        print(f"   Profiles created: {created_count}")
        print(f"   Profiles updated: {updated_count}")
        print(f"   Total fixed: {created_count + updated_count}")
        print()

        # Step 4: Verify results
        profiles_with_timestamp = await db.execute(
            select(func.count(CompanyProfile.symbol)).where(
                CompanyProfile.fundamentals_last_fetched.isnot(None)
            )
        )
        total_with_timestamp = profiles_with_timestamp.scalar()

        print(f"📋 Final Status:")
        print(f"   Symbols with fundamental data: {len(all_fundamental_symbols)}")
        print(f"   Company profiles with timestamp: {total_with_timestamp}")
        print(f"   Match: {'✅ YES' if total_with_timestamp >= len(all_fundamental_symbols) else '❌ NO'}")
        print()

    print("=" * 80)
    print("✅ BACKFILL COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    print("\n" + "⏰" * 40)
    print()
    asyncio.run(backfill_timestamps())
    print("⏰" * 40)
    print()
