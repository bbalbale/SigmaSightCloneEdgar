#!/usr/bin/env python
"""
V2 Batch Architecture Test Script for Railway

Tests V2 mode is enabled and working:
1. Health endpoints (live, ready, status)
2. Symbol cache initialization status
3. V2 mode detection

Usage:
  python scripts/railway/test_v2_batch.py
"""
import requests
import json
import sys

BASE_URL = "https://sigmasight-be-production.up.railway.app"

print("=" * 60)
print("  V2 BATCH ARCHITECTURE TEST")
print("=" * 60)
print(f"Target: {BASE_URL}\n")

# Test 1: Liveness probe
print("1. Testing /health/live (liveness probe)...")
try:
    resp = requests.get(f"{BASE_URL}/health/live", timeout=10)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}")
    if resp.status_code == 200:
        print("   [OK] Liveness: PASSED")
    else:
        print("   [FAIL] Liveness: FAILED")
except Exception as e:
    print(f"   [ERROR] Error: {e}")

# Test 2: Readiness probe
print("\n2. Testing /health/ready (readiness probe)...")
try:
    resp = requests.get(f"{BASE_URL}/health/ready", timeout=10)
    print(f"   Status: {resp.status_code}")
    data = resp.json()
    print(f"   Response: {json.dumps(data, indent=6)}")
    if data.get("mode") == "v2":
        print("   [OK] V2 Mode: CONFIRMED")
        if data.get("status") == "ready":
            print("   [OK] Readiness: READY")
        else:
            print("   [WARN]  Readiness: INITIALIZING (cache warming up)")
    else:
        print("   [WARN]  Running in V1 mode")
except Exception as e:
    print(f"   [FAIL] Error: {e}")

# Test 3: Detailed status
print("\n3. Testing /health/status (detailed status)...")
try:
    resp = requests.get(f"{BASE_URL}/health/status", timeout=10)
    print(f"   Status: {resp.status_code}")
    data = resp.json()

    print(f"   V2 Enabled: {data.get('batch_v2_enabled')}")
    print(f"   Ready: {data.get('ready')}")

    if "symbol_cache" in data:
        cache = data["symbol_cache"]
        print(f"\n   Symbol Cache Status:")
        print(f"     - Initialized: {cache.get('initialized')}")
        print(f"     - Symbols Cached: {cache.get('symbols_cached')}")
        print(f"     - Dates Cached: {cache.get('dates_cached')}")
        if "price_cache_stats" in cache:
            stats = cache["price_cache_stats"]
            print(f"     - Prices Cached: {stats.get('cached_prices')}")
            print(f"     - Hit Rate: {stats.get('hit_rate_pct', 'N/A')}%")
        print("   [OK] Symbol Cache: OPERATIONAL")
    else:
        print("   [WARN]  Symbol cache not available (V1 mode)")
except Exception as e:
    print(f"   [FAIL] Error: {e}")

# Test 4: Check onboarding mode
print("\n4. Checking onboarding status for V2 mode detection...")
print("   (Requires auth - skipping for public test)")

# Summary
print("\n" + "=" * 60)
print("  TEST SUMMARY")
print("=" * 60)

try:
    status_resp = requests.get(f"{BASE_URL}/health/status", timeout=10)
    status_data = status_resp.json()

    if status_data.get("batch_v2_enabled"):
        print("[OK] V2 BATCH MODE: ENABLED")

        if status_data.get("ready"):
            print("[OK] SYSTEM STATUS: READY")
            print("\nNext steps to test V2 batch:")
            print("  1. Wait for scheduled cron (9 PM ET / 2 AM UTC)")
            print("  2. Or manually trigger via Railway CLI:")
            print("     railway run python scripts/batch_processing/run_symbol_batch.py")
        else:
            print("[WARN]  SYSTEM STATUS: INITIALIZING")
            print("   Cache is warming up, will be ready shortly")
    else:
        print("[WARN]  V1 BATCH MODE: ACTIVE")
        print("   V2 batch is not enabled. Set BATCH_V2_ENABLED=true in Railway")

except Exception as e:
    print(f"[FAIL] Could not determine status: {e}")

print("=" * 60)
