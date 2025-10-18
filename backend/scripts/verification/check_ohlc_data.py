"""Check if we have OHLC data populated."""
import asyncio
from sqlalchemy import select
from app.database import get_async_session
from app.models.market_data import MarketDataCache


async def check_ohlc():
    async with get_async_session() as db:
        result = await db.execute(
            select(MarketDataCache)
            .where(MarketDataCache.symbol == 'AAPL')
            .order_by(MarketDataCache.date.desc())
            .limit(5)
        )
        prices = result.scalars().all()

        print("\nSample AAPL price data (most recent 5 days):")
        print(f"{'Date':<12} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10}")
        print("-" * 52)

        for p in prices:
            print(f"{p.date!s:<12} {p.open!s:<10} {p.high!s:<10} {p.low!s:<10} {p.close!s:<10}")

        # Check if OHLC is populated
        has_ohlc = all(p.open is not None and p.high is not None and p.low is not None for p in prices)

        if has_ohlc:
            print("\n[OK] OHLC data is fully populated!")
            print("We can use Parkinson or Garman-Klass volatility estimators.")
        else:
            print("\n[X] OHLC data is missing!")
            print("Only close prices available.")


if __name__ == "__main__":
    asyncio.run(check_ohlc())
