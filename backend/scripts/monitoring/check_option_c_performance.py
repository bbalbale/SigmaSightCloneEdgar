"""
Monitor Option C Performance Metrics

Tracks tool usage rate and performance to ensure Option C is working as expected.
Target: <20% tool usage, ~18-22s avg generation time, ~$0.02 avg cost
"""
import asyncio
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
from app.database import AsyncSessionLocal
from app.models.ai_insights import AIInsight


async def check_option_c_metrics():
    """Check Option C performance metrics"""

    async with AsyncSessionLocal() as db:
        # Get insights from last 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)

        result = await db.execute(
            select(
                func.count(AIInsight.id).label('total_insights'),
                func.avg(AIInsight.tool_calls_count).label('avg_tools'),
                func.sum(AIInsight.tool_calls_count == 0).label('interpreted_only'),
                func.avg(AIInsight.generation_time_ms).label('avg_time_ms'),
                func.avg(AIInsight.cost_usd).label('avg_cost'),
                func.percentile_cont(0.95).within_group(AIInsight.generation_time_ms).label('p95_time_ms')
            )
            .where(AIInsight.created_at >= cutoff)
        )

        stats = result.one()

        if stats.total_insights == 0:
            print("\nNo insights generated in the last 7 days")
            print("Go to http://localhost:3005/sigmasight-ai and click 'Generate'!")
            return

        # Calculate metrics
        interpretation_rate = (stats.interpreted_only / stats.total_insights) * 100
        tool_usage_rate = 100 - interpretation_rate

        print("\n" + "="*60)
        print("OPTION C PERFORMANCE METRICS (Last 7 Days)")
        print("="*60)

        print(f"\n📊 VOLUME:")
        print(f"   Total Insights: {stats.total_insights}")

        print(f"\n🔧 TOOL USAGE:")
        print(f"   Interpretation-only: {stats.interpreted_only}/{stats.total_insights} ({interpretation_rate:.1f}%)")
        print(f"   Tool usage rate: {tool_usage_rate:.1f}%")
        print(f"   Avg tools per insight: {stats.avg_tools:.2f}")
        print(f"   {'✅ PASS' if tool_usage_rate < 20 else '⚠️  WARN'} Target: <20% tool usage")

        print(f"\n⚡ PERFORMANCE:")
        print(f"   Avg generation time: {stats.avg_time_ms/1000:.1f}s")
        print(f"   P95 generation time: {stats.p95_time_ms/1000:.1f}s")
        print(f"   {'✅ PASS' if 15000 <= stats.avg_time_ms <= 25000 else '⚠️  WARN'} Target: 18-22s avg")

        print(f"\n💰 COST:")
        print(f"   Avg cost per insight: ${stats.avg_cost:.4f}")
        print(f"   {'✅ PASS' if stats.avg_cost <= 0.03 else '⚠️  WARN'} Target: <$0.03")

        print("\n" + "="*60)

        # Show recent insights breakdown
        print("\n📝 RECENT INSIGHTS BREAKDOWN:")

        recent = await db.execute(
            select(AIInsight)
            .where(AIInsight.created_at >= cutoff)
            .order_by(AIInsight.created_at.desc())
            .limit(10)
        )

        for insight in recent.scalars():
            tools_icon = "🔧" if insight.tool_calls_count > 0 else "💭"
            time_sec = insight.generation_time_ms / 1000
            print(f"   {tools_icon} {insight.created_at.strftime('%Y-%m-%d %H:%M')} | "
                  f"{time_sec:.1f}s | ${insight.cost_usd:.3f} | "
                  f"{insight.tool_calls_count} tools | {insight.title[:50]}")


async def main():
    await check_option_c_metrics()


if __name__ == "__main__":
    asyncio.run(main())
