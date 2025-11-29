"""Quick check of fundamentals_last_fetched timestamps"""
import asyncio
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.market_data import CompanyProfile
from app.models.fundamentals import IncomeStatement


async def check():
    async with AsyncSessionLocal() as db:
        # Count profiles with timestamps
        timestamp_result = await db.execute(
            select(func.count(CompanyProfile.symbol)).where(
                CompanyProfile.fundamentals_last_fetched.isnot(None)
            )
        )
        timestamp_count = timestamp_result.scalar()

        # Count unique symbols with fundamental data
        fundamental_result = await db.execute(
            select(func.count(func.distinct(IncomeStatement.symbol)))
        )
        fundamental_count = fundamental_result.scalar()

        print(f"\n✅ Timestamp Check:")
        print(f"   Symbols with fundamental data: {fundamental_count}")
        print(f"   Company profiles with timestamp: {timestamp_count}")
        print(f"   Match: {'YES ✅' if timestamp_count >= fundamental_count else 'NO ❌'}\n")


if __name__ == "__main__":
    asyncio.run(check())
