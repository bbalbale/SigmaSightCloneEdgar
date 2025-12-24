"""
Investigate Equity Balance Differences Between Core DB and Legacy DB

Created: 2025-12-23
"""
import asyncio
import sys
import io
from datetime import date
from typing import Dict, List, Any
from decimal import Decimal

# Fix Windows encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import asyncpg

# Database connection strings
CORE_DB_URL = "postgresql://postgres:GdTokAXPkwuJtsMQYbfTgJtPUvFIVYbo@gondola.proxy.rlwy.net:38391/railway"
LEGACY_DB_URL = "postgresql://postgres:md56mfuhi7mca0b1q1f9kozndwyh8er8@metro.proxy.rlwy.net:19517/railway"


async def get_portfolio_details(conn, portfolio_id: str) -> Dict:
    """Get portfolio details including equity balance."""
    query = """
        SELECT
            p.id,
            p.name,
            p.equity_balance,
            p.created_at,
            p.updated_at,
            u.email
        FROM portfolios p
        JOIN users u ON p.user_id = u.id
        WHERE p.id = $1
    """
    row = await conn.fetchrow(query, portfolio_id)
    return dict(row) if row else {}


async def get_positions_summary(conn, portfolio_id: str) -> Dict:
    """Get positions summary for a portfolio."""
    query = """
        SELECT
            COUNT(*) as position_count,
            SUM(CASE WHEN position_type = 'LONG' THEN quantity * entry_price ELSE 0 END) as long_entry_value,
            SUM(CASE WHEN position_type = 'SHORT' THEN ABS(quantity * entry_price) ELSE 0 END) as short_entry_value,
            SUM(COALESCE(market_value, 0)) as total_market_value,
            SUM(quantity * entry_price) as net_entry_value
        FROM positions
        WHERE portfolio_id = $1
    """
    row = await conn.fetchrow(query, portfolio_id)
    return dict(row) if row else {}


async def get_positions_detail(conn, portfolio_id: str) -> List[Dict]:
    """Get detailed position information."""
    query = """
        SELECT
            id,
            symbol,
            quantity,
            entry_price,
            market_value,
            position_type,
            investment_class,
            created_at,
            updated_at
        FROM positions
        WHERE portfolio_id = $1
        ORDER BY symbol
    """
    rows = await conn.fetch(query, portfolio_id)
    return [dict(row) for row in rows]


async def get_latest_snapshot(conn, portfolio_id: str) -> Dict:
    """Get the latest portfolio snapshot."""
    # First check what columns exist
    try:
        query = """
            SELECT
                id,
                snapshot_date,
                total_value,
                long_exposure,
                short_exposure,
                gross_exposure,
                net_exposure,
                created_at
            FROM portfolio_snapshots
            WHERE portfolio_id = $1
            ORDER BY snapshot_date DESC
            LIMIT 1
        """
        row = await conn.fetchrow(query, portfolio_id)
        return dict(row) if row else {}
    except Exception as e:
        # Try alternate column name
        try:
            query = """
                SELECT
                    id,
                    created_at as snapshot_date,
                    total_value,
                    long_exposure,
                    short_exposure,
                    gross_exposure,
                    net_exposure,
                    created_at
                FROM portfolio_snapshots
                WHERE portfolio_id = $1
                ORDER BY created_at DESC
                LIMIT 1
            """
            row = await conn.fetchrow(query, portfolio_id)
            return dict(row) if row else {}
        except:
            return {}


async def get_all_portfolios(conn) -> List[Dict]:
    """Get all portfolios."""
    query = """
        SELECT id, name, equity_balance
        FROM portfolios
        ORDER BY name
    """
    rows = await conn.fetch(query)
    return [dict(row) for row in rows]


