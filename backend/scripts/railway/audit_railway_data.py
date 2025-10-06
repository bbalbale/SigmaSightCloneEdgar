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


def audit_portfolio(portfolio: Dict[str, Any], token: str, report_file=None) -> Dict[str, Any]:
    """Comprehensive audit of a single portfolio"""
    portfolio_id = portfolio["id"]
    portfolio_name = portfolio["name"]

    # Print to console
    print(f"\n{'='*80}")
    print(f"📊 PORTFOLIO: {portfolio_name}")
    print(f"{'='*80}")
    print(f"ID: {portfolio_id}")
    print(f"Position Count: {portfolio.get('position_count', 0)}")
    print(f"Total Value: ${portfolio.get('total_value', 0):,.2f}")
    print(f"Equity Balance: ${portfolio.get('equity_balance', 0):,.2f}")
    print(f"Market Value: ${portfolio.get('total_market_value', 0):,.2f}")

    # Write to report file if provided
    if report_file:
        report_file.write(f"\n{'='*120}\n")
        report_file.write(f"PORTFOLIO: {portfolio_name}\n")
        report_file.write(f"{'='*120}\n")
        report_file.write(f"ID: {portfolio_id}\n")
        report_file.write(f"Position Count: {portfolio.get('position_count', 0)}\n")
        report_file.write(f"Total Value: ${portfolio.get('total_value', 0):,.2f}\n")
        report_file.write(f"Equity Balance: ${portfolio.get('equity_balance', 0):,.2f}\n")
        report_file.write(f"Market Value: ${portfolio.get('total_market_value', 0):,.2f}\n")

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

        # Print detailed position table
        print(f"\n{'─'*120}")
        print(f"DETAILED POSITION LIST")
        print(f"{'─'*120}")
        print(f"{'#':<3} {'SYMBOL':<16} {'TYPE':<6} {'QTY':<10} {'ENTRY $':<10} {'LAST $':<10} {'MKT VAL':<12} {'P&L $':<12} {'ENTRY DATE':<12}")
        print(f"{'─'*120}")

        # Write to report file
        if report_file:
            report_file.write(f"\n{'─'*120}\n")
            report_file.write(f"DETAILED POSITION LIST\n")
            report_file.write(f"{'─'*120}\n")
            report_file.write(f"{'#':<3} {'SYMBOL':<16} {'TYPE':<6} {'QTY':<10} {'ENTRY $':<10} {'LAST $':<10} {'MKT VAL':<12} {'P&L $':<12} {'ENTRY DATE':<12}\n")
            report_file.write(f"{'─'*120}\n")

        for i, holding in enumerate(holdings, 1):
            symbol = holding.get("symbol", "N/A")[:16]
            pos_type = holding.get("position_type", "N/A")[:6]
            quantity = holding.get("quantity", 0)
            entry_price = holding.get("entry_price", 0)
            last_price = holding.get("last_price", 0)
            market_value = holding.get("market_value", 0)
            unrealized_pnl = holding.get("unrealized_pnl", 0)
            entry_date = holding.get("entry_date", "N/A")[:10]

            # Format numbers
            qty_str = f"{quantity:,.2f}" if quantity else "N/A"
            entry_str = f"${entry_price:,.2f}" if entry_price else "N/A"
            last_str = f"${last_price:,.2f}" if last_price else "N/A"
            mkt_str = f"${market_value:,.2f}" if market_value else "N/A"
            pnl_str = f"${unrealized_pnl:,.2f}" if unrealized_pnl else "N/A"

            line = f"{i:<3} {symbol:<16} {pos_type:<6} {qty_str:<10} {entry_str:<10} {last_str:<10} {mkt_str:<12} {pnl_str:<12} {entry_date:<12}"
            print(line)
            if report_file:
                report_file.write(line + "\n")

        print(f"{'─'*120}")
        if report_file:
            report_file.write(f"{'─'*120}\n")

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

    # Open output file for detailed report
    report_filename = "railway_audit_detailed_report.txt"

    with open(report_filename, "w", encoding="utf-8") as report:
        from datetime import datetime
        report.write("=" * 120 + "\n")
        report.write("RAILWAY DATABASE AUDIT - DETAILED REPORT\n")
        report.write("=" * 120 + "\n")
        report.write(f"Backend: {RAILWAY_URL}\n")
        report.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for user_info in DEMO_USERS:
            print(f"\n{'#'*80}")
            print(f"👤 USER: {user_info['name']} ({user_info['email']})")
            print(f"{'#'*80}")

            report.write(f"\n{'#'*120}\n")
            report.write(f"USER: {user_info['name']} ({user_info['email']})\n")
            report.write(f"{'#'*120}\n")

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
                results = audit_portfolio(portfolio, token, report)
                results["user"] = user_info["name"]
                all_results.append(results)

        # Summary
        print(f"\n\n{'='*80}")
        print(f"📊 AUDIT SUMMARY")
        print(f"{'='*80}")

        report.write(f"\n\n{'='*120}\n")
        report.write(f"AUDIT SUMMARY\n")
        report.write(f"{'='*120}\n")

        total_portfolios = len(all_results)
        total_positions = sum(r.get("position_count", 0) for r in all_results)
        total_value = sum(r.get("total_value", 0) for r in all_results)

        summary_lines = [
            f"Total Portfolios: {total_portfolios}",
            f"Total Positions: {total_positions}",
            f"Total Value: ${total_value:,.2f}"
        ]

        for line in summary_lines:
            print(line)
            report.write(line + "\n")

    # Save results
    output_file = "railway_audit_results.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n✅ Audit complete!")
    print(f"   - JSON results: {output_file}")
    print(f"   - Detailed report: {report_filename}")


if __name__ == "__main__":
    main()
