"""
Check which portfolios have positions with tags
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.positions import Position
from app.models.position_tags import PositionTag
from app.models.tags_v2 import TagV2

async def check_portfolios_with_tags():
    async with get_async_session() as session:
        print("\n" + "="*60)
        print("CHECKING PORTFOLIOS AND THEIR TAGGED POSITIONS")
        print("="*60)

        # Get all portfolios with their positions that have tags
        result = await session.execute(
            select(Portfolio)
            .options(
                selectinload(Portfolio.positions).selectinload(Position.position_tags).selectinload(PositionTag.tag)
            )
        )
        portfolios = result.scalars().all()

        print(f"\n[INFO] Total portfolios: {len(portfolios)}")

        for portfolio in portfolios:
            # Count positions with tags
            positions_with_tags = [
                pos for pos in portfolio.positions
                if pos.position_tags and len(pos.position_tags) > 0
            ]

            if positions_with_tags:
                print(f"\n[PORTFOLIO] ID: {portfolio.id}")
                print(f"  Name: {portfolio.name}")
                print(f"  Total positions: {len(portfolio.positions)}")
                print(f"  Positions with tags: {len(positions_with_tags)}")

                # Show first 5 tagged positions
                print(f"\n  Tagged positions:")
                for pos in positions_with_tags[:5]:
                    tags = [pt.tag.name for pt in pos.position_tags if pt.tag]
                    print(f"    * {pos.symbol:10} | Tags: {', '.join(tags)}")

                if len(positions_with_tags) > 5:
                    print(f"    ... and {len(positions_with_tags) - 5} more")

        # Also get the demo user portfolios specifically
        demo_emails = [
            'demo_hnw@sigmasight.com',
            'demo_individual@sigmasight.com',
            'demo_hedgefundstyle@sigmasight.com'
        ]

        print("\n" + "-"*60)
        print("DEMO USER PORTFOLIOS:")
        print("-"*60)

        from app.models.users import User
        for email in demo_emails:
            result = await session.execute(
                select(User)
                .where(User.email == email)
                .options(selectinload(User.portfolios))
            )
            user = result.scalar_one_or_none()

            if user and user.portfolios:
                for portfolio in user.portfolios:
                    print(f"\n[{email}]")
                    print(f"  Portfolio ID: {portfolio.id}")
                    print(f"  Portfolio Name: {portfolio.name}")

if __name__ == "__main__":
    asyncio.run(check_portfolios_with_tags())