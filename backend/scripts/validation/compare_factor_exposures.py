"""
Compare Factor Exposures - Validates symbol-level vs position-level calculations.

Part of the Symbol Factor Universe architecture (Phase 6: Validation).

This script compares two approaches for calculating factor exposures:
1. Position-level: Current method, stores per-position betas in position_factor_exposures
2. Symbol-level: New method, stores per-symbol betas in symbol_factor_exposures

Success criteria for deprecating position-level:
- Match rate > 99.9% across 30+ days
- Zero unexplained discrepancies
- Options delta handling validated

Usage:
    python scripts/validation/compare_factor_exposures.py --start-date 2025-12-01 --end-date 2025-12-19

Created: 2025-12-20
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID

# Set up path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Set environment
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
)

from sqlalchemy import select, and_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal

# Tolerance for floating point comparison
BETA_TOLERANCE = 0.0001  # 0.01% difference allowed
PORTFOLIO_TOLERANCE = 0.001  # 0.1% difference for aggregated values


async def get_position_factor_exposures(
    db: AsyncSession,
    calculation_date: date
) -> Dict[str, Dict[str, Dict[str, float]]]:
    """
    Get position-level factor exposures (current method).

    Returns: {portfolio_id: {position_id: {factor_name: beta_value}}}
    """
    result = {}

    stmt = text("""
        SELECT
            p.portfolio_id,
            pfe.position_id,
            p.symbol,
            fd.name as factor_name,
            pfe.beta_value
        FROM position_factor_exposures pfe
        JOIN positions p ON pfe.position_id = p.id
        JOIN factor_definitions fd ON pfe.factor_id = fd.id
        WHERE pfe.calculation_date = :calc_date
    """)

    rows = await db.execute(stmt, {'calc_date': calculation_date})

    for portfolio_id, position_id, symbol, factor_name, beta_value in rows.fetchall():
        portfolio_key = str(portfolio_id)
        position_key = str(position_id)

        if portfolio_key not in result:
            result[portfolio_key] = {}
        if position_key not in result[portfolio_key]:
            result[portfolio_key][position_key] = {'symbol': symbol}

        result[portfolio_key][position_key][factor_name] = float(beta_value) if beta_value else 0.0

    return result


async def get_symbol_factor_exposures(
    db: AsyncSession,
    calculation_date: date
) -> Dict[str, Dict[str, float]]:
    """
    Get symbol-level factor exposures (new method).

    Returns: {symbol: {factor_name: beta_value}}
    """
    result = {}

    stmt = text("""
        SELECT
            sfe.symbol,
            fd.name as factor_name,
            sfe.beta_value
        FROM symbol_factor_exposures sfe
        JOIN factor_definitions fd ON sfe.factor_id = fd.id
        WHERE sfe.calculation_date = :calc_date
    """)

    rows = await db.execute(stmt, {'calc_date': calculation_date})

    for symbol, factor_name, beta_value in rows.fetchall():
        if symbol not in result:
            result[symbol] = {}
        result[symbol][factor_name] = float(beta_value) if beta_value else 0.0

    return result


async def get_position_details(
    db: AsyncSession
) -> Dict[str, Dict[str, Any]]:
    """
    Get position details including weight and delta (for options).

    Returns: {position_id: {symbol, weight, is_option, delta}}
    """
    result = {}

    stmt = text("""
        SELECT
            p.id as position_id,
            p.portfolio_id,
            p.symbol,
            p.underlying_symbol,
            p.investment_class,
            p.quantity,
            p.entry_price,
            p.market_value,
            port.equity_balance,
            pg.delta
        FROM positions p
        JOIN portfolios port ON p.portfolio_id = port.id
        LEFT JOIN position_greeks pg ON p.id = pg.position_id
        WHERE p.exit_date IS NULL
    """)

    rows = await db.execute(stmt)

    for row in rows.fetchall():
        position_id = str(row[0])
        equity = float(row[8]) if row[8] else 1.0
        market_value = float(row[7]) if row[7] else (float(row[5]) * float(row[6]) if row[5] and row[6] else 0)

        result[position_id] = {
            'portfolio_id': str(row[1]),
            'symbol': row[2],
            'underlying_symbol': row[3],
            'investment_class': row[4],
            'is_option': row[4] == 'OPTIONS',
            'weight': market_value / equity if equity > 0 else 0,
            'delta': float(row[9]) if row[9] else None,
        }

    return result


async def compare_for_date(calculation_date: date) -> Dict[str, Any]:
    """
    Compare position-level vs symbol-level factors for a single date.
    """
    async with AsyncSessionLocal() as db:
        # Get position-level exposures (current method)
        position_exposures = await get_position_factor_exposures(db, calculation_date)

        # Get symbol-level exposures (new method)
        symbol_exposures = await get_symbol_factor_exposures(db, calculation_date)

        # Get position details for delta adjustment
        position_details = await get_position_details(db)

        discrepancies = []
        matches = 0
        missing_symbols = set()
        total_comparisons = 0

        # Compare each position's factor exposures
        for portfolio_id, positions in position_exposures.items():
            for position_id, pos_factors in positions.items():
                position_symbol = pos_factors.get('symbol', '')
                position_info = position_details.get(position_id, {})

                # Determine which symbol to use for lookup
                if position_info.get('is_option'):
                    lookup_symbol = position_info.get('underlying_symbol', position_symbol)
                else:
                    lookup_symbol = position_symbol

                # Get symbol-level betas
                if lookup_symbol not in symbol_exposures:
                    missing_symbols.add(lookup_symbol)
                    continue

                symbol_betas = symbol_exposures[lookup_symbol]

                # Compare each factor
                for factor_name, position_beta in pos_factors.items():
                    if factor_name == 'symbol':
                        continue  # Skip metadata

                    total_comparisons += 1

                    if factor_name not in symbol_betas:
                        missing_symbols.add(f"{lookup_symbol}:{factor_name}")
                        continue

                    symbol_beta = symbol_betas[factor_name]

                    # For options, position beta should be delta-adjusted
                    if position_info.get('is_option') and position_info.get('delta'):
                        expected_beta = position_info['delta'] * symbol_beta
                    else:
                        expected_beta = symbol_beta

                    # Compare with tolerance
                    diff = abs(position_beta - expected_beta)
                    if diff > BETA_TOLERANCE:
                        discrepancies.append({
                            'portfolio_id': portfolio_id,
                            'position_id': position_id,
                            'symbol': position_symbol,
                            'lookup_symbol': lookup_symbol,
                            'factor': factor_name,
                            'position_beta': position_beta,
                            'symbol_beta': symbol_beta,
                            'expected_beta': expected_beta,
                            'difference': diff,
                            'is_option': position_info.get('is_option', False),
                            'delta': position_info.get('delta'),
                        })
                    else:
                        matches += 1

        match_rate = matches / total_comparisons if total_comparisons > 0 else 1.0

        return {
            'date': calculation_date.isoformat(),
            'total_comparisons': total_comparisons,
            'matches': matches,
            'discrepancy_count': len(discrepancies),
            'match_rate': match_rate,
            'missing_symbols': list(missing_symbols),
            'discrepancies': discrepancies[:10],  # First 10 only for brevity
            'status': 'PASS' if match_rate >= 0.999 else 'INVESTIGATE'
        }


async def compare_portfolio_aggregation(
    portfolio_id: str,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Compare portfolio-level factor exposure calculated two ways:
    1. Sum of position_factor_exposures (current method)
    2. Sum of symbol_factor_exposures x position weights (new method)
    """
    async with AsyncSessionLocal() as db:
        # Method 1: Aggregate from position_factor_exposures
        position_stmt = text("""
            SELECT
                fd.name as factor_name,
                SUM(pfe.beta_value * (p.market_value / port.equity_balance)) as weighted_beta
            FROM position_factor_exposures pfe
            JOIN positions p ON pfe.position_id = p.id
            JOIN portfolios port ON p.portfolio_id = port.id
            JOIN factor_definitions fd ON pfe.factor_id = fd.id
            WHERE p.portfolio_id = :portfolio_id
            AND pfe.calculation_date = :calc_date
            AND p.exit_date IS NULL
            GROUP BY fd.name
        """)

        position_result = await db.execute(position_stmt, {
            'portfolio_id': portfolio_id,
            'calc_date': calculation_date
        })
        position_betas = {row[0]: float(row[1]) if row[1] else 0.0 for row in position_result.fetchall()}

        # Method 2: Aggregate from symbol_factor_exposures
        symbol_stmt = text("""
            SELECT
                fd.name as factor_name,
                SUM(
                    sfe.beta_value *
                    COALESCE(pg.delta, 1.0) *
                    (p.market_value / port.equity_balance)
                ) as weighted_beta
            FROM positions p
            JOIN portfolios port ON p.portfolio_id = port.id
            LEFT JOIN position_greeks pg ON p.id = pg.position_id
            LEFT JOIN symbol_factor_exposures sfe ON
                COALESCE(p.underlying_symbol, p.symbol) = sfe.symbol
                AND sfe.calculation_date = :calc_date
            JOIN factor_definitions fd ON sfe.factor_id = fd.id
            WHERE p.portfolio_id = :portfolio_id
            AND p.exit_date IS NULL
            AND p.investment_class = 'PUBLIC'
            GROUP BY fd.name
        """)

        symbol_result = await db.execute(symbol_stmt, {
            'portfolio_id': portfolio_id,
            'calc_date': calculation_date
        })
        symbol_betas = {row[0]: float(row[1]) if row[1] else 0.0 for row in symbol_result.fetchall()}

        # Compare
        discrepancies = []
        matches = 0
        all_factors = set(position_betas.keys()) | set(symbol_betas.keys())

        for factor in all_factors:
            pos_beta = position_betas.get(factor, 0.0)
            sym_beta = symbol_betas.get(factor, 0.0)
            diff = abs(pos_beta - sym_beta)

            if diff > PORTFOLIO_TOLERANCE:
                discrepancies.append({
                    'factor': factor,
                    'position_level': pos_beta,
                    'symbol_level': sym_beta,
                    'difference': diff
                })
            else:
                matches += 1

        return {
            'portfolio_id': portfolio_id,
            'date': calculation_date.isoformat(),
            'factors_compared': len(all_factors),
            'matches': matches,
            'discrepancies': discrepancies,
            'match_rate': matches / len(all_factors) if all_factors else 1.0
        }


