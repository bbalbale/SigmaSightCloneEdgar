"""Emergency script to seed positions when they're missing"""
import asyncio
from app.database import AsyncSessionLocal
from app.db.seed_demo_portfolios import seed_demo_portfolios
from app.models.positions import Position
from sqlalchemy import select, func

async def seed_positions():
    async with AsyncSessionLocal() as db:
        # Check current state
        position_count = await db.scalar(select(func.count(Position.id)))
        print(f"Current positions in database: {position_count}")

        if position_count > 0:
            print(f"✅ Positions already exist. No action needed.")
            return

        print("❌ No positions found. Seeding positions now...")

        # Seed the portfolios and positions
        result = await seed_demo_portfolios(db)

        # Explicitly commit the transaction
        await db.commit()

        # Verify positions were created
        new_count = await db.scalar(select(func.count(Position.id)))
        print(f"✅ Seeding complete! New position count: {new_count}")

        # Show sample positions
        positions = await db.execute(select(Position).limit(5))
        print("\nSample positions created:")
        for p in positions.scalars():
            print(f"  - {p.symbol}: {p.quantity} shares (Portfolio: {p.portfolio_id})")

        return result

if __name__ == "__main__":
    asyncio.run(seed_positions())