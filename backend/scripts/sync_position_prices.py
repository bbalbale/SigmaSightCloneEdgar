"""
Sync Position Prices from MarketDataCache
Updates Position.last_price, market_value, and unrealized_pnl from current market data
"""
import asyncio
from decimal import Decimal
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.market_data import MarketDataCache
from app.core.logging import get_logger

logger = get_logger(__name__)


async def sync_position_prices():
    """Update all position prices from MarketDataCache"""
    async with AsyncSessionLocal() as db:
        logger.info("Starting position price sync from MarketDataCache")

        # Get all positions
        stmt = select(Position).options(selectinload(Position.portfolio))
        result = await db.execute(stmt)
        positions = result.scalars().all()

        logger.info(f"Found {len(positions)} positions to process")

        updated_count = 0
        skipped_count = 0
        error_count = 0
        total_value_change = Decimal("0")

        for position in positions:
            try:
                # Get latest market data for this symbol
                cache_stmt = (
                    select(MarketDataCache)
                    .where(MarketDataCache.symbol == position.symbol)
                    .order_by(MarketDataCache.updated_at.desc())
                )
                cache_result = await db.execute(cache_stmt)
                market_data = cache_result.scalars().first()

                if not market_data:
                    logger.warning(f"⚠️  No market data found for {position.symbol}")
                    skipped_count += 1
                    continue

                # Get current price from cache
                new_price = Decimal(str(market_data.close))
                old_price = position.last_price or position.entry_price

                # Calculate new values
                new_market_value = position.quantity * new_price
                new_unrealized_pnl = (new_price - position.entry_price) * position.quantity

                # Calculate change
                old_market_value = position.quantity * old_price
                value_change = new_market_value - old_market_value

                # Update position
                position.last_price = new_price
                position.market_value = new_market_value
                position.unrealized_pnl = new_unrealized_pnl

                updated_count += 1
                total_value_change += value_change

                # Log update
                price_change_pct = ((new_price - old_price) / old_price * 100) if old_price else 0
                logger.info(
                    f"✅ {position.symbol}: "
                    f"${float(old_price):,.2f} → ${float(new_price):,.2f} "
                    f"({price_change_pct:+.2f}%) | "
                    f"MV: ${float(old_market_value):,.2f} → ${float(new_market_value):,.2f} "
                    f"({float(value_change):+,.2f})"
                )

            except Exception as e:
                logger.error(f"❌ Error updating {position.symbol}: {str(e)}")
                error_count += 1
                continue

        # Commit all updates
        await db.commit()

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY: Position Price Sync")
        print("=" * 80)
        print(f"Total positions:     {len(positions)}")
        print(f"Updated:             {updated_count}")
        print(f"Skipped (no data):   {skipped_count}")
        print(f"Errors:              {error_count}")
        print(f"Total value change:  ${float(total_value_change):+,.2f}")
        print("=" * 80)

        return updated_count


if __name__ == "__main__":
    asyncio.run(sync_position_prices())
