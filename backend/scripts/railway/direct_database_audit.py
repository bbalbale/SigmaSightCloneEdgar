#!/usr/bin/env python3
"""
Direct Railway Database Audit
Queries the database directly to see what market data actually exists
"""
import os
import asyncio
from sqlalchemy import select, func, distinct
from datetime import datetime

# Fix Railway DATABASE_URL format BEFORE any imports
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        print("✅ Converted DATABASE_URL to use asyncpg driver\n")

from app.database import get_async_session
from app.models.market_data import MarketDataCache, CompanyProfile
from app.models.positions import Position
from app.models.users import Portfolio


async def audit_market_data_cache():
    """Check what's in the market_data_cache table"""
    print("=" * 80)
    print("DIRECT DATABASE AUDIT - MARKET DATA CACHE")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    async with get_async_session() as db:
        # 1. Total records in market_data_cache
        result = await db.execute(select(func.count(MarketDataCache.id)))
        total_records = result.scalar()
        print(f"📊 Total Market Data Cache Records: {total_records:,}")

        if total_records == 0:
            print("❌ No historical price data in database\n")
        else:
            # 2. Unique symbols with data
            result = await db.execute(select(func.count(distinct(MarketDataCache.symbol))))
            unique_symbols = result.scalar()
            print(f"📈 Unique Symbols with Data: {unique_symbols}")

            # 3. Date range
            result = await db.execute(
                select(
                    func.min(MarketDataCache.date),
                    func.max(MarketDataCache.date)
                )
            )
            min_date, max_date = result.one()
            print(f"📅 Date Range: {min_date} to {max_date}")

            # 4. Data source breakdown
            result = await db.execute(
                select(
                    MarketDataCache.data_source,
                    func.count(MarketDataCache.id)
                ).group_by(MarketDataCache.data_source)
            )
            print(f"\n📋 Data Sources:")
            for source, count in result:
                print(f"   {source}: {count:,} records")

            # 5. Per-symbol breakdown (showing first 20)
            result = await db.execute(
                select(
                    MarketDataCache.symbol,
                    func.count(MarketDataCache.id).label('days'),
                    func.min(MarketDataCache.date).label('first_date'),
                    func.max(MarketDataCache.date).label('last_date')
                )
                .group_by(MarketDataCache.symbol)
                .order_by(MarketDataCache.symbol)
            )

            print(f"\n📊 Per-Symbol Coverage:")
            print(f"{'SYMBOL':<12} {'DAYS':<6} {'FIRST DATE':<12} {'LAST DATE':<12}")
            print(f"{'-'*12} {'-'*6} {'-'*12} {'-'*12}")

            count = 0
            for symbol, days, first_date, last_date in result:
                print(f"{symbol:<12} {days:<6} {str(first_date):<12} {str(last_date):<12}")
                count += 1
                if count >= 20:
                    remaining = unique_symbols - 20
                    if remaining > 0:
                        print(f"... and {remaining} more symbols")
                    break

        print(f"\n{'='*80}")


async def audit_company_profiles():
    """Check what's in the company_profiles table"""
    print("\nCOMPANY PROFILES")
    print("=" * 80)

    async with get_async_session() as db:
        result = await db.execute(select(func.count(CompanyProfile.symbol)))
        total_profiles = result.scalar()
        print(f"📋 Total Company Profiles: {total_profiles}")

        if total_profiles > 0:
            # Show sample
            result = await db.execute(select(CompanyProfile).limit(5))
            profiles = result.scalars().all()
            print(f"\n🏢 Sample Profiles:")
            for profile in profiles:
                print(f"   {profile.symbol}: {profile.company_name or 'N/A'}")

        print(f"{'='*80}\n")


async def audit_positions():
    """Check what positions exist and match against market data"""
    print("POSITION VS MARKET DATA COVERAGE")
    print("=" * 80)

    async with get_async_session() as db:
        # Get all unique symbols from positions
        result = await db.execute(
            select(distinct(Position.symbol))
            .join(Portfolio)
            .order_by(Position.symbol)
        )
        position_symbols = [row[0] for row in result]

        print(f"📋 Total Unique Position Symbols: {len(position_symbols)}")

        # Check which have market data
        result = await db.execute(
            select(distinct(MarketDataCache.symbol))
        )
        market_data_symbols = set(row[0] for row in result)

        # Compare
        symbols_with_data = []
        symbols_without_data = []

        for symbol in position_symbols:
            if symbol in market_data_symbols:
                symbols_with_data.append(symbol)
            else:
                symbols_without_data.append(symbol)

        print(f"\n✅ Positions WITH Market Data: {len(symbols_with_data)}")
        if symbols_with_data:
            print(f"   {', '.join(symbols_with_data[:10])}{'...' if len(symbols_with_data) > 10 else ''}")

        print(f"\n❌ Positions WITHOUT Market Data: {len(symbols_without_data)}")
        if symbols_without_data:
            print(f"   {', '.join(symbols_without_data[:10])}{'...' if len(symbols_without_data) > 10 else ''}")

        coverage_pct = (len(symbols_with_data) / len(position_symbols) * 100) if position_symbols else 0
        print(f"\n📊 Coverage: {coverage_pct:.1f}%")

        print(f"{'='*80}\n")


async def main():
    """Run all audits"""
    print("🔍 DIRECT RAILWAY DATABASE AUDIT\n")
    print("This script queries the database directly to see what data exists,")
    print("bypassing the API layer.\n")

    await audit_market_data_cache()
    await audit_company_profiles()
    await audit_positions()

    print("✅ Direct database audit complete!")


if __name__ == "__main__":
    asyncio.run(main())
