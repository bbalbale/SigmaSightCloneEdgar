"""
Reset daily insights rate limit

This script clears old insights from today to reset the 10-per-day limit.
Useful for testing Option C implementation.
"""
import asyncio
from datetime import datetime, date
from sqlalchemy import select, delete
from app.database import AsyncSessionLocal
from app.models.ai_insights import AIInsight


async def reset_daily_insights():
    """Delete today's insights to reset rate limit"""

    async with AsyncSessionLocal() as db:
        # Get today's date (start of day)
        today = datetime.combine(date.today(), datetime.min.time())

        # Count insights from today
        count_result = await db.execute(
            select(AIInsight)
            .where(AIInsight.created_at >= today)
        )
        insights_today = count_result.scalars().all()

        print(f"\nFound {len(insights_today)} insights from today")

        if len(insights_today) == 0:
            print("No insights to delete. Rate limit is already clear.")
            return

        # Show which portfolios
        portfolio_counts = {}
        for insight in insights_today:
            pid = str(insight.portfolio_id)
            portfolio_counts[pid] = portfolio_counts.get(pid, 0) + 1

        print("\nInsights by portfolio:")
        for pid, count in portfolio_counts.items():
            print(f"  {pid}: {count} insights")

        # Ask for confirmation
        response = input("\nDelete these insights to reset rate limit? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return

        # Delete insights from today
        await db.execute(
            delete(AIInsight)
            .where(AIInsight.created_at >= today)
        )
        await db.commit()

        print(f"\n✅ Deleted {len(insights_today)} insights")
        print("Rate limit reset! You can now generate 10 more insights per portfolio today.")


if __name__ == "__main__":
    asyncio.run(reset_daily_insights())
