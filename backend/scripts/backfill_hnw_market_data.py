"""
Backfill 180 days of market data for High Net Worth portfolio holdings.
"""

import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select
from app.database import get_async_session
from app.models.users import Portfolio
from app.models.positions import Position
from app.services.market_data_service import MarketDataService


async def main():
    print("=" * 80)
    print("BACKFILLING 180 DAYS OF MARKET DATA FOR HNW PORTFOLIO")
    print("=" * 80)
    print()

    async with get_async_session() as db:
        # Find the HNW portfolio
        stmt = select(Portfolio).where(
            Portfolio.name.like('%High Net Worth%')
        )
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()

        if not portfolio:
            print("❌ High Net Worth portfolio not found")
            return

        print(f"✓ Found portfolio: {portfolio.name}")
        print(f"  Portfolio ID: {portfolio.id}")
        print()

        # Get all positions for this portfolio
        stmt = select(Position).where(
            Position.portfolio_id == portfolio.id
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()

        print(f"✓ Found {len(positions)} positions")
        print()

        # Extract unique symbols
        symbols = list(set([p.symbol for p in positions if p.symbol]))
        symbols.sort()

        print("Symbols to backfill:")
        for i, symbol in enumerate(symbols, 1):
            print(f"  {i}. {symbol}")
        print()

        # Initialize market data service
        market_data_service = MarketDataService()

        # Backfill 180 days of data
        print(f"Starting backfill for {len(symbols)} symbols (180 days)...")
        print(f"Date range: {(datetime.now() - timedelta(days=180)).date()} to {datetime.now().date()}")
        print()

        try:
            stats = await market_data_service.bulk_fetch_and_cache(
                db=db,
                symbols=symbols,
                days_back=180,
                include_gics=False  # Skip GICS for speed
            )

            print("=" * 80)
            print("BACKFILL COMPLETE")
            print("=" * 80)
            print()
            print(f"Symbols processed:      {stats['symbols_processed']}")
            print(f"Symbols updated:        {stats['symbols_updated']}")
            print(f"Records attempted:      {stats['total_records_attempted']}")
            print(f"Records inserted:       {stats['records_inserted']}")
            print(f"Records skipped:        {stats['records_skipped']} (already existed)")
            print(f"API calls saved:        {stats.get('api_calls_saved', 0)}")
            print()

            if stats['records_inserted'] > 0:
                print("✅ Successfully backfilled market data!")
                print(f"   Added {stats['records_inserted']} new price records")
            elif stats['records_skipped'] > 0:
                print("✓ All data already cached")
                print(f"  Skipped {stats['records_skipped']} existing records")
            else:
                print("⚠️  No new data added. Check if symbols are valid.")

        except Exception as e:
            print(f"❌ Error during backfill: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
