"""Get portfolio equity from portfolios table"""
import asyncio
from app.database import get_async_session
from sqlalchemy import text

async def get_portfolio_equity():
    async with get_async_session() as db:
        result = await db.execute(text('''
            SELECT
                p.id as portfolio_id,
                p.name as portfolio_name,
                p.equity_balance as current_equity_balance,
                u.email
            FROM portfolios p
            JOIN users u ON p.user_id = u.id
            WHERE u.email LIKE 'demo%@sigmasight.com'
            ORDER BY u.email
        '''))

        portfolios = result.fetchall()

        print('Portfolio Equity Balance (from portfolios table):')
        print('=' * 80)
        for row in portfolios:
            print(f'Portfolio ID: {row.portfolio_id}')
            print(f'Name: {row.portfolio_name}')
            print(f'Email: {row.email}')
            print(f'Current Equity Balance: ${float(row.current_equity_balance or 0):,.2f}')
            print('-' * 80)

if __name__ == "__main__":
    asyncio.run(get_portfolio_equity())
