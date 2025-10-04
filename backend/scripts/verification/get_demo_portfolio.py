#!/usr/bin/env python
"""Get the portfolio ID for a demo user"""

import asyncio
from app.database import get_async_session
from app.models.users import User, Portfolio
from sqlalchemy import select

async def get_portfolio_for_user(email: str):
    async with get_async_session() as db:
        # Get user
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User not found: {email}")
            return
        
        # Get portfolio
        stmt = select(Portfolio).where(Portfolio.user_id == user.id)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if portfolio:
            print(f"User: {email}")
            print(f"Portfolio ID: {portfolio.id}")
            print(f"Portfolio Name: {portfolio.name}")
        else:
            print(f"No portfolio found for {email}")

asyncio.run(get_portfolio_for_user("demo_individual@sigmasight.com"))