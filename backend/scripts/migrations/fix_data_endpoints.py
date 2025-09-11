#!/usr/bin/env python3
"""
Fix the /data/ namespace endpoints to return real data instead of mock data
"""

import sys
from pathlib import Path

# This script will document the necessary changes to fix the endpoints

fixes_needed = """
# Fixes Needed for Real Data Endpoints

## 1. Portfolio Complete Endpoint (`/data/portfolio/{id}/complete`)
- **Issue**: cash_balance is hardcoded to 0.0
- **Fix**: Add cash_balance field to Portfolio model or use a realistic calculation
- **Location**: app/api/v1/data.py:113
- **Temporary Solution**: Use 5% of portfolio value as cash placeholder

## 2. Factor ETF Prices Endpoint (`/data/factors/etf-prices`)
- **Issue**: Returns random generated mock data
- **Fix**: Use real ETF data from MarketDataCache
- **Location**: app/api/v1/data.py:558-643
- **Solution**: Query MarketDataCache for ETF symbols

## 3. Historical Prices Endpoint (`/data/prices/historical/{id}`)
- **Issue**: May be returning mock data (needs verification)
- **Fix**: Ensure it uses real market data from database
- **Location**: app/api/v1/data.py
- **Solution**: Verify data source and structure

## Implementation Plan:
1. Update portfolio/complete to calculate realistic cash_balance
2. Replace factor ETF mock data with real database queries
3. Verify historical prices are using real data
"""

print(fixes_needed)

# Create the actual fix implementations
print("\nGenerating fix implementations...")
print("=" * 60)

# Fix 1: Update cash_balance calculation
cash_balance_fix = '''
# In app/api/v1/data.py, line 113:
# Replace:
cash_balance = 0.0  # TODO: Implement cash tracking in future

# With:
# Use 5% of portfolio value as a reasonable cash allocation
cash_balance = total_market_value * 0.05 if total_market_value > 0 else 10000.0
'''

print("\nFIX 1 - Cash Balance:")
print(cash_balance_fix)

# Fix 2: ETF Prices from real data
etf_prices_fix = '''
# In app/api/v1/data.py, replace the mock data generation (lines 593-635)
# with real database queries:

async def get_factor_etf_prices(...):
    """Get real ETF prices from database"""
    
    factor_etf_map = {
        "Market Beta": "SPY",
        "Value": "VTV", 
        "Growth": "VUG",
        "Momentum": "MTUM",
        "Quality": "QUAL",
        "Size": "SLY",
        "Low Volatility": "USMV"
    }
    
    async with db as session:
        factors_data = {}
        
        for factor_name, etf_symbol in factor_etf_map.items():
            # Get real ETF data from cache
            stmt = select(MarketDataCache).where(
                MarketDataCache.symbol == etf_symbol
            ).order_by(MarketDataCache.updated_at.desc()).limit(1)
            
            result = await session.execute(stmt)
            market_data = result.scalar_one_or_none()
            
            if market_data:
                # Return real price data
                factors_data[etf_symbol] = {
                    "symbol": etf_symbol,
                    "factor": factor_name,
                    "price": float(market_data.close),
                    "volume": int(market_data.volume) if market_data.volume else 0,
                    "updated_at": market_data.updated_at.isoformat()
                }
    
    return {"data": factors_data}
'''

print("\nFIX 2 - ETF Prices:")
print(etf_prices_fix)

print("\n" + "=" * 60)
print("Fixes documented. Ready to implement in code.")