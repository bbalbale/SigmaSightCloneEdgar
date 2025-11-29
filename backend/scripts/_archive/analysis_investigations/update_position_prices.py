"""Update all position last_price from market_data_cache"""
import asyncio
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models.positions import Position
from app.models.market_data import MarketDataCache
from decimal import Decimal

async def update_positions():
    async with AsyncSessionLocal() as db:
        # Get all positions
        result = await db.execute(select(Position))
        positions = result.scalars().all()

        print("=" * 80)
        print("UPDATING POSITION PRICES FROM MARKET DATA CACHE")
        print("=" * 80)
        print()

        updated = 0
        skipped = 0

        for pos in positions:
            # Get latest market price
            market_result = await db.execute(
                select(MarketDataCache)
                .where(MarketDataCache.symbol == pos.symbol)
                .order_by(MarketDataCache.date.desc())
                .limit(1)
            )
            market = market_result.scalar_one_or_none()

            if market and market.close:
                old_price = float(pos.last_price) if pos.last_price else 0.0
                new_price = float(market.close)

                # Update position
                pos.last_price = Decimal(str(market.close))
                pos.market_value = pos.quantity * pos.last_price
                if pos.entry_price and pos.entry_price > 0:
                    pos.unrealized_pnl = (pos.last_price - pos.entry_price) * pos.quantity

                print(f"{pos.symbol:15} {old_price:10.2f} -> {new_price:10.2f}  Date: {market.date}  {'✅' if abs(new_price - old_price) > 0.01 else '='}")
                updated += 1
            else:
                print(f"{pos.symbol:15} SKIPPED - No market data")
                skipped += 1

        await db.commit()

        print()
        print("=" * 80)
        print(f"COMPLETE: Updated {updated}, Skipped {skipped}")
        print("=" * 80)

asyncio.run(update_positions())
