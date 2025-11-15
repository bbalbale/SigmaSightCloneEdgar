"""Check Railway database users and portfolios via backend API"""
import requests

BASE_URL = "https://sigmasight-be-production.up.railway.app/api/v1"

# Login first to get token
print("Logging in...")
login_resp = requests.post(
    f"{BASE_URL}/auth/login",
    json={"email": "demo_hnw@sigmasight.com", "password": "demo12345"}
)

if login_resp.status_code != 200:
    print(f"Login failed: {login_resp.status_code}")
    print(login_resp.text)
    exit(1)

token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("=" * 70)
print("RAILWAY DATABASE CHECK")
print("=" * 70)

# Get current user info
print("\n1. CURRENT USER INFO")
print("-" * 70)
me_resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
if me_resp.status_code == 200:
    user_data = me_resp.json()
    print(f"Email: {user_data.get('email')}")
    print(f"User ID: {user_data.get('id')}")
    print(f"Portfolio ID: {user_data.get('portfolio_id')}")
else:
    print(f"ERROR: {me_resp.status_code}")

# Try to get demo HNW portfolio
portfolio_id = "e23ab931-a033-edfe-ed4f-9d02474780b4"  # Demo HNW

print(f"\n2. DEMO HNW PORTFOLIO ({portfolio_id})")
print("-" * 70)
portfolio_resp = requests.get(
    f"{BASE_URL}/data/portfolio/{portfolio_id}/complete",
    headers=headers
)
if portfolio_resp.status_code == 200:
    portfolio = portfolio_resp.json()
    print(f"Name: {portfolio.get('name')}")
    print(f"Total Positions: {len(portfolio.get('positions', []))}")
    print(f"Total Value: ${portfolio.get('total_value', 0):,.2f}")

    if portfolio.get('positions'):
        print(f"\nFirst 10 positions:")
        for pos in portfolio.get('positions', [])[:10]:
            symbol = pos.get('symbol', 'N/A')
            qty = pos.get('quantity', 0)
            mv = pos.get('market_value', 0)
            print(f"  {symbol:8} | Qty: {qty:>10.2f} | Value: ${mv:>12,.2f}")
    else:
        print("\n⚠️  NO POSITIONS FOUND!")
else:
    print(f"ERROR: {portfolio_resp.status_code}")
    print(portfolio_resp.text[:200])

# Try Family Office portfolio (if it exists)
print(f"\n3. CHECKING FOR OTHER PORTFOLIOS")
print("-" * 70)

# Known demo portfolio IDs from seed data
demo_portfolios = {
    "Individual": "52110fe1-ca52-42ff-abaa-c0c90e8e21be",
    "HNW": "e23ab931-a033-edfe-ed4f-9d02474780b4",
    "Hedge Fund": "a6f4e8d3-9b2c-4a1f-8e7d-6c5b4a3f2e1d"
}

for name, pid in demo_portfolios.items():
    resp = requests.get(f"{BASE_URL}/data/portfolio/{pid}/complete", headers=headers)
    if resp.status_code == 200:
        p = resp.json()
        pos_count = len(p.get('positions', []))
        print(f"✓ {name:15} | ID: {pid[:8]}... | Positions: {pos_count}")
    else:
        print(f"✗ {name:15} | Not found or no access")

print("\n" + "=" * 70)
print("CHECK COMPLETE")
print("=" * 70)
