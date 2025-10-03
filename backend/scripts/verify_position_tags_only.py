"""
Verify ONLY position_tags table entries (not strategies or anything else)
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from app.database import get_async_session

async def verify_position_tags():
    async with get_async_session() as session:
        print("\n" + "="*60)
        print("CHECKING POSITION_TAGS TABLE DIRECTLY")
        print("="*60)

        # Direct SQL query to position_tags table
        result = await session.execute(text("""
            SELECT
                pt.id,
                pt.position_id,
                pt.tag_id,
                pt.assigned_at,
                p.symbol,
                p.portfolio_id,
                t.name as tag_name,
                port.name as portfolio_name
            FROM position_tags pt
            JOIN positions p ON pt.position_id = p.id
            JOIN tags_v2 t ON pt.tag_id = t.id
            JOIN portfolios port ON p.portfolio_id = port.id
            ORDER BY port.name, p.symbol, t.name
        """))

        rows = result.fetchall()

        print(f"\n[FACT] Total rows in position_tags table: {len(rows)}")

        if rows:
            # Group by portfolio
            portfolios = {}
            for row in rows:
                portfolio_name = row.portfolio_name
                if portfolio_name not in portfolios:
                    portfolios[portfolio_name] = []
                portfolios[portfolio_name].append(row)

            for portfolio_name, positions in portfolios.items():
                print(f"\n[PORTFOLIO] {portfolio_name}")
                print(f"  Position-tag relationships: {len(positions)}")

                # Group by position
                position_tags = {}
                for row in positions:
                    if row.symbol not in position_tags:
                        position_tags[row.symbol] = []
                    position_tags[row.symbol].append(row.tag_name)

                print(f"  Unique positions with tags: {len(position_tags)}")
                print("\n  Details (first 10):")
                for i, (symbol, tags) in enumerate(list(position_tags.items())[:10]):
                    print(f"    {symbol:15} -> {', '.join(tags)}")
                    if i >= 9 and len(position_tags) > 10:
                        print(f"    ... and {len(position_tags) - 10} more positions")

        # Also check when these were created
        print("\n" + "-"*60)
        print("CHECKING WHEN TAGS WERE ASSIGNED:")
        result = await session.execute(text("""
            SELECT
                DATE(assigned_at) as date,
                COUNT(*) as count
            FROM position_tags
            GROUP BY DATE(assigned_at)
            ORDER BY date DESC
            LIMIT 10
        """))

        date_rows = result.fetchall()
        for row in date_rows:
            print(f"  {row.date}: {row.count} tags assigned")

if __name__ == "__main__":
    asyncio.run(verify_position_tags())