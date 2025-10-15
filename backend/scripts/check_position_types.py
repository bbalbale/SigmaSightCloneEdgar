"""
Check Position Types for All Portfolios
"""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import Portfolio
from app.models.positions import Position

async def main():
    async with AsyncSessionLocal() as db:
        # Get all portfolios
        stmt = select(Portfolio)
        result = await db.execute(stmt)
        portfolios = result.scalars().all()

        for portfolio in portfolios:
            print(f"\n{'='*80}")
            print(f"Portfolio: {portfolio.name}")
            print(f"ID: {portfolio.id}")
            print(f"{'='*80}")

            # Get positions with their types
            pos_stmt = select(Position).where(Position.portfolio_id == portfolio.id)
            pos_result = await db.execute(pos_stmt)
            positions = pos_result.scalars().all()

            print(f"\nTotal positions: {len(positions)}")

            # Count by position_type
            type_counts = {}
            for p in positions:
                position_type = str(p.position_type) if p.position_type else "NULL"
                type_counts[position_type] = type_counts.get(position_type, 0) + 1

            print(f"\nPosition types:")
            for ptype, count in sorted(type_counts.items()):
                print(f"  {ptype}: {count}")

            # Show sample positions
            print(f"\nSample positions (first 5):")
            for p in positions[:5]:
                print(f"  {p.symbol:10s} - Type: {p.position_type} - InvestClass: {p.investment_class}")

if __name__ == "__main__":
    asyncio.run(main())
