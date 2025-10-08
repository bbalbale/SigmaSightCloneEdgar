#!/usr/bin/env python3
"""
Railway Analytics Audit Script
Tests all /analytics/ endpoints across all 3 demo portfolios
Displays complete rows and columns from each API response
"""
import requests
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

RAILWAY_URL = "https://sigmasight-be-production.up.railway.app/api/v1"

DEMO_USERS = [
    {
        "email": "demo_individual@sigmasight.com",
        "password": "demo12345",
        "name": "Individual Investor"
    },
    {
        "email": "demo_hnw@sigmasight.com",
        "password": "demo12345",
        "name": "High Net Worth"
    },
    {
        "email": "demo_hedgefundstyle@sigmasight.com",
        "password": "demo12345",
        "name": "Hedge Fund Style"
    }
]


def login(email: str, password: str) -> Optional[str]:
    """Login and return JWT token"""
    response = requests.post(
        f"{RAILWAY_URL}/auth/login",
        json={"email": email, "password": password}
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print(f"❌ Login failed for {email}: {response.status_code}")
        return None


def get_portfolio(token: str) -> Optional[Dict[str, Any]]:
    """Get user's first portfolio"""
    response = requests.get(
        f"{RAILWAY_URL}/data/portfolios",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        portfolios = response.json()
        return portfolios[0] if portfolios else None
    return None


def test_portfolio_summary(portfolio_id: str, token: str, report_file):
    """Test /analytics/portfolio/{id}/overview"""
    print(f"\n   📊 Portfolio Overview")
    print(f"   {'-'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/overview",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Status: 200 OK")

        # Display key metrics
        print(f"\n   Portfolio Metrics:")
        print(f"      Total Value: ${data.get('total_value', 0):,.2f}")
        print(f"      Equity Balance: ${data.get('equity_balance', 0):,.2f}")
        print(f"      Market Value: ${data.get('total_market_value', 0):,.2f}")
        print(f"      Total P&L: ${data.get('total_pnl', 0):,.2f} ({data.get('total_pnl_percent', 0):.2f}%)")
        print(f"      Position Count: {data.get('position_count', 0)}")

        # Position type breakdown
        if data.get('position_types'):
            print(f"\n   Position Types:")
            for ptype, count in data['position_types'].items():
                print(f"      {ptype}: {count}")

        # Investment class breakdown
        if data.get('investment_classes'):
            print(f"\n   Investment Classes:")
            for iclass, count in data['investment_classes'].items():
                print(f"      {iclass}: {count}")

        # Write to report
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"PORTFOLIO SUMMARY\n")
        report_file.write(f"{'─'*120}\n")
        report_file.write(json.dumps(data, indent=2, default=str))
        report_file.write(f"\n")

        return data
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        report_file.write(f"\nPORTFOLIO SUMMARY: ERROR {response.status_code}\n{response.text}\n")
        return None


def test_portfolio_exposures(portfolio_id: str, token: str, report_file):
    """Test /analytics/portfolio/{id}/factor-exposures"""
    print(f"\n   📈 Portfolio Factor Exposures")
    print(f"   {'-'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/factor-exposures",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Status: 200 OK")

        # Display exposures
        exposures = data.get('exposures', {})
        print(f"\n   Portfolio Exposures:")
        print(f"      Gross Exposure: ${exposures.get('gross_exposure', 0):,.2f}")
        print(f"      Net Exposure: ${exposures.get('net_exposure', 0):,.2f}")
        print(f"      Long Exposure: ${exposures.get('long_exposure', 0):,.2f}")
        print(f"      Short Exposure: ${exposures.get('short_exposure', 0):,.2f}")

        # Delta adjusted exposure
        if exposures.get('delta_adjusted_exposure') is not None:
            print(f"      Delta Adjusted: ${exposures.get('delta_adjusted_exposure', 0):,.2f}")

        # Sector exposures
        if data.get('sector_exposures'):
            print(f"\n   Top Sector Exposures:")
            for sector in list(data['sector_exposures'])[:5]:
                value = sector.get('exposure', 0)
                pct = sector.get('percent_of_portfolio', 0)
                print(f"      {sector.get('sector', 'Unknown'):20} ${value:>12,.2f} ({pct:>5.1f}%)")

        # Write to report
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"PORTFOLIO EXPOSURES\n")
        report_file.write(f"{'─'*120}\n")
        report_file.write(json.dumps(data, indent=2, default=str))
        report_file.write(f"\n")

        return data
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        report_file.write(f"\nPORTFOLIO EXPOSURES: ERROR {response.status_code}\n{response.text}\n")
        return None


def test_portfolio_greeks(portfolio_id: str, token: str, report_file):
    """Test /analytics/portfolio/{id}/positions/factor-exposures"""
    print(f"\n   🏭 Position-Level Factor Exposures")
    print(f"   {'-'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/positions/factor-exposures",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 50}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Status: 200 OK")

        # Display aggregated Greeks
        greeks = data.get('aggregated_greeks', {})
        print(f"\n   Aggregated Greeks:")
        print(f"      Delta: {greeks.get('total_delta', 0):,.4f}")
        print(f"      Gamma: {greeks.get('total_gamma', 0):,.4f}")
        print(f"      Theta: {greeks.get('total_theta', 0):,.4f}")
        print(f"      Vega: {greeks.get('total_vega', 0):,.4f}")
        print(f"      Rho: {greeks.get('total_rho', 0):,.4f}")

        # Position-level Greeks
        position_greeks = data.get('position_greeks', [])
        if position_greeks:
            print(f"\n   Position-Level Greeks ({len(position_greeks)} positions):")
            print(f"      {'SYMBOL':<12} {'DELTA':>10} {'GAMMA':>10} {'THETA':>10} {'VEGA':>10}")
            print(f"      {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
            for pos in position_greeks[:10]:  # Show first 10
                symbol = pos.get('symbol', 'N/A')
                delta = pos.get('delta', 0) or 0
                gamma = pos.get('gamma', 0) or 0
                theta = pos.get('theta', 0) or 0
                vega = pos.get('vega', 0) or 0
                print(f"      {symbol:<12} {delta:>10.4f} {gamma:>10.4f} {theta:>10.4f} {vega:>10.4f}")

            if len(position_greeks) > 10:
                print(f"      ... and {len(position_greeks) - 10} more")

        # Write to report
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"PORTFOLIO GREEKS\n")
        report_file.write(f"{'─'*120}\n")
        report_file.write(json.dumps(data, indent=2, default=str))
        report_file.write(f"\n")

        return data
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        report_file.write(f"\nPORTFOLIO GREEKS: ERROR {response.status_code}\n{response.text}\n")
        return None


def test_portfolio_factors(portfolio_id: str, token: str, report_file):
    """Test /analytics/portfolio/{id}/factors"""
    print(f"\n   🏭 Factor Analysis")
    print(f"   {'-'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/factors",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Status: 200 OK")

        # Display portfolio-level factors
        portfolio_factors = data.get('portfolio_factors', {})
        if portfolio_factors:
            print(f"\n   Portfolio-Level Factor Exposures:")
            print(f"      Market Beta: {portfolio_factors.get('market_beta', 0):.4f}")
            print(f"      Value Beta: {portfolio_factors.get('value_beta', 0):.4f}")
            print(f"      Growth Beta: {portfolio_factors.get('growth_beta', 0):.4f}")
            print(f"      Momentum Beta: {portfolio_factors.get('momentum_beta', 0):.4f}")
            print(f"      Quality Beta: {portfolio_factors.get('quality_beta', 0):.4f}")
            print(f"      IR Beta: {portfolio_factors.get('ir_beta', 0):.4f}")

        # Position-level factors
        position_factors = data.get('position_factors', [])
        if position_factors:
            print(f"\n   Position-Level Factors ({len(position_factors)} positions with data):")
            print(f"      {'SYMBOL':<12} {'MKT BETA':>10} {'VALUE':>10} {'GROWTH':>10} {'MOMENTUM':>10}")
            print(f"      {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
            for pos in position_factors[:10]:  # Show first 10
                symbol = pos.get('symbol', 'N/A')
                market = pos.get('market_beta', 0) or 0
                value = pos.get('value_beta', 0) or 0
                growth = pos.get('growth_beta', 0) or 0
                momentum = pos.get('momentum_beta', 0) or 0
                print(f"      {symbol:<12} {market:>10.4f} {value:>10.4f} {growth:>10.4f} {momentum:>10.4f}")

            if len(position_factors) > 10:
                print(f"      ... and {len(position_factors) - 10} more")

        # Write to report
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"FACTOR ANALYSIS\n")
        report_file.write(f"{'─'*120}\n")
        report_file.write(json.dumps(data, indent=2, default=str))
        report_file.write(f"\n")

        return data
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        report_file.write(f"\nFACTOR ANALYSIS: ERROR {response.status_code}\n{response.text}\n")
        return None


def test_portfolio_correlations(portfolio_id: str, token: str, report_file):
    """Test /analytics/portfolio/{id}/correlation-matrix"""
    print(f"\n   🔗 Correlation Matrix")
    print(f"   {'-'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/correlation-matrix",
        headers={"Authorization": f"Bearer {token}"},
        params={"lookback_days": 90, "min_overlap": 30}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Status: 200 OK")

        # Display correlation matrix info
        matrix = data.get('correlation_matrix', [])
        symbols = data.get('symbols', [])

        print(f"\n   Correlation Matrix:")
        print(f"      Symbols: {len(symbols)}")
        print(f"      Matrix size: {len(matrix)}x{len(matrix[0]) if matrix else 0}")

        if symbols and len(symbols) <= 10:
            # Show small correlation matrices
            print(f"\n      {'':<12}", end='')
            for sym in symbols:
                print(f"{sym:<8}", end='')
            print()

            for i, row in enumerate(matrix):
                print(f"      {symbols[i]:<12}", end='')
                for val in row:
                    print(f"{val:>8.3f}", end='')
                print()
        elif symbols:
            print(f"\n      Sample (first 5x5):")
            print(f"      {'':<12}", end='')
            for sym in symbols[:5]:
                print(f"{sym:<8}", end='')
            print()

            for i in range(min(5, len(matrix))):
                print(f"      {symbols[i]:<12}", end='')
                for val in matrix[i][:5]:
                    print(f"{val:>8.3f}", end='')
                print()

        # High/low correlations
        high_corr = data.get('high_correlations', [])
        low_corr = data.get('low_correlations', [])

        if high_corr:
            print(f"\n   Highest Correlations:")
            for corr in high_corr[:5]:
                print(f"      {corr.get('symbol_1', 'N/A'):8} - {corr.get('symbol_2', 'N/A'):8} : {corr.get('correlation', 0):>6.3f}")

        if low_corr:
            print(f"\n   Lowest Correlations:")
            for corr in low_corr[:5]:
                print(f"      {corr.get('symbol_1', 'N/A'):8} - {corr.get('symbol_2', 'N/A'):8} : {corr.get('correlation', 0):>6.3f}")

        # Write to report
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"CORRELATION ANALYSIS\n")
        report_file.write(f"{'─'*120}\n")
        report_file.write(json.dumps(data, indent=2, default=str))
        report_file.write(f"\n")

        return data
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        report_file.write(f"\nCORRELATION ANALYSIS: ERROR {response.status_code}\n{response.text}\n")
        return None


def test_portfolio_scenarios(portfolio_id: str, token: str, report_file):
    """Test /analytics/portfolio/{id}/stress-test"""
    print(f"\n   🎯 Stress Test Results")
    print(f"   {'-'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/stress-test",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Status: 200 OK")

        # Display scenarios
        scenarios = data.get('scenarios', [])

        if scenarios:
            print(f"\n   Scenario Results ({len(scenarios)} scenarios):")
            print(f"      {'SCENARIO':<25} {'P&L':>15} {'P&L %':>10}")
            print(f"      {'-'*25} {'-'*15} {'-'*10}")

            for scenario in scenarios:
                name = scenario.get('scenario_name', 'N/A')
                pnl = scenario.get('total_pnl', 0)
                pnl_pct = scenario.get('pnl_percent', 0)
                print(f"      {name:<25} ${pnl:>14,.2f} {pnl_pct:>9.2f}%")

        # Write to report
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"SCENARIO ANALYSIS\n")
        report_file.write(f"{'─'*120}\n")
        report_file.write(json.dumps(data, indent=2, default=str))
        report_file.write(f"\n")

        return data
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        report_file.write(f"\nSCENARIO ANALYSIS: ERROR {response.status_code}\n{response.text}\n")
        return None


def test_diversification_score(portfolio_id: str, token: str, report_file):
    """Test /analytics/portfolio/{id}/diversification-score"""
    print(f"\n   🎲 Diversification Score")
    print(f"   {'-'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/diversification-score",
        headers={"Authorization": f"Bearer {token}"},
        params={"lookback_days": 90, "min_overlap": 30}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Status: 200 OK")

        # Display diversification metrics
        print(f"\n   Diversification Metrics:")
        print(f"      Overall Score: {data.get('overall_score', 0):.2f}/100")
        print(f"      Rating: {data.get('rating', 'N/A')}")

        # Component scores
        components = data.get('component_scores', {})
        if components:
            print(f"\n   Component Scores:")
            print(f"      Position Count: {components.get('position_count_score', 0):.2f}")
            print(f"      Sector Diversity: {components.get('sector_diversity_score', 0):.2f}")
            print(f"      Asset Class Diversity: {components.get('asset_class_diversity_score', 0):.2f}")
            print(f"      Concentration Risk: {components.get('concentration_score', 0):.2f}")
            print(f"      Correlation: {components.get('correlation_score', 0):.2f}")

        # Top holdings
        top_holdings = data.get('top_holdings', [])
        if top_holdings:
            print(f"\n   Top Holdings:")
            for holding in top_holdings[:5]:
                symbol = holding.get('symbol', 'N/A')
                pct = holding.get('percent_of_portfolio', 0)
                print(f"      {symbol:10} {pct:>6.2f}%")

        # Sector breakdown
        sectors = data.get('sector_breakdown', [])
        if sectors:
            print(f"\n   Sector Breakdown:")
            for sector in sectors[:5]:
                name = sector.get('sector', 'Unknown')
                pct = sector.get('percent', 0)
                print(f"      {name:20} {pct:>6.2f}%")

        # Write to report
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"DIVERSIFICATION SCORE\n")
        report_file.write(f"{'─'*120}\n")
        report_file.write(json.dumps(data, indent=2, default=str))
        report_file.write(f"\n")

        return data
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        report_file.write(f"\nDIVERSIFICATION SCORE: ERROR {response.status_code}\n{response.text}\n")
        return None


def audit_portfolio(user_info: Dict[str, str], report_file):
    """Run full analytics audit for a single portfolio"""
    print(f"\n{'='*120}")
    print(f"USER: {user_info['name']} ({user_info['email']})")
    print(f"{'='*120}")

    report_file.write(f"\n{'='*120}\n")
    report_file.write(f"USER: {user_info['name']} ({user_info['email']})\n")
    report_file.write(f"{'='*120}\n")

    # Login
    token = login(user_info['email'], user_info['password'])
    if not token:
        return None

    # Get portfolio
    portfolio = get_portfolio(token)
    if not portfolio:
        print(f"❌ No portfolio found")
        return None

    print(f"\nPortfolio: {portfolio['name']}")
    print(f"Portfolio ID: {portfolio['id']}")
    print(f"Position Count: {portfolio['position_count']}")
    print(f"Total Value: ${portfolio['total_value']:,.2f}")

    report_file.write(f"\nPortfolio: {portfolio['name']}\n")
    report_file.write(f"Portfolio ID: {portfolio['id']}\n")
    report_file.write(f"Position Count: {portfolio['position_count']}\n")
    report_file.write(f"Total Value: ${portfolio['total_value']:,.2f}\n")

    portfolio_id = portfolio['id']

    # Run all analytics tests
    results = {
        'portfolio_info': portfolio,
        'overview': test_portfolio_summary(portfolio_id, token, report_file),
        'factor_exposures': test_portfolio_exposures(portfolio_id, token, report_file),
        'position_factors': test_portfolio_greeks(portfolio_id, token, report_file),
        'correlations': test_portfolio_correlations(portfolio_id, token, report_file),
        'stress_test': test_portfolio_scenarios(portfolio_id, token, report_file),
        'diversification': test_diversification_score(portfolio_id, token, report_file)
    }

    return results


def main():
    """Main analytics audit"""
    print("🚀 Railway Analytics Audit")
    print(f"Backend: {RAILWAY_URL}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Open output file
    report_filename = "railway_analytics_audit_report.txt"

    with open(report_filename, "w", encoding="utf-8") as report:
        report.write("=" * 120 + "\n")
        report.write("RAILWAY ANALYTICS AUDIT - COMPLETE REPORT\n")
        report.write("=" * 120 + "\n")
        report.write(f"Backend: {RAILWAY_URL}\n")
        report.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        all_results = {}

        # Test each portfolio
        for user_info in DEMO_USERS:
            try:
                results = audit_portfolio(user_info, report)
                all_results[user_info['name']] = results
            except Exception as e:
                print(f"\n❌ Error auditing {user_info['name']}: {e}")
                import traceback
                traceback.print_exc()

        # Summary
        print(f"\n\n{'='*120}")
        print(f"📊 ANALYTICS AUDIT SUMMARY")
        print(f"{'='*120}")

        report.write(f"\n\n{'='*120}\n")
        report.write(f"ANALYTICS AUDIT SUMMARY\n")
        report.write(f"{'='*120}\n")

        for user_name, results in all_results.items():
            if results:
                print(f"\n{user_name}:")
                report.write(f"\n{user_name}:\n")

                endpoints_tested = sum(1 for k, v in results.items() if v is not None and k != 'portfolio_info')
                total_endpoints = 6  # overview, factor-exposures, position-factors, correlation, stress-test, diversification

                status_line = f"  ✅ {endpoints_tested}/{total_endpoints} analytics endpoints working"
                print(status_line)
                report.write(status_line + "\n")

                # List which endpoints worked
                endpoint_status = {
                    'overview': '✅' if results.get('overview') else '❌',
                    'factor_exposures': '✅' if results.get('factor_exposures') else '❌',
                    'position_factors': '✅' if results.get('position_factors') else '❌',
                    'correlations': '✅' if results.get('correlations') else '❌',
                    'stress_test': '✅' if results.get('stress_test') else '❌',
                    'diversification': '✅' if results.get('diversification') else '❌'
                }

                for endpoint, status in endpoint_status.items():
                    line = f"    {status} {endpoint}"
                    print(line)
                    report.write(line + "\n")

    # Save JSON results
    json_filename = "railway_analytics_audit_results.json"
    with open(json_filename, "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n✅ Analytics audit complete!")
    print(f"   - JSON results: {json_filename}")
    print(f"   - Detailed report: {report_filename}")


if __name__ == "__main__":
    main()
