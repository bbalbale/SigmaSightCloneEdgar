#!/usr/bin/env python3
"""
Quick script to check database content for testing
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.users import Portfolio, User
from app.models.positions import Position
from app.models.market_data import FactorDefinition
from sqlalchemy import select, func


async def check_database():
    """Check database content"""
    print("Database Content Check")
    print("=" * 30)
    
    async with AsyncSessionLocal() as db:
        # Check users
        stmt = select(func.count(User.id))
        result = await db.execute(stmt)
        user_count = result.scalar()
        print(f"Users: {user_count}")
        
        # Check portfolios
        stmt = select(func.count(Portfolio.id))
        result = await db.execute(stmt)
        portfolio_count = result.scalar()
        print(f"Portfolios: {portfolio_count}")
        
        if portfolio_count > 0:
            # Show portfolio details
            stmt = select(Portfolio.id, Portfolio.name)
            result = await db.execute(stmt)
            portfolios = result.all()
            print("\nPortfolio Details:")
            for portfolio_id, name in portfolios:
                print(f"  {name} (ID: {portfolio_id})")
        
        # Check positions
        stmt = select(func.count(Position.id))
        result = await db.execute(stmt)
        position_count = result.scalar()
        print(f"Total Positions: {position_count}")
        
        # Check active positions
        stmt = select(func.count(Position.id)).where(Position.exit_date.is_(None))
        result = await db.execute(stmt)
        active_position_count = result.scalar()
        print(f"Active Positions: {active_position_count}")
        
        if active_position_count > 0:
            # Show sample positions
            stmt = select(Position.id, Position.symbol, Position.quantity, Position.portfolio_id).where(
                Position.exit_date.is_(None)
            ).limit(5)
            result = await db.execute(stmt)
            positions = result.all()
            print("\nSample Active Positions:")
            for pos_id, symbol, quantity, portfolio_id in positions:
                print(f"  {symbol}: {quantity} shares (Portfolio: {portfolio_id})")
        
        # Check factor definitions
        stmt = select(func.count(FactorDefinition.id))
        result = await db.execute(stmt)
        factor_count = result.scalar()
        print(f"Factor Definitions: {factor_count}")
        
        if factor_count > 0:
            stmt = select(FactorDefinition.name, FactorDefinition.etf_proxy).where(
                FactorDefinition.is_active == True
            )
            result = await db.execute(stmt)
            factors = result.all()
            print("\nActive Factors:")
            for name, etf_proxy in factors:
                print(f"  {name} ({etf_proxy})")


if __name__ == "__main__":
    asyncio.run(check_database())