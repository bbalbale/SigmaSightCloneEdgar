#!/usr/bin/env python3
"""
Test FMP Company Profile API for GICS sector/industry data
Tests the implementation for Section 1.6.14 Phase 4 - GICS Sector Data Integration
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.market_data_service import market_data_service
from app.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_fmp_company_profiles():
    """Test FMP Company Profile API integration"""
    print("\n" + "="*80)
    print("FMP Company Profile API Test - GICS Sector/Industry Data")
    print("="*80)
    
    # Test symbols from demo portfolios
    test_symbols = [
        'AAPL',  # Tech stock
        'MSFT',  # Tech stock
        'JPM',   # Financial
        'JNJ',   # Healthcare
        'XOM',   # Energy
        'WMT',   # Consumer Staples
        'DIS',   # Communication Services
        'BA',    # Industrials
        'SPY',   # ETF (should show as ETF)
        'BRK-B'  # Berkshire Hathaway (test special symbol)
    ]
    
    try:
        # Test 1: Direct API call
        print("\n📊 Test 1: Direct FMP API Call")
        print("-" * 40)
        
        profiles = await market_data_service.fetch_company_profiles(test_symbols)
        
        if profiles:
            print(f"✅ Retrieved {len(profiles)} company profiles")
            print("\nSample Results:")
            for symbol in test_symbols[:5]:  # Show first 5
                if symbol in profiles:
                    profile = profiles[symbol]
                    print(f"\n{symbol}:")
                    print(f"  Company: {profile.get('company_name', 'N/A')}")
                    print(f"  Sector: {profile.get('sector', 'N/A')}")
                    print(f"  Industry: {profile.get('industry', 'N/A')}")
                    print(f"  Exchange: {profile.get('exchange', 'N/A')}")
                    print(f"  Country: {profile.get('country', 'N/A')}")
                    if profile.get('is_etf'):
                        print(f"  Type: ETF")
                    elif profile.get('is_fund'):
                        print(f"  Type: Mutual Fund")
                else:
                    print(f"\n{symbol}: ❌ No profile data")
        else:
            print("❌ No profiles retrieved")
        
        # Test 2: Database integration
        print("\n💾 Test 2: Database Integration")
        print("-" * 40)
        
        async with AsyncSessionLocal() as db:
            results = await market_data_service.update_security_metadata(
                db, 
                test_symbols,
                force_refresh=True  # Force update even if cached
            )
            
            success_count = sum(1 for v in results.values() if v)
            print(f"✅ Updated {success_count}/{len(test_symbols)} symbols in database")
            
            for symbol, success in results.items():
                status = "✅" if success else "❌"
                print(f"  {symbol}: {status}")
        
        # Test 3: Special cases
        print("\n🔍 Test 3: Special Cases")
        print("-" * 40)
        
        special_symbols = ['BRK-B', 'BRK.B', 'ZOOM']  # Test symbol format variations
        special_profiles = await market_data_service.fetch_company_profiles(special_symbols)
        
        for symbol in special_symbols:
            if symbol in special_profiles:
                profile = special_profiles[symbol]
                print(f"{symbol}: ✅ Found - {profile.get('sector', 'N/A')} / {profile.get('industry', 'N/A')}")
            else:
                print(f"{symbol}: ❌ Not found")
        
        # Summary
        print("\n" + "="*80)
        print("📈 FMP Company Profile Test Summary")
        print("="*80)
        
        total_tested = len(test_symbols)
        total_success = len(profiles) if profiles else 0
        success_rate = (total_success / total_tested) * 100 if total_tested > 0 else 0
        
        print(f"Total Symbols Tested: {total_tested}")
        print(f"Successfully Retrieved: {total_success}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("\n✅ FMP Company Profile API is working well!")
            print("   Ready for GICS sector data integration")
        elif success_rate >= 50:
            print("\n⚠️ FMP Company Profile API has partial coverage")
            print("   May need fallback for some symbols")
        else:
            print("\n❌ FMP Company Profile API has poor coverage")
            print("   Need to investigate API key or endpoint issues")
        
        return success_rate >= 80
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        await market_data_service.close()


if __name__ == "__main__":
    result = asyncio.run(test_fmp_company_profiles())
    sys.exit(0 if result else 1)