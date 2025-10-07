"""
Market data synchronization batch job
"""
import asyncio
from datetime import datetime, date, timedelta
from typing import List, Set, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct, func, and_

from app.database import AsyncSessionLocal
from app.services.market_data_service import market_data_service
from app.models.positions import Position
from app.models.market_data import MarketDataCache
from app.core.logging import get_logger
from app.core.datetime_utils import utc_now

# Configure UTF-8 output handling for Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


logger = get_logger(__name__)


async def sync_market_data():
    """
    Daily market data synchronization from external sources
    - Fetches data for all symbols in active portfolios
    - Updates price data ONLY if cache is stale (>1 day old)
    - Skips API calls if data is already current
    """
    start_time = utc_now()
    logger.info(f"Starting market data sync at {start_time}")

    try:
        async with AsyncSessionLocal() as db:
            # Get all unique symbols from active positions
            symbols = await get_active_portfolio_symbols(db)

            if not symbols:
                logger.info("No active portfolio symbols found, skipping sync")
                return

            logger.info(f"Syncing market data for {len(symbols)} symbols: {', '.join(list(symbols)[:5])}{'...' if len(symbols) > 5 else ''}")

            # Check cache staleness before fetching
            # bulk_fetch_and_cache already has smart cache checking - it will skip symbols with current data
            # It also auto-detects market close time and skips today's data if before 4:05 PM ET
            # We only fetch last 5 days to catch any recent missing data
            stats = await market_data_service.bulk_fetch_and_cache(
                db=db,
                symbols=list(symbols),
                days_back=5  # Get last 5 trading days for daily sync
            )

            duration = utc_now() - start_time

            # Log results with clarity on whether API calls were needed
            if stats.get('api_calls_saved', 0) > 0:
                logger.info(f"Market data sync completed in {duration.total_seconds():.2f}s - Saved {stats['api_calls_saved']} API calls (data already cached)")
            else:
                logger.info(f"Market data sync completed in {duration.total_seconds():.2f}s: {stats}")

            return stats

    except Exception as e:
        logger.error(f"Market data sync failed: {str(e)}")
        raise


async def get_active_portfolio_symbols(db: AsyncSession) -> Set[str]:
    """
    Get all unique symbols from active portfolio positions
    
    Args:
        db: Database session
        
    Returns:
        Set of unique symbols
    """
    # Get all unique symbols from positions
    stmt = select(distinct(Position.symbol)).where(Position.quantity != 0)
    result = await db.execute(stmt)
    symbols = result.scalars().all()
    
    # Also include factor ETF symbols for factor calculations
    factor_etfs = ['SPY', 'VTV', 'VUG', 'MTUM', 'QUAL', 'IWM', 'USMV']
    
    all_symbols = set(symbols) | set(factor_etfs)
    
    logger.info(f"Found {len(symbols)} portfolio symbols and {len(factor_etfs)} factor ETFs")
    return all_symbols


async def fetch_missing_historical_data(days_back: int = 90):
    """
    Fetch missing historical data for all portfolio symbols
    
    Args:
        days_back: Number of days to backfill
    """
    logger.info(f"Starting historical data backfill for {days_back} days")
    
    try:
        async with AsyncSessionLocal() as db:
            symbols = await get_active_portfolio_symbols(db)
            
            if not symbols:
                logger.info("No symbols found for historical backfill")
                return
            
            # Check coverage per symbol (Fix 1 from Section 6.1.10)
            start_date = date.today() - timedelta(days=days_back)
            end_date = date.today()
            
            # Calculate expected trading days (approximate)
            expected_days = 0
            current = start_date
            while current <= end_date:
                if current.weekday() < 5:  # Monday=0, Friday=4
                    expected_days += 1
                current += timedelta(days=1)
            
            # Check coverage for each symbol
            symbols_needing_backfill = []
            for symbol in symbols:
                # Count distinct dates with actual price data (filter out metadata)
                stmt = select(func.count(distinct(MarketDataCache.date))).where(
                    and_(
                        MarketDataCache.symbol == symbol,
                        MarketDataCache.date >= start_date,
                        MarketDataCache.close > 0,  # Filter out metadata rows
                        MarketDataCache.data_source.in_(['fmp', 'polygon'])  # Only price data
                    )
                )
                count = (await db.execute(stmt)).scalar() or 0
                
                # Use 80% threshold to account for holidays/weekends
                if count < expected_days * 0.8:
                    symbols_needing_backfill.append(symbol)
                    logger.info(f"Symbol {symbol} has {count}/{expected_days} days (needs backfill)")
                else:
                    logger.debug(f"Symbol {symbol} has sufficient coverage: {count}/{expected_days} days")
            
            if symbols_needing_backfill:
                logger.info(f"Backfilling data for {len(symbols_needing_backfill)} symbols with insufficient coverage")
                stats = await market_data_service.bulk_fetch_and_cache(
                    db=db,
                    symbols=symbols_needing_backfill,
                    days_back=days_back
                )
                logger.info(f"Historical backfill completed: {stats}")
                return stats
            else:
                logger.info("All symbols have sufficient historical data coverage")
                return {"message": "No backfill needed"}
                
    except Exception as e:
        logger.error(f"Historical data backfill failed: {str(e)}")
        raise


