#!/usr/bin/env python
"""
Create batch_run_tracking table if it doesn't exist.
Run this on Railway SSH: python scripts/railway/create_batch_run_tracking.py

Uses the db_utils module which auto-detects environment and uses the correct
database driver (psycopg2 for Railway, handles asyncpg URLs for local).
"""
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.db_utils import get_sync_cursor, is_railway_environment


def create_table():
    print(f"Environment: {'Railway' if is_railway_environment() else 'Local'}")
    print("Connecting to database...")

    with get_sync_cursor() as cur:
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


if __name__ == "__main__":
    create_table()
