#!/usr/bin/env python
"""
Database Diagnostic Script for Railway pgvector Database

Run on Railway: railway run python scripts/railway/diagnose_db.py
Or locally with DATABASE_URL set

Checks:
1. All tables and row counts
2. Stress test scenarios
3. Factor definitions
4. AI Knowledge Base documents
5. AI Memories
6. Portfolio/Position data
7. Recent insights
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_url():
    """Get database URL, handling async driver prefix."""
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    return url


def run_diagnostics():
    """Run comprehensive database diagnostics."""
    db_url = get_db_url()
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return

    print("=" * 80)
    print("DATABASE DIAGNOSTIC REPORT")
    print("=" * 80)

    conn = psycopg2.connect(db_url)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1. List all tables with row counts
    print("\n📋 ALL TABLES AND ROW COUNTS:")
    print("-" * 50)
    cur.execute("""
        SELECT schemaname, tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    """)
    tables = cur.fetchall()

    for table in tables:
        table_name = table['tablename']
        try:
            cur.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
            count = cur.fetchone()['cnt']
            print(f"  {table_name}: {count} rows")
        except Exception as e:
            print(f"  {table_name}: ERROR - {e}")

    # 2. Check stress_scenarios
    print("\n🔥 STRESS TEST SCENARIOS:")
    print("-" * 50)
    cur.execute("SELECT COUNT(*) as cnt FROM stress_scenarios")
    count = cur.fetchone()['cnt']
    print(f"  Total scenarios: {count}")

    if count > 0:
        cur.execute("SELECT name, category, description FROM stress_scenarios LIMIT 5")
        scenarios = cur.fetchall()
        for s in scenarios:
            print(f"    - {s['name']} ({s['category']})")
    else:
        print("  ⚠️ NO STRESS SCENARIOS - Need to run seed_stress_scenarios.py")

    # 3. Check factor_definitions
    print("\n📊 FACTOR DEFINITIONS:")
    print("-" * 50)
    cur.execute("SELECT COUNT(*) as cnt FROM factor_definitions")
    count = cur.fetchone()['cnt']
    print(f"  Total factors: {count}")

    if count > 0:
        cur.execute("SELECT name, factor_type FROM factor_definitions")
        factors = cur.fetchall()
        for f in factors:
            print(f"    - {f['name']} ({f['factor_type']})")
    else:
        print("  ⚠️ NO FACTOR DEFINITIONS - Need to run seed_factors")

    # 4. Check AI Knowledge Base
    print("\n🧠 AI KNOWLEDGE BASE (ai_kb_documents):")
    print("-" * 50)
    try:
        cur.execute("SELECT COUNT(*) as cnt FROM ai_kb_documents")
        count = cur.fetchone()['cnt']
        print(f"  Total KB documents: {count}")

        if count > 0:
            cur.execute("SELECT title, scope, doc_type FROM ai_kb_documents LIMIT 5")
            docs = cur.fetchall()
            for d in docs:
                print(f"    - {d['title']} (scope: {d['scope']}, type: {d['doc_type']})")
        else:
            print("  ⚠️ NO KB DOCUMENTS - RAG will not work")
    except Exception as e:
        print(f"  ❌ TABLE MISSING OR ERROR: {e}")

    # 5. Check AI Memories
    print("\n💭 AI MEMORIES (ai_memories):")
    print("-" * 50)
    try:
        cur.execute("SELECT COUNT(*) as cnt FROM ai_memories")
        count = cur.fetchone()['cnt']
        print(f"  Total memories: {count}")
    except Exception as e:
        print(f"  ❌ TABLE MISSING OR ERROR: {e}")

    # 6. Check pgvector extension
    print("\n🔌 PGVECTOR EXTENSION:")
    print("-" * 50)
    try:
        cur.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
        ext = cur.fetchone()
        if ext:
            print(f"  ✅ pgvector installed (version: {ext.get('extversion', 'unknown')})")
        else:
            print("  ❌ pgvector NOT installed")
    except Exception as e:
        print(f"  ❌ Error checking: {e}")

    # 7. Check portfolios and positions
    print("\n💼 PORTFOLIOS AND POSITIONS:")
    print("-" * 50)
    cur.execute("SELECT COUNT(*) as cnt FROM portfolios")
    portfolio_count = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM positions WHERE deleted_at IS NULL")
    position_count = cur.fetchone()['cnt']
    print(f"  Portfolios: {portfolio_count}")
    print(f"  Active Positions: {position_count}")

    if portfolio_count > 0:
        cur.execute("""
            SELECT p.name, p.equity_balance, COUNT(pos.id) as pos_count
            FROM portfolios p
            LEFT JOIN positions pos ON p.id = pos.portfolio_id AND pos.deleted_at IS NULL
            GROUP BY p.id, p.name, p.equity_balance
        """)
        portfolios = cur.fetchall()
        for p in portfolios:
            print(f"    - {p['name']}: {p['pos_count']} positions, ${p['equity_balance']:,.2f}")

    # 8. Check recent AI insights
    print("\n🤖 RECENT AI INSIGHTS:")
    print("-" * 50)
    try:
        cur.execute("""
            SELECT insight_type, title, created_at,
                   CASE WHEN full_analysis IS NULL OR full_analysis = '' THEN 'EMPTY' ELSE 'HAS CONTENT' END as content_status
            FROM ai_insights
            ORDER BY created_at DESC
            LIMIT 5
        """)
        insights = cur.fetchall()
        if insights:
            for i in insights:
                print(f"    - [{i['content_status']}] {i['insight_type']}: {i['title'][:50]}... ({i['created_at']})")
        else:
            print("  No insights found")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # 9. Check portfolio_snapshots
    print("\n📸 PORTFOLIO SNAPSHOTS:")
    print("-" * 50)
    cur.execute("SELECT COUNT(*) as cnt FROM portfolio_snapshots")
    count = cur.fetchone()['cnt']
    print(f"  Total snapshots: {count}")

    if count > 0:
        cur.execute("""
            SELECT snapshot_date, COUNT(*) as cnt
            FROM portfolio_snapshots
            GROUP BY snapshot_date
            ORDER BY snapshot_date DESC
            LIMIT 5
        """)
        dates = cur.fetchall()
        for d in dates:
            print(f"    - {d['snapshot_date']}: {d['cnt']} snapshots")

    # 10. Check market_data_cache
    print("\n📈 MARKET DATA CACHE:")
    print("-" * 50)
    cur.execute("SELECT COUNT(*) as cnt FROM market_data_cache")
    count = cur.fetchone()['cnt']
    print(f"  Total cached prices: {count}")

    cur.close()
    conn.close()

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_diagnostics()
