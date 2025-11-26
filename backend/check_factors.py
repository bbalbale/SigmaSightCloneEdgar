#!/usr/bin/env python3
import asyncio
from sqlalchemy import select, text
from app.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as db:
        # Get all active factors
        result = await db.execute(text("""
            SELECT name, factor_type, is_active, display_order
            FROM factor_definitions
            WHERE is_active = true AND factor_type IN ('style', 'macro')
            ORDER BY display_order, name
        """))

        print('\n=== ACTIVE FACTORS (style + macro) ===')
        for row in result:
            print(f'  {row[0]:30} ({row[1]:8}) order={row[3]}')

        # Check latest exposure date for HNW portfolio
        result2 = await db.execute(text("""
            SELECT
                fe.calculation_date,
                COUNT(DISTINCT fe.factor_id) as num_factors,
                string_agg(DISTINCT fd.name, ', ' ORDER BY fd.name) as factor_names
            FROM factor_exposures fe
            JOIN factor_definitions fd ON fe.factor_id = fd.id
            WHERE fe.portfolio_id = 'e23ab931-a033-edfe-ed4f-9d02474780b4'
            GROUP BY fe.calculation_date
            ORDER BY fe.calculation_date DESC
            LIMIT 5
        """))

        print('\n=== RECENT CALCULATION DATES ===')
        for row in result2:
            print(f'{row[0]}: {row[1]} factors - {row[2]}')

asyncio.run(check())
