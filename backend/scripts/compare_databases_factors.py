"""
Compare Portfolio Factor Exposures: Core DB vs Legacy DB

Compares factor exposures between:
- Core DB (gondola): Current production with symbol-level architecture
- Legacy DB (metro:19517): FrontendRailway branch with position-level architecture

Created: 2025-12-23
"""
import asyncio
import json
import sys
import io
from datetime import date, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Fix Windows encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import asyncpg

# Database connection strings
CORE_DB_URL = "postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
LEGACY_DB_URL = "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@metro.proxy.rlwy.net:19517/railway"

# Tolerance for floating point comparison
BETA_TOLERANCE = 0.01  # 1% difference allowed


async def get_portfolio_factor_exposures(
    conn,
    calculation_date: Optional[date] = None
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Get portfolio-level factor exposures from factor_exposures table.

    Returns: {portfolio_id: {factor_name: {'beta': value, 'dollar': value}}}
    """
    query = """
        SELECT
            fe.portfolio_id,
            fd.name as factor_name,
            fe.exposure_value,
            fe.exposure_dollar,
            fe.calculation_date
        FROM factor_exposures fe
        JOIN factor_definitions fd ON fe.factor_id = fd.id
    """

    if calculation_date:
        query += " WHERE fe.calculation_date = $1"
        rows = await conn.fetch(query, calculation_date)
    else:
        query += " ORDER BY fe.calculation_date DESC"
        rows = await conn.fetch(query)

    result = {}
    for row in rows:
        portfolio_id = str(row['portfolio_id'])
        factor_name = row['factor_name']

        if portfolio_id not in result:
            result[portfolio_id] = {}

        result[portfolio_id][factor_name] = {
            'beta': float(row['exposure_value']) if row['exposure_value'] else 0.0,
            'dollar': float(row['exposure_dollar']) if row['exposure_dollar'] else 0.0,
            'date': row['calculation_date'].isoformat() if row['calculation_date'] else None
        }

    return result


async def get_portfolio_names(conn) -> Dict[str, str]:
    """Get portfolio ID to name mapping."""
    query = "SELECT id, name FROM portfolios"
    rows = await conn.fetch(query)
    return {str(row['id']): row['name'] for row in rows}


async def get_latest_calculation_dates(conn) -> List[date]:
    """Get the most recent calculation dates."""
    query = """
        SELECT DISTINCT calculation_date
        FROM factor_exposures
        ORDER BY calculation_date DESC
        LIMIT 5
    """
    rows = await conn.fetch(query)
    return [row['calculation_date'] for row in rows]


async def compare_databases():
    """Main comparison function."""
    print("=" * 80)
    print("Portfolio Factor Exposures: Core DB vs Legacy DB Comparison")
    print("=" * 80)

    # Connect to both databases
    print("\nConnecting to databases...")

    try:
        core_conn = await asyncpg.connect(CORE_DB_URL)
        print("✅ Connected to Core DB (gondola)")
    except Exception as e:
        print(f"❌ Failed to connect to Core DB: {e}")
        return

    try:
        legacy_conn = await asyncpg.connect(LEGACY_DB_URL)
        print("✅ Connected to Legacy DB (metro:19517)")
    except Exception as e:
        print(f"❌ Failed to connect to Legacy DB: {e}")
        await core_conn.close()
        return

    try:
        # Get portfolio names from both
        core_portfolios = await get_portfolio_names(core_conn)
        legacy_portfolios = await get_portfolio_names(legacy_conn)

        print(f"\nCore DB portfolios: {len(core_portfolios)}")
        print(f"Legacy DB portfolios: {len(legacy_portfolios)}")

        # Get latest calculation dates
        core_dates = await get_latest_calculation_dates(core_conn)
        legacy_dates = await get_latest_calculation_dates(legacy_conn)

        print(f"\nCore DB latest dates: {[d.isoformat() for d in core_dates[:3]]}")
        print(f"Legacy DB latest dates: {[d.isoformat() for d in legacy_dates[:3]]}")

        # Find common date to compare
        common_dates = set(core_dates) & set(legacy_dates)
        if common_dates:
            compare_date = max(common_dates)
            print(f"\n📅 Comparing on common date: {compare_date}")
        else:
            print("\n⚠️ No common dates found. Comparing latest available from each.")
            compare_date = None

        # Get factor exposures
        print("\nFetching factor exposures...")

        if compare_date:
            core_exposures = await get_portfolio_factor_exposures(core_conn, compare_date)
            legacy_exposures = await get_portfolio_factor_exposures(legacy_conn, compare_date)
        else:
            core_exposures = await get_portfolio_factor_exposures(core_conn, core_dates[0] if core_dates else None)
            legacy_exposures = await get_portfolio_factor_exposures(legacy_conn, legacy_dates[0] if legacy_dates else None)

        print(f"Core DB: {len(core_exposures)} portfolios with exposures")
        print(f"Legacy DB: {len(legacy_exposures)} portfolios with exposures")

        # Compare portfolios
        print("\n" + "=" * 80)
        print("COMPARISON RESULTS")
        print("=" * 80)

        all_portfolio_ids = set(core_exposures.keys()) | set(legacy_exposures.keys())

        comparison_results = []
        total_factors = 0
        matching_factors = 0

        for portfolio_id in sorted(all_portfolio_ids):
            portfolio_name = core_portfolios.get(portfolio_id) or legacy_portfolios.get(portfolio_id, "Unknown")

            core_factors = core_exposures.get(portfolio_id, {})
            legacy_factors = legacy_exposures.get(portfolio_id, {})

            if not core_factors and not legacy_factors:
                continue

            print(f"\n📊 Portfolio: {portfolio_name}")
            print(f"   ID: {portfolio_id}")

            if not core_factors:
                print("   ⚠️ Missing from Core DB")
                continue
            if not legacy_factors:
                print("   ⚠️ Missing from Legacy DB")
                continue

            # Get core date for display
            sample_factor = next(iter(core_factors.values()), {})
            core_date = sample_factor.get('date', 'N/A')
            sample_factor = next(iter(legacy_factors.values()), {})
            legacy_date = sample_factor.get('date', 'N/A')

            print(f"   Core Date: {core_date} | Legacy Date: {legacy_date}")
            print(f"   {'Factor':<25} {'Core Beta':>12} {'Legacy Beta':>12} {'Diff':>10} {'Status':>8}")
            print(f"   {'-'*25} {'-'*12} {'-'*12} {'-'*10} {'-'*8}")

            all_factors = set(core_factors.keys()) | set(legacy_factors.keys())

            portfolio_match = True
            for factor_name in sorted(all_factors):
                core_beta = core_factors.get(factor_name, {}).get('beta', 0.0)
                legacy_beta = legacy_factors.get(factor_name, {}).get('beta', 0.0)

                diff = abs(core_beta - legacy_beta)
                total_factors += 1

                if diff <= BETA_TOLERANCE:
                    status = "✅"
                    matching_factors += 1
                else:
                    status = "❌"
                    portfolio_match = False

                print(f"   {factor_name:<25} {core_beta:>12.6f} {legacy_beta:>12.6f} {diff:>10.6f} {status:>8}")

                comparison_results.append({
                    'portfolio_id': portfolio_id,
                    'portfolio_name': portfolio_name,
                    'factor': factor_name,
                    'core_beta': core_beta,
                    'legacy_beta': legacy_beta,
                    'difference': diff,
                    'match': diff <= BETA_TOLERANCE
                })

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        match_rate = matching_factors / total_factors if total_factors > 0 else 0
        print(f"\nTotal factors compared: {total_factors}")
        print(f"Matching (within {BETA_TOLERANCE*100:.1f}% tolerance): {matching_factors}")
        print(f"Discrepancies: {total_factors - matching_factors}")
        print(f"Match rate: {match_rate:.1%}")

        if match_rate >= 0.99:
            print("\n✅ EXCELLENT: Factor exposures are highly consistent between databases")
        elif match_rate >= 0.90:
            print("\n⚠️ GOOD: Most factors match, but some discrepancies exist")
        else:
            print("\n❌ INVESTIGATE: Significant discrepancies between databases")

        # Save detailed results
        output_file = "database_factor_comparison.json"
        with open(output_file, 'w') as f:
            json.dump({
                'comparison_date': compare_date.isoformat() if compare_date else None,
                'core_dates': [d.isoformat() for d in core_dates],
                'legacy_dates': [d.isoformat() for d in legacy_dates],
                'total_factors': total_factors,
                'matching_factors': matching_factors,
                'match_rate': match_rate,
                'tolerance': BETA_TOLERANCE,
                'results': comparison_results
            }, f, indent=2)

        print(f"\n📄 Detailed results saved to: {output_file}")

    finally:
        await core_conn.close()
        await legacy_conn.close()
        print("\n✅ Database connections closed")


if __name__ == '__main__':
    asyncio.run(compare_databases())
