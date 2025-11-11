#!/usr/bin/env python
"""Comprehensive test of all Raw Data Mode APIs after fixes"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_all_raw_data_endpoints():
    print("=" * 70)
    print("RAW DATA MODE API TEST SUITE - Phase 3.0")
    print("=" * 70)
    
    async with httpx.AsyncClient(base_url='http://localhost:8000') as client:
        # Login
        login_data = {'email': 'demo_individual@sigmasight.com', 'password': 'demo12345'}
        login_response = await client.post('/api/v1/auth/login', json=login_data)
        
        if login_response.status_code != 200:
            print(f'❌ Login failed: {login_response.status_code}')
            return
            
        token = login_response.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # Get portfolio ID
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent))
        
        from app.database import get_async_session
        from sqlalchemy import select
        from app.models.users import Portfolio
        from uuid import UUID
        
        user_response = await client.get('/api/v1/auth/me', headers=headers)
        user_id = user_response.json()['id']
        
        async with get_async_session() as db:
            stmt = select(Portfolio).where(Portfolio.user_id == UUID(user_id))
            result = await db.execute(stmt)
            portfolio = result.scalar_one_or_none()
            portfolio_id = str(portfolio.id)
        
        print(f"\n📋 Testing Portfolio: {portfolio.name}")
        print(f"   Portfolio ID: {portfolio_id}")
        print("\n" + "=" * 70)
        
        test_results = []
        
        # Test 1: Portfolio Complete Data
        print("\n✅ TEST 1: GET /api/v1/data/portfolio/{id}/complete")
        print("-" * 50)
        response = await client.get(f'/api/v1/data/portfolio/{portfolio_id}/complete', headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            test_results.append(("Portfolio Complete", "✅ PASS"))
            print(f"Status: {response.status_code} OK")
            print(f"Portfolio Name: {data['portfolio']['name']}")
            print(f"Total Value: ${data['portfolio']['total_value']:,.2f}")
            print(f"Position Count: {data['portfolio']['position_count']}")
            print(f"Response Size: ~{len(json.dumps(data))} bytes")
        else:
            test_results.append(("Portfolio Complete", "❌ FAIL"))
            print(f"Status: {response.status_code} - FAILED")
        
        # Test 2: Data Quality Assessment
        print("\n✅ TEST 2: GET /api/v1/data/portfolio/{id}/data-quality")
        print("-" * 50)
        response = await client.get(f'/api/v1/data/portfolio/{portfolio_id}/data-quality', headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            test_results.append(("Data Quality", "✅ PASS"))
            print(f"Status: {response.status_code} OK")
            print(f"Total Positions: {data['summary']['total_positions']}")
            print(f"Complete Data: {data['summary']['complete_data']}")
            print(f"Data Coverage: {data['summary']['data_coverage_percent']:.1f}%")
            
            # Check calculation feasibility
            cf = data['calculation_feasibility']
            print(f"Can Calculate Correlations: {cf['correlation_matrix']['feasible']}")
            print(f"Can Calculate Factors: {cf['factor_regression']['feasible']}")
        else:
            test_results.append(("Data Quality", "❌ FAIL"))
            print(f"Status: {response.status_code} - FAILED")
        
        # Test 3: Position Details
        print("\n✅ TEST 3: GET /api/v1/data/positions/details")
        print("-" * 50)
        response = await client.get(
            '/api/v1/data/positions/details',
            params={'portfolio_id': portfolio_id},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            test_results.append(("Position Details", "✅ PASS"))
            print(f"Status: {response.status_code} OK")
            print(f"Total Positions: {data['summary']['total_positions']}")
            print(f"Total Cost Basis: ${data['summary']['total_cost_basis']:,.2f}")
            print(f"Total Market Value: ${data['summary']['total_market_value']:,.2f}")
            print(f"Total Unrealized P&L: ${data['summary']['total_unrealized_pnl']:,.2f}")
            
            # Show sample positions
            if data['positions']:
                print("\nSample Positions (first 3):")
                for pos in data['positions'][:3]:
                    print(f"  {pos['symbol']}: {pos['quantity']} @ ${pos['current_price']:.2f}")
        else:
            test_results.append(("Position Details", "❌ FAIL"))
            print(f"Status: {response.status_code} - FAILED")
        
        # Test 4: Historical Prices
        print("\n✅ TEST 4: GET /api/v1/data/prices/historical/{portfolio_id}")
        print("-" * 50)
        response = await client.get(
            f'/api/v1/data/prices/historical/{portfolio_id}',
            params={'lookback_days': 30},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            test_results.append(("Historical Prices", "✅ PASS"))
            print(f"Status: {response.status_code} OK")
            
            if 'symbols' in data:
                symbols = list(data['symbols'].keys())
                print(f"Symbols with data: {len(symbols)}")
                print(f"First 5 symbols: {', '.join(symbols[:5])}")
                
                # Check data points
                first_symbol = symbols[0] if symbols else None
                if first_symbol and first_symbol in data['symbols']:
                    symbol_data = data['symbols'][first_symbol]
                    if isinstance(symbol_data, list):
                        print(f"Data points for {first_symbol}: {len(symbol_data)}")
                    elif isinstance(symbol_data, dict) and 'prices' in symbol_data:
                        print(f"Data points for {first_symbol}: {len(symbol_data['prices'])}")
            
            if 'factor_etfs' in data:
                print(f"Factor ETFs included: {len(data.get('factor_etfs', {}))}")
        else:
            test_results.append(("Historical Prices", "❌ FAIL"))
            print(f"Status: {response.status_code} - FAILED")
        
        # Test 5: Market Quotes
        print("\n✅ TEST 5: GET /api/v1/data/prices/quotes")
        print("-" * 50)
        response = await client.get(
            '/api/v1/data/prices/quotes',
            params={'symbols': 'AAPL,MSFT,GOOGL,AMZN,TSLA'},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            test_results.append(("Market Quotes", "✅ PASS"))
            print(f"Status: {response.status_code} OK")
            print(f"Requested Symbols: {data['metadata']['requested_symbols']}")
            print(f"Successful Quotes: {data['metadata']['successful_quotes']}")
            print(f"Failed Quotes: {data['metadata']['failed_quotes']}")
            
            # Show quotes
            if data['quotes']:
                print("\nQuotes Retrieved:")
                for quote in data['quotes']:
                    print(f"  {quote['symbol']}: ${quote['last_price']:.2f}")
        else:
            test_results.append(("Market Quotes", "❌ FAIL"))
            print(f"Status: {response.status_code} - FAILED")
        
        # Test 6: Factor ETF Prices
        print("\n✅ TEST 6: GET /api/v1/data/factors/etf-prices")
        print("-" * 50)
        response = await client.get(
            '/api/v1/data/factors/etf-prices',
            params={'lookback_days': 30},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            test_results.append(("Factor ETF Prices", "✅ PASS"))
            print(f"Status: {response.status_code} OK")
            print(f"Factor Model Version: {data['factor_model']['version']}")
            print(f"Regression Window: {data['factor_model']['regression_window']} days")
            
            # Show factors
            if 'factors' in data:
                print(f"\nFactors Available: {len(data['factors'])}")
                for factor_name, factor_data in list(data['factors'].items())[:3]:
                    print(f"  {factor_name}: ETF={factor_data['etf_symbol']}, " +
                          f"Prices={len(factor_data.get('prices', []))}")
        else:
            test_results.append(("Factor ETF Prices", "❌ FAIL"))
            print(f"Status: {response.status_code} - FAILED")
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        passed = sum(1 for _, status in test_results if "PASS" in status)
        total = len(test_results)
        
        for test_name, status in test_results:
            print(f"{status} {test_name}")
        
        print("\n" + "-" * 50)
        print(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Raw Data Mode APIs are fully functional.")
        else:
            print(f"⚠️  {total - passed} test(s) failed. Review the output above.")
        
        print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_all_raw_data_endpoints())