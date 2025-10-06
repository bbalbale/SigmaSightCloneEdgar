#!/usr/bin/env python3
"""
Railway Database Audit Script
Uses raw data APIs to assess what data exists in Railway production database
"""
import requests
import json
from typing import Dict, Any

RAILWAY_URL = "https://sigmasight-be-production.up.railway.app/api/v1"

# Demo credentials
DEMO_USERS = [
    {"email": "demo_individual@sigmasight.com", "password": "demo12345", "name": "Individual"},
    {"email": "demo_hnw@sigmasight.com", "password": "demo12345", "name": "HNW"},
    {"email": "demo_hedgefundstyle@sigmasight.com", "password": "demo12345", "name": "Hedge Fund"}
]


def login(email: str, password: str) -> Dict[str, Any]:
    """Login and get access token"""
    response = requests.post(
        f"{RAILWAY_URL}/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Login failed for {email}: {response.status_code}")
        return None


def get_portfolios(token: str) -> list:
    """Get all portfolios for user"""
    response = requests.get(
        f"{RAILWAY_URL}/data/portfolios",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get portfolios: {response.status_code}")
        return []


def get_portfolio_complete(portfolio_id: str, token: str) -> Dict[str, Any]:
    """Get complete portfolio data"""
    response = requests.get(
        f"{RAILWAY_URL}/data/portfolio/{portfolio_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "include_holdings": True,
            "include_position_tags": True,
            "include_timeseries": False,
            "include_attrib": False
        }
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get portfolio complete: {response.status_code}")
        return {}


def get_data_quality(portfolio_id: str, token: str) -> Dict[str, Any]:
    """Get data quality metrics"""
    response = requests.get(
        f"{RAILWAY_URL}/data/portfolio/{portfolio_id}/data-quality",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get data quality: {response.status_code}")
        return {}


def audit_portfolio(portfolio: Dict[str, Any], token: str) -> Dict[str, Any]:
    """Comprehensive audit of a single portfolio"""
    portfolio_id = portfolio["id"]
    portfolio_name = portfolio["name"]

    print(f"\n{'='*80}")
    print(f"📊 PORTFOLIO: {portfolio_name}")
    print(f"{'='*80}")
    print(f"ID: {portfolio_id}")
    print(f"Position Count: {portfolio.get('position_count', 0)}")
    print(f"Total Value: ${portfolio.get('total_value', 0):,.2f}")
    print(f"Equity Balance: ${portfolio.get('equity_balance', 0):,.2f}")
    print(f"Market Value: ${portfolio.get('total_market_value', 0):,.2f}")

    # Get complete portfolio data
    print(f"\n📦 Fetching complete portfolio data...")
    complete_data = get_portfolio_complete(portfolio_id, token)

    audit_results = {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio_name,
        "total_value": portfolio.get("total_value", 0),
        "position_count": portfolio.get("position_count", 0)
    }

    if complete_data:
        holdings = complete_data.get("holdings", [])
        print(f"✅ Holdings: {len(holdings)} positions")

        # Analyze position types
        position_types = {}
        investment_classes = {}
        positions_with_company_name = 0
        positions_with_last_price = 0

        for holding in holdings:
            # Position type
            pos_type = holding.get("position_type", "UNKNOWN")
            position_types[pos_type] = position_types.get(pos_type, 0) + 1

            # Investment class
            inv_class = holding.get("investment_class", "UNKNOWN")
            investment_classes[inv_class] = investment_classes.get(inv_class, 0) + 1

            # Data completeness
            if holding.get("company_name"):
                positions_with_company_name += 1
            if holding.get("last_price"):
                positions_with_last_price += 1

        print(f"\n📈 Position Types:")
        for ptype, count in sorted(position_types.items()):
            print(f"   {ptype}: {count}")

        print(f"\n💼 Investment Classes:")
        for iclass, count in sorted(investment_classes.items()):
            print(f"   {iclass}: {count}")

        print(f"\n🏢 Data Coverage:")
        print(f"   Company Names: {positions_with_company_name}/{len(holdings)} ({positions_with_company_name/len(holdings)*100:.1f}%)")
        print(f"   Last Prices: {positions_with_last_price}/{len(holdings)} ({positions_with_last_price/len(holdings)*100:.1f}%)")

        # Check tags
        position_tags = complete_data.get("position_tags", [])
        if position_tags:
            print(f"\n🏷️  Position Tags: {len(position_tags)} tag assignments")
            unique_tags = set(tag.get("tag_name") for tag in position_tags if tag.get("tag_name"))
            print(f"   Unique Tags: {len(unique_tags)}")
            print(f"   Tags: {', '.join(sorted(unique_tags)[:10])}{'...' if len(unique_tags) > 10 else ''}")

        audit_results.update({
            "position_types": position_types,
            "investment_classes": investment_classes,
            "company_name_coverage": f"{positions_with_company_name}/{len(holdings)}",
            "price_coverage": f"{positions_with_last_price}/{len(holdings)}",
            "tag_count": len(position_tags),
            "unique_tags": len(unique_tags) if position_tags else 0
        })

    # Get data quality
    print(f"\n🔍 Checking data quality...")
    data_quality = get_data_quality(portfolio_id, token)

    if data_quality:
        quality_summary = data_quality.get("summary", {})
        print(f"✅ Data Quality Report:")
        print(f"   Total Positions: {quality_summary.get('total_positions', 0)}")
        print(f"   With Greeks: {quality_summary.get('positions_with_greeks', 0)}")
        print(f"   With Factors: {quality_summary.get('positions_with_factors', 0)}")
        print(f"   Completeness: {quality_summary.get('data_completeness_percent', 0):.1f}%")

        audit_results["data_quality"] = quality_summary

    return audit_results


def main():
    """Main audit routine"""
    print("🚀 Railway Database Audit")
    print(f"Backend: {RAILWAY_URL}")
    print(f"Users to audit: {len(DEMO_USERS)}\n")

    all_results = []

    for user_info in DEMO_USERS:
        print(f"\n{'#'*80}")
        print(f"👤 USER: {user_info['name']} ({user_info['email']})")
        print(f"{'#'*80}")

        # Login
        auth_data = login(user_info["email"], user_info["password"])
        if not auth_data:
            continue

        token = auth_data["access_token"]
        print(f"✅ Logged in successfully")

        # Get portfolios
        portfolios = get_portfolios(token)
        if not portfolios:
            print(f"⚠️  No portfolios found for user")
            continue

        print(f"✅ Found {len(portfolios)} portfolio(s)")

        # Audit each portfolio
        for portfolio in portfolios:
            results = audit_portfolio(portfolio, token)
            results["user"] = user_info["name"]
            all_results.append(results)

    # Summary
    print(f"\n\n{'='*80}")
    print(f"📊 AUDIT SUMMARY")
    print(f"{'='*80}")

    total_portfolios = len(all_results)
    total_positions = sum(r.get("position_count", 0) for r in all_results)
    total_value = sum(r.get("total_value", 0) for r in all_results)

    print(f"Total Portfolios: {total_portfolios}")
    print(f"Total Positions: {total_positions}")
    print(f"Total Value: ${total_value:,.2f}")

    # Save results
    output_file = "railway_audit_results.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n✅ Audit complete! Results saved to: {output_file}")


if __name__ == "__main__":
    main()
