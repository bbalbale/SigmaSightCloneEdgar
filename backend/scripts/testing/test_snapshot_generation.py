#!/usr/bin/env python3
"""
Manual testing script for portfolio snapshot generation
Tests the complete snapshot creation flow with real data
"""
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path
from decimal import Decimal

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.database import get_db
from app.calculations.snapshots import create_portfolio_snapshot
from app.utils.trading_calendar import trading_calendar
from app.core.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger("test_snapshot_generation")


async def test_trading_calendar():
    """Test trading calendar functionality"""
    logger.info("=== Testing Trading Calendar ===")
    
    test_dates = [
        date(2025, 1, 15),  # Wednesday
        date(2025, 1, 18),  # Saturday
        date(2025, 1, 20),  # MLK Day (Holiday)
        date(2025, 12, 25), # Christmas
    ]
    
    for test_date in test_dates:
        is_trading = trading_calendar.is_trading_day(test_date)
        logger.info(f"  {test_date} ({test_date.strftime('%A')}): {'Trading Day' if is_trading else 'Non-Trading Day'}")
    
    # Test previous/next trading day
    today = date.today()
    prev_trading = trading_calendar.get_previous_trading_day(today)
    next_trading = trading_calendar.get_next_trading_day(today)
    
    logger.info(f"  Today: {today}")
    logger.info(f"  Previous trading day: {prev_trading}")
    logger.info(f"  Next trading day: {next_trading}")
    logger.info(f"  Should run batch job today: {trading_calendar.should_run_batch_job()}")


async def test_snapshot_creation():
    """Test snapshot creation for all portfolios"""
    logger.info("\n=== Testing Snapshot Creation ===")
    
    async for db in get_db():
        try:
            # Get all portfolios
            from sqlalchemy import select
            from app.models.users import Portfolio
            
            portfolios_query = select(Portfolio)
            result = await db.execute(portfolios_query)
            portfolios = result.scalars().all()
            
            if not portfolios:
                logger.warning("No portfolios found in database")
                return
            
            logger.info(f"Found {len(portfolios)} portfolios")
            
            # Test snapshot creation for each portfolio
            calculation_date = date.today()
            
            # If today is not a trading day, use the previous trading day
            if not trading_calendar.is_trading_day(calculation_date):
                calculation_date = trading_calendar.get_previous_trading_day(calculation_date)
                if not calculation_date:
                    logger.error("No recent trading day found")
                    return
                logger.info(f"Using previous trading day: {calculation_date}")
            
            for portfolio in portfolios:
                logger.info(f"\n--- Testing Portfolio: {portfolio.id} ({portfolio.name}) ---")
                
                try:
                    result = await create_portfolio_snapshot(
                        db=db,
                        portfolio_id=portfolio.id,
                        calculation_date=calculation_date
                    )
                    
                    if result["success"]:
                        logger.info("✅ Snapshot created successfully")
                        stats = result["statistics"]
                        logger.info(f"  Positions: {stats['positions_processed']}")
                        logger.info(f"  Total Value: ${stats['total_value']:,.2f}")
                        logger.info(f"  Daily P&L: ${stats['daily_pnl']:,.2f}")
                        
                        if stats["warnings"]:
                            logger.warning(f"  Warnings: {len(stats['warnings'])}")
                            for warning in stats["warnings"]:
                                logger.warning(f"    - {warning}")
                    else:
                        logger.error(f"❌ Snapshot creation failed: {result['message']}")
                
                except Exception as e:
                    logger.error(f"❌ Exception during snapshot creation: {str(e)}")
                    
        finally:
            await db.close()


async def test_snapshot_consistency():
    """Test snapshot consistency over multiple days"""
    logger.info("\n=== Testing Snapshot Consistency ===")
    
    async for db in get_db():
        try:
            # Get first portfolio
            from sqlalchemy import select
            from app.models.users import Portfolio
            
            portfolio_query = select(Portfolio).limit(1)
            result = await db.execute(portfolio_query)
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                logger.warning("No portfolio found for consistency test")
                return
            
            logger.info(f"Testing consistency for portfolio: {portfolio.id}")
            
            # Test creating snapshots for the last 5 trading days
            end_date = date.today()
            trading_days = []
            
            current_date = end_date
            for _ in range(10):  # Look back up to 10 days to find 5 trading days
                if trading_calendar.is_trading_day(current_date):
                    trading_days.append(current_date)
                    if len(trading_days) >= 5:
                        break
                current_date -= timedelta(days=1)
            
            trading_days.reverse()  # Chronological order
            
            logger.info(f"Testing {len(trading_days)} trading days: {trading_days}")
            
            snapshots = []
            for test_date in trading_days:
                try:
                    result = await create_portfolio_snapshot(
                        db=db,
                        portfolio_id=portfolio.id,
                        calculation_date=test_date
                    )
                    
                    if result["success"]:
                        snapshots.append({
                            "date": test_date,
                            "value": result["statistics"]["total_value"],
                            "pnl": result["statistics"]["daily_pnl"]
                        })
                        logger.info(f"  {test_date}: Value=${result['statistics']['total_value']:,.2f}, P&L=${result['statistics']['daily_pnl']:,.2f}")
                    else:
                        logger.error(f"  {test_date}: Failed - {result['message']}")
                        
                except Exception as e:
                    logger.error(f"  {test_date}: Exception - {str(e)}")
            
            # Analyze consistency
            if len(snapshots) >= 2:
                logger.info("\n--- Consistency Analysis ---")
                for i in range(1, len(snapshots)):
                    prev_snap = snapshots[i-1]
                    curr_snap = snapshots[i]
                    
                    expected_value = prev_snap["value"] + curr_snap["pnl"]
                    actual_value = curr_snap["value"]
                    
                    diff = abs(expected_value - actual_value)
                    
                    logger.info(f"  {curr_snap['date']}: Expected=${expected_value:,.2f}, Actual=${actual_value:,.2f}, Diff=${diff:,.2f}")
                    
                    if diff > 0.01:  # More than 1 cent difference
                        logger.warning(f"    ⚠️  Large difference detected!")
                    else:
                        logger.info(f"    ✅ Values consistent")
                        
        finally:
            await db.close()


async def test_missing_data_handling():
    """Test how snapshot handles missing prerequisite data"""
    logger.info("\n=== Testing Missing Data Handling ===")
    
    async for db in get_db():
        try:
            # This test would require creating test positions without Greeks/market data
            # For now, just log that this test needs implementation
            logger.info("Missing data handling test requires test data setup")
            logger.info("This should be implemented when test database fixtures are available")
                        
        finally:
            await db.close()


async def main():
    """Run all snapshot generation tests"""
    logger.info("🚀 Starting Portfolio Snapshot Generation Tests")
    
    try:
        await test_trading_calendar()
        await test_snapshot_creation()
        await test_snapshot_consistency()
        await test_missing_data_handling()
        
        logger.info("\n✅ All snapshot generation tests completed!")
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())