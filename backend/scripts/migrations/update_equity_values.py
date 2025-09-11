"""
Update equity balances for demo portfolios
"""
import asyncio
from sqlalchemy import update
from app.database import get_async_session
from app.models.users import Portfolio
from uuid import UUID

async def update_equity_values():
    """Update equity values to new amounts"""
    
    portfolios = [
        {
            'id': UUID('1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe'),
            'name': 'Demo Individual',
            'new_equity': 600000.00
        },
        {
            'id': UUID('e23ab931-a033-edfe-ed4f-9d02474780b4'),
            'name': 'Demo HNW',
            'new_equity': 2000000.00
        },
        {
            'id': UUID('fcd71196-e93e-f000-5a74-31a9eead3118'),
            'name': 'Demo Hedge Fund',
            'new_equity': 4000000.00
        }
    ]
    
    async with get_async_session() as db:
        print("Updating equity balances...")
        print("-" * 50)
        
        for portfolio in portfolios:
            stmt = (
                update(Portfolio)
                .where(Portfolio.id == portfolio['id'])
                .values(equity_balance=portfolio['new_equity'])
            )
            await db.execute(stmt)
            print(f"{portfolio['name']}: ${portfolio['new_equity']:,.2f}")
        
        await db.commit()
        print("-" * 50)
        print("✅ Equity balances updated successfully!")

if __name__ == "__main__":
    asyncio.run(update_equity_values())