#!/usr/bin/env python3
"""
Quick test of TradeFeeds API to verify it's working
"""
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from app.config import settings
from app.clients import TradeFeedsClient

async def test_quick():
    """Quick test with just a few funds"""
    
    if not settings.TRADEFEEDS_API_KEY:
        print("❌ TRADEFEEDS_API_KEY not configured")
        return
    
    print(f"✅ API Key configured: {settings.TRADEFEEDS_API_KEY[:10]}...")
    
    client = TradeFeedsClient(
        api_key=settings.TRADEFEEDS_API_KEY,
        timeout=settings.TRADEFEEDS_TIMEOUT_SECONDS,
        max_retries=settings.TRADEFEEDS_MAX_RETRIES,
        rate_limit=settings.TRADEFEEDS_RATE_LIMIT
    )
    
    # Test just a few funds
    test_funds = [
        ("VTSAX", "Vanguard Total Stock Market"),
        ("FXNAX", "Fidelity US Bond Index"),
        ("SPY", "SPDR S&P 500 ETF"),
        ("VTI", "Vanguard Total Stock Market ETF")
    ]
    
    for symbol, name in test_funds:
        print(f"\nTesting {symbol} ({name})...")
        try:
            holdings = await client.get_fund_holdings(symbol)
            if holdings and len(holdings) > 0:
                print(f"  ✅ Success: {len(holdings)} holdings")
                print(f"     Top holding: {holdings[0].get('symbol', 'N/A')} - {holdings[0].get('weight', 0)*100:.2f}%")
            else:
                print(f"  ⚠️ No holdings data returned")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
    
    await client.close()
    print("\n✅ Test complete")

if __name__ == "__main__":
    asyncio.run(test_quick())