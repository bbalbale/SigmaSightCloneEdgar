"""
Historical Price Seeding - Section 1.5 Implementation

Bootstraps market data cache with 180 days of real historical price data
from YFinance for all demo portfolio symbols. Required for correlation
and factor analysis calculations to work correctly from day 1.

IMPORTANT: This replaces the old CURRENT_PRICES hardcoded dictionary approach.
We now fetch real data from YFinance during seeding.
"""
import asyncio
from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import get_logger
from app.models.market_data import MarketDataCache
from app.models.positions import Position
from app.calculations.market_data import calculate_position_market_value
from app.db.fetch_historical_data import (
    fetch_and_store_historical_data,
    filter_stock_symbols
)

logger = get_logger(__name__)


async def get_all_portfolio_symbols(db: AsyncSession) -> List[str]:
    """Get all unique symbols from demo portfolios"""
    result = await db.execute(select(Position.symbol).distinct())
    symbols = [row[0] for row in result.fetchall()]
    logger.info(f"Found {len(symbols)} unique symbols in demo portfolios")
    return symbols


async def update_position_market_values(db: AsyncSession) -> int:
    """Update market values for all positions using newly seeded prices"""
    logger.info("💰 Calculating initial position market values...")

    # Get all positions
    result = await db.execute(select(Position))
    positions = result.scalars().all()

    updated_count = 0

    for position in positions:
        try:
            # Get current price for this symbol (most recent date)
            price_result = await db.execute(
                select(MarketDataCache.close).where(
                    MarketDataCache.symbol == position.symbol
                ).order_by(MarketDataCache.date.desc()).limit(1)
            )
            current_price = price_result.scalar_one_or_none()

            if current_price:
                # Calculate market value and P&L using Section 1.4.1 function
                calc_result = await calculate_position_market_value(position, current_price)

                # Update position with calculated values
                position.last_price = current_price
                position.market_value = calc_result["market_value"]
                position.unrealized_pnl = calc_result["unrealized_pnl"]
                position.updated_at = datetime.utcnow()

                updated_count += 1
                logger.debug(f"Updated {position.symbol}: MV=${calc_result['market_value']}, P&L=${calc_result['unrealized_pnl']}")
            else:
                logger.warning(f"⚠️ No price found for position {position.symbol}")

        except Exception as e:
            logger.error(f"❌ Failed to update market value for {position.symbol}: {e}")

    logger.info(f"✅ Updated market values for {updated_count} positions")
    return updated_count


async def seed_historical_prices(db: AsyncSession, days: int = 180) -> None:
    """
    Seed historical prices for all demo portfolio symbols using real YFinance data.

    This function replaces the old CURRENT_PRICES hardcoded approach with real
    historical data fetching from YFinance.

    Args:
        db: Database session
        days: Number of days of historical data to fetch (default 180)
    """
    logger.info("=" * 80)
    logger.info("HISTORICAL PRICE SEEDING")
    logger.info("=" * 80)
    logger.info(f"Fetching {days} days of real market data from YFinance")
    logger.info("This replaces the old hardcoded CURRENT_PRICES approach")
    logger.info("")

    # Get all symbols from demo portfolios
    all_symbols = await get_all_portfolio_symbols(db)

    # Filter to stocks/ETFs only (exclude options for now)
    stock_symbols = await filter_stock_symbols(all_symbols)

    if not stock_symbols:
        logger.warning("⚠️ No symbols found to seed")
        return

    logger.info(f"Symbols to seed: {', '.join(sorted(stock_symbols)[:15])}{'...' if len(stock_symbols) > 15 else ''}")
    logger.info("")

    # Fetch and store historical data using shared function
    try:
        records_per_symbol = await fetch_and_store_historical_data(
            db=db,
            symbols=stock_symbols,
            days=days,
            batch_size=10  # Process 10 symbols at a time for progress tracking
        )

        # Log summary
        successful = sum(1 for count in records_per_symbol.values() if count > 0)
        total_records = sum(records_per_symbol.values())

        logger.info(f"✅ Successfully seeded {successful}/{len(stock_symbols)} symbols")
        logger.info(f"✅ Total records stored: {total_records}")

        # Show sample of what was stored
        logger.info("")
        logger.info("Sample of stored data:")
        for symbol in sorted(stock_symbols)[:5]:
            count = records_per_symbol.get(symbol, 0)
            logger.info(f"  {symbol}: {count} days")

    except Exception as e:
        logger.error(f"❌ Historical price seeding failed: {e}")
        raise

    # Flush to ensure prices are available for position calculations
    await db.flush()

    # Update position market values using the newly seeded prices
    logger.info("")
    updated_positions = await update_position_market_values(db)

    logger.info("")
    logger.info("=" * 80)
    logger.info("SEEDING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"✅ Stored {total_records} price records for {successful} symbols")
    logger.info(f"✅ Updated market values for {updated_positions} positions")
    logger.info("🎯 Database ready for correlation and factor analysis!")
    logger.info("")


# Maintain backward compatibility - old function name redirects to new one
async def seed_initial_prices(db: AsyncSession) -> None:
    """
    Legacy function name for backward compatibility.
    Redirects to seed_historical_prices().
    """
    await seed_historical_prices(db, days=180)


async def main():
    """Main function for testing"""
    from app.database import get_async_session

    async with get_async_session() as db:
        try:
            await seed_historical_prices(db, days=180)
            await db.commit()
            logger.info("✅ Historical price seeding completed successfully")
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Historical price seeding failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
