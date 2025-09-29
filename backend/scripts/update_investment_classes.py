"""
Update existing positions with investment_class field
"""
import asyncio
from sqlalchemy import update
from app.database import get_async_session
from app.models.positions import Position
from app.core.logging import get_logger

logger = get_logger(__name__)

def determine_investment_class(symbol: str) -> str:
    """Determine investment class from symbol

    Returns:
        'OPTION' for options (symbols with expiry/strike pattern)
        'PUBLIC' for regular stocks and ETFs
        'PRIVATE' for anything else
    """
    # Check if it's an option (has expiry date and strike price pattern)
    if len(symbol) > 10 and any(char in symbol for char in ['C', 'P']):
        return 'OPTION'
    # Everything else is public equity (stocks, ETFs, mutual funds)
    else:
        return 'PUBLIC'

async def update_investment_classes():
    """Update all positions with appropriate investment_class"""

    async with get_async_session() as db:
        try:
            # Get all positions
            from sqlalchemy import select
            stmt = select(Position)
            result = await db.execute(stmt)
            positions = result.scalars().all()

            logger.info(f"Found {len(positions)} positions to update")

            updated_count = 0
            for position in positions:
                investment_class = determine_investment_class(position.symbol)

                # Only update if different or null
                if position.investment_class != investment_class:
                    position.investment_class = investment_class
                    db.add(position)
                    updated_count += 1
                    logger.info(f"Updated {position.symbol}: investment_class = {investment_class}")

            await db.commit()
            logger.info(f"✅ Updated {updated_count} positions with investment_class")

        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update investment classes: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(update_investment_classes())