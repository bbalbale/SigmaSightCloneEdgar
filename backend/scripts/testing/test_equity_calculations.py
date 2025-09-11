import asyncio
import httpx

async def test_equity_calculations():
    portfolios = [
        {
            'id': '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe', 
            'name': 'Demo Individual', 
            'email': 'demo_individual@sigmasight.com', 
            'expected_equity': 600000.00
        },
        {
            'id': 'e23ab931-a033-edfe-ed4f-9d02474780b4', 
            'name': 'Demo HNW', 
            'email': 'demo_hnw@sigmasight.com', 
            'expected_equity': 2000000.00
        },
        {
            'id': 'fcd71196-e93e-f000-5a74-31a9eead3118', 
            'name': 'Demo Hedge Fund', 
            'email': 'demo_hedgefundstyle@sigmasight.com', 
            'expected_equity': 4000000.00
        }
    ]
    
    print('=' * 70)
    print('TESTING EQUITY-BASED PORTFOLIO CALCULATIONS')
    print('=' * 70)
    
    for portfolio in portfolios:
        async with httpx.AsyncClient() as client:
            # Login
            login_resp = await client.post(
                'http://localhost:8000/api/v1/auth/login',
                json={'email': portfolio['email'], 'password': 'demo12345'}
            )
            
            if login_resp.status_code != 200:
                print(f'Login failed for {portfolio["name"]}')
                continue
                
            token = login_resp.json().get('access_token')
            headers = {'Authorization': f'Bearer {token}'}
            
            # Get analytics with equity calculations
            resp = await client.get(
                f'http://localhost:8000/api/v1/analytics/portfolio/{portfolio["id"]}/overview',
                headers=headers
            )
            
            if resp.status_code == 200:
                data = resp.json()
                
                print(f'\n{portfolio["name"]}')
                print('-' * 60)
                
                # Check if equity matches expected value
                actual_equity = data.get("equity_balance", 0)
                expected_equity = portfolio["expected_equity"]
                if abs(actual_equity - expected_equity) < 0.01:
                    print(f'Equity Balance: ${actual_equity:,.2f} ✅')
                else:
                    print(f'Equity Balance: ${actual_equity:,.2f} ❌ (expected ${expected_equity:,.2f})')
                
                print(f'Cash Balance: ${data.get("cash_balance", 0):,.2f}')
                print(f'Leverage: {data.get("leverage", 0):.2f}x')
                
                exposures = data.get('exposures', {})
                print(f'Long Exposure: ${exposures.get("long_exposure", 0):,.2f}')
                print(f'Short Exposure: ${exposures.get("short_exposure", 0):,.2f}')
                print(f'Gross Exposure: ${exposures.get("gross_exposure", 0):,.2f}')
                print(f'Net Exposure: ${exposures.get("net_exposure", 0):,.2f}')
                
                # Check calculations
                equity = data.get('equity_balance', 0)
                cash = data.get('cash_balance', 0)
                long_exp = exposures.get('long_exposure', 0)
                short_exp = exposures.get('short_exposure', 0)
                
                # Verify: Cash = Equity - Long + |Short|
                expected_cash = equity - long_exp + abs(short_exp) if equity else 0
                if abs(cash - expected_cash) < 0.01:
                    print('✅ Cash calculation correct!')
                else:
                    print(f'❌ Cash mismatch: got {cash:.2f}, expected {expected_cash:.2f}')
                    
                # Check leverage
                if equity > 0:
                    expected_leverage = exposures.get('gross_exposure', 0) / equity
                    actual_leverage = data.get('leverage', 0)
                    if abs(actual_leverage - expected_leverage) < 0.01:
                        print('✅ Leverage calculation correct!')
                    else:
                        print(f'❌ Leverage mismatch: got {actual_leverage:.2f}, expected {expected_leverage:.2f}')
            else:
                print(f'API Error: {resp.status_code}')
    
    print('\n' + '=' * 70)
    print('✅ EQUITY-BASED CALCULATIONS COMPLETE')
    print('=' * 70)

if __name__ == "__main__":
    asyncio.run(test_equity_calculations())