async def verify_market_data_quality():
    """
    Verify the quality and completeness of cached market data
    """
    logger.info("Starting market data quality verification")
    
    try:
        async with AsyncSessionLocal() as db:
            # Check for recent data
            recent_date = date.today() - timedelta(days=7)
            
            stmt = select(
                MarketDataCache.symbol,
                MarketDataCache.date
            ).where(
                MarketDataCache.date >= recent_date
            ).order_by(MarketDataCache.symbol, MarketDataCache.date.desc())
            
            result = await db.execute(stmt)
            recent_data = result.all()
            
            # Group by symbol and check latest date
            symbol_latest = {}
            for record in recent_data:
                if record.symbol not in symbol_latest:
                    symbol_latest[record.symbol] = record.date
            
            stale_symbols = []
            for symbol, latest_date in symbol_latest.items():
                days_old = (date.today() - latest_date).days
                if days_old > 3:  # Consider data stale if > 3 days old
                    stale_symbols.append(symbol)
            
            if stale_symbols:
                logger.warning(f"Found {len(stale_symbols)} symbols with stale data: {stale_symbols[:5]}")
            else:
                logger.info("All market data is current")
            
            return {
                "total_symbols": len(symbol_latest),
                "stale_symbols": len(stale_symbols),
                "stale_symbol_list": stale_symbols
            }
            
    except Exception as e:
        logger.error(f"Market data quality verification failed: {str(e)}")
        raise


async def validate_and_ensure_factor_analysis_data(db: AsyncSession) -> Dict[str, Any]:
    """
    Validate historical data requirements for factor analysis and trigger backfill if needed

    Uses REGRESSION_WINDOW_DAYS from constants (currently 90 days)

    Args:
        db: Database session

    Returns:
        Dictionary with validation results and backfill actions taken
    """
    from app.constants.factors import FACTOR_ETFS, REGRESSION_WINDOW_DAYS
    from sqlalchemy import func, and_

    logger.info(f"🔍 Validating {REGRESSION_WINDOW_DAYS}-day historical data requirements for factor analysis")
    start_time = utc_now()
    
    try:
        # Get all portfolio + factor ETF symbols
        portfolio_symbols = await get_active_portfolio_symbols(db)
        factor_etf_symbols = set(FACTOR_ETFS.values())
        all_symbols = portfolio_symbols | factor_etf_symbols
        
        logger.info(f"Checking {REGRESSION_WINDOW_DAYS}-day coverage for {len(all_symbols)} symbols:")
        logger.info(f"  Portfolio symbols: {len(portfolio_symbols)}")
        logger.info(f"  Factor ETF symbols: {len(factor_etf_symbols)}")

        # Check historical data coverage (REGRESSION_WINDOW_DAYS from constants)
        required_date = date.today() - timedelta(days=REGRESSION_WINDOW_DAYS + 30)  # Extra buffer
        
        validation_results = {
            'total_symbols': len(all_symbols),
            'symbols_with_sufficient_data': [],
            'symbols_needing_backfill': [],
            'validation_date': required_date,
            'required_days': REGRESSION_WINDOW_DAYS,
            'backfill_triggered': False,
            'backfill_results': None
        }
        
        # Check each symbol's historical data coverage
        for symbol in all_symbols:
            # Count days of historical data for this symbol
            stmt = select(func.count(MarketDataCache.id)).where(
                and_(
                    MarketDataCache.symbol == symbol,
                    MarketDataCache.date >= required_date
                )
            )
            result = await db.execute(stmt)
            days_available = result.scalar() or 0
            
            if days_available >= REGRESSION_WINDOW_DAYS * 0.8:  # 80% threshold (200+ days)
                validation_results['symbols_with_sufficient_data'].append({
                    'symbol': symbol, 
                    'days_available': days_available
                })
                logger.debug(f"✅ {symbol}: {days_available} days (sufficient)")
            else:
                validation_results['symbols_needing_backfill'].append({
                    'symbol': symbol,
                    'days_available': days_available,
                    'days_needed': REGRESSION_WINDOW_DAYS - days_available
                })
                logger.warning(f"❌ {symbol}: {days_available} days (needs {REGRESSION_WINDOW_DAYS - days_available} more)")
        
        sufficient_count = len(validation_results['symbols_with_sufficient_data'])
        insufficient_count = len(validation_results['symbols_needing_backfill'])
        coverage_percentage = (sufficient_count / len(all_symbols)) * 100
        
        logger.info(f"📊 Historical Data Coverage Assessment:")
        logger.info(f"  ✅ Sufficient data: {sufficient_count}/{len(all_symbols)} symbols ({coverage_percentage:.1f}%)")
        logger.info(f"  ❌ Insufficient data: {insufficient_count} symbols")
        
        # Trigger automatic backfill if coverage is insufficient
        if insufficient_count > 0:
            logger.info(f"🔄 Triggering automatic {REGRESSION_WINDOW_DAYS}-day backfill for {insufficient_count} symbols")
            insufficient_symbols = [item['symbol'] for item in validation_results['symbols_needing_backfill']]
            
            backfill_results = await market_data_service.bulk_fetch_and_cache(
                db=db,
                symbols=insufficient_symbols,
                days_back=REGRESSION_WINDOW_DAYS + 30  # Extra buffer for trading days
            )
            
            validation_results['backfill_triggered'] = True
            validation_results['backfill_results'] = backfill_results
            
            logger.info(f"✅ Backfill completed: {backfill_results}")
        
        # Final validation summary
        duration = utc_now() - start_time
        validation_results['validation_duration_seconds'] = duration.total_seconds()
        validation_results['status'] = 'passed' if insufficient_count == 0 else 'backfill_completed'
        
        logger.info(f"🎯 Factor analysis data validation completed in {duration.total_seconds():.2f}s")
        
        return validation_results
        
    except Exception as e:
        logger.error(f"❌ Factor analysis data validation failed: {str(e)}")
        return {
            'status': 'failed',
            'error': str(e),
            'validation_duration_seconds': (utc_now() - start_time).total_seconds()
        }


