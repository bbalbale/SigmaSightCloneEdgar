#!/usr/bin/env python
"""
Collect pgvector performance diagnostics on Railway.

Usage (Railway shell or railway run):
  uv run python scripts/railway/pgvector_performance_diagnostic.py
  uv run python scripts/railway/pgvector_performance_diagnostic.py --queryid <id>

What it captures:
1) Runtime settings: work_mem, shared_buffers, effective_cache_size, ivfflat/hnsw knobs
2) Top queries by total_time + vector-related queries (pg_stat_statements)
3) Vector index definitions
4) Bloat/stats signals for vector tables
5) Index usage counters for vector indexes
6) Optional: full EXPLAIN (ANALYZE, BUFFERS, VERBOSE) for a specific queryid

Outputs to stdout for copy/paste back to the team.
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    return url


def connect():
    db_url = get_db_url()
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    conn = psycopg2.connect(db_url)
    conn.set_session(autocommit=True)
    return conn


def header(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def fetch_all(cur, sql, params=None):
    cur.execute(sql, params or {})
    return cur.fetchall()


def show_settings(cur):
    header("Settings")
    settings = [
        "server_version",
        "max_parallel_workers_per_gather",
        "work_mem",
        "shared_buffers",
        "effective_cache_size",
        "ivfflat.probes",
        "hnsw.ef_search",
        "hnsw.ef_construction",
    ]
    for s in settings:
        try:
            cur.execute(f"SHOW {s};")
            row = cur.fetchone()
            # RealDictCursor returns a dict keyed by the setting name; fall back to first value
            value = next(iter(row.values())) if isinstance(row, dict) else row[0]
            print(f"{s}: {value}")
        except Exception as e:
            print(f"{s}: not supported ({e.__class__.__name__})")
            try:
                cur.connection.rollback()
            except Exception:
                pass


def show_top_queries(cur):
    header("Top 15 by total_time (pg_stat_statements)")
    try:
        rows = fetch_all(
            cur,
            """
            SELECT queryid, calls, round(total_time/1000,2) AS total_s,
                   round(mean_time,2) AS mean_ms, rows
            FROM pg_stat_statements
            ORDER BY total_time DESC
            LIMIT 15;
            """,
        )
        for r in rows:
            print(
                f"queryid={r['queryid']} calls={r['calls']} total_s={r['total_s']} "
                f"mean_ms={r['mean_ms']} rows={r['rows']}"
            )

        header("Vector-ish queries (pg_stat_statements)")
        rows = fetch_all(
            cur,
            """
            SELECT queryid, calls, round(total_time/1000,2) AS total_s,
                   round(mean_time,2) AS mean_ms, rows, query
            FROM pg_stat_statements
            WHERE query ILIKE '%<->%' OR query ILIKE '%vector%' OR query ILIKE '%embedding%'
            ORDER BY total_time DESC
            LIMIT 10;
            """,
        )
        for r in rows:
            print(
                f"queryid={r['queryid']} calls={r['calls']} total_s={r['total_s']} "
                f"mean_ms={r['mean_ms']} rows={r['rows']}"
            )
            print(f"query: {r['query']}\n")
    except Exception as e:
        print(f"pg_stat_statements not available ({e.__class__.__name__}: {e})")
        try:
            cur.connection.rollback()
        except Exception:
            pass


def show_vector_indexes(cur):
    header("Vector index definitions")
    rows = fetch_all(
        cur,
        """
        SELECT schemaname, tablename, indexname, indexdef
        FROM pg_indexes
        WHERE indexdef ILIKE '%vector%'
        ORDER BY tablename, indexname;
        """,
    )
    for r in rows:
        print(
            f"{r['schemaname']}.{r['tablename']} :: {r['indexname']} :: {r['indexdef']}"
        )


def show_table_stats(cur):
    header("Table stats (vector tables)")
    rows = fetch_all(
        cur,
        """
        WITH vt AS (
          SELECT DISTINCT tablename FROM pg_indexes WHERE indexdef ILIKE '%vector%'
        )
        SELECT s.schemaname, s.relname, s.n_live_tup, s.n_dead_tup,
               s.vacuum_count, s.analyze_count
        FROM pg_stat_all_tables s
        JOIN vt v ON v.tablename = s.relname
        ORDER BY s.n_live_tup DESC;
        """,
    )
    for r in rows:
        print(
            f"{r['schemaname']}.{r['relname']} "
            f"live={r['n_live_tup']} dead={r['n_dead_tup']} "
            f"vacuum={r['vacuum_count']} analyze={r['analyze_count']}"
        )


def show_index_usage(cur):
    header("Index usage (vector tables)")
    rows = fetch_all(
        cur,
        """
        WITH vt AS (
          SELECT DISTINCT tablename FROM pg_indexes WHERE indexdef ILIKE '%vector%'
        )
        SELECT s.relname, i.indexrelname, i.idx_scan, i.idx_tup_read, i.idx_tup_fetch
        FROM pg_stat_all_indexes i
        JOIN pg_stat_all_tables s ON s.relid = i.relid
        JOIN vt v ON v.tablename = s.relname
        ORDER BY i.idx_scan DESC;
        """,
    )
    for r in rows:
        print(
            f"{r['relname']} :: {r['indexrelname']} "
            f"idx_scan={r['idx_scan']} idx_tup_read={r['idx_tup_read']} "
            f"idx_tup_fetch={r['idx_tup_fetch']}"
        )


def show_query_and_plan(cur, queryid: int):
    try:
        header(f"Query text for queryid={queryid}")
        cur.execute(
            "SELECT query FROM pg_stat_statements WHERE queryid = %s;", (queryid,)
        )
        row = cur.fetchone()
        if not row:
            print("Query not found")
            return
        query = row[0]
        print(query)

        header(f"EXPLAIN (ANALYZE, BUFFERS, VERBOSE) for queryid={queryid}")
        cur.execute("SET track_io_timing = on;")
        cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, VERBOSE) {query}")
        for plan_line in cur.fetchall():
            print(plan_line[0])
    except Exception as e:
        print(f"Could not get plan for queryid={queryid} ({e.__class__.__name__}: {e})")
        try:
            cur.connection.rollback()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="pgvector performance diagnostic")
    parser.add_argument("--queryid", type=int, help="queryid to explain (from pg_stat_statements)")
    args = parser.parse_args()

    conn = connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    show_settings(cur)
    show_top_queries(cur)
    show_vector_indexes(cur)
    show_table_stats(cur)
    show_index_usage(cur)

    if args.queryid is not None:
        show_query_and_plan(cur, args.queryid)

    cur.close()
    conn.close()


if __name__ == "__main__":
    # Ensure project root on sys.path for parity with other scripts
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    main()
