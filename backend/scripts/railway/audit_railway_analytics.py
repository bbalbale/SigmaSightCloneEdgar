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
    print(f"\n   📊 PORTFOLIO SUMMARY")
    print(f"   {'═'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/overview",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        data = response.json()

        # Account Value Section
        print(f"\n   ACCOUNT VALUE")
        print(f"   {'-'*100}")
        equity = data.get('equity_balance', 0)
        exposures = data.get('exposures', {})
        pnl_data = data.get('pnl', {})

        total_pnl = pnl_data.get('total_pnl', 0)
        unrealized = pnl_data.get('unrealized_pnl', 0)
        realized = pnl_data.get('realized_pnl', 0)

        print(f"   Total Equity:                      ${equity:>15,.2f}")
        print(f"   Cash Balance:                      ${data.get('cash_balance', 0):>15,.2f}")
        print(f"   Leverage Ratio:                    {data.get('leverage', 0):>15.2f}x")

        # P&L Section
        print(f"\n   PROFIT & LOSS")
        print(f"   {'-'*100}")
        pnl_pct = (total_pnl / equity * 100) if equity else 0
        print(f"   Total P&L:                         ${total_pnl:>15,.2f}  ({pnl_pct:+.2f}%)")
        print(f"   Unrealized P&L:                    ${unrealized:>15,.2f}")
        print(f"   Realized P&L:                      ${realized:>15,.2f}")

        # Exposure Section
        print(f"\n   MARKET EXPOSURE")
        print(f"   {'-'*100}")
        long_exp = exposures.get('long_exposure', 0)
        short_exp = exposures.get('short_exposure', 0)
        gross_exp = exposures.get('gross_exposure', 0)
        net_exp = exposures.get('net_exposure', 0)

        print(f"   Long Exposure:                     ${long_exp:>15,.2f}  ({exposures.get('long_percentage', 0):>6.1f}%)")
        print(f"   Short Exposure:                    ${short_exp:>15,.2f}  ({exposures.get('short_percentage', 0):>6.1f}%)")
        print(f"   Gross Exposure:                    ${gross_exp:>15,.2f}  ({exposures.get('gross_percentage', 0):>6.1f}%)")
        print(f"   Net Exposure:                      ${net_exp:>15,.2f}  ({exposures.get('net_percentage', 0):>6.1f}%)")

        # Position Count Section
        position_count = data.get('position_count', {})
        print(f"\n   POSITIONS")
        print(f"   {'-'*100}")
        print(f"   Total Positions:                   {position_count.get('total_positions', 0):>15}")
        print(f"   Long Positions:                    {position_count.get('long_count', 0):>15}")
        print(f"   Short Positions:                   {position_count.get('short_count', 0):>15}")
        print(f"   Options Positions:                 {position_count.get('option_count', 0):>15}")

        # Write to report (client-friendly format)
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"PORTFOLIO SUMMARY\n")
        report_file.write(f"{'─'*120}\n\n")
        report_file.write(f"ACCOUNT VALUE\n")
        report_file.write(f"{'-'*120}\n")
        report_file.write(f"Total Equity:                      ${equity:>15,.2f}\n")
        report_file.write(f"Cash Balance:                      ${data.get('cash_balance', 0):>15,.2f}\n")
        report_file.write(f"Leverage Ratio:                    {data.get('leverage', 0):>15.2f}x\n\n")
        report_file.write(f"PROFIT & LOSS\n")
        report_file.write(f"{'-'*120}\n")
        report_file.write(f"Total P&L:                         ${total_pnl:>15,.2f}  ({pnl_pct:+.2f}%)\n")
        report_file.write(f"Unrealized P&L:                    ${unrealized:>15,.2f}\n")
        report_file.write(f"Realized P&L:                      ${realized:>15,.2f}\n\n")
        report_file.write(f"MARKET EXPOSURE\n")
        report_file.write(f"{'-'*120}\n")
        report_file.write(f"Long Exposure:                     ${long_exp:>15,.2f}  ({exposures.get('long_percentage', 0):>6.1f}%)\n")
        report_file.write(f"Short Exposure:                    ${short_exp:>15,.2f}  ({exposures.get('short_percentage', 0):>6.1f}%)\n")
        report_file.write(f"Gross Exposure:                    ${gross_exp:>15,.2f}  ({exposures.get('gross_percentage', 0):>6.1f}%)\n")
        report_file.write(f"Net Exposure:                      ${net_exp:>15,.2f}  ({exposures.get('net_percentage', 0):>6.1f}%)\n\n")
        report_file.write(f"POSITIONS\n")
        report_file.write(f"{'-'*120}\n")
        report_file.write(f"Total Positions:                   {position_count.get('total_positions', 0):>15}\n")
        report_file.write(f"Long Positions:                    {position_count.get('long_count', 0):>15}\n")
        report_file.write(f"Short Positions:                   {position_count.get('short_count', 0):>15}\n")
        report_file.write(f"Options Positions:                 {position_count.get('option_count', 0):>15}\n")

        return data
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        report_file.write(f"\nPORTFOLIO SUMMARY: ERROR {response.status_code}\n{response.text}\n")
        return None


