#!/usr/bin/env python3
"""
Test Polygon Options API Access
Debug why Starter Plan ($29) might not be returning options data
Tests correct endpoints and symbol formats
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from polygon import RESTClient
from app.config import settings

def test_polygon_options():
    """Test various Polygon options endpoints"""
    print("\n" + "="*80)
    print("Polygon Options API Access Test")
    print("="*80)
    
    client = RESTClient(api_key=settings.POLYGON_API_KEY)
    
    # Test stock symbol for baseline
    test_symbol = "AAPL"
    
    # 1. Test Account Status
    print("\n📊 1. Account Information")
    print("-" * 40)
    print(f"API Key: {settings.POLYGON_API_KEY[:8]}...")
    print(f"Plan Type: {settings.POLYGON_PLAN}")
    
    # 2. Test Stock Data (should work on all plans)
    print("\n📊 2. Stock Data Test (Baseline)")
    print("-" * 40)
    
    try:
        # Get last trade for stock
        last_trade = client.get_last_trade(ticker=test_symbol)
        if last_trade:
            print(f"✅ Stock last trade: {test_symbol} @ ${last_trade.price}")
        else:
            print(f"❌ No stock trade data for {test_symbol}")
    except Exception as e:
        print(f"❌ Stock trade error: {str(e)}")
    
    # 3. Test Options Contracts Listing
    print("\n📊 3. Options Contracts Listing")
    print("-" * 40)
    
    try:
        # List options contracts for AAPL
        contracts = client.list_options_contracts(
            underlying_ticker=test_symbol,
            limit=5
        )
        
        contracts_list = list(contracts)
        if contracts_list:
            print(f"✅ Found {len(contracts_list)} options contracts")
            for i, contract in enumerate(contracts_list[:3], 1):
                print(f"   {i}. {contract.ticker}")
                print(f"      Strike: ${contract.strike_price}")
                print(f"      Expiry: {contract.expiration_date}")
                print(f"      Type: {contract.contract_type}")
        else:
            print(f"❌ No options contracts found for {test_symbol}")
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Options contracts error: {error_msg}")
        
        # Check for specific error types
        if "403" in error_msg:
            print("   ⚠️ 403 Forbidden - Subscription tier may not include options")
        elif "404" in error_msg:
            print("   ⚠️ 404 Not Found - Endpoint may not exist for your plan")
        elif "401" in error_msg:
            print("   ⚠️ 401 Unauthorized - API key issue")
    
    # 4. Test Options Last Trade (with proper OCC symbol)
    print("\n📊 4. Options Last Trade Test")
    print("-" * 40)
    
    # Construct an options symbol (OCC format)
    # Example: O:AAPL241220C00250000 (AAPL Dec 20 2024 $250 Call)
    expiry = datetime.now() + timedelta(days=30)
    options_symbol = f"O:AAPL{expiry.strftime('%y%m%d')}C00250000"
    
    print(f"Testing options symbol: {options_symbol}")
    
    try:
        last_trade = client.get_last_trade(ticker=options_symbol)
        if last_trade:
            print(f"✅ Options last trade: {options_symbol} @ ${last_trade.price}")
        else:
            print(f"❌ No trade data for options symbol {options_symbol}")
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Options trade error: {error_msg}")
    
    # 5. Test Options Chain Snapshot
    print("\n📊 5. Options Chain Snapshot")
    print("-" * 40)
    
    try:
        # Try to get options chain snapshot
        # Note: This might require a higher tier
        snapshot = client.get_snapshot_option(
            underlying_ticker=test_symbol,
            option_contract=options_symbol[2:]  # Remove O: prefix
        )
        
        if snapshot:
            print(f"✅ Options snapshot retrieved")
            if hasattr(snapshot, 'day'):
                print(f"   Day volume: {snapshot.day.volume if snapshot.day else 'N/A'}")
            if hasattr(snapshot, 'last_quote'):
                print(f"   Bid/Ask: ${snapshot.last_quote.bid if snapshot.last_quote else 'N/A'} / ${snapshot.last_quote.ask if snapshot.last_quote else 'N/A'}")
        else:
            print(f"❌ No snapshot data available")
            
    except AttributeError as e:
        print(f"⚠️ Method not available: {str(e)}")
        print("   Snapshot methods may not be in the Python client")
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Snapshot error: {error_msg}")
    
    # 6. Test Raw API Call
    print("\n📊 6. Raw API Call Test")
    print("-" * 40)
    
    try:
        # Try a raw API call to options endpoint
        url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={test_symbol}&limit=1&apiKey={settings.POLYGON_API_KEY}"
        response = client._get_raw(f"/v3/reference/options/contracts?underlying_ticker={test_symbol}&limit=1")
        
        if response and 'results' in response:
            print(f"✅ Raw API call successful")
            print(f"   Results count: {len(response.get('results', []))}")
            if response.get('status'):
                print(f"   Status: {response['status']}")
        else:
            print(f"❌ Raw API call returned no results")
            print(f"   Response: {response}")
            
    except Exception as e:
        print(f"❌ Raw API error: {str(e)}")
    
    # Summary
    print("\n" + "="*80)
    print("📊 Polygon Options API Test Summary")
    print("="*80)
    
    print("\nDiagnosis:")
    print("1. Check if options contracts are listed (most basic options feature)")
    print("2. Verify if options trades/quotes require higher tier")
    print("3. Confirm OCC symbol format is correct (O: prefix)")
    print("4. Review error messages for subscription limitations")
    
    print("\nNext Steps:")
    print("1. If 403 errors: Contact Polygon support about Starter plan options access")
    print("2. If no contracts found: Verify underlying ticker has options")
    print("3. If methods missing: Update polygon-api-client library")
    print("4. Consider upgrading to Developer plan if needed for options")


if __name__ == "__main__":
    test_polygon_options()