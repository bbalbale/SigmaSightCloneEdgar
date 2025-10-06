#!/usr/bin/env python3
"""
Railway Market Data Audit Script
Assesses market data storage (company profiles, prices, factor ETFs)
"""
import requests
import json
from typing import Dict, Any, List

RAILWAY_URL = "https://sigmasight-be-production.up.railway.app/api/v1"


def login() -> str:
    """Login with demo_hnw user"""
    response = requests.post(
        f"{RAILWAY_URL}/auth/login",
        json={"email": "demo_hnw@sigmasight.com", "password": "demo12345"}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed: {response.status_code}")
        return None


def get_portfolio_symbols(token: str) -> List[str]:
    """Get all symbols from demo_hnw portfolio"""
    # Get portfolio
    portfolios = requests.get(
        f"{RAILWAY_URL}/data/portfolios",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    if not portfolios:
        return []

    portfolio_id = portfolios[0]["id"]

    # Get complete portfolio data
    complete = requests.get(
        f"{RAILWAY_URL}/data/portfolio/{portfolio_id}/complete",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    holdings = complete.get("holdings", [])
    symbols = [h["symbol"] for h in holdings if h.get("symbol")]

    return list(set(symbols))  # Unique symbols


def test_market_quotes(symbols: List[str], token: str):
    """Test market quotes endpoint"""
    print(f"\n📊 Testing Market Quotes Endpoint")
    print(f"=" * 80)

    # Test with first 5 symbols
    test_symbols = symbols[:5]
    symbols_str = ",".join(test_symbols)

    response = requests.get(
        f"{RAILWAY_URL}/data/prices/quotes",
        headers={"Authorization": f"Bearer {token}"},
        params={"symbols": symbols_str}
    )

    if response.status_code == 200:
        quotes = response.json()
        print(f"✅ Market Quotes: {response.status_code}")
        print(f"   Requested: {len(test_symbols)} symbols")
        print(f"   Received: {len(quotes.get('quotes', []))} quotes")

        # Show sample
        if quotes.get("quotes"):
            sample = quotes["quotes"][0]
            print(f"\n   Sample quote for {sample.get('symbol', 'N/A')}:")
            print(f"      Price: ${sample.get('price', 0)}")
            print(f"      Change: {sample.get('change_percent', 0):.2f}%")
            print(f"      Volume: {sample.get('volume', 0):,}")

        return quotes
    else:
        print(f"❌ Market Quotes: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return None


def test_historical_prices(portfolio_id: str, symbols: List[str], token: str, report_file=None):
    """Test historical prices endpoint with detailed per-symbol breakdown"""
    print(f"\n📈 Testing Historical Prices - Detailed Per-Position Coverage")
    print(f"=" * 80)

    if report_file:
        report_file.write(f"\n📈 HISTORICAL PRICES - DETAILED PER-POSITION COVERAGE\n")
        report_file.write(f"{'='*80}\n")

    response = requests.get(
        f"{RAILWAY_URL}/data/prices/historical/{portfolio_id}",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "lookback_days": 252,  # One trading year of data
            "interval": "daily"
        }
    )

    if response.status_code == 200:
        prices = response.json()
        print(f"✅ Historical Prices: {response.status_code}\n")

        # Get timeseries data per symbol
        timeseries = prices.get("symbols", {})

        # Build detailed coverage report
        coverage_report = []

        for symbol in sorted(symbols):
            symbol_data = timeseries.get(symbol, {})

            # API returns {dates: [...], open: [...], close: [...], ...}
            # Not a list of objects
            if symbol_data and symbol_data.get("dates"):
                dates = symbol_data["dates"]
                min_date = min(dates)
                max_date = max(dates)
                days_count = len(dates)

                coverage_report.append({
                    "symbol": symbol,
                    "days": days_count,
                    "first_date": min_date,
                    "last_date": max_date,
                    "status": "✅"
                })
            else:
                coverage_report.append({
                    "symbol": symbol,
                    "days": 0,
                    "first_date": None,
                    "last_date": None,
                    "status": "❌"
                })

        # Print detailed table
        print(f"{'SYMBOL':<12} {'STATUS':<6} {'DAYS':<6} {'FIRST DATE':<12} {'LAST DATE':<12}")
        print(f"{'-'*12} {'-'*6} {'-'*6} {'-'*12} {'-'*12}")

        if report_file:
            report_file.write(f"\n{'SYMBOL':<12} {'STATUS':<6} {'DAYS':<6} {'FIRST DATE':<12} {'LAST DATE':<12}\n")
            report_file.write(f"{'-'*12} {'-'*6} {'-'*6} {'-'*12} {'-'*12}\n")

        for entry in coverage_report:
            symbol = entry["symbol"]
            status = entry["status"]
            days = entry["days"]
            first = entry["first_date"] or "N/A"
            last = entry["last_date"] or "N/A"

            line = f"{symbol:<12} {status:<6} {days:<6} {first:<12} {last:<12}"
            print(line)
            if report_file:
                report_file.write(line + "\n")

        # Summary stats
        with_data = sum(1 for e in coverage_report if e["days"] > 0)
        without_data = len(coverage_report) - with_data
        avg_days = sum(e["days"] for e in coverage_report) / len(coverage_report) if coverage_report else 0

        print(f"\n{'='*80}")
        print(f"HISTORICAL DATA SUMMARY:")
        print(f"   Total Symbols: {len(coverage_report)}")
        print(f"   With Data: {with_data} ({with_data/len(coverage_report)*100:.1f}%)")
        print(f"   Missing Data: {without_data} ({without_data/len(coverage_report)*100:.1f}%)")
        print(f"   Average Days per Symbol: {avg_days:.1f}")

        if report_file:
            report_file.write(f"\n{'='*80}\n")
            report_file.write(f"HISTORICAL DATA SUMMARY:\n")
            report_file.write(f"   Total Symbols: {len(coverage_report)}\n")
            report_file.write(f"   With Data: {with_data} ({with_data/len(coverage_report)*100:.1f}%)\n")
            report_file.write(f"   Missing Data: {without_data} ({without_data/len(coverage_report)*100:.1f}%)\n")
            report_file.write(f"   Average Days per Symbol: {avg_days:.1f}\n")

        return {
            "coverage_report": coverage_report,
            "summary": {
                "total_symbols": len(coverage_report),
                "with_data": with_data,
                "without_data": without_data,
                "avg_days": avg_days
            }
        }
    else:
        print(f"❌ Historical Prices: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return None


def test_factor_etf_prices(token: str):
    """Test factor ETF prices endpoint"""
    print(f"\n🏭 Testing Factor ETF Prices Endpoint")
    print(f"=" * 80)

    response = requests.get(
        f"{RAILWAY_URL}/data/factors/etf-prices",
        headers={"Authorization": f"Bearer {token}"},
        params={"lookback_days": 252}
    )

    if response.status_code == 200:
        factors = response.json()
        print(f"✅ Factor ETF Prices: {response.status_code}")

        # API returns {metadata: {...}, data: {symbol: {...}, ...}}
        etf_data = factors.get("data", {})
        print(f"   Factor ETFs tracked: {len(etf_data)}")

        for symbol, data in list(etf_data.items())[:5]:  # Show first 5
            factor_name = data.get("factor_name", "N/A")
            current_price = data.get("current_price", 0)
            print(f"      {symbol} ({factor_name}): ${current_price:.2f}")

        return factors
    else:
        print(f"❌ Factor ETF Prices: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return None


def test_company_profiles(symbols: List[str], token: str, report_file=None):
    """Test if company profiles exist (indirect via position details)"""
    print(f"\n🏢 Testing Company Profile Data")
    print(f"=" * 80)

    if report_file:
        report_file.write(f"\n🏢 COMPANY PROFILE DATA\n")
        report_file.write(f"{'='*80}\n")

    # Get portfolios to find portfolio_id
    portfolios = requests.get(
        f"{RAILWAY_URL}/data/portfolios",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    if not portfolios:
        print(f"❌ No portfolios found")
        return None

    portfolio_id = portfolios[0]["id"]

    # Get position details (includes company_name from company_profiles)
    response = requests.get(
        f"{RAILWAY_URL}/data/positions/details",
        headers={"Authorization": f"Bearer {token}"},
        params={"portfolio_id": portfolio_id}
    )

    if response.status_code == 200:
        data = response.json()
        positions = data.get("positions", [])

        print(f"✅ Position Details: {response.status_code}")
        print(f"   Total positions: {len(positions)}")

        with_company_name = sum(1 for p in positions if p.get("company_name"))
        without_company_name = len(positions) - with_company_name

        coverage_pct = (with_company_name/len(positions)*100) if positions else 0

        print(f"   With company name: {with_company_name} ({coverage_pct:.1f}%)")
        print(f"   Missing company name: {without_company_name} ({100-coverage_pct:.1f}%)")

        if report_file:
            report_file.write(f"Total positions: {len(positions)}\n")
            report_file.write(f"With company name: {with_company_name} ({coverage_pct:.1f}%)\n")
            report_file.write(f"Missing company name: {without_company_name} ({100-coverage_pct:.1f}%)\n")

        if with_company_name > 0:
            sample = next((p for p in positions if p.get("company_name")), None)
            if sample:
                print(f"\n   Sample:")
                print(f"      {sample['symbol']}: {sample.get('company_name', 'N/A')}")

        return {
            "total": len(positions),
            "with_profile": with_company_name,
            "without_profile": without_company_name
        }
    else:
        print(f"❌ Position Details: {response.status_code}")
        return None


def main():
    """Main market data audit"""
    print("🚀 Railway Market Data Audit")
    print(f"Backend: {RAILWAY_URL}\n")

    # Open output file for detailed report
    report_filename = "railway_market_data_audit_report.txt"

    with open(report_filename, "w", encoding="utf-8") as report:
        from datetime import datetime
        report.write("=" * 80 + "\n")
        report.write("RAILWAY MARKET DATA AUDIT - DETAILED REPORT\n")
        report.write("=" * 80 + "\n")
        report.write(f"Backend: {RAILWAY_URL}\n")
        report.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Login
        print("🔐 Logging in...")
        token = login()
        if not token:
            return

        print("✅ Authenticated\n")

        # Get portfolio symbols
        print("📋 Fetching portfolio symbols...")
        symbols = get_portfolio_symbols(token)
        print(f"✅ Found {len(symbols)} unique symbols\n")
        print(f"   Symbols: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}\n")

        report.write(f"Total Unique Symbols: {len(symbols)}\n")
        report.write(f"Symbols: {', '.join(symbols)}\n\n")

        # Test each market data endpoint
        results = {}

        # 1. Company Profiles
        results["company_profiles"] = test_company_profiles(symbols, token, report)

        # 2. Market Quotes
        results["market_quotes"] = test_market_quotes(symbols, token)

        # 3. Historical Prices (with detailed per-symbol coverage)
        portfolios = requests.get(
            f"{RAILWAY_URL}/data/portfolios",
            headers={"Authorization": f"Bearer {token}"}
        ).json()
        portfolio_id = portfolios[0]["id"] if portfolios else None

        if portfolio_id:
            results["historical_prices"] = test_historical_prices(portfolio_id, symbols, token, report)

        # 4. Factor ETF Prices
        results["factor_etfs"] = test_factor_etf_prices(token)

        # Summary
        print(f"\n\n{'='*80}")
        print(f"📊 MARKET DATA AUDIT SUMMARY")
        print(f"{'='*80}")

        report.write(f"\n\n{'='*80}\n")
        report.write(f"MARKET DATA AUDIT SUMMARY\n")
        report.write(f"{'='*80}\n")

        summary_lines = []

        if results.get("company_profiles"):
            cp = results["company_profiles"]
            line = f"Company Profiles: {cp['with_profile']}/{cp['total']} ({cp['with_profile']/cp['total']*100:.1f}%)"
            summary_lines.append(line)

        if results.get("market_quotes"):
            summary_lines.append("Market Quotes: ✅ Working")
        else:
            summary_lines.append("Market Quotes: ❌ Not available")

        if results.get("historical_prices"):
            hp = results["historical_prices"]
            summary = hp.get("summary", {})
            total = summary.get("total_symbols", 0)
            with_data = summary.get("with_data", 0)
            avg_days = summary.get("avg_days", 0)
            line = f"Historical Prices: {with_data}/{total} symbols with data ({avg_days:.1f} avg days)"
            summary_lines.append(line)
        else:
            summary_lines.append("Historical Prices: ❌ Not available")

        if results.get("factor_etfs"):
            fe = results["factor_etfs"]
            etf_count = len(fe.get("data", {}))
            line = f"Factor ETFs: {etf_count} tracked"
            summary_lines.append(line)
        else:
            summary_lines.append("Factor ETFs: ❌ Not available")

        for line in summary_lines:
            print(line)
            report.write(line + "\n")

    # Save JSON results
    json_filename = "railway_market_data_audit_results.json"
    with open(json_filename, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Market data audit complete!")
    print(f"   - JSON results: {json_filename}")
    print(f"   - Detailed report: {report_filename}")


if __name__ == "__main__":
    main()