def test_portfolio_exposures(portfolio_id: str, token: str, report_file):
    """Test /analytics/portfolio/{id}/factor-exposures"""
    print(f"\n   📈 RISK FACTOR ANALYSIS")
    print(f"   {'═'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/factor-exposures",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        data = response.json()

        if not data.get('available'):
            print(f"\n   No factor analysis data available yet")
            print(f"   Run batch calculations to generate factor exposures")
        else:
            factors = data.get('factors', [])
            metadata = data.get('metadata', {})

            print(f"\n   FACTOR EXPOSURES")
            print(f"   {'-'*100}")
            print(f"   Factor Model: {metadata.get('factor_model', 'N/A')}")
            print(f"   Calculation Date: {data.get('calculation_date', 'N/A')}")
            print(f"\n   {'RISK FACTOR':<20} {'BETA':<12} {'DOLLAR EXPOSURE':<20}")
            print(f"   {'-'*20} {'-'*12} {'-'*20}")

            for factor in factors:
                name = factor.get('name', 'N/A')
                beta = factor.get('beta', 0)
                exposure = factor.get('exposure_dollar', 0)

                # Interpret beta strength
                if abs(beta) >= 1.0:
                    strength = "High"
                elif abs(beta) >= 0.5:
                    strength = "Moderate"
                else:
                    strength = "Low"

                print(f"   {name:<20} {beta:>11.3f}  ${exposure:>18,.2f}")

            print(f"\n   INTERPRETATION")
            print(f"   {'-'*100}")
            print(f"   • Beta > 1.0 = High sensitivity to factor movements")
            print(f"   • Beta 0.5-1.0 = Moderate sensitivity")
            print(f"   • Beta < 0.5 = Low sensitivity")
            print(f"   • Negative beta = Inverse relationship to factor")

        # Write to report (client-friendly format)
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"RISK FACTOR ANALYSIS\n")
        report_file.write(f"{'─'*120}\n\n")
        if not data.get('available'):
            report_file.write(f"No factor analysis data available yet\n")
            report_file.write(f"Run batch calculations to generate factor exposures\n")
        else:
            report_file.write(f"FACTOR EXPOSURES\n")
            report_file.write(f"{'-'*120}\n")
            report_file.write(f"Factor Model: {metadata.get('factor_model', 'N/A')}\n")
            report_file.write(f"Calculation Date: {data.get('calculation_date', 'N/A')}\n\n")
            report_file.write(f"{'RISK FACTOR':<20} {'BETA':<12} {'DOLLAR EXPOSURE':<20}\n")
            report_file.write(f"{'-'*20} {'-'*12} {'-'*20}\n")
            for factor in factors:
                name = factor.get('name', 'N/A')
                beta = factor.get('beta', 0)
                exposure = factor.get('exposure_dollar', 0)
                report_file.write(f"{name:<20} {beta:>11.3f}  ${exposure:>18,.2f}\n")
            report_file.write(f"\nINTERPRETATION\n")
            report_file.write(f"{'-'*120}\n")
            report_file.write(f"• Beta > 1.0 = High sensitivity to factor movements\n")
            report_file.write(f"• Beta 0.5-1.0 = Moderate sensitivity\n")
            report_file.write(f"• Beta < 0.5 = Low sensitivity\n")
            report_file.write(f"• Negative beta = Inverse relationship to factor\n")

        return data
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        report_file.write(f"\nPORTFOLIO EXPOSURES: ERROR {response.status_code}\n{response.text}\n")
        return None


