"""
Test the volatility API endpoint directly
"""

import asyncio
import requests
from app.database import get_async_session
from app.core.auth import create_token_response
from app.models.users import User
from sqlalchemy import select

BASE_URL = "http://localhost:8000"
PORTFOLIO_ID = "1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe"  # Demo Individual Investor


async def get_demo_user_token():
    """Get a JWT token for the demo user"""
    async with get_async_session() as db:
        result = await db.execute(
            select(User).where(User.email == "demo_individual@sigmasight.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            print("[ERROR] Demo user not found!")
            return None

        # Create token
        token_response = create_token_response(user.id, user.email)
        return token_response["access_token"]


async def test_volatility_endpoint():
    """Test the volatility endpoint"""
    print("=" * 80)
    print("TESTING VOLATILITY API ENDPOINT")
    print("=" * 80)
    print()

    # Get token
    print("[1] Getting authentication token...")
    token = await get_demo_user_token()

    if not token:
        return

    print(f"[OK] Got token: {token[:20]}...")
    print()

    # Make API request
    print(f"[2] Testing endpoint: /api/v1/analytics/portfolio/{PORTFOLIO_ID}/volatility")
    url = f"{BASE_URL}/api/v1/analytics/portfolio/{PORTFOLIO_ID}/volatility"
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        print(f"[OK] Response status: {response.status_code}")
        print()

        if response.status_code == 200:
            data = response.json()
            print("[3] Response Data:")
            print("-" * 80)

            # Pretty print the response
            import json
            print(json.dumps(data, indent=2))
            print()

            # Check availability
            if data.get("available"):
                print("[OK] Volatility data IS available!")

                if data.get("data"):
                    vol_data = data["data"]
                    print()
                    print("Volatility Metrics:")
                    print(f"  - realized_volatility_21d: {vol_data.get('realized_volatility_21d')}")
                    print(f"  - realized_volatility_63d: {vol_data.get('realized_volatility_63d')}")
                    print(f"  - expected_volatility_21d: {vol_data.get('expected_volatility_21d')}")
                    print(f"  - volatility_trend: {vol_data.get('volatility_trend')}")
                    print(f"  - volatility_percentile: {vol_data.get('volatility_percentile')}")
            else:
                print("[ERROR] Volatility data is NOT available!")
                if data.get("metadata"):
                    print(f"  Error: {data['metadata'].get('error')}")
        else:
            print(f"[ERROR] Request failed:")
            print(f"  {response.text}")

    except Exception as e:
        print(f"[ERROR] Exception during API call: {e}")


if __name__ == "__main__":
    asyncio.run(test_volatility_endpoint())
