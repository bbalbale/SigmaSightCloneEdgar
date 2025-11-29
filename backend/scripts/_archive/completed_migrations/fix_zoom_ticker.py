"""
Fix ZOOM ticker symbol to ZM in database
"""
import asyncio
from sqlalchemy import update, delete
from app.database import get_async_session
from app.models.positions import Position
from app.models.market_data import MarketDataCache
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_zoom_ticker():
    """Update ZOOM to ZM in positions and clear related market data cache"""
    
    async with get_async_session() as db:
        logger.info("Fixing ZOOM ticker to ZM...")
        logger.info("-" * 50)
        
        # Update positions from ZOOM to ZM
        stmt = (
            update(Position)
            .where(Position.symbol == "ZOOM")
            .values(symbol="ZM")
        )
        result = await db.execute(stmt)
        positions_updated = result.rowcount
        logger.info(f"Updated {positions_updated} position(s) from ZOOM to ZM")
        
        # Delete any cached market data for ZOOM (it's invalid)
        delete_stmt = delete(MarketDataCache).where(MarketDataCache.symbol == "ZOOM")
        delete_result = await db.execute(delete_stmt)
        cache_deleted = delete_result.rowcount
        logger.info(f"Deleted {cache_deleted} invalid ZOOM market data cache entries")
        
        await db.commit()
        logger.info("-" * 50)
        logger.info("✅ Ticker fix completed successfully!")
        
        # Verify the fix
        from sqlalchemy import select
        verify_stmt = select(Position).where(Position.symbol.in_(["ZOOM", "ZM"]))
        verify_result = await db.execute(verify_stmt)
        positions = verify_result.scalars().all()
        
        zoom_count = sum(1 for p in positions if p.symbol == "ZOOM")
        zm_count = sum(1 for p in positions if p.symbol == "ZM")
        
        logger.info(f"Verification: ZOOM positions: {zoom_count}, ZM positions: {zm_count}")
        
        if zoom_count > 0:
            logger.warning("⚠️ Some ZOOM positions still exist!")
        else:
            logger.info("✅ All ZOOM positions successfully converted to ZM")

if __name__ == "__main__":
    asyncio.run(fix_zoom_ticker())