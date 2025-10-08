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
    """Test company profiles endpoint - full access to all 53 fields"""
    print(f"\n🏢 Testing Company Profile Data - Full Table (All 53 Fields)")
    print(f"=" * 80)

    if report_file:
        report_file.write(f"\n🏢 COMPANY PROFILE DATA - COMPLETE FIELD COVERAGE (53 FIELDS)\n")
        report_file.write(f"{'='*120}\n")

    # Get portfolios to find portfolio_id
    portfolios = requests.get(
        f"{RAILWAY_URL}/data/portfolios",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    if not portfolios:
        print(f"❌ No portfolios found")
        return None

    portfolio_id = portfolios[0]["id"]

    # Use new company-profiles endpoint to get ALL fields
    response = requests.get(
        f"{RAILWAY_URL}/data/company-profiles",
        headers={"Authorization": f"Bearer {token}"},
        params={"portfolio_id": portfolio_id}
    )

    if response.status_code == 200:
        data = response.json()
        profiles = data.get("profiles", [])
        meta = data.get("meta", {})

        print(f"✅ Company Profiles: {response.status_code}")
        print(f"   Total requested: {len(meta.get('requested_symbols', []))}")
        print(f"   Profiles returned: {meta.get('returned_profiles', 0)}")
        print(f"   Missing profiles: {len(meta.get('missing_profiles', []))}")

        # Console: Show key fields table
        print(f"\n   SUMMARY TABLE (Key Fields):")
        print(f"   {'-'*130}")
        header = f"   {'SYMBOL':<12} {'COMPANY NAME':<40} {'SECTOR':<20} {'MARKET CAP':<15} {'PE':<8} {'BETA':<8}"
        print(header)
        print(f"   {'-'*130}")

        for profile in sorted(profiles, key=lambda x: x.get("symbol", "")):
            symbol = profile.get("symbol", "N/A")
            company_name = (profile.get("company_name") or "N/A")[:37]
            sector = (profile.get("sector") or "N/A")[:17]

            market_cap = profile.get("market_cap")
            if market_cap:
                mc_display = f"${market_cap/1e9:.1f}B"
            else:
                mc_display = "N/A"

            pe_ratio = profile.get("pe_ratio")
            pe_display = f"{pe_ratio:.2f}" if pe_ratio else "N/A"

            beta = profile.get("beta")
            beta_display = f"{beta:.3f}" if beta else "N/A"

            row = f"   {symbol:<12} {company_name:<40} {sector:<20} {mc_display:<15} {pe_display:<8} {beta_display:<8}"
            print(row)

        print(f"   {'-'*130}")

        # Report file: Complete field dump for each position
        if report_file:
            report_file.write(f"\nTOTAL SYMBOLS: {len(meta.get('requested_symbols', []))}\n")
            report_file.write(f"PROFILES RETURNED: {meta.get('returned_profiles', 0)}\n")
            report_file.write(f"MISSING PROFILES: {len(meta.get('missing_profiles', []))}\n\n")

            if meta.get('missing_profiles'):
                report_file.write(f"MISSING (No Public Data): {', '.join(meta['missing_profiles'])}\n\n")

            report_file.write(f"\n{'='*120}\n")
            report_file.write(f"COMPLETE COMPANY PROFILES - ALL FIELDS\n")
            report_file.write(f"{'='*120}\n\n")

            # Field groups for organization
            basic_fields = ['symbol', 'company_name', 'sector', 'industry', 'exchange', 'country', 'is_etf', 'is_fund']
            company_fields = ['ceo', 'employees', 'website', 'description']
            valuation_fields = ['market_cap', 'pe_ratio', 'forward_pe', 'forward_eps', 'dividend_yield', 'beta']
            price_fields = ['week_52_high', 'week_52_low']
            analyst_fields = ['target_mean_price', 'target_high_price', 'target_low_price',
                            'number_of_analyst_opinions', 'recommendation_mean', 'recommendation_key']
            profitability_fields = ['profit_margins', 'operating_margins', 'gross_margins',
                                   'return_on_assets', 'return_on_equity']
            growth_fields = ['earnings_growth', 'revenue_growth', 'earnings_quarterly_growth']
            revenue_fields = ['total_revenue']
            current_year_fields = ['current_year_revenue_avg', 'current_year_revenue_low',
                                  'current_year_revenue_high', 'current_year_revenue_growth',
                                  'current_year_earnings_avg', 'current_year_earnings_low',
                                  'current_year_earnings_high', 'current_year_end_date']
            next_year_fields = ['next_year_revenue_avg', 'next_year_revenue_low',
                               'next_year_revenue_high', 'next_year_revenue_growth',
                               'next_year_earnings_avg', 'next_year_earnings_low',
                               'next_year_earnings_high', 'next_year_end_date']

            for profile in sorted(profiles, key=lambda x: x.get("symbol", "")):
                symbol = profile.get("symbol", "N/A")

                report_file.write(f"\n{'─'*120}\n")
                report_file.write(f"SYMBOL: {symbol}\n")
                report_file.write(f"{'─'*120}\n")

                # Basic Info
                report_file.write(f"\nBASIC INFORMATION:\n")
                for field in basic_fields:
                    value = profile.get(field, "N/A")
                    report_file.write(f"  {field:30} {value}\n")

                # Company Details
                report_file.write(f"\nCOMPANY DETAILS:\n")
                for field in company_fields:
                    value = profile.get(field, "N/A")
                    if field == 'description' and value and value != "N/A":
                        # Truncate long descriptions
                        value = value[:200] + "..." if len(str(value)) > 200 else value
                    report_file.write(f"  {field:30} {value}\n")

                # Valuation Metrics
                report_file.write(f"\nVALUATION METRICS:\n")
                for field in valuation_fields:
                    value = profile.get(field, "N/A")
                    report_file.write(f"  {field:30} {value}\n")

                # Price Range
                report_file.write(f"\nPRICE RANGE (52-WEEK):\n")
                for field in price_fields:
                    value = profile.get(field, "N/A")
                    report_file.write(f"  {field:30} {value}\n")

                # Analyst Data
                report_file.write(f"\nANALYST CONSENSUS:\n")
                for field in analyst_fields:
                    value = profile.get(field, "N/A")
                    report_file.write(f"  {field:30} {value}\n")

                # Profitability Margins
                report_file.write(f"\nPROFITABILITY MARGINS:\n")
                for field in profitability_fields:
                    value = profile.get(field, "N/A")
                    report_file.write(f"  {field:30} {value}\n")

                # Growth Metrics
                report_file.write(f"\nGROWTH METRICS:\n")
                for field in growth_fields:
                    value = profile.get(field, "N/A")
                    report_file.write(f"  {field:30} {value}\n")

                # Revenue
                report_file.write(f"\nREVENUE:\n")
                for field in revenue_fields:
                    value = profile.get(field, "N/A")
                    report_file.write(f"  {field:30} {value}\n")

                # Current Year Estimates
                report_file.write(f"\nCURRENT YEAR ESTIMATES:\n")
                for field in current_year_fields:
                    value = profile.get(field, "N/A")
                    report_file.write(f"  {field:30} {value}\n")

                # Next Year Estimates
                report_file.write(f"\nNEXT YEAR ESTIMATES:\n")
                for field in next_year_fields:
                    value = profile.get(field, "N/A")
                    report_file.write(f"  {field:30} {value}\n")

            report_file.write(f"\n{'='*120}\n")

        # Calculate field coverage statistics
        field_coverage = {}
        all_fields = set()
        for profile in profiles:
            all_fields.update(profile.keys())

        # Remove 'symbol' from coverage calc (always present)
        all_fields.discard('symbol')

        for field in sorted(all_fields):
            count = sum(1 for p in profiles if p.get(field) is not None)
            pct = (count/len(profiles)*100) if profiles else 0
            field_coverage[field] = {"count": count, "percent": pct}

        # Print field coverage summary
        print(f"\n   FIELD COVERAGE STATISTICS ({len(all_fields)} data fields):")
        print(f"   {'-'*80}")

        # Group by coverage level
        high_coverage = {k: v for k, v in field_coverage.items() if v['percent'] >= 75}
        medium_coverage = {k: v for k, v in field_coverage.items() if 25 <= v['percent'] < 75}
        low_coverage = {k: v for k, v in field_coverage.items() if v['percent'] < 25}

        print(f"   High Coverage (≥75%): {len(high_coverage)} fields")
        for field in sorted(high_coverage.keys())[:5]:
            stats = high_coverage[field]
            print(f"      {field:30} {stats['count']:3}/{len(profiles):3} ({stats['percent']:5.1f}%)")
        if len(high_coverage) > 5:
            print(f"      ... and {len(high_coverage)-5} more")

        print(f"\n   Medium Coverage (25-74%): {len(medium_coverage)} fields")
        for field in sorted(medium_coverage.keys())[:5]:
            stats = medium_coverage[field]
            print(f"      {field:30} {stats['count']:3}/{len(profiles):3} ({stats['percent']:5.1f}%)")
        if len(medium_coverage) > 5:
            print(f"      ... and {len(medium_coverage)-5} more")

        print(f"\n   Low Coverage (<25%): {len(low_coverage)} fields")
        for field in sorted(low_coverage.keys())[:5]:
            stats = low_coverage[field]
            print(f"      {field:30} {stats['count']:3}/{len(profiles):3} ({stats['percent']:5.1f}%)")
        if len(low_coverage) > 5:
            print(f"      ... and {len(low_coverage)-5} more")

        if report_file:
            report_file.write(f"\nFIELD COVERAGE STATISTICS ({len(all_fields)} data fields):\n")
            report_file.write(f"{'─'*80}\n")

            for field in sorted(field_coverage.keys()):
                stats = field_coverage[field]
                report_file.write(f"{field:40} {stats['count']:3}/{len(profiles):3} ({stats['percent']:5.1f}%)\n")

        return {
            "total": len(meta.get('requested_symbols', [])),
            "with_profile": meta.get('returned_profiles', 0),
            "without_profile": len(meta.get('missing_profiles', [])),
            "coverage_percent": (meta.get('returned_profiles', 0)/len(meta.get('requested_symbols', []))*100) if meta.get('requested_symbols') else 0,
            "field_coverage": field_coverage,
            "profiles": profiles
        }
    else:
        print(f"❌ Company Profiles: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
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
