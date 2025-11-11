"""Quick test to check IR Beta in API"""
import requests
import json

# Login
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "demo_hnw@sigmasight.com", "password": "demo12345"}
)
token = login_response.json()["access_token"]

# Get factor exposures
portfolio_id = "e23ab931-a033-edfe-ed4f-9d02474780b4"
headers = {"Authorization": f"Bearer {token}"}

response = requests.get(
    f"http://localhost:8000/api/v1/analytics/portfolio/{portfolio_id}/factor-exposures",
    headers=headers
)

data = response.json()
print(f"Calculation Date: {data.get('calculation_date')}")
print(f"Number of factors: {len(data.get('factors', []))}")

for factor in data.get('factors', []):
    name = factor.get('name')
    beta = factor.get('beta', 0)
    print(f"  {name}: {beta}")

ir_beta = [f for f in data.get('factors', []) if 'IR' in f.get('name', '')]
if ir_beta:
    print(f"\nIR Beta FOUND: beta={ir_beta[0].get('beta')}")
else:
    print("\nIR Beta NOT FOUND in response")
