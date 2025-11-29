#!/usr/bin/env python3
"""Check ETF mapping and data availability"""

import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import get_async_session
from app.models.market_data import MarketDataCache
from sqlalchemy import select


async def check_etf_mapping():
    """Check ETF mapping and availability"""
    
    # Factor to ETF mapping from the API
    factor_etf_map = {
        "Market Beta": "SPY",
        "Value": "VTV",
        "Growth": "VUG",
        "Momentum": "MTUM",
        "Quality": "QUAL",
        "Size": "SLY",
        "Low Volatility": "USMV"
    }
    
    print("=" * 60)
    print("7-FACTOR MODEL ETF MAPPING STATUS")
    print("=" * 60)
    print()
    print("Factor Name          | ETF Symbol | Status")
    print("-" * 60)
    
    async with get_async_session() as db:
        found_count = 0
        missing_etfs = []
        
        for factor_name, etf_symbol in factor_etf_map.items():
            stmt = select(MarketDataCache).where(
                MarketDataCache.symbol == etf_symbol
            ).order_by(MarketDataCache.updated_at.desc()).limit(1)
            
            result = await db.execute(stmt)
            data = result.scalar_one_or_none()
            
            status = "✅ Available" if data else "❌ Missing"
            print(f"{factor_name:<20} | {etf_symbol:<10} | {status}")
            
            if data:
                found_count += 1
            else:
                missing_etfs.append(f"{factor_name} ({etf_symbol})")
    
    print("-" * 60)
    print(f"\nSummary: {found_count}/{len(factor_etf_map)} ETFs have data")
    
    if missing_etfs:
        print("\n⚠️  Missing ETFs:")
        for etf in missing_etfs:
            print(f"   - {etf}")
    else:
        print("\n✅ All factor ETFs have data available!")
    
    # Check what's actually returned by the API endpoint
    print("\n" + "=" * 60)
    print("ETFs RETURNED BY API:")
    print("=" * 60)
    
    returned_etfs = ["MTUM", "QUAL", "SLY", "SPY", "USMV", "VTV", "VUG"]
    
    for factor_name, etf_symbol in factor_etf_map.items():
        if etf_symbol in returned_etfs:
            print(f"✅ {factor_name:<20} ({etf_symbol}) - Returned by API")
        else:
            print(f"❌ {factor_name:<20} ({etf_symbol}) - NOT returned by API")
    
    # Identify the issue
    all_etfs = set(factor_etf_map.values())
    returned_set = set(returned_etfs)
    missing_from_api = all_etfs - returned_set
    
    if missing_from_api:
        print(f"\n🔍 ETFs in database but NOT returned by API: {missing_from_api}")


if __name__ == "__main__":
    asyncio.run(check_etf_mapping())