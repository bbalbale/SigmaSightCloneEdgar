import requests
import json

# Login
login_response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"username": "demo_hnw@sigmasight.com", "password": "demo12345"}
)
token = login_response.json()["access_token"]

# Get positions
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(
    "http://localhost:8000/api/v1/data/positions/details?portfolio_id=e23ab931-a033-edfe-ed4f-9d02474780b4",
    headers=headers
)

data = response.json()

# Find PG and print its data
for position in data.get("positions", []):
    if position.get("symbol") == "PG":
        print("\n=== PG Position Data ===")
        print(json.dumps(position, indent=2, default=str))
        print(f"\nHas company_name field: {'company_name' in position}")
        print(f"company_name value: {position.get('company_name')}")
        break
else:
    print("PG not found in response")
    print(f"Total positions: {len(data.get('positions', []))}")