async def sync_company_profiles(force_refresh: bool = False):
    """
    Sync company profiles for all portfolio symbols
    Updates company names, sectors, industries, revenue estimates, etc.
    Uses hybrid yfinance + yahooquery approach for comprehensive data.

    Args:
        force_refresh: Force refresh even if profiles exist (default: False)

    Returns:
        Dictionary with sync statistics
    """
    start_time = utc_now()
    logger.info(f"Starting company profile sync at {start_time}")

    try:
        async with AsyncSessionLocal() as db:
            # Get all unique symbols from active positions
            symbols = await get_active_portfolio_symbols(db)

            if not symbols:
                logger.info("No active portfolio symbols found, skipping company profile sync")
                return {
                    'total': 0,
                    'successful': 0,
                    'failed': 0,
                    'duration': 0
                }

            # Convert set to list and filter out synthetic symbols
            symbols_list = list(symbols)
            logger.info(f"Syncing company profiles for {len(symbols_list)} symbols")

            # Fetch and cache profiles using market_data_service
            # This uses the hybrid yfinance + yahooquery fetcher
            results = await market_data_service.fetch_and_cache_company_profiles(
                db, symbols_list
            )

            duration = utc_now() - start_time
            success_count = sum(1 for v in results.values() if v)
            failed_count = len(symbols_list) - success_count

            logger.info(
                f"Company profile sync completed in {duration.total_seconds():.2f}s: "
                f"{success_count}/{len(symbols_list)} successful, {failed_count} failed"
            )

            # Log failed symbols for debugging
            if failed_count > 0:
                failed_symbols = [s for s, success in results.items() if not success]
                logger.warning(f"Failed to fetch profiles for: {failed_symbols[:10]}")

            return {
                'total': len(symbols_list),
                'successful': success_count,
                'failed': failed_count,
                'duration': duration.total_seconds()
            }

    except Exception as e:
        logger.error(f"Company profile sync failed: {str(e)}")
        raise


async def main():
    """Main CLI entry point for market data sync operations"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'validate-historical':
        # Run historical data validation
        async with AsyncSessionLocal() as db:
            results = await validate_and_ensure_factor_analysis_data(db)
            print(f"\n🎯 Validation Results:")
            print(f"Status: {results.get('status')}")
            if results.get('status') != 'failed':
                print(f"Total symbols: {results['total_symbols']}")
                print(f"Sufficient data: {len(results['symbols_with_sufficient_data'])}")
                print(f"Backfill needed: {len(results['symbols_needing_backfill'])}")
                if results.get('backfill_triggered'):
                    print(f"Backfill completed: {results['backfill_results']}")
            else:
                print(f"Error: {results.get('error')}")
    elif len(sys.argv) > 1 and sys.argv[1] == 'sync-profiles':
        # Run company profile sync
        results = await sync_company_profiles()
        print(f"\n✅ Company Profile Sync Results:")
        print(f"Total: {results['total']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        print(f"Duration: {results['duration']:.2f}s")
    else:
        # Run standard market data sync
        await sync_market_data()


if __name__ == "__main__":
    asyncio.run(main())