async def investigate():
    """Main investigation function."""
    print("=" * 100)
    print("EQUITY BALANCE INVESTIGATION: Core DB vs Legacy DB")
    print("=" * 100)

    # Connect to both databases
    print("\nConnecting to databases...")
    core_conn = await asyncpg.connect(CORE_DB_URL)
    legacy_conn = await asyncpg.connect(LEGACY_DB_URL)
    print("Connected.\n")

    try:
        # Get all portfolios from both
        core_portfolios = await get_all_portfolios(core_conn)
        legacy_portfolios = await get_all_portfolios(legacy_conn)

        core_map = {str(p['id']): p for p in core_portfolios}
        legacy_map = {str(p['id']): p for p in legacy_portfolios}

        # Find portfolios with equity mismatches
        print("=" * 100)
        print("PORTFOLIOS WITH EQUITY BALANCE DIFFERENCES")
        print("=" * 100)

        mismatched_portfolios = []

        print(f"\n{'Portfolio Name':<45} {'Core Equity':>18} {'Legacy Equity':>18} {'Delta':>15} {'% Diff':>10}")
        print(f"{'-'*45} {'-'*18} {'-'*18} {'-'*15} {'-'*10}")

        for portfolio_id in sorted(core_map.keys()):
            core_p = core_map.get(portfolio_id, {})
            legacy_p = legacy_map.get(portfolio_id, {})

            if not legacy_p:
                continue

            core_equity = float(core_p.get('equity_balance', 0) or 0)
            legacy_equity = float(legacy_p.get('equity_balance', 0) or 0)

            delta = core_equity - legacy_equity
            pct_diff = (delta / legacy_equity * 100) if legacy_equity != 0 else 0

            name = core_p.get('name', 'Unknown')[:44]

            if abs(delta) > 1:  # More than $1 difference
                mismatched_portfolios.append(portfolio_id)
                marker = "***"
            else:
                marker = ""

            print(f"{name:<45} {core_equity:>18,.2f} {legacy_equity:>18,.2f} {delta:>15,.2f} {pct_diff:>9.1f}% {marker}")

        # Deep dive into mismatched portfolios
        print("\n" + "=" * 100)
        print("DETAILED ANALYSIS OF MISMATCHED PORTFOLIOS")
        print("=" * 100)

        for portfolio_id in mismatched_portfolios[:5]:  # Analyze top 5
            core_details = await get_portfolio_details(core_conn, portfolio_id)
            legacy_details = await get_portfolio_details(legacy_conn, portfolio_id)

            name = core_details.get('name', 'Unknown')

            print(f"\n{'='*100}")
            print(f"PORTFOLIO: {name}")
            print(f"ID: {portfolio_id}")
            print(f"{'='*100}")

            # Basic info comparison
            print(f"\n--- Portfolio Table Data ---")
            print(f"{'Field':<25} {'Core DB':>25} {'Legacy DB':>25}")
            print(f"{'-'*25} {'-'*25} {'-'*25}")

            core_equity = float(core_details.get('equity_balance', 0) or 0)
            legacy_equity = float(legacy_details.get('equity_balance', 0) or 0)
            print(f"{'equity_balance':<25} {core_equity:>25,.2f} {legacy_equity:>25,.2f}")

            core_updated = str(core_details.get('updated_at', 'N/A'))[:19]
            legacy_updated = str(legacy_details.get('updated_at', 'N/A'))[:19]
            print(f"{'updated_at':<25} {core_updated:>25} {legacy_updated:>25}")

            # Position summary
            print(f"\n--- Position Summary ---")
            core_pos = await get_positions_summary(core_conn, portfolio_id)
            legacy_pos = await get_positions_summary(legacy_conn, portfolio_id)

            print(f"{'Metric':<25} {'Core DB':>25} {'Legacy DB':>25} {'Match':>10}")
            print(f"{'-'*25} {'-'*25} {'-'*25} {'-'*10}")

            metrics = [
                ('position_count', 'Position Count'),
                ('long_entry_value', 'Long Entry Value'),
                ('short_entry_value', 'Short Entry Value'),
                ('net_entry_value', 'Net Entry Value'),
                ('total_market_value', 'Total Market Value'),
            ]

            for key, label in metrics:
                core_val = float(core_pos.get(key, 0) or 0)
                legacy_val = float(legacy_pos.get(key, 0) or 0)
                match = "YES" if abs(core_val - legacy_val) < 1 else "NO"

                if key == 'position_count':
                    print(f"{label:<25} {int(core_val):>25} {int(legacy_val):>25} {match:>10}")
                else:
                    print(f"{label:<25} {core_val:>25,.2f} {legacy_val:>25,.2f} {match:>10}")

            # Latest snapshot
            print(f"\n--- Latest Snapshot ---")
            core_snap = await get_latest_snapshot(core_conn, portfolio_id)
            legacy_snap = await get_latest_snapshot(legacy_conn, portfolio_id)

            if core_snap or legacy_snap:
                print(f"{'Metric':<25} {'Core DB':>25} {'Legacy DB':>25}")
                print(f"{'-'*25} {'-'*25} {'-'*25}")

                core_date = str(core_snap.get('calculation_date', 'N/A')) if core_snap else 'N/A'
                legacy_date = str(legacy_snap.get('calculation_date', 'N/A')) if legacy_snap else 'N/A'
                print(f"{'calculation_date':<25} {core_date:>25} {legacy_date:>25}")

                for key in ['total_value', 'long_exposure', 'short_exposure', 'gross_exposure', 'net_exposure']:
                    core_val = float(core_snap.get(key, 0) or 0) if core_snap else 0
                    legacy_val = float(legacy_snap.get(key, 0) or 0) if legacy_snap else 0
                    print(f"{key:<25} {core_val:>25,.2f} {legacy_val:>25,.2f}")
            else:
                print("  No snapshots found")

            # Position-level comparison
            print(f"\n--- Position-Level Comparison ---")
            core_positions = await get_positions_detail(core_conn, portfolio_id)
            legacy_positions = await get_positions_detail(legacy_conn, portfolio_id)

            core_pos_map = {p['symbol']: p for p in core_positions}
            legacy_pos_map = {p['symbol']: p for p in legacy_positions}

            all_symbols = sorted(set(core_pos_map.keys()) | set(legacy_pos_map.keys()))

            print(f"{'Symbol':<10} {'Core Qty':>12} {'Legacy Qty':>12} {'Core MV':>15} {'Legacy MV':>15} {'Core Entry':>12} {'Legacy Entry':>12}")
            print(f"{'-'*10} {'-'*12} {'-'*12} {'-'*15} {'-'*15} {'-'*12} {'-'*12}")

            for symbol in all_symbols[:15]:  # First 15 positions
                core_p = core_pos_map.get(symbol, {})
                legacy_p = legacy_pos_map.get(symbol, {})

                core_qty = float(core_p.get('quantity', 0) or 0)
                legacy_qty = float(legacy_p.get('quantity', 0) or 0)

                core_mv = float(core_p.get('market_value', 0) or 0)
                legacy_mv = float(legacy_p.get('market_value', 0) or 0)

                core_entry = float(core_p.get('entry_price', 0) or 0)
                legacy_entry = float(legacy_p.get('entry_price', 0) or 0)

                print(f"{symbol:<10} {core_qty:>12,.2f} {legacy_qty:>12,.2f} {core_mv:>15,.2f} {legacy_mv:>15,.2f} {core_entry:>12,.2f} {legacy_entry:>12,.2f}")

        # Summary
        print("\n" + "=" * 100)
        print("SUMMARY")
        print("=" * 100)

        print(f"""
Total portfolios compared: {len(core_map)}
Portfolios with equity mismatch: {len(mismatched_portfolios)}

Possible causes of equity_balance differences:
1. Different P&L calculations updating equity differently
2. Different batch run dates/times
3. Manual equity adjustments in one DB but not the other
4. Different market data feeding into calculations
5. Legacy DB may have stale data if not running batch jobs

The equity_balance field is typically:
- Set initially when portfolio is created
- Updated during batch processing based on P&L
- The Core DB runs daily batch jobs that update this
""")

    finally:
        await core_conn.close()
        await legacy_conn.close()
        print("\nDatabase connections closed.")


if __name__ == '__main__':
    asyncio.run(investigate())