def test_portfolio_greeks(portfolio_id: str, token: str, report_file):
    """Test /analytics/portfolio/{id}/positions/factor-exposures"""
    print(f"\n   🏭 HOLDINGS FACTOR BREAKDOWN")
    print(f"   {'═'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/positions/factor-exposures",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 50}
    )

    if response.status_code == 200:
        data = response.json()

        if not data.get('available'):
            print(f"\n   No position-level factor data available yet")
            print(f"   Run batch calculations to generate factor exposures")
        else:
            positions = data.get('positions', [])
            total = data.get('total', 0)

            if positions:
                print(f"\n   INDIVIDUAL POSITION FACTOR EXPOSURES")
                print(f"   {'-'*100}")
                print(f"   Showing {len(positions)} of {total} positions")

                # Show top positions with highest market beta
                sorted_positions = sorted(positions, key=lambda x: abs(x.get('exposures', {}).get('Market Beta', 0)), reverse=True)

                print(f"\n   {'SYMBOL':<12} {'MKT BETA':>10} {'VALUE':>10} {'GROWTH':>10} {'MOMENTUM':>10} {'QUALITY':>10}")
                print(f"   {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")

                for pos in sorted_positions[:15]:  # Show top 15
                    symbol = pos.get('symbol', 'N/A')
                    exp = pos.get('exposures', {})

                    market = exp.get('Market Beta', 0)
                    value = exp.get('Value', 0)
                    growth = exp.get('Growth', 0)
                    momentum = exp.get('Momentum', 0)
                    quality = exp.get('Quality', 0)

                    print(f"   {symbol:<12} {market:>10.3f} {value:>10.3f} {growth:>10.3f} {momentum:>10.3f} {quality:>10.3f}")

                if len(sorted_positions) > 15:
                    print(f"\n   ... and {len(sorted_positions) - 15} more positions")

                print(f"\n   FACTOR INTERPRETATION")
                print(f"   {'-'*100}")
                print(f"   • Market Beta: Sensitivity to overall market movements")
                print(f"   • Value: Exposure to undervalued stocks (low P/E, P/B ratios)")
                print(f"   • Growth: Exposure to high-growth companies")
                print(f"   • Momentum: Exposure to stocks with strong recent performance")
                print(f"   • Quality: Exposure to profitable, stable companies")
            else:
                print(f"\n   No position data available")

        # Write to report (client-friendly format)
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"HOLDINGS FACTOR BREAKDOWN\n")
        report_file.write(f"{'─'*120}\n\n")
        if not data.get('available'):
            report_file.write(f"No position-level factor data available yet\n")
            report_file.write(f"Run batch calculations to generate factor exposures\n")
        else:
            if positions:
                report_file.write(f"INDIVIDUAL POSITION FACTOR EXPOSURES\n")
                report_file.write(f"{'-'*120}\n")
                report_file.write(f"Showing {len(positions)} of {total} positions\n\n")
                sorted_positions = sorted(positions, key=lambda x: abs(x.get('exposures', {}).get('Market Beta', 0)), reverse=True)
                report_file.write(f"{'SYMBOL':<12} {'MKT BETA':>10} {'VALUE':>10} {'GROWTH':>10} {'MOMENTUM':>10} {'QUALITY':>10}\n")
                report_file.write(f"{'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*10}\n")
                for pos in sorted_positions[:15]:
                    symbol = pos.get('symbol', 'N/A')
                    exp = pos.get('exposures', {})
                    market = exp.get('Market Beta', 0)
                    value = exp.get('Value', 0)
                    growth = exp.get('Growth', 0)
                    momentum = exp.get('Momentum', 0)
                    quality = exp.get('Quality', 0)
                    report_file.write(f"{symbol:<12} {market:>10.3f} {value:>10.3f} {growth:>10.3f} {momentum:>10.3f} {quality:>10.3f}\n")
                if len(sorted_positions) > 15:
                    report_file.write(f"\n... and {len(sorted_positions) - 15} more positions\n")
                report_file.write(f"\nFACTOR INTERPRETATION\n")
                report_file.write(f"{'-'*120}\n")
                report_file.write(f"• Market Beta: Sensitivity to overall market movements\n")
                report_file.write(f"• Value: Exposure to undervalued stocks (low P/E, P/B ratios)\n")
                report_file.write(f"• Growth: Exposure to high-growth companies\n")
                report_file.write(f"• Momentum: Exposure to stocks with strong recent performance\n")
                report_file.write(f"• Quality: Exposure to profitable, stable companies\n")
            else:
                report_file.write(f"No position data available\n")

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
    print(f"\n   🔗 PORTFOLIO CORRELATION ANALYSIS")
    print(f"   {'═'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/correlation-matrix",
        headers={"Authorization": f"Bearer {token}"},
        params={"lookback_days": 90, "min_overlap": 30}
    )

    if response.status_code == 200:
        data = response.json()

        if not data.get('available'):
            print(f"\n   No correlation data available yet")
            print(f"   Requires 90 days of historical price data")
        else:
            matrix = data.get('correlation_matrix', [])
            symbols = data.get('symbols', [])
            quality = data.get('data_quality') or {}

            print(f"\n   CORRELATION MATRIX SUMMARY")
            print(f"   {'-'*100}")
            print(f"   Number of Holdings Analyzed:       {len(symbols):>15}")
            print(f"   Analysis Period:                   {quality.get('lookback_days', 90):>12} days")
            print(f"   Average Data Points:               {quality.get('avg_overlap', 0):>15.0f}")

            if symbols and len(symbols) <= 10:
                # Show full correlation matrix for small portfolios
                print(f"\n   CORRELATION MATRIX")
                print(f"   {'-'*100}")
                print(f"   {'':<12}", end='')
                for sym in symbols:
                    print(f"{sym:<8}", end='')
                print()

                for i, row in enumerate(matrix):
                    print(f"   {symbols[i]:<12}", end='')
                    for val in row:
                        # Color code correlations
                        if val > 0.7:
                            marker = "█"  # High positive
                        elif val > 0.3:
                            marker = "▓"  # Medium positive
                        elif val > -0.3:
                            marker = "░"  # Low correlation
                        else:
                            marker = "▒"  # Negative
                        print(f"{val:>7.2f}{marker}", end='')
                    print()

                print(f"\n   Key: █ High (>0.7)  ▓ Medium (0.3-0.7)  ░ Low (±0.3)  ▒ Negative (<-0.3)")

            # High/low correlations
            high_corr = data.get('high_correlations', [])
            low_corr = data.get('low_correlations', [])

            if high_corr:
                print(f"\n   HIGHLY CORRELATED PAIRS (Move together)")
                print(f"   {'-'*100}")
                print(f"   {'SYMBOL 1':<12} {'SYMBOL 2':<12} {'CORRELATION':<15}")
                print(f"   {'-'*12} {'-'*12} {'-'*15}")
                for corr in high_corr[:5]:
                    sym1 = corr.get('symbol_1', 'N/A')
                    sym2 = corr.get('symbol_2', 'N/A')
                    val = corr.get('correlation', 0)
                    print(f"   {sym1:<12} {sym2:<12} {val:>14.2f}")

            if low_corr:
                print(f"\n   NEGATIVELY CORRELATED PAIRS (Move opposite)")
                print(f"   {'-'*100}")
                print(f"   {'SYMBOL 1':<12} {'SYMBOL 2':<12} {'CORRELATION':<15}")
                print(f"   {'-'*12} {'-'*12} {'-'*15}")
                for corr in low_corr[:5]:
                    sym1 = corr.get('symbol_1', 'N/A')
                    sym2 = corr.get('symbol_2', 'N/A')
                    val = corr.get('correlation', 0)
                    print(f"   {sym1:<12} {sym2:<12} {val:>14.2f}")

        # Write to report (client-friendly format)
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"PORTFOLIO CORRELATION ANALYSIS\n")
        report_file.write(f"{'─'*120}\n\n")
        if not data.get('available'):
            report_file.write(f"No correlation data available yet\n")
            report_file.write(f"Requires 90 days of historical price data\n")
        else:
            report_file.write(f"CORRELATION MATRIX SUMMARY\n")
            report_file.write(f"{'-'*120}\n")
            report_file.write(f"Number of Holdings Analyzed:       {len(symbols):>15}\n")
            report_file.write(f"Analysis Period:                   {quality.get('lookback_days', 90):>12} days\n")
            report_file.write(f"Average Data Points:               {quality.get('avg_overlap', 0):>15.0f}\n")
            if symbols and matrix and len(symbols) <= 10:
                report_file.write(f"\nCORRELATION MATRIX\n")
                report_file.write(f"{'-'*120}\n")
                report_file.write(f"{'':12}")
                for sym in symbols:
                    report_file.write(f"{sym:<8}")
                report_file.write(f"\n")
                for i, row in enumerate(matrix):
                    report_file.write(f"{symbols[i]:<12}")
                    for val in row:
                        marker = "█" if val > 0.7 else "▓" if val > 0.3 else "░" if val > -0.3 else "▒"
                        report_file.write(f"{val:>7.2f}{marker}")
                    report_file.write(f"\n")
                report_file.write(f"\nKey: █ High (>0.7)  ▓ Medium (0.3-0.7)  ░ Low (±0.3)  ▒ Negative (<-0.3)\n")

        return data
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        report_file.write(f"\nCORRELATION ANALYSIS: ERROR {response.status_code}\n{response.text}\n")
        return None


