"""Quick Railway production data check"""
import requests

base_url = "https://sigmasight-be-production.up.railway.app/api/v1"
portfolio_id = "e23ab931-a033-edfe-ed4f-9d02474780b4"

print("=" * 50)
print("RAILWAY PRODUCTION DATA CHECK")
print("=" * 50)

# 1. Check portfolio data
print("\n1. PORTFOLIO DATA")
print("-" * 50)
resp = requests.get(f"{base_url}/data/portfolio/{portfolio_id}/complete")
if resp.status_code == 200:
    data = resp.json()
    print(f"Portfolio Name: {data.get('name', 'Unknown')}")
    print(f"Total Value: ${data.get('total_value', 0):,.2f}")
    print(f"Positions Count: {len(data.get('positions', []))}")
    print(f"\nFirst 5 positions:")
    for pos in data.get("positions", [])[:5]:
        print(f"  {pos.get('symbol'):8} | Qty: {pos.get('quantity'):>8.2f} | Value: ${pos.get('market_value', 0):>12,.2f}")
else:
    print(f"ERROR: {resp.status_code} - {resp.text[:200]}")

# 2. Check data quality
print("\n2. DATA QUALITY")
print("-" * 50)
resp = requests.get(f"{base_url}/data/portfolio/{portfolio_id}/data-quality")
if resp.status_code == 200:
    quality = resp.json()
    print(f"Overall Completeness: {quality.get('overall_completeness', 0):.1f}%")
    print(f"Market Data Coverage: {quality.get('market_data_coverage', 0):.1f}%")
    print(f"Positions with Prices: {quality.get('positions_with_prices', 0)}/{quality.get('total_positions', 0)}")

    missing = quality.get('missing_data', {})
    if missing:
        print(f"\nMissing Data:")
        for key, count in missing.items():
            if count > 0:
                print(f"  {key}: {count}")
else:
    print(f"ERROR: {resp.status_code}")

# 3. Check analytics
print("\n3. ANALYTICS DATA")
print("-" * 50)
resp = requests.get(f"{base_url}/analytics/portfolio/{portfolio_id}/overview")
if resp.status_code == 200:
    analytics = resp.json()
    print(f"Factor Exposures Available: {len(analytics.get('factor_exposures', []))}")
    print(f"Latest Snapshot Date: {analytics.get('latest_snapshot_date', 'None')}")
    print(f"Greeks Calculated: {'Yes' if analytics.get('greeks_available') else 'No'}")
else:
    print(f"ERROR: {resp.status_code}")

# 4. Check batch processing status
print("\n4. BATCH PROCESSING")
print("-" * 50)
resp = requests.get(f"{base_url}/admin/batch/data-quality")
if resp.status_code == 200:
    batch = resp.json()
    print(f"Last Batch Run: {batch.get('last_run', 'Never')}")
    print(f"Status: {batch.get('status', 'Unknown')}")
else:
    print(f"ERROR: {resp.status_code}")

print("\n" + "=" * 50)
print("DIAGNOSIS COMPLETE")
print("=" * 50)
