"""
Test script for fundamental data API endpoints
"""
import requests

# Base URL (assuming backend running on localhost:8000)
BASE_URL = "http://localhost:8000/api/v1/fundamentals"

def test_income_statement():
    print("="*80)
    print("Testing: GET /api/v1/fundamentals/MSFT/income-statement")
    print("="*80)
    response = requests.get(f"{BASE_URL}/MSFT/income-statement?periods=3&frequency=q")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Symbol: {data['symbol']}, Periods: {data['periods_returned']}")
        if data['periods']:
            p = data['periods'][0]
            print(f"Latest ({p['period_date']}): Revenue ${p.get('total_revenue', 0):,.0f}, EPS ${p.get('diluted_eps', 0):.2f}")
        print("[OK] Income Statement Working")
    else:
        print(f"[ERROR] {response.text}")
    print()

def test_balance_sheet():
    print("="*80)
    print("Testing: GET /api/v1/fundamentals/MSFT/balance-sheet")
    print("="*80)
    response = requests.get(f"{BASE_URL}/MSFT/balance-sheet?periods=3&frequency=q")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Symbol: {data['symbol']}, Periods: {data['periods_returned']}")
        if data['periods']:
            p = data['periods'][0]
            print(f"Latest ({p['period_date']}): Assets ${p.get('total_assets', 0):,.0f}, Equity ${p.get('total_stockholders_equity', 0):,.0f}")
        print("[OK] Balance Sheet Working")
    else:
        print(f"[ERROR] {response.text}")
    print()

def test_cash_flow():
    print("="*80)
    print("Testing: GET /api/v1/fundamentals/MSFT/cash-flow")
    print("="*80)
    response = requests.get(f"{BASE_URL}/MSFT/cash-flow?periods=3&frequency=q")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Symbol: {data['symbol']}, Periods: {data['periods_returned']}")
        if data['periods']:
            p = data['periods'][0]
            print(f"Latest ({p['period_date']}): OCF ${p.get('operating_cash_flow', 0):,.0f}, FCF ${p.get('free_cash_flow', 0):,.0f}")
        print("[OK] Cash Flow Working")
    else:
        print(f"[ERROR] {response.text}")
    print()

def test_analyst_estimates():
    print("="*80)
    print("Testing: GET /api/v1/fundamentals/MSFT/analyst-estimates")
    print("="*80)
    response = requests.get(f"{BASE_URL}/MSFT/analyst-estimates")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        est = data['estimates']
        print(f"Symbol: {data['symbol']}")
        print(f"Current Quarter: Revenue ${est.get('current_quarter_revenue_avg', 0):,.0f}, EPS ${est.get('current_quarter_eps_avg', 0):.2f}")
        print(f"Current Year: Revenue ${est.get('current_year_revenue_avg', 0):,.0f}, EPS ${est.get('current_year_earnings_avg', 0):.2f}")
        print("[OK] Analyst Estimates Working")
    else:
        print(f"[ERROR] {response.text}")
    print()

if __name__ == "__main__":
    print("\nFUNDAMENTAL DATA API ENDPOINT TESTS\n")
    try:
        test_income_statement()
        test_balance_sheet()
        test_cash_flow()
        test_analyst_estimates()
        print("="*80)
        print("ALL TESTS COMPLETED!")
        print("="*80)
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect - ensure backend is running on http://localhost:8000")
    except Exception as e:
        print(f"[ERROR] {e}")