def test_portfolio_scenarios(portfolio_id: str, token: str, report_file):
    """Test /analytics/portfolio/{id}/stress-test"""
    print(f"\n   🎯 PORTFOLIO STRESS TESTING")
    print(f"   {'═'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/stress-test",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        data = response.json()

        if not data.get('available'):
            print(f"\n   No stress test results available yet")
            print(f"   Run batch calculations to generate stress scenarios")
        else:
            scenarios = data.get('scenarios', [])
            baseline = data.get('baseline_value', 0)

            if scenarios:
                print(f"\n   STRESS SCENARIO ANALYSIS")
                print(f"   {'-'*100}")
                print(f"   Current Portfolio Value:           ${baseline:>15,.2f}")
                print(f"   Number of Scenarios Tested:        {len(scenarios):>15}")

                print(f"\n   {'SCENARIO':<30} {'IMPACT':<20} {'CHANGE %':<12} {'NEW VALUE':<20}")
                print(f"   {'-'*30} {'-'*20} {'-'*12} {'-'*20}")

                for scenario in scenarios:
                    name = scenario.get('scenario_name', 'N/A')
                    pnl = scenario.get('total_pnl', 0)
                    pnl_pct = scenario.get('pnl_percent', 0)
                    new_value = baseline + pnl

                    # Format with + or - sign
                    pnl_str = f"${pnl:+,.2f}" if pnl != 0 else "$0.00"
                    pct_str = f"{pnl_pct:+.2f}%" if pnl_pct != 0 else "0.00%"

                    print(f"   {name:<30} {pnl_str:<20} {pct_str:<12} ${new_value:>18,.2f}")

                # Find worst and best scenarios
                if len(scenarios) > 0:
                    worst = min(scenarios, key=lambda x: x.get('total_pnl', 0))
                    best = max(scenarios, key=lambda x: x.get('total_pnl', 0))

                    print(f"\n   KEY INSIGHTS")
                    print(f"   {'-'*100}")
                    print(f"   Worst Case Scenario:  {worst.get('scenario_name', 'N/A')}")
                    print(f"   └─ Impact: ${worst.get('total_pnl', 0):+,.2f} ({worst.get('pnl_percent', 0):+.2f}%)")
                    print(f"\n   Best Case Scenario:   {best.get('scenario_name', 'N/A')}")
                    print(f"   └─ Impact: ${best.get('total_pnl', 0):+,.2f} ({best.get('pnl_percent', 0):+.2f}%)")
            else:
                print(f"\n   No scenarios available")

        # Write to report (client-friendly format)
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"PORTFOLIO STRESS TESTING\n")
        report_file.write(f"{'─'*120}\n\n")
        if not data.get('available'):
            report_file.write(f"No stress test results available yet\n")
            report_file.write(f"Run batch calculations to generate stress scenarios\n")
        else:
            if scenarios:
                report_file.write(f"STRESS SCENARIO ANALYSIS\n")
                report_file.write(f"{'-'*120}\n")
                report_file.write(f"Current Portfolio Value:           ${baseline:>15,.2f}\n")
                report_file.write(f"Number of Scenarios Tested:        {len(scenarios):>15}\n\n")
                report_file.write(f"{'SCENARIO':<30} {'IMPACT':<20} {'CHANGE %':<12} {'NEW VALUE':<20}\n")
                report_file.write(f"{'-'*30} {'-'*20} {'-'*12} {'-'*20}\n")
                for scenario in scenarios:
                    name = scenario.get('scenario_name', 'N/A')
                    pnl = scenario.get('total_pnl', 0)
                    pnl_pct = scenario.get('pnl_percent', 0)
                    new_value = baseline + pnl
                    pnl_str = f"${pnl:+,.2f}" if pnl != 0 else "$0.00"
                    pct_str = f"{pnl_pct:+.2f}%" if pnl_pct != 0 else "0.00%"
                    report_file.write(f"{name:<30} {pnl_str:<20} {pct_str:<12} ${new_value:>18,.2f}\n")
                if len(scenarios) > 0:
                    worst = min(scenarios, key=lambda x: x.get('total_pnl', 0))
                    best = max(scenarios, key=lambda x: x.get('total_pnl', 0))
                    report_file.write(f"\nKEY INSIGHTS\n")
                    report_file.write(f"{'-'*120}\n")
                    report_file.write(f"Worst Case Scenario:  {worst.get('scenario_name', 'N/A')}\n")
                    report_file.write(f"└─ Impact: ${worst.get('total_pnl', 0):+,.2f} ({worst.get('pnl_percent', 0):+.2f}%)\n\n")
                    report_file.write(f"Best Case Scenario:   {best.get('scenario_name', 'N/A')}\n")
                    report_file.write(f"└─ Impact: ${best.get('total_pnl', 0):+,.2f} ({best.get('pnl_percent', 0):+.2f}%)\n")
            else:
                report_file.write(f"No scenarios available\n")

        return data
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        report_file.write(f"\nSCENARIO ANALYSIS: ERROR {response.status_code}\n{response.text}\n")
        return None


