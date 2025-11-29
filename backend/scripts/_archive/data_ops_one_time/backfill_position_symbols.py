#!/usr/bin/env python3
"""
Backfill price data for position symbols using YFinance
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.services.market_data_service import market_data_service
from app.models.positions import Position
from sqlalchemy import select


async def backfill_position_symbols():
    """Backfill price data for all position symbols"""
    print("Backfilling Position Symbol Data")
    print("=" * 35)
    
    async with AsyncSessionLocal() as db:
        # Get unique symbols from active positions
        stmt = select(Position.symbol).where(Position.exit_date.is_(None)).distinct()
        result = await db.execute(stmt)
        symbols = [row[0] for row in result.all()]
        
        if not symbols:
            print("❌ No active positions found")
            return False
        
        print(f"Found {len(symbols)} unique symbols to backfill:")
        print(f"Symbols: {', '.join(symbols)}")
        
        # Use FMP hybrid approach to backfill data for these symbols
        try:
            result = await market_data_service.bulk_fetch_and_cache(
                db=db,
                symbols=symbols,
                days_back=300  # Get plenty of historical data
            )
            
            print(f"\n✅ Backfill completed:")
            print(f"  Symbols processed: {result['symbols_processed']}")
            print(f"  Records added: {result['total_records']}")
            
            if result['errors']:
                print(f"  Errors: {len(result['errors'])}")
                for error in result['errors'][:3]:
                    print(f"    - {error}")
            
            return result['symbols_processed'] > 0
            
        except Exception as e:
            print(f"❌ Error during backfill: {str(e)}")
            return False


if __name__ == "__main__":
    success = asyncio.run(backfill_position_symbols())
    sys.exit(0 if success else 1)