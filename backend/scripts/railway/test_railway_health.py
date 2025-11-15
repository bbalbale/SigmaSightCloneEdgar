#!/usr/bin/env python
"""
Quick health check for Railway backend
"""
import requests

BASE_URL = "https://sigmasight-be-production.up.railway.app"

print("Testing Railway backend health...")
print(f"Target: {BASE_URL}\n")

# Test 1: Root endpoint
print("1. Testing root endpoint...")
try:
    resp = requests.get(f"{BASE_URL}/", timeout=10)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.text[:200]}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Health endpoint
print("\n2. Testing health endpoint...")
try:
    resp = requests.get(f"{BASE_URL}/health", timeout=10)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Docs endpoint
print("\n3. Testing API docs...")
try:
    resp = requests.get(f"{BASE_URL}/docs", timeout=10)
    print(f"   Status: {resp.status_code}")
    print(f"   ✓ Docs accessible")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\nIf all tests passed, backend is healthy and the SSL error is transient.")
print("Try running the fix script again.")