def test_diversification_score(portfolio_id: str, token: str, report_file):
    """Test /analytics/portfolio/{id}/diversification-score"""
    print(f"\n   🎲 PORTFOLIO DIVERSIFICATION ANALYSIS")
    print(f"   {'═'*100}")

    response = requests.get(
        f"{RAILWAY_URL}/analytics/portfolio/{portfolio_id}/diversification-score",
        headers={"Authorization": f"Bearer {token}"},
        params={"lookback_days": 90, "min_overlap": 30}
    )

    if response.status_code == 200:
        data = response.json()

        if not data.get('available'):
            print(f"\n   No diversification data available yet")
            print(f"   Requires correlation calculations to complete")
        else:
            score = data.get('weighted_abs_correlation', 0)
            quality = data.get('data_quality') or {}

            print(f"\n   DIVERSIFICATION SCORE")
            print(f"   {'-'*100}")

            # Convert correlation to diversification score (0-100)
            # Lower correlation = Higher diversification
            div_score = (1 - score) * 100

            # Rating based on score
            if div_score >= 80:
                rating = "Excellent"
                emoji = "🌟"
            elif div_score >= 60:
                rating = "Good"
                emoji = "✅"
            elif div_score >= 40:
                rating = "Moderate"
                emoji = "⚠️"
            else:
                rating = "Poor"
                emoji = "❌"

            print(f"   Diversification Score:             {div_score:>15.1f}/100  {emoji}")
            print(f"   Rating:                            {rating:>20}")
            print(f"   Average Correlation:               {score:>20.2f}")

            print(f"\n   DATA QUALITY")
            print(f"   {'-'*100}")
            print(f"   Symbols Analyzed:                  {quality.get('symbols_calculated', 0):>15}")
            print(f"   Analysis Period:                   {quality.get('lookback_days', 90):>12} days")
            print(f"   Average Data Points:               {quality.get('avg_overlap', 0):>15.0f}")

            print(f"\n   INTERPRETATION")
            print(f"   {'-'*100}")
            if div_score >= 60:
                print(f"   ✅ Your portfolio shows {rating.lower()} diversification")
                print(f"   Holdings tend to move independently, reducing concentration risk")
            elif div_score >= 40:
                print(f"   ⚠️  Your portfolio shows moderate diversification")
                print(f"   Some holdings move together - consider adding uncorrelated assets")
            else:
                print(f"   ❌ Your portfolio shows poor diversification")
                print(f"   Many holdings move together - high concentration risk")
                print(f"   Consider adding assets with different risk factors")

        # Write to report (client-friendly format)
        report_file.write(f"\n{'─'*120}\n")
        report_file.write(f"PORTFOLIO DIVERSIFICATION ANALYSIS\n")
        report_file.write(f"{'─'*120}\n\n")
        if not data.get('available'):
            report_file.write(f"No diversification data available yet\n")
            report_file.write(f"Requires correlation calculations to complete\n")
        else:
            div_score = (1 - score) * 100
            if div_score >= 80:
                rating = "Excellent"
                emoji = "🌟"
            elif div_score >= 60:
                rating = "Good"
                emoji = "✅"
            elif div_score >= 40:
                rating = "Moderate"
                emoji = "⚠️"
            else:
                rating = "Poor"
                emoji = "❌"
            report_file.write(f"DIVERSIFICATION SCORE\n")
            report_file.write(f"{'-'*120}\n")
            report_file.write(f"Diversification Score:             {div_score:>15.1f}/100  {emoji}\n")
            report_file.write(f"Rating:                            {rating:>20}\n")
            report_file.write(f"Average Correlation:               {score:>20.2f}\n\n")
            report_file.write(f"DATA QUALITY\n")
            report_file.write(f"{'-'*120}\n")
            report_file.write(f"Symbols Analyzed:                  {quality.get('symbols_calculated', 0):>15}\n")
            report_file.write(f"Analysis Period:                   {quality.get('lookback_days', 90):>12} days\n")
            report_file.write(f"Average Data Points:               {quality.get('avg_overlap', 0):>15.0f}\n\n")
            report_file.write(f"INTERPRETATION\n")
            report_file.write(f"{'-'*120}\n")
            if div_score >= 60:
                report_file.write(f"✅ Your portfolio shows {rating.lower()} diversification\n")
                report_file.write(f"Holdings tend to move independently, reducing concentration risk\n")
            elif div_score >= 40:
                report_file.write(f"⚠️  Your portfolio shows moderate diversification\n")
                report_file.write(f"Some holdings move together - consider adding uncorrelated assets\n")
            else:
                report_file.write(f"❌ Your portfolio shows poor diversification\n")
                report_file.write(f"Many holdings move together - high concentration risk\n")
                report_file.write(f"Consider adding assets with different risk factors\n")

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
