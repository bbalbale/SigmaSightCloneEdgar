"""
Test factor exposure API with flexible factor count
"""
import asyncio
import httpx
import json

async def test_factor_flexibility():
    portfolios = [
        {
            'id': '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe',
            'name': 'Demo Individual',
            'email': 'demo_individual@sigmasight.com'
        },
        {
            'id': 'e23ab931-a033-edfe-ed4f-9d02474780b4',
            'name': 'Demo HNW', 
            'email': 'demo_hnw@sigmasight.com'
        },
        {
            'id': 'fcd71196-e93e-f000-5a74-31a9eead3118',
            'name': 'Demo Hedge Fund',
            'email': 'demo_hedgefundstyle@sigmasight.com'
        }
    ]
    
    print('=' * 70)
    print('TESTING FLEXIBLE FACTOR EXPOSURE API')
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
            
            # Get factor exposures
            resp = await client.get(
                f'http://localhost:8000/api/v1/analytics/portfolio/{portfolio["id"]}/factor-exposures',
                headers=headers
            )
            
            print(f'\n{portfolio["name"]}')
            print('-' * 60)
            
            if resp.status_code == 200:
                data = resp.json()
                
                if data.get('available'):
                    factors = data.get('factors', [])
                    metadata = data.get('metadata', {})
                    
                    print(f'Status: ✅ Available')
                    print(f'Calculation Date: {data.get("calculation_date")}')
                    print(f'Completeness: {metadata.get("completeness", "unknown")}')
                    print(f'Factors Calculated: {metadata.get("factors_calculated", 0)}/{metadata.get("total_active_factors", 0)}')
                    print(f'Has Market Beta: {metadata.get("has_market_beta", False)}')
                    print(f'Factor Model: {metadata.get("factor_model", "unknown")}')
                    
                    print(f'\nFactor Exposures:')
                    for factor in factors:
                        print(f'  - {factor["name"]}: {factor["beta"]:.4f}')
                        
                    # Check if Short Interest is present
                    factor_names = [f['name'] for f in factors]
                    if 'Short Interest' in factor_names:
                        print('\n⚠️ WARNING: Short Interest factor still present!')
                    else:
                        print('\n✅ Short Interest factor correctly excluded')
                else:
                    print(f'Status: ❌ Not Available')
                    metadata = data.get('metadata', {})
                    print(f'Reason: {metadata.get("reason", "unknown")}')
                    print(f'Detail: {metadata.get("detail", "unknown")}')
            else:
                print(f'API Error: {resp.status_code}')
                print(f'Response: {resp.text}')
    
    print('\n' + '=' * 70)
    print('✅ FACTOR FLEXIBILITY TEST COMPLETE')
    print('=' * 70)

if __name__ == "__main__":
    asyncio.run(test_factor_flexibility())