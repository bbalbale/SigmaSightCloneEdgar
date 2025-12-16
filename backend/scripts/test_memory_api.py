"""
Test script for memory API endpoints.
Tests the full end-to-end flow including authentication.
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"


def get_auth_token():
    """Login and get an auth token."""
    # Login expects JSON with email and password
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": "demo_individual@sigmasight.com",
            "password": "demo12345",
        },
    )
    if response.status_code != 200:
        print(f"Login failed: {response.status_code}")
        print(response.text)
        return None

    token_data = response.json()
    return token_data.get("access_token")


def test_memory_endpoints():
    """Test all memory API endpoints."""
    # Get auth token
    token = get_auth_token()
    if not token:
        print("ERROR: Could not get auth token")
        return

    print(f"Got auth token: {token[:20]}...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # 1. Get memory count (should be 0 initially)
    print("\n1. Testing GET /agent/memories/count")
    response = requests.get(f"{BASE_URL}/agent/memories/count", headers=headers)
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text}")

    # 2. List memories (should be empty)
    print("\n2. Testing GET /agent/memories")
    response = requests.get(f"{BASE_URL}/agent/memories", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total: {data.get('total')}, Memories: {len(data.get('memories', []))}")
    else:
        print(f"   Error: {response.text}")

    # 3. Create a memory
    print("\n3. Testing POST /agent/memories")
    memory_data = {
        "content": "User prefers detailed explanations with examples",
        "scope": "user",
        "tags": {"category": "preference", "source": "api_test"},
    }
    response = requests.post(
        f"{BASE_URL}/agent/memories",
        headers=headers,
        json=memory_data,
    )
    print(f"   Status: {response.status_code}")
    memory_id = None
    if response.status_code == 200:
        data = response.json()
        memory_id = data.get("id")
        print(f"   Created memory ID: {memory_id}")
        print(f"   Message: {data.get('message')}")
    else:
        print(f"   Error: {response.text}")

    # 4. List memories again (should have 1)
    print("\n4. Testing GET /agent/memories (after create)")
    response = requests.get(f"{BASE_URL}/agent/memories", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total: {data.get('total')}")
        for m in data.get("memories", []):
            print(f"   - [{m['scope']}] {m['content'][:50]}...")
    else:
        print(f"   Error: {response.text}")

    # 5. Delete the memory
    if memory_id:
        print(f"\n5. Testing DELETE /agent/memories/{memory_id}")
        response = requests.delete(
            f"{BASE_URL}/agent/memories/{memory_id}",
            headers=headers,
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success')}")
            print(f"   Message: {data.get('message')}")
        else:
            print(f"   Error: {response.text}")

    # 6. Final count (should be 0)
    print("\n6. Testing GET /agent/memories/count (after delete)")
    response = requests.get(f"{BASE_URL}/agent/memories/count", headers=headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Count: {data.get('count')}")
    else:
        print(f"   Error: {response.text}")

    print("\n=== Memory API Test Complete ===")


if __name__ == "__main__":
    test_memory_endpoints()
