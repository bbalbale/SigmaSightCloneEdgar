#!/usr/bin/env python3
"""
Check Historical Data Coverage in market_data_cache
Diagnose why Treasury/FRED IR beta calculation has no overlapping data
"""
import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta
from sqlalchemy import select, func, and_

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.market_data import MarketDataCache
from app.models.positions import Position
from app.models.users import Portfolio
from app.core.logging import get_logger

logger = get_logger(__name__)


async def check_data_coverage():
    """Check historical price data coverage in market_data_cache"""
    print("\n" + "="*80)
    print("Historical Data Coverage Check")
    print("="*80)
    
    async with AsyncSessionLocal() as db:
        # Get demo portfolios
        stmt = select(Portfolio).where(
            Portfolio.name.like('Demo%')
        ).limit(3)
        result = await db.execute(stmt)
        portfolios = result.scalars().all()
        
        print(f"\nFound {len(portfolios)} demo portfolios")
        
        for portfolio in portfolios:
            print(f"\n📁 Portfolio: {portfolio.name}")
            print("-" * 40)
            
            # Get positions
            stmt = select(Position).where(
                and_(
                    Position.portfolio_id == portfolio.id,
                    Position.exit_date.is_(None)
                )
            )
            result = await db.execute(stmt)
            positions = result.scalars().all()
            
            if not positions:
                print("   No active positions")
                continue
            
            print(f"   Active positions: {len(positions)}")
            
            # Check data coverage for each symbol
            symbols = list(set(p.symbol for p in positions))
            print(f"   Unique symbols: {symbols[:5]}..." if len(symbols) > 5 else f"   Unique symbols: {symbols}")
            
            for symbol in symbols[:5]:  # Check first 5 symbols
                # Get date range of available data
                stmt = select(
                    func.min(MarketDataCache.date).label('min_date'),
                    func.max(MarketDataCache.date).label('max_date'),
                    func.count(MarketDataCache.id).label('count')
                ).where(
                    MarketDataCache.symbol == symbol
                )
                result = await db.execute(stmt)
                data_info = result.first()
                
                if data_info and data_info.count > 0:
                    print(f"\n   📊 {symbol}:")
                    print(f"      Data points: {data_info.count}")
                    print(f"      Date range: {data_info.min_date} to {data_info.max_date}")
                    
                    # Check recent data availability
                    recent_date = date.today() - timedelta(days=30)
                    stmt = select(func.count(MarketDataCache.id)).where(
                        and_(
                            MarketDataCache.symbol == symbol,
                            MarketDataCache.date >= recent_date
                        )
                    )
                    result = await db.execute(stmt)
                    recent_count = result.scalar()
                    
                    print(f"      Recent data (last 30 days): {recent_count} points")
                    
                    if recent_count == 0:
                        print(f"      ⚠️ WARNING: No recent data!")
                else:
                    print(f"\n   ❌ {symbol}: No data in market_data_cache")
        
        # Overall statistics
        print("\n" + "="*80)
        print("Overall Market Data Statistics")
        print("-" * 40)
        
        # Total records
        stmt = select(func.count(MarketDataCache.id))
        result = await db.execute(stmt)
        total_records = result.scalar()
        
        # Unique symbols
        stmt = select(func.count(func.distinct(MarketDataCache.symbol)))
        result = await db.execute(stmt)
        unique_symbols = result.scalar()
        
        # Date range
        stmt = select(
            func.min(MarketDataCache.date).label('min_date'),
            func.max(MarketDataCache.date).label('max_date')
        )
        result = await db.execute(stmt)
        date_range = result.first()
        
        print(f"Total records: {total_records:,}")
        print(f"Unique symbols: {unique_symbols}")
        if date_range:
            print(f"Date range: {date_range.min_date} to {date_range.max_date}")
            
            # Check if we have recent data
            days_old = (date.today() - date_range.max_date).days
            if days_old > 7:
                print(f"⚠️ WARNING: Latest data is {days_old} days old!")
        
        # Check for BRK.B vs BRK-B
        print("\n" + "-" * 40)
        print("Symbol Format Check")
        print("-" * 40)
        
        for symbol_variant in ['BRK.B', 'BRK-B', 'BRKB']:
            stmt = select(func.count(MarketDataCache.id)).where(
                MarketDataCache.symbol == symbol_variant
            )
            result = await db.execute(stmt)
            count = result.scalar()
            print(f"{symbol_variant}: {count} records")
        
        print("\n" + "="*80)
        print("Diagnosis")
        print("-" * 40)
        
        if total_records == 0:
            print("❌ No historical data in market_data_cache!")
            print("   Run: python scripts/reset_and_seed.py seed")
        elif days_old > 7 if date_range else True:
            print("⚠️ Historical data is stale or missing recent dates")
            print("   This would cause IR beta calculation to fail")
            print("   Need to run market data sync to fetch recent prices")
        else:
            print("✅ Historical data appears to be available")
            print("   Check if symbols match between positions and market_data_cache")


if __name__ == "__main__":
    asyncio.run(check_data_coverage())