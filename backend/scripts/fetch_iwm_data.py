#!/usr/bin/env python3
"""
Fetch IWM historical data for factor calculations
Ensures we have at least 150 days of history for regression calculations
"""
import asyncio
from datetime import date, timedelta
from app.database import AsyncSessionLocal
from app.services.market_data_service import market_data_service
from app.constants.factors import REGRESSION_WINDOW_DAYS
from app.core.logging import get_logger

# Configure UTF-8 output handling for Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


logger = get_logger(__name__)

async def fetch_iwm_historical_data():
    """Fetch IWM (Russell 2000) historical data for SIZE factor calculations"""
    
    # Calculate days needed (150 + buffer for weekends/holidays)
    days_back = REGRESSION_WINDOW_DAYS + 30  # 180 days total
    
    logger.info(f"🎯 Fetching IWM historical data")
    logger.info(f"   Target: {REGRESSION_WINDOW_DAYS} trading days minimum")
    logger.info(f"   Fetching: {days_back} calendar days (includes buffer)")
    
    async with AsyncSessionLocal() as db:
        try:
            # Fetch and cache IWM data
            stats = await market_data_service.bulk_fetch_and_cache(
                db=db,
                symbols=['IWM'],
                days_back=days_back
            )
            
            logger.info(f"✅ Successfully fetched IWM data: {stats}")
            
            # Verify we have enough data
            from sqlalchemy import select, func
            from app.models.market_data import MarketDataCache
            
            stmt = select(
                func.min(MarketDataCache.date),
                func.max(MarketDataCache.date),
                func.count(MarketDataCache.id)
            ).where(MarketDataCache.symbol == 'IWM')
            
            result = await db.execute(stmt)
            min_date, max_date, count = result.first()
            
            if count and count >= REGRESSION_WINDOW_DAYS * 0.8:  # 80% threshold
                logger.info(f"✅ Verification passed:")
                logger.info(f"   Date range: {min_date} to {max_date}")
                logger.info(f"   Records: {count} (need ~{REGRESSION_WINDOW_DAYS})")
                logger.info(f"   Coverage: {(count / REGRESSION_WINDOW_DAYS * 100):.1f}%")
                return True
            else:
                logger.warning(f"⚠️ Insufficient data:")
                logger.warning(f"   Got {count} records, need at least {int(REGRESSION_WINDOW_DAYS * 0.8)}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to fetch IWM data: {str(e)}")
            return False


async def main():
    """Main entry point"""
    success = await fetch_iwm_historical_data()
    
    if success:
        print("\n✅ IWM data successfully fetched and ready for factor calculations!")
        print("You can now run batch calculations with the SIZE factor using IWM.")
    else:
        print("\n⚠️ IWM data fetch incomplete. Check logs for details.")
        print("You may need to:")
        print("1. Check API keys and rate limits")
        print("2. Try a different data provider")
        print("3. Reduce the days_back parameter")


if __name__ == "__main__":
    asyncio.run(main())