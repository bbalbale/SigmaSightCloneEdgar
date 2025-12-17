#!/usr/bin/env python
"""
Create batch_run_tracking table if it doesn't exist.
Run this on Railway SSH: python scripts/railway/create_batch_run_tracking.py
"""
import os
import psycopg2


def create_table():
    # Get DATABASE_URL and ensure it works with psycopg2
    database_url = os.environ.get("DATABASE_URL", "")

    # Remove asyncpg prefix if present, psycopg2 needs plain postgresql://
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return

    print(f"Connecting to database...")

    conn = psycopg2.connect(database_url)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS batch_run_tracking (
            id UUID NOT NULL PRIMARY KEY,
            run_date DATE NOT NULL UNIQUE,
            phase_1_status VARCHAR(20),
            phase_2_status VARCHAR(20),
            phase_3_status VARCHAR(20),
            phase_1_duration_seconds INTEGER,
            phase_2_duration_seconds INTEGER,
            phase_3_duration_seconds INTEGER,
            portfolios_processed INTEGER,
            symbols_fetched INTEGER,
            data_coverage_pct NUMERIC(5, 2),
            error_message TEXT,
            completed_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
        )
    ''')

    cur.execute('CREATE INDEX IF NOT EXISTS idx_batch_run_date ON batch_run_tracking (run_date)')

    print('batch_run_tracking table created successfully')

    cur.close()
    conn.close()


if __name__ == "__main__":
    create_table()
