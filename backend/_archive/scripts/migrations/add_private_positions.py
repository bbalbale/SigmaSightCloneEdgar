"""
Add private investment positions to the High Net Worth demo portfolio.
Based on the specifications in Ben Mock Portfolios.md
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.users import Portfolio, User
from app.models.positions import Position, PositionType
from app.core.logging import get_logger

logger = get_logger(__name__)

async def add_private_positions():
    """Add private investment positions to HNW portfolio."""

    async with AsyncSessionLocal() as session:
        # Find HNW portfolio
        result = await session.execute(
            select(Portfolio)
            .join(User, Portfolio.user_id == User.id)
            .where(User.email == 'demo_hnw@sigmasight.com')
        )
        portfolio = result.scalars().first()

        if not portfolio:
            logger.error("High Net Worth portfolio not found")
            return

        logger.info(f"Found portfolio: {portfolio.name} (ID: {portfolio.id})")

        # Define private investment positions based on Ben Mock Portfolios.md
        private_positions = [
            {
                'symbol': 'BX_PRIVATE_EQUITY',
                'position_type': PositionType.LONG,
                'quantity': Decimal('1'),  # Fund shares
                'entry_price': Decimal('285000.00'),
                'investment_class': 'PRIVATE',
                'investment_subtype': 'PRIVATE_EQUITY',
                'last_price': Decimal('285000.00'),
                'market_value': Decimal('285000.00'),
            },
            {
                'symbol': 'A16Z_VC_FUND',
                'position_type': PositionType.LONG,
                'quantity': Decimal('1'),  # Fund shares
                'entry_price': Decimal('142500.00'),
                'investment_class': 'PRIVATE',
                'investment_subtype': 'VENTURE_CAPITAL',
                'last_price': Decimal('142500.00'),
                'market_value': Decimal('142500.00'),
            },
            {
                'symbol': 'STARWOOD_REIT',
                'position_type': PositionType.LONG,
                'quantity': Decimal('1'),  # Fund shares
                'entry_price': Decimal('142500.00'),
                'investment_class': 'PRIVATE',
                'investment_subtype': 'PRIVATE_REIT',
                'last_price': Decimal('142500.00'),
                'market_value': Decimal('142500.00'),
            },
            {
                'symbol': 'TWO_SIGMA_FUND',
                'position_type': PositionType.LONG,
                'quantity': Decimal('1'),  # Fund shares
                'entry_price': Decimal('142500.00'),
                'investment_class': 'PRIVATE',
                'investment_subtype': 'HEDGE_FUND',
                'last_price': Decimal('142500.00'),
                'market_value': Decimal('142500.00'),
            }
        ]

        # Check for existing private positions to avoid duplicates
        existing_result = await session.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio.id)
            .where(Position.investment_class == 'PRIVATE')
        )
        existing_private = existing_result.scalars().all()

        if existing_private:
            logger.warning(f"Found {len(existing_private)} existing private positions. Skipping to avoid duplicates.")
            for pos in existing_private:
                logger.info(f"  - {pos.symbol}: {pos.investment_subtype}")
            return

        # Add private positions
        added_count = 0
        for pos_data in private_positions:
            position = Position(
                id=uuid4(),
                portfolio_id=portfolio.id,
                symbol=pos_data['symbol'],
                position_type=pos_data['position_type'],
                quantity=pos_data['quantity'],
                entry_price=pos_data['entry_price'],
                entry_date=datetime.now(timezone.utc).date(),
                investment_class=pos_data['investment_class'],
                investment_subtype=pos_data['investment_subtype'],
                last_price=pos_data['last_price'],
                market_value=pos_data['market_value'],
                unrealized_pnl=Decimal('0'),  # No P&L for initial entry
                realized_pnl=Decimal('0'),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(position)
            added_count += 1
            logger.info(f"Added private position: {position.symbol} ({position.investment_subtype})")

        await session.commit()
        logger.info(f"Successfully added {added_count} private investment positions")

        # Verify the additions
        all_positions_result = await session.execute(
            select(Position)
            .where(Position.portfolio_id == portfolio.id)
            .order_by(Position.investment_class, Position.symbol)
        )
        all_positions = all_positions_result.scalars().all()

        # Group by investment class for summary
        by_class = {}
        for pos in all_positions:
            class_name = pos.investment_class or 'UNKNOWN'
            if class_name not in by_class:
                by_class[class_name] = []
            by_class[class_name].append(pos)

        logger.info("\nUpdated portfolio summary:")
        logger.info(f"Total positions: {len(all_positions)}")
        for class_name in sorted(by_class.keys()):
            logger.info(f"  {class_name}: {len(by_class[class_name])} positions")

if __name__ == "__main__":
    asyncio.run(add_private_positions())