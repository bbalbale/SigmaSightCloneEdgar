"""
Investigate Factor Delta Between Core DB and Legacy DB

Deep investigation into why factor exposures differ between:
- Core DB (gondola): Symbol-level architecture
- Legacy DB (metro:19517): Position-level architecture

Created: 2025-12-23
"""
import asyncio
import json
import sys
import io
from datetime import date
from typing import Dict, List, Any, Optional
from decimal import Decimal

# Fix Windows encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import asyncpg

# Database connection strings
CORE_DB_URL = "postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
LEGACY_DB_URL = "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@metro.proxy.rlwy.net:19517/railway"


async def get_portfolio_info(conn) -> List[Dict]:
    """Get all portfolios with their details."""
    query = """
        SELECT
            p.id,
            p.name,
            p.equity_balance,
            u.email as user_email,
            (SELECT COUNT(*) FROM positions WHERE portfolio_id = p.id) as position_count
        FROM portfolios p
        JOIN users u ON p.user_id = u.id
        ORDER BY p.name
    """
    rows = await conn.fetch(query)
    return [dict(row) for row in rows]


async def get_factor_definitions(conn) -> Dict[str, str]:
    """Get factor ID to name mapping."""
    query = "SELECT id, name FROM factor_definitions"
    rows = await conn.fetch(query)
    return {str(row['id']): row['name'] for row in rows}


async def get_portfolio_factor_exposures(conn, portfolio_id: str, calc_date: date) -> Dict[str, Dict]:
    """Get portfolio-level factor exposures."""
    query = """
        SELECT
            fd.name as factor_name,
            fe.exposure_value,
            fe.exposure_dollar,
            fe.calculation_date
        FROM factor_exposures fe
        JOIN factor_definitions fd ON fe.factor_id = fd.id
        WHERE fe.portfolio_id = $1 AND fe.calculation_date = $2
        ORDER BY fd.name
    """
    rows = await conn.fetch(query, portfolio_id, calc_date)
    result = {}
    for row in rows:
        result[row['factor_name']] = {
            'beta': float(row['exposure_value']) if row['exposure_value'] else 0.0,
            'dollar': float(row['exposure_dollar']) if row['exposure_dollar'] else 0.0
        }
    return result


async def get_position_factor_exposures(conn, portfolio_id: str, calc_date: date) -> List[Dict]:
    """Get position-level factor exposures."""
    query = """
        SELECT
            p.symbol,
            p.quantity,
            p.entry_price,
            p.market_value,
            p.position_type,
            fd.name as factor_name,
            pfe.exposure_value as beta
        FROM position_factor_exposures pfe
        JOIN positions p ON pfe.position_id = p.id
        JOIN factor_definitions fd ON pfe.factor_id = fd.id
        WHERE p.portfolio_id = $1 AND pfe.calculation_date = $2
        ORDER BY p.symbol, fd.name
    """
    rows = await conn.fetch(query, portfolio_id, calc_date)
    return [dict(row) for row in rows]


async def get_symbol_factor_exposures(conn, calc_date: date) -> Dict[str, Dict[str, float]]:
    """Get symbol-level factor exposures (Core DB only)."""
    query = """
        SELECT
            sfe.symbol,
            fd.name as factor_name,
            sfe.beta_value
        FROM symbol_factor_exposures sfe
        JOIN factor_definitions fd ON sfe.factor_id = fd.id
        WHERE sfe.calculation_date = $1
        ORDER BY sfe.symbol, fd.name
    """
    try:
        rows = await conn.fetch(query, calc_date)
        result = {}
        for row in rows:
            symbol = row['symbol']
            if symbol not in result:
                result[symbol] = {}
            result[symbol][row['factor_name']] = float(row['beta_value'])
        return result
    except Exception as e:
        print(f"  (symbol_factor_exposures table not found or error: {e})")
        return {}


async def get_positions(conn, portfolio_id: str) -> List[Dict]:
    """Get positions for a portfolio."""
    query = """
        SELECT
            id,
            symbol,
            quantity,
            entry_price,
            market_value,
            position_type,
            investment_class
        FROM positions
        WHERE portfolio_id = $1
        ORDER BY symbol
    """
    rows = await conn.fetch(query, portfolio_id)
    return [dict(row) for row in rows]


