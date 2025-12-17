#!/usr/bin/env python
"""
Create batch_run_tracking table if it doesn't exist.
Run this on Railway SSH: python scripts/railway/create_batch_run_tracking.py
"""
import asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal


async def create_table():
    async with AsyncSessionLocal() as db:
        await db.execute(text('''
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
        '''))
        await db.execute(text('CREATE INDEX IF NOT EXISTS idx_batch_run_date ON batch_run_tracking (run_date)'))
        await db.commit()
        print('batch_run_tracking table created successfully')


if __name__ == "__main__":
    asyncio.run(create_table())
