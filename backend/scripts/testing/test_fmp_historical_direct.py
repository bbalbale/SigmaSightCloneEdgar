#!/usr/bin/env python3
"""
Direct FMP Historical Data Test
Test FMP client historical data capability for factor ETFs
"""
import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.clients import market_data_factory
from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Factor ETFs to test
FACTOR_ETFS = ["SPY", "VTV", "VUG", "MTUM", "QUAL", "SLY", "USMV"]
BRK_VARIANTS = ["BRK.B", "BRK-B"]

async def test_fmp_direct():
    """Test FMP client historical data directly"""
    
    print("🔍 Testing FMP Historical Data Capability...")
    print(f"FMP API Key configured: {bool(settings.FMP_API_KEY)}")
    
    # Initialize market data factory
    market_data_factory.initialize()
    
    # Get FMP provider
    from app.clients import DataType
    provider = market_data_factory.get_provider_for_data_type(DataType.STOCKS)
    
    if not provider:
        print("❌ No FMP provider configured")
        return
        
    print(f"✅ Using provider: {provider.provider_name}")
    
    # Test historical data for factor ETFs
    results = {}
    
    test_symbols = FACTOR_ETFS + BRK_VARIANTS
    
    for symbol in test_symbols:
        print(f"\n📈 Testing {symbol}...")
        
        try:
            # Test direct FMP historical data
            if hasattr(provider, 'get_historical_prices'):
                historical_data = await provider.get_historical_prices(symbol, days=30)
                
                results[symbol] = {
                    'success': True,
                    'records_count': len(historical_data) if historical_data else 0,
                    'sample_data': historical_data[:2] if historical_data else None
                }
                
                print(f"  ✅ Historical: {len(historical_data) if historical_data else 0} records")
                if historical_data:
                    sample = historical_data[0]
                    print(f"  📊 Sample: Date={sample.get('date')}, Close=${sample.get('close')}")
                
            else:
                results[symbol] = {
                    'success': False,
                    'error': 'get_historical_prices method not available'
                }
                print(f"  ❌ No historical data method available")
                
        except Exception as e:
            results[symbol] = {
                'success': False,
                'error': str(e)
            }
            print(f"  ❌ Error: {str(e)}")
    
    # Summary report
    print("\n" + "="*60)
    print("📋 DIRECT FMP TEST SUMMARY")
    print("="*60)
    
    successful = [s for s, r in results.items() if r['success'] and r.get('records_count', 0) > 0]
    failed = [s for s, r in results.items() if not r['success'] or r.get('records_count', 0) == 0]
    
    print(f"✅ Successful: {len(successful)}/{len(test_symbols)} ({len(successful)/len(test_symbols)*100:.1f}%)")
    print(f"❌ Failed: {len(failed)}/{len(test_symbols)}")
    
    if successful:
        print(f"\n✅ Working symbols: {', '.join(successful)}")
    
    if failed:
        print(f"\n❌ Failed symbols: {', '.join(failed)}")
        
    # Detailed results
    print(f"\n📊 DETAILED RESULTS:")
    for symbol, result in results.items():
        if result['success']:
            count = result.get('records_count', 0)
            print(f"  {symbol}: {count} records")
        else:
            error = result.get('error', 'Unknown error')
            print(f"  {symbol}: FAILED - {error}")
    
    # Close provider connections
    await market_data_factory.close_all()
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_fmp_direct())