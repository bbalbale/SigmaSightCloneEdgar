"""Get demo portfolio information for reprocessing"""
import asyncio
from app.database import get_async_session
from sqlalchemy import text

async def get_demo_portfolios():
    async with get_async_session() as db:
        result = await db.execute(text('''
            SELECT
                p.id as portfolio_id,
                p.name as portfolio_name,
                u.email,
                ps.equity_balance as starting_equity
            FROM portfolios p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN LATERAL (
                SELECT equity_balance
                FROM portfolio_snapshots
                WHERE portfolio_id = p.id
                AND snapshot_date = '2025-09-30'
                ORDER BY snapshot_date ASC
                LIMIT 1
            ) ps ON true
            WHERE u.email LIKE 'demo%@sigmasight.com'
            ORDER BY u.email
        '''))

        portfolios = result.fetchall()

        print('Demo Portfolios:')
        print('=' * 80)
        for row in portfolios:
            print(f'Portfolio ID: {row.portfolio_id}')
            print(f'Name: {row.portfolio_name}')
            print(f'Email: {row.email}')
            print(f'Starting Equity (Sept 30): ${float(row.starting_equity or 0):,.2f}')
            print('-' * 80)

if __name__ == "__main__":
    asyncio.run(get_demo_portfolios())
