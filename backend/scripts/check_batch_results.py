#!/usr/bin/env python3
"""Quick script to check what data exists after batch run"""
import requests
import sys

BASE_URL = "https://sigmasight-be-production.up.railway.app"
PORTFOLIO_ID = "1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe"

# Login
resp = requests.post(f"{BASE_URL}/api/v1/auth/login",
                     json={"email": "demo_individual@sigmasight.com", "password": "demo12345"})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get complete portfolio data
resp = requests.get(f"{BASE_URL}/api/v1/data/portfolio/{PORTFOLIO_ID}/complete", headers=headers)
data = resp.json()

print("📊 Batch Run Results Analysis")
print("=" * 60)
print(f"\n✅ What Worked:")

# Check what data exists
if data.get("portfolio"):
    print(f"   - Portfolio data: {data['portfolio'].get('name', 'N/A')}")
    print(f"   - Positions: {len(data.get('positions', []))}")
    print(f"   - Total value: ${data['portfolio'].get('total_value', 0):,.2f}")

if data.get("greeks"):
    print(f"   - Greeks calculations: {len(data['greeks'])} positions")
else:
    print(f"   - Greeks calculations: 0 positions")

if data.get("factor_exposures"):
    print(f"   - Factor exposures: {len(data['factor_exposures'])} positions")
else:
    print(f"   - Factor exposures: 0 positions")

if data.get("correlations"):
    print(f"   - Correlations: {len(data['correlations'])} calculated")
else:
    print(f"   - Correlations: 0 calculated")

if data.get("snapshots"):
    print(f"   - Portfolio snapshots: {len(data['snapshots'])} saved")
else:
    print(f"   - Portfolio snapshots: 0 saved")

print(f"\n❌ What Didn't Work:")

if not data.get("greeks"):
    print(f"   - No Greeks data (options calculations disabled)")

if not data.get("factor_exposures"):
    print(f"   - No factor exposure data")

if not data.get("correlations"):
    print(f"   - No correlation data")

if not data.get("snapshots"):
    print(f"   - No snapshot data")

# Check data quality
resp = requests.get(f"{BASE_URL}/api/v1/admin/batch/data-quality", headers=headers)
quality = resp.json()
print(f"\n📈 Data Quality:")
print(f"   - Overall score: {quality.get('quality_score', 0):.1%}")
print(f"   - Current prices coverage: {quality['coverage_details']['current_prices']['coverage_percentage']:.1%}")
print(f"   - Historical data coverage: {quality['coverage_details']['historical_data']['coverage_percentage']:.1%}")

print("\n" + "=" * 60)
