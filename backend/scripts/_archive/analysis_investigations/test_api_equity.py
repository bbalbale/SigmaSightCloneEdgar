"""Test the overview API to verify equity_balance is correct"""
import asyncio
import httpx

async def test_equity():
    # Login first
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "demo_hnw@sigmasight.com", "password": "demo12345"}
        )
        login_data = login_response.json()
        token = login_data["access_token"]

        # Get overview
        headers = {"Authorization": f"Bearer {token}"}
        overview_response = await client.get(
            "/api/v1/analytics/portfolio/e23ab931-a033-edfe-ed4f-9d02474780b4/overview",
            headers=headers
        )

        data = overview_response.json()
        equity = data.get("equity_balance")

        print("=" * 80)
        print("API EQUITY BALANCE TEST")
        print("=" * 80)
        print(f"Equity Balance from API: ${equity:,.2f}")
        print()

        if abs(equity - 3077014.0) < 1.0:
            print("✅ SUCCESS! API is returning correct equity from PortfolioSnapshot")
        elif abs(equity - 2850000.0) < 1.0:
            print("❌ FAILED! API is still returning initial equity from Portfolio table")
        else:
            print(f"⚠️  UNEXPECTED! API returned ${equity:,.2f}")
        print("=" * 80)

asyncio.run(test_equity())