async def run_full_comparison(
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """Run comparison across date range and generate report."""
    print(f"\n{'='*60}")
    print(f"FACTOR EXPOSURE COMPARISON REPORT")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"{'='*60}\n")

    results = []
    current = start_date

    while current <= end_date:
        # Skip weekends
        if current.weekday() < 5:
            print(f"Comparing {current}...", end=" ")
            result = await compare_for_date(current)
            results.append(result)
            print(f"Match rate: {result['match_rate']:.2%} ({result['status']})")

        current += timedelta(days=1)

    # Summary statistics
    total_comparisons = sum(r['total_comparisons'] for r in results)
    total_matches = sum(r['matches'] for r in results)
    total_discrepancies = sum(r['discrepancy_count'] for r in results)
    overall_match_rate = total_matches / total_comparisons if total_comparisons else 1.0

    # Collect all discrepancies
    all_discrepancies = []
    for r in results:
        all_discrepancies.extend(r.get('discrepancies', []))

    # Collect all missing symbols
    all_missing = set()
    for r in results:
        all_missing.update(r.get('missing_symbols', []))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Dates analyzed: {len(results)}")
    print(f"Total comparisons: {total_comparisons}")
    print(f"Total matches: {total_matches}")
    print(f"Total discrepancies: {total_discrepancies}")
    print(f"Overall match rate: {overall_match_rate:.4%}")
    print(f"Missing symbols: {len(all_missing)}")

    if all_discrepancies:
        print(f"\nTop discrepancies (showing first 5):")
        for d in all_discrepancies[:5]:
            print(f"  {d['symbol']} / {d['factor']}: "
                  f"pos={d['position_beta']:.4f}, sym={d['expected_beta']:.4f}, diff={d['difference']:.4f}")

    recommendation = 'SAFE_TO_DEPRECATE' if total_discrepancies == 0 and overall_match_rate >= 0.999 else 'INVESTIGATE_DISCREPANCIES'
    print(f"\nRecommendation: {recommendation}")
    print(f"{'='*60}\n")

    return {
        'date_range': f"{start_date} to {end_date}",
        'dates_analyzed': len(results),
        'total_comparisons': total_comparisons,
        'total_matches': total_matches,
        'total_discrepancies': total_discrepancies,
        'overall_match_rate': overall_match_rate,
        'missing_symbols': list(all_missing),
        'daily_results': results,
        'sample_discrepancies': all_discrepancies[:20],
        'recommendation': recommendation
    }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Compare position-level vs symbol-level factor exposures'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default=(date.today() - timedelta(days=7)).isoformat(),
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        default=date.today().isoformat(),
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='factor_comparison_report.json',
        help='Output file path'
    )

    args = parser.parse_args()

    start = date.fromisoformat(args.start_date)
    end = date.fromisoformat(args.end_date)

    result = await run_full_comparison(start, end)

    # Write report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"Report saved to: {output_path}")


if __name__ == '__main__':
    asyncio.run(main())
