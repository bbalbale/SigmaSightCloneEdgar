#!/usr/bin/env python3
"""Check if ETF data exists in the database"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_async_session
from app.models.market_data import MarketDataCache
from sqlalchemy import select


async def check_etf_data():
    """Check ETF data in database"""
    async with get_async_session() as db:
        etf_symbols = ['SPY', 'QQQ', 'VTV', 'VUG', 'MTUM', 'QUAL', 'SLY', 'USMV']
        
        print("ETF Data in MarketDataCache:")
        print("-" * 40)
        
        found_count = 0
        for symbol in etf_symbols:
            stmt = select(MarketDataCache).where(
                MarketDataCache.symbol == symbol
            ).order_by(MarketDataCache.updated_at.desc()).limit(1)
            result = await db.execute(stmt)
            data = result.scalar_one_or_none()
            
            if data:
                print(f'✅ {symbol}: ${data.close:.2f} (updated: {data.updated_at})')
                found_count += 1
            else:
                print(f'❌ {symbol}: No data')
        
        print("-" * 40)
        print(f"Found {found_count}/{len(etf_symbols)} ETFs in database")
        
        return found_count > 0


if __name__ == "__main__":
    has_data = asyncio.run(check_etf_data())
    sys.exit(0 if has_data else 1)