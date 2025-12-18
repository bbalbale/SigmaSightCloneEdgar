#!/usr/bin/env python
"""
Database Diagnostic Script for Railway pgvector Database

Run on Railway: python scripts/railway/diagnose_db.py
Or locally with DATABASE_URL set

Uses asyncpg via SQLAlchemy (no psycopg2 dependency)

Checks:
1. All tables and row counts
2. Stress test scenarios
3. Factor definitions
4. AI Knowledge Base documents
5. AI Memories
6. Portfolio/Position data
7. Recent insights
8. Agent conversations/messages
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def get_db_url():
    """Get database URL, ensuring asyncpg driver."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return ""
    # Ensure we use asyncpg driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


async def safe_query(conn, sql, description=""):
    """Execute a query with error handling, rolling back on failure."""
    try:
        result = await conn.execute(text(sql))
        return result, None
    except Exception as e:
        # Rollback to clear the aborted transaction state
        await conn.rollback()
        return None, str(e)


async def run_diagnostics():
    """Run comprehensive database diagnostics."""
    db_url = get_db_url()
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        return

    print("=" * 80)
    print("DATABASE DIAGNOSTIC REPORT")
    print("=" * 80)

    # Use autocommit to avoid transaction issues on errors
    engine = create_async_engine(db_url, isolation_level="AUTOCOMMIT")

    async with engine.connect() as conn:
        # 1. List all tables with row counts
        print("\n📋 ALL TABLES AND ROW COUNTS:")
        print("-" * 50)
        result = await conn.execute(text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """))
        tables = result.fetchall()

        for (table_name,) in tables:
            try:
                result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                print(f"  {table_name}: {count} rows")
            except Exception as e:
                print(f"  {table_name}: ERROR - {e}")

        # 2. Check stress_test_scenarios (correct table name)
        print("\n🔥 STRESS TEST SCENARIOS:")
        print("-" * 50)
        try:
            result = await conn.execute(text("SELECT COUNT(*) FROM stress_test_scenarios"))
            count = result.scalar()
            print(f"  Total scenarios: {count}")

            if count > 0:
                result = await conn.execute(text("SELECT name, category FROM stress_test_scenarios LIMIT 5"))
                scenarios = result.fetchall()
                for name, category in scenarios:
                    print(f"    - {name} ({category})")
            else:
                print("  ⚠️ NO STRESS SCENARIOS - Need to seed stress test data")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        # 3. Check factor_definitions
        print("\n📊 FACTOR DEFINITIONS:")
        print("-" * 50)
        try:
            result = await conn.execute(text("SELECT COUNT(*) FROM factor_definitions"))
            count = result.scalar()
            print(f"  Total factors: {count}")

            if count > 0:
                result = await conn.execute(text("SELECT name, factor_type FROM factor_definitions"))
                factors = result.fetchall()
                for name, factor_type in factors:
                    print(f"    - {name} ({factor_type})")
            else:
                print("  ⚠️ NO FACTOR DEFINITIONS - Need to run seed_factors")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        # 4. Check AI Knowledge Base
        print("\n🧠 AI KNOWLEDGE BASE (ai_kb_documents):")
        print("-" * 50)
        try:
            result = await conn.execute(text("SELECT COUNT(*) FROM ai_kb_documents"))
            count = result.scalar()
            print(f"  Total KB documents: {count}")

            if count > 0:
                result = await conn.execute(text("SELECT title, scope FROM ai_kb_documents LIMIT 5"))
                docs = result.fetchall()
                for title, scope in docs:
                    print(f"    - {title[:50]} (scope: {scope})")
            else:
                print("  ⚠️ NO KB DOCUMENTS - RAG will not work")
        except Exception as e:
            print(f"  ❌ TABLE MISSING OR ERROR: {e}")

        # 5. Check AI Memories
        print("\n💭 AI MEMORIES (ai_memories):")
        print("-" * 50)
        try:
            result = await conn.execute(text("SELECT COUNT(*) FROM ai_memories"))
            count = result.scalar()
            print(f"  Total memories: {count}")
        except Exception as e:
            print(f"  ❌ TABLE MISSING OR ERROR: {e}")

        # 6. Check pgvector extension
        print("\n🔌 PGVECTOR EXTENSION:")
        print("-" * 50)
        try:
            result = await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector'"))
            row = result.fetchone()
            if row:
                print(f"  ✅ pgvector installed (version: {row[0]})")
            else:
                print("  ❌ pgvector NOT installed")
        except Exception as e:
            print(f"  ❌ Error checking: {e}")

        # 7. Check portfolios and positions
        print("\n💼 PORTFOLIOS AND POSITIONS:")
        print("-" * 50)
        try:
            result = await conn.execute(text("SELECT COUNT(*) FROM portfolios"))
            portfolio_count = result.scalar()
            result = await conn.execute(text("SELECT COUNT(*) FROM positions WHERE deleted_at IS NULL"))
            position_count = result.scalar()
            print(f"  Portfolios: {portfolio_count}")
            print(f"  Active Positions: {position_count}")

            if portfolio_count > 0:
                result = await conn.execute(text("""
                    SELECT p.name, p.equity_balance, COUNT(pos.id) as pos_count
                    FROM portfolios p
                    LEFT JOIN positions pos ON p.id = pos.portfolio_id AND pos.deleted_at IS NULL
                    GROUP BY p.id, p.name, p.equity_balance
                """))
                portfolios = result.fetchall()
                for name, equity_balance, pos_count in portfolios:
                    print(f"    - {name}: {pos_count} positions, ${equity_balance:,.2f}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        # 8. Check agent conversations and messages
        print("\n💬 AGENT CONVERSATIONS & MESSAGES:")
        print("-" * 50)
        try:
            result = await conn.execute(text("SELECT COUNT(*) FROM agent_conversations"))
            conv_count = result.scalar()
            result = await conn.execute(text("SELECT COUNT(*) FROM agent_messages"))
            msg_count = result.scalar()
            print(f"  Conversations: {conv_count}")
            print(f"  Messages: {msg_count}")

            if conv_count > 0:
                result = await conn.execute(text("""
                    SELECT c.id, c.mode, c.metadata->>'portfolio_id' as portfolio_id,
                           COUNT(m.id) as msg_count, c.created_at
                    FROM agent_conversations c
                    LEFT JOIN agent_messages m ON m.conversation_id = c.id
                    GROUP BY c.id, c.mode, c.metadata, c.created_at
                    ORDER BY c.created_at DESC
                    LIMIT 5
                """))
                convs = result.fetchall()
                for conv_id, mode, portfolio_id, msg_count, created_at in convs:
                    print(f"    - {str(conv_id)[:8]}... mode={mode} portfolio={portfolio_id[:8] if portfolio_id else 'None'}... msgs={msg_count}")
        except Exception as e:
            print(f"  ❌ TABLE MISSING OR ERROR: {e}")

        # 9. Check portfolio_snapshots
        print("\n📸 PORTFOLIO SNAPSHOTS:")
        print("-" * 50)
        try:
            result = await conn.execute(text("SELECT COUNT(*) FROM portfolio_snapshots"))
            count = result.scalar()
            print(f"  Total snapshots: {count}")

            if count > 0:
                result = await conn.execute(text("""
                    SELECT snapshot_date, COUNT(*) as cnt
                    FROM portfolio_snapshots
                    GROUP BY snapshot_date
                    ORDER BY snapshot_date DESC
                    LIMIT 5
                """))
                dates = result.fetchall()
                for snapshot_date, cnt in dates:
                    print(f"    - {snapshot_date}: {cnt} snapshots")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        # 10. Check market_data_cache
        print("\n📈 MARKET DATA CACHE:")
        print("-" * 50)
        try:
            result = await conn.execute(text("SELECT COUNT(*) FROM market_data_cache"))
            count = result.scalar()
            print(f"  Total cached prices: {count}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

        # 11. Check alembic version
        print("\n🔄 ALEMBIC MIGRATION STATUS:")
        print("-" * 50)
        try:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            print(f"  Current version: {version}")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    await engine.dispose()

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_diagnostics())
