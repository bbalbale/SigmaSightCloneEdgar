"""Test the overview API for Individual portfolio to check leverage fix"""
import asyncio
import httpx

async def test_individual():
    # Individual Investor portfolio ID
    indiv_id = '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe'

    # Login first
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Login
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "demo_individual@sigmasight.com", "password": "demo12345"}
        )
        login_data = login_response.json()
        token = login_data["access_token"]

        # Get overview
        headers = {"Authorization": f"Bearer {token}"}
        overview_response = await client.get(
            f"/api/v1/analytics/portfolio/{indiv_id}/overview",
            headers=headers
        )

        data = overview_response.json()
        equity = data.get("equity_balance")
        leverage = data.get("leverage")
        cash = data.get("cash_balance")

        print("=" * 80)
        print("INDIVIDUAL INVESTOR PORTFOLIO - API TEST")
        print("=" * 80)
        print(f"Equity Balance:  ${equity:,.2f}")
        print(f"Leverage:        {leverage:.2f}x")
        print(f"Cash Balance:    ${cash:,.2f}")
        print()

        # Check results
        if cash < 0:
            print("❌ NEGATIVE CASH - Equity not adjusted for intraday P&L!")
        else:
            print("✅ POSITIVE CASH - Equity correctly adjusted!")

        if leverage > 1.01:
            print(f"❌ LEVERAGE {leverage:.2f}x - Indicates borrowing (should be ≤1.0 for long-only)")
        elif leverage > 0.99:
            print(f"✅ LEVERAGE {leverage:.2f}x - Fully invested")
        else:
            print(f"✅ LEVERAGE {leverage:.2f}x - Partially invested")

        print("=" * 80)

asyncio.run(test_individual())
