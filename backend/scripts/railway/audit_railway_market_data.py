#!/usr/bin/env python3
"""
Railway Market Data Audit Script
Assesses market data storage (company profiles, prices, factor ETFs)
"""
import requests
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


def test_historical_prices(portfolio_id: str, symbols: List[str], token: str):
    """Test historical prices endpoint with detailed per-symbol breakdown"""
    print(f"\n📈 Testing Historical Prices - Detailed Per-Position Coverage")
    print(f"=" * 80)

    response = requests.get(
        f"{RAILWAY_URL}/data/prices/historical/{portfolio_id}",
        headers={"Authorization": f"Bearer {token}"},
        params={
            "lookback_days": 90,  # Increased to see more data
            "interval": "daily"
        }
    )

    if response.status_code == 200:
        prices = response.json()
        print(f"✅ Historical Prices: {response.status_code}\n")

        # Get timeseries data per symbol
        timeseries = prices.get("timeseries", {})

        # Build detailed coverage report
        coverage_report = []

        for symbol in sorted(symbols):
            symbol_data = timeseries.get(symbol, [])

            if symbol_data:
                # Calculate date range
                dates = [entry.get("date") for entry in symbol_data if entry.get("date")]
                if dates:
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

        for entry in coverage_report:
            symbol = entry["symbol"]
            status = entry["status"]
            days = entry["days"]
            first = entry["first_date"] or "N/A"
            last = entry["last_date"] or "N/A"

            print(f"{symbol:<12} {status:<6} {days:<6} {first:<12} {last:<12}")

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
        params={"lookback_days": 90}
    )

    if response.status_code == 200:
        factors = response.json()
        print(f"✅ Factor ETF Prices: {response.status_code}")

        etfs = factors.get("factor_etfs", [])
        print(f"   Factor ETFs tracked: {len(etfs)}")

        for etf in etfs[:5]:  # Show first 5
            symbol = etf.get("symbol", "N/A")
            data_points = len(etf.get("prices", []))
            print(f"      {symbol}: {data_points} data points")

        return factors
    else:
        print(f"❌ Factor ETF Prices: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return None


def test_company_profiles(symbols: List[str], token: str):
    """Test if company profiles exist (indirect via position details)"""
    print(f"\n🏢 Testing Company Profile Data")
    print(f"=" * 80)

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

        print(f"   With company name: {with_company_name} ({with_company_name/len(positions)*100:.1f}%)")
        print(f"   Missing company name: {without_company_name} ({without_company_name/len(positions)*100:.1f}%)")

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

    # Test each market data endpoint
    results = {}

    # 1. Company Profiles
    results["company_profiles"] = test_company_profiles(symbols, token)

    # 2. Market Quotes
    results["market_quotes"] = test_market_quotes(symbols, token)

    # 3. Historical Prices (with detailed per-symbol coverage)
    portfolios = requests.get(
        f"{RAILWAY_URL}/data/portfolios",
        headers={"Authorization": f"Bearer {token}"}
    ).json()
    portfolio_id = portfolios[0]["id"] if portfolios else None

    if portfolio_id:
        results["historical_prices"] = test_historical_prices(portfolio_id, symbols, token)

    # 4. Factor ETF Prices
    results["factor_etfs"] = test_factor_etf_prices(token)

    # Summary
    print(f"\n\n{'='*80}")
    print(f"📊 MARKET DATA AUDIT SUMMARY")
    print(f"{'='*80}")

    if results.get("company_profiles"):
        cp = results["company_profiles"]
        print(f"Company Profiles: {cp['with_profile']}/{cp['total']} ({cp['with_profile']/cp['total']*100:.1f}%)")

    if results.get("market_quotes"):
        print(f"Market Quotes: ✅ Working")
    else:
        print(f"Market Quotes: ❌ Not available")

    if results.get("historical_prices"):
        hp = results["historical_prices"]
        summary = hp.get("summary", {})
        total = summary.get("total_symbols", 0)
        with_data = summary.get("with_data", 0)
        avg_days = summary.get("avg_days", 0)
        print(f"Historical Prices: {with_data}/{total} symbols with data ({avg_days:.1f} avg days)")
    else:
        print(f"Historical Prices: ❌ Not available")

    if results.get("factor_etfs"):
        fe = results["factor_etfs"]
        etf_count = len(fe.get("factor_etfs", []))
        print(f"Factor ETFs: {etf_count} tracked")
    else:
        print(f"Factor ETFs: ❌ Not available")

    print(f"\n✅ Market data audit complete!")


if __name__ == "__main__":
    main()
