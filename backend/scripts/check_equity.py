import asyncio
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio

async def check_equity():
    async with get_async_session() as db:
        result = await db.execute(select(Portfolio.id, Portfolio.name, Portfolio.equity_balance))
        portfolios = result.all()
        print("\n=== Portfolio Equity Balances ===")
        for p in portfolios:
            if p.equity_balance:
                print(f"{p.name}: Equity = ${p.equity_balance:,.2f}")
            else:
                print(f"{p.name}: No equity set")

if __name__ == "__main__":
    asyncio.run(check_equity())