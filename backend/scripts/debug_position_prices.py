"""
Debug script to check if position prices are being updated
"""
import asyncio
from sqlalchemy import select, func
from app.database import get_async_session
from app.models.positions import Position
from app.models.users import Portfolio


async def check_position_price_updates():
    """Check when position prices were last updated"""
    async with get_async_session() as db:
        print("\n" + "="*80)
        print("POSITION PRICE UPDATE STATUS")
        print("="*80)

        # Get all portfolios
        portfolio_query = select(Portfolio)
        portfolio_result = await db.execute(portfolio_query)
        portfolios = portfolio_result.scalars().all()

        for portfolio in portfolios:
            print(f"\n{'='*80}")
            print(f"Portfolio: {portfolio.name}")
            print(f"{'='*80}")

            # Get all positions for this portfolio
            position_query = select(Position).where(Position.portfolio_id == portfolio.id)
            position_result = await db.execute(position_query)
            positions = position_result.scalars().all()

            if not positions:
                print("  No positions found")
                continue

            print(f"\n{'Symbol':<8} {'Quantity':<12} {'Last Price':<15} {'Market Value':<18} {'Updated At':<25}")
            print("-" * 90)

            for pos in positions:
                last_price_str = f"${pos.last_price:,.2f}" if pos.last_price else "NULL"
                market_value_str = f"${pos.market_value:,.2f}" if pos.market_value else "NULL"
                updated_at_str = pos.updated_at.strftime("%Y-%m-%d %H:%M:%S") if pos.updated_at else "NULL"

                print(f"{pos.symbol:<8} {float(pos.quantity):<12.2f} {last_price_str:<15} {market_value_str:<18} {updated_at_str:<25}")

            # Check when positions were last updated
            latest_update_query = select(func.max(Position.updated_at)).where(
                Position.portfolio_id == portfolio.id
            )
            latest_result = await db.execute(latest_update_query)
            latest_update = latest_result.scalar()

            print(f"\n  Latest position update: {latest_update if latest_update else 'NULL'}")

        # Check historical_prices table for recent updates
        print(f"\n\n{'='*80}")
        print("HISTORICAL PRICES TABLE STATUS")
        print("="*80)

        try:
            from app.models.history import HistoricalPrice

            # Get count of historical prices
            price_count_query = select(func.count(HistoricalPrice.id))
            price_count_result = await db.execute(price_count_query)
            price_count = price_count_result.scalar()

            print(f"\nTotal historical price records: {price_count}")

            # Get latest date in historical_prices
            latest_price_date_query = select(func.max(HistoricalPrice.price_date))
            latest_price_result = await db.execute(latest_price_date_query)
            latest_price_date = latest_price_result.scalar()

            print(f"Latest historical price date: {latest_price_date}")

            # Get sample of recent prices
            if price_count > 0:
                sample_query = (
                    select(HistoricalPrice)
                    .order_by(HistoricalPrice.price_date.desc())
                    .limit(10)
                )
                sample_result = await db.execute(sample_query)
                samples = sample_result.scalars().all()

                print(f"\nRecent historical prices (sample of 10):")
                print(f"{'Symbol':<8} {'Date':<12} {'Close Price':<15}")
                print("-" * 40)
                for price in samples:
                    print(f"{price.symbol:<8} {price.price_date} ${price.close_price:,.2f}")

        except Exception as e:
            print(f"\nError accessing historical_prices: {e}")


if __name__ == "__main__":
    asyncio.run(check_position_price_updates())
