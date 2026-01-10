"""Check snapshot status for all portfolios on Railway"""
import asyncio
import os

# Fix Railway DATABASE_URL format
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    if db_url.startswith('postgresql://'):
        os.environ['DATABASE_URL'] = db_url.replace('postgresql://', 'postgresql+asyncpg://', 1)

from sqlalchemy import text
from app.database import AsyncSessionLocal
from datetime import date, timedelta

async def main():
    async with AsyncSessionLocal() as db:
        # Get snapshot summary per portfolio
        result = await db.execute(text('''
            SELECT
                p.name,
                MIN(ps.snapshot_date) as first_snapshot,
                MAX(ps.snapshot_date) as last_snapshot,
                COUNT(ps.id) as snapshot_count
            FROM portfolios p
            LEFT JOIN portfolio_snapshots ps ON p.id = ps.portfolio_id
            WHERE p.deleted_at IS NULL
            GROUP BY p.id, p.name
            ORDER BY last_snapshot DESC NULLS LAST
        '''))

        rows = result.fetchall()
        today = date.today()

        print('=' * 95)
        print(f'PORTFOLIO SNAPSHOT STATUS - Railway Production (Today: {today})')
        print('=' * 95)
        print(f'{"Portfolio":<42} {"First":<12} {"Last":<12} {"Count":<8} Status')
        print('-' * 95)

        current = 0
        behind = 0
        no_data = 0

        for name, first_snap, last_snap, count in rows:
            name_short = name[:39] + '...' if len(name) > 42 else name
            first_str = str(first_snap) if first_snap else 'N/A'
            last_str = str(last_snap) if last_snap else 'N/A'

            if last_snap is None:
                status = '❌ NO DATA'
                no_data += 1
            elif last_snap >= today:
                status = '✅ Current'
                current += 1
            elif last_snap >= today - timedelta(days=1):
                status = '✅ 1 day behind'
                current += 1
            else:
                days_behind = (today - last_snap).days
                status = f'⚠️  {days_behind} days behind'
                behind += 1

            print(f'{name_short:<42} {first_str:<12} {last_str:<12} {count:<8} {status}')

        print('=' * 95)
        print(f'\nSUMMARY: {current} current, {behind} behind, {no_data} no data')
        print('=' * 95)

if __name__ == "__main__":
    asyncio.run(main())
