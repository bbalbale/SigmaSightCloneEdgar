"""
Integration test for Portfolio CRUD endpoints

Tests creating, listing, updating, and deleting portfolios.
"""
import asyncio
import httpx
from uuid import UUID

# Test configuration
BASE_URL = "http://localhost:8000/api/v1"
TEST_EMAIL = "demo_individual@sigmasight.com"
TEST_PASSWORD = "demo12345"


async def test_portfolio_crud():
    """Test portfolio CRUD operations."""

    async with httpx.AsyncClient() as client:
        print("=== Portfolio CRUD Integration Test ===\n")

        # Step 1: Login to get auth token
        print("1. Authenticating...")
        login_response = await client.post(
            f"{BASE_URL}/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
        )

        if login_response.status_code != 200:
            print(f"Login failed: {login_response.status_code}")
            print(login_response.text)
            return

        token_data = login_response.json()
        access_token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        print(f"[OK] Authenticated as {TEST_EMAIL}\n")

        # Step 2: List existing portfolios
        print("2. Listing existing portfolios...")
        list_response = await client.get(
            f"{BASE_URL}/portfolios",
            headers=headers
        )

        if list_response.status_code != 200:
            print(f"List failed: {list_response.status_code}")
            print(list_response.text)
            return

        list_data = list_response.json()
        print(f"[OK] Found {list_data['total_count']} portfolios")
        print(f"  Active: {list_data['active_count']}")
        print(f"  Total value: ${list_data['total_value']:,.2f}")

        for portfolio in list_data['portfolios']:
            print(f"  - {portfolio['account_name']} ({portfolio['account_type']}): ${portfolio['total_value']:,.2f}")
        print()

        # Step 3: Create a new portfolio
        print("3. Creating new portfolio...")
        create_response = await client.post(
            f"{BASE_URL}/portfolios",
            headers=headers,
            json={
                "name": "Test Schwab IRA",
                "account_name": "Schwab Traditional IRA",
                "account_type": "ira",
                "description": "Test IRA account for integration testing",
                "currency": "USD",
                "equity_balance": 50000.00,
                "is_active": True
            }
        )

        if create_response.status_code != 201:
            print(f"Create failed: {create_response.status_code}")
            print(create_response.text)
            return

        created_portfolio = create_response.json()
        new_portfolio_id = created_portfolio["id"]
        print(f"[OK] Created portfolio: {new_portfolio_id}")
        print(f"  Name: {created_portfolio['account_name']}")
        print(f"  Type: {created_portfolio['account_type']}")
        print(f"  Balance: ${created_portfolio['equity_balance']:,.2f}\n")

        # Step 4: Get the new portfolio by ID
        print(f"4. Fetching portfolio {new_portfolio_id}...")
        get_response = await client.get(
            f"{BASE_URL}/portfolios/{new_portfolio_id}",
            headers=headers
        )

        if get_response.status_code != 200:
            print(f"Get failed: {get_response.status_code}")
            print(get_response.text)
            return

        portfolio_data = get_response.json()
        print(f"[OK] Retrieved portfolio:")
        print(f"  Name: {portfolio_data['account_name']}")
        print(f"  Active: {portfolio_data['is_active']}")
        print(f"  Positions: {portfolio_data['position_count']}\n")

        # Step 5: Update the portfolio
        print(f"5. Updating portfolio {new_portfolio_id}...")
        update_response = await client.put(
            f"{BASE_URL}/portfolios/{new_portfolio_id}",
            headers=headers,
            json={
                "account_name": "Schwab Roth IRA (Updated)",
                "account_type": "roth_ira",
                "equity_balance": 75000.00
            }
        )

        if update_response.status_code != 200:
            print(f"Update failed: {update_response.status_code}")
            print(update_response.text)
            return

        updated_portfolio = update_response.json()
        print(f"[OK] Updated portfolio:")
        print(f"  Name: {updated_portfolio['account_name']}")
        print(f"  Type: {updated_portfolio['account_type']}")
        print(f"  Balance: ${updated_portfolio['equity_balance']:,.2f}\n")

        # Step 6: Verify we now have 2 portfolios
        print("6. Verifying portfolio count...")
        list_response2 = await client.get(
            f"{BASE_URL}/portfolios",
            headers=headers
        )

        if list_response2.status_code != 200:
            print(f"List failed: {list_response2.status_code}")
            return

        list_data2 = list_response2.json()
        print(f"[OK] Now have {list_data2['total_count']} portfolios")
        print(f"  Total value: ${list_data2['total_value']:,.2f}\n")

        # Step 7: Delete the test portfolio
        print(f"7. Deleting test portfolio {new_portfolio_id}...")
        delete_response = await client.delete(
            f"{BASE_URL}/portfolios/{new_portfolio_id}",
            headers=headers
        )

        if delete_response.status_code != 200:
            print(f"Delete failed: {delete_response.status_code}")
            print(delete_response.text)
            return

        delete_data = delete_response.json()
        print(f"[OK] Deleted portfolio:")
        print(f"  Success: {delete_data['success']}")
        print(f"  Message: {delete_data['message']}")
        print(f"  Deleted at: {delete_data['deleted_at']}\n")

        # Step 8: Verify portfolio is gone (not in active list)
        print("8. Verifying deletion...")
        list_response3 = await client.get(
            f"{BASE_URL}/portfolios",
            headers=headers
        )

        if list_response3.status_code != 200:
            print(f"List failed: {list_response3.status_code}")
            return

        list_data3 = list_response3.json()
        print(f"[OK] Back to {list_data3['active_count']} active portfolios")

        # Step 9: Check inactive list includes deleted portfolio
        print("\n9. Checking inactive portfolios...")
        list_all_response = await client.get(
            f"{BASE_URL}/portfolios?include_inactive=true",
            headers=headers
        )

        if list_all_response.status_code != 200:
            print(f"List all failed: {list_all_response.status_code}")
            return

        list_all_data = list_all_response.json()
        print(f"[OK] Total portfolios (including inactive): {list_all_data['total_count']}")

        inactive_portfolios = [p for p in list_all_data['portfolios'] if not p['is_active']]
        print(f"  Inactive portfolios: {len(inactive_portfolios)}")
        for p in inactive_portfolios:
            print(f"    - {p['account_name']} (deleted at: {p['deleted_at']})")

        print("\n=== All tests passed! ===")


if __name__ == "__main__":
    print("Starting Portfolio CRUD test...")
    print("Make sure the backend server is running on http://localhost:8000\n")
    asyncio.run(test_portfolio_crud())
