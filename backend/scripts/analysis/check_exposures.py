"""Check full overview data including exposures"""
import asyncio
import httpx
import json

async def check_overview():
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

        print("=" * 80)
        print("INDIVIDUAL INVESTOR PORTFOLIO - FULL OVERVIEW")
        print("=" * 80)
        print()

        print(f"Equity Balance:  ${data.get('equity_balance'):,.2f}")
        print(f"Total Value:     ${data.get('total_value'):,.2f}")
        print(f"Cash Balance:    ${data.get('cash_balance'):,.2f}")
        print(f"Leverage:        {data.get('leverage'):.2f}x")
        print()

        exposures = data.get('exposures', {})
        print("EXPOSURES:")
        print(f"  Long Exposure:   ${exposures.get('long_exposure'):,.2f}  ({exposures.get('long_percentage'):.1f}%)")
        print(f"  Short Exposure:  ${exposures.get('short_exposure'):,.2f}  ({exposures.get('short_percentage'):.1f}%)")
        print(f"  Gross Exposure:  ${exposures.get('gross_exposure'):,.2f}  ({exposures.get('gross_percentage'):.1f}%)")
        print(f"  Net Exposure:    ${exposures.get('net_exposure'):,.2f}  ({exposures.get('net_percentage'):.1f}%)")
        print()

        pnl = data.get('pnl', {})
        print("P&L:")
        print(f"  Total P&L:       ${pnl.get('total_pnl'):,.2f}")
        print(f"  Unrealized P&L:  ${pnl.get('unrealized_pnl'):,.2f}")
        print(f"  Realized P&L:    ${pnl.get('realized_pnl'):,.2f}")
        print()

        print("=" * 80)
        print()
        print("VALIDATION:")
        print(f"  Gross Exposure + Cash = ${exposures.get('gross_exposure') + data.get('cash_balance'):,.2f}")
        print(f"  Should Equal Equity   = ${data.get('equity_balance'):,.2f}")
        print(f"  Match: {'✅' if abs((exposures.get('gross_exposure') + data.get('cash_balance')) - data.get('equity_balance')) < 1.0 else '❌'}")
        print("=" * 80)

asyncio.run(check_overview())