async def check_table_exists(conn, table_name: str) -> bool:
    """Check if a table exists."""
    query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = $1
        )
    """
    result = await conn.fetchval(query, table_name)
    return result


async def investigate():
    """Main investigation function."""
    print("=" * 100)
    print("DEEP INVESTIGATION: Factor Exposure Delta")
    print("=" * 100)

    # Connect to both databases
    print("\nConnecting to databases...")
    core_conn = await asyncpg.connect(CORE_DB_URL)
    legacy_conn = await asyncpg.connect(LEGACY_DB_URL)
    print("Connected to both databases.\n")

    calc_date = date(2025, 12, 22)
    print(f"Analysis Date: {calc_date}\n")

    try:
        # Check what tables exist
        print("=" * 100)
        print("TABLE STRUCTURE CHECK")
        print("=" * 100)

        for db_name, conn in [("Core DB", core_conn), ("Legacy DB", legacy_conn)]:
            print(f"\n{db_name}:")
            tables = ['factor_exposures', 'position_factor_exposures', 'symbol_factor_exposures', 'symbol_daily_metrics']
            for table in tables:
                exists = await check_table_exists(conn, table)
                status = "EXISTS" if exists else "NOT FOUND"
                print(f"  {table}: {status}")

        # Get portfolios
        print("\n" + "=" * 100)
        print("PORTFOLIO COMPARISON")
        print("=" * 100)

        core_portfolios = await get_portfolio_info(core_conn)
        legacy_portfolios = await get_portfolio_info(legacy_conn)

        # Create lookup by ID
        core_portfolio_map = {str(p['id']): p for p in core_portfolios}
        legacy_portfolio_map = {str(p['id']): p for p in legacy_portfolios}

        all_portfolio_ids = set(core_portfolio_map.keys()) | set(legacy_portfolio_map.keys())

        for portfolio_id in sorted(all_portfolio_ids):
            core_p = core_portfolio_map.get(portfolio_id, {})
            legacy_p = legacy_portfolio_map.get(portfolio_id, {})

            name = core_p.get('name') or legacy_p.get('name', 'Unknown')

            print(f"\n{'='*100}")
            print(f"PORTFOLIO: {name}")
            print(f"ID: {portfolio_id}")
            print(f"{'='*100}")

            # Portfolio metadata
            print(f"\n--- Portfolio Metadata ---")
            print(f"{'Metric':<25} {'Core DB':>20} {'Legacy DB':>20} {'Match':>10}")
            print(f"{'-'*25} {'-'*20} {'-'*20} {'-'*10}")

            core_equity = float(core_p.get('equity_balance', 0) or 0)
            legacy_equity = float(legacy_p.get('equity_balance', 0) or 0)
            equity_match = "YES" if abs(core_equity - legacy_equity) < 0.01 else "NO"
            print(f"{'Equity Balance':<25} {core_equity:>20,.2f} {legacy_equity:>20,.2f} {equity_match:>10}")

            core_pos_count = core_p.get('position_count', 0)
            legacy_pos_count = legacy_p.get('position_count', 0)
            pos_match = "YES" if core_pos_count == legacy_pos_count else "NO"
            print(f"{'Position Count':<25} {core_pos_count:>20} {legacy_pos_count:>20} {pos_match:>10}")

            # Get factor exposures
            core_factors = await get_portfolio_factor_exposures(core_conn, portfolio_id, calc_date)
            legacy_factors = await get_portfolio_factor_exposures(legacy_conn, portfolio_id, calc_date)

            print(f"\n--- Portfolio Factor Exposures (Beta Values) ---")
            print(f"{'Factor':<25} {'Core DB':>15} {'Legacy DB':>15} {'Delta':>12} {'% Diff':>10}")
            print(f"{'-'*25} {'-'*15} {'-'*15} {'-'*12} {'-'*10}")

            all_factors = sorted(set(core_factors.keys()) | set(legacy_factors.keys()))

            for factor in all_factors:
                core_beta = core_factors.get(factor, {}).get('beta', 0.0)
                legacy_beta = legacy_factors.get(factor, {}).get('beta', 0.0)
                delta = core_beta - legacy_beta

                if legacy_beta != 0:
                    pct_diff = (delta / abs(legacy_beta)) * 100
                    pct_str = f"{pct_diff:>9.1f}%"
                else:
                    pct_str = "N/A"

                print(f"{factor:<25} {core_beta:>15.6f} {legacy_beta:>15.6f} {delta:>12.6f} {pct_str}")

            # Check position-level factors in legacy
            print(f"\n--- Position-Level Factor Check (Legacy DB) ---")
            legacy_pos_factors = await get_position_factor_exposures(legacy_conn, portfolio_id, calc_date)

            if legacy_pos_factors:
                # Group by symbol
                symbols_with_factors = set(pf['symbol'] for pf in legacy_pos_factors)
                print(f"Symbols with position_factor_exposures: {len(symbols_with_factors)}")

                # Show sample
                sample_symbols = list(symbols_with_factors)[:3]
                for symbol in sample_symbols:
                    symbol_factors = [pf for pf in legacy_pos_factors if pf['symbol'] == symbol]
                    print(f"\n  {symbol}:")
                    for sf in symbol_factors[:4]:  # First 4 factors
                        print(f"    {sf['factor_name']}: {float(sf['beta']):.6f}")
            else:
                print("  No position-level factor exposures found")

            # Check symbol-level factors in core
            print(f"\n--- Symbol-Level Factor Check (Core DB) ---")

            # Get positions for this portfolio
            core_positions = await get_positions(core_conn, portfolio_id)
            portfolio_symbols = [p['symbol'] for p in core_positions if p['symbol']]

            # Get symbol factors
            core_symbol_factors = await get_symbol_factor_exposures(core_conn, calc_date)

            if core_symbol_factors:
                symbols_with_factors = [s for s in portfolio_symbols if s in core_symbol_factors]
                print(f"Portfolio symbols with symbol_factor_exposures: {len(symbols_with_factors)}/{len(portfolio_symbols)}")

                # Show sample
                sample_symbols = symbols_with_factors[:3]
                for symbol in sample_symbols:
                    factors = core_symbol_factors.get(symbol, {})
                    print(f"\n  {symbol}:")
                    for fname, beta in list(factors.items())[:4]:
                        print(f"    {fname}: {beta:.6f}")
            else:
                print("  Symbol factor exposures table not available or empty")

        # Summary statistics
        print("\n" + "=" * 100)
        print("OVERALL ANALYSIS")
        print("=" * 100)

        print("""
Key Questions to Investigate:
1. Are the same positions in both databases?
2. Are position weights calculated the same way?
3. Are symbol-level betas different from position-level betas?
4. Is there a timing difference in when factors were calculated?

Likely Causes of Delta:
- Symbol-level calculates factors ONCE per symbol, then aggregates by weight
- Position-level calculates factors PER POSITION (can have slight variations)
- Different regression windows or calculation dates
- Weight calculation differences (market_value vs entry_value based)
""")

    finally:
        await core_conn.close()
        await legacy_conn.close()
        print("\nDatabase connections closed.")


if __name__ == '__main__':
    asyncio.run(investigate())
