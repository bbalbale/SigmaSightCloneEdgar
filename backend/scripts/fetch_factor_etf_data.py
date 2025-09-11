#!/usr/bin/env python3
"""
Unified script for fetching factor ETF historical data
Ensures all factor ETFs have sufficient history for regression calculations
"""
import asyncio
import argparse
from datetime import date, timedelta
from typing import List, Optional, Dict, Any
from app.database import AsyncSessionLocal
from app.services.market_data_service import market_data_service
from app.constants.factors import FACTOR_ETFS, REGRESSION_WINDOW_DAYS
from app.core.logging import get_logger
from sqlalchemy import select, func
from app.models.market_data import MarketDataCache

# Configure UTF-8 output handling for Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logger = get_logger(__name__)


async def validate_etf_coverage(db, etf: str, required_days: int = REGRESSION_WINDOW_DAYS) -> Dict[str, Any]:
    """
    Validate historical data coverage for a factor ETF
    
    Args:
        db: Database session
        etf: ETF symbol to validate
        required_days: Minimum days required (default: REGRESSION_WINDOW_DAYS)
    
    Returns:
        Dictionary with validation results
    """
    stmt = select(
        func.min(MarketDataCache.date),
        func.max(MarketDataCache.date),
        func.count(MarketDataCache.id)
    ).where(MarketDataCache.symbol == etf)
    
    result = await db.execute(stmt)
    min_date, max_date, count = result.first()
    
    validation = {
        'symbol': etf,
        'min_date': min_date,
        'max_date': max_date,
        'record_count': count or 0,
        'required_days': required_days,
        'has_sufficient_data': False,
        'coverage_percentage': 0.0,
        'days_missing': 0
    }
    
    if count and count >= required_days * 0.8:  # 80% threshold
        validation['has_sufficient_data'] = True
        validation['coverage_percentage'] = (count / required_days * 100)
    else:
        validation['days_missing'] = max(0, int(required_days * 0.8) - (count or 0))
        validation['coverage_percentage'] = ((count or 0) / required_days * 100) if required_days > 0 else 0
    
    return validation


async def fetch_factor_etf_data(
    etfs: Optional[List[str]] = None,
    days_back: int = None,
    validate_coverage: bool = True,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Fetch historical data for factor ETFs
    
    Args:
        etfs: List of ETF symbols to fetch (None = all factor ETFs)
        days_back: Number of days to fetch (default: REGRESSION_WINDOW_DAYS + 30)
        validate_coverage: Whether to validate data coverage after fetching
        force_refresh: Force refresh even if data exists
    
    Returns:
        Dictionary with fetch results and validation
    """
    
    # Default to all factor ETFs if none specified
    if etfs is None:
        etfs = list(FACTOR_ETFS.values())
        logger.info(f"🎯 Fetching data for ALL factor ETFs: {', '.join(etfs)}")
    else:
        logger.info(f"🎯 Fetching data for specified ETFs: {', '.join(etfs)}")
    
    # Default days back
    if days_back is None:
        days_back = REGRESSION_WINDOW_DAYS + 30  # 180 days total (150 + buffer)
    
    logger.info(f"   Target: {REGRESSION_WINDOW_DAYS} trading days minimum")
    logger.info(f"   Fetching: {days_back} calendar days (includes buffer)")
    
    results = {
        'etfs_processed': [],
        'etfs_skipped': [],
        'etfs_failed': [],
        'validation_results': {},
        'fetch_stats': {}
    }
    
    async with AsyncSessionLocal() as db:
        for etf in etfs:
            logger.info(f"\n📊 Processing {etf}...")
            
            try:
                # Check existing coverage if not forcing refresh
                if not force_refresh:
                    validation = await validate_etf_coverage(db, etf)
                    
                    if validation['has_sufficient_data']:
                        logger.info(f"   ✅ {etf} already has sufficient data: {validation['record_count']} records")
                        logger.info(f"      Date range: {validation['min_date']} to {validation['max_date']}")
                        logger.info(f"      Coverage: {validation['coverage_percentage']:.1f}%")
                        results['etfs_skipped'].append(etf)
                        results['validation_results'][etf] = validation
                        continue
                    else:
                        logger.info(f"   ⚠️ {etf} needs more data: {validation['days_missing']} days missing")
                
                # Fetch and cache ETF data
                logger.info(f"   🔄 Fetching {days_back} days of data for {etf}...")
                stats = await market_data_service.bulk_fetch_and_cache(
                    db=db,
                    symbols=[etf],
                    days_back=days_back
                )
                
                results['fetch_stats'][etf] = stats
                logger.info(f"   ✅ Successfully fetched {etf} data: {stats}")
                
                # Validate after fetching
                if validate_coverage:
                    validation = await validate_etf_coverage(db, etf)
                    results['validation_results'][etf] = validation
                    
                    if validation['has_sufficient_data']:
                        logger.info(f"   ✅ Validation passed:")
                        logger.info(f"      Date range: {validation['min_date']} to {validation['max_date']}")
                        logger.info(f"      Records: {validation['record_count']} (need ~{REGRESSION_WINDOW_DAYS})")
                        logger.info(f"      Coverage: {validation['coverage_percentage']:.1f}%")
                        results['etfs_processed'].append(etf)
                    else:
                        logger.warning(f"   ⚠️ Insufficient data after fetch:")
                        logger.warning(f"      Got {validation['record_count']} records, need at least {int(REGRESSION_WINDOW_DAYS * 0.8)}")
                        results['etfs_failed'].append(etf)
                else:
                    results['etfs_processed'].append(etf)
                    
            except Exception as e:
                logger.error(f"   ❌ Failed to fetch {etf} data: {str(e)}")
                results['etfs_failed'].append(etf)
                results['validation_results'][etf] = {'error': str(e)}
    
    # Print summary
    print_summary(results)
    
    return results


def print_summary(results: Dict[str, Any]):
    """Print a formatted summary of the fetch results"""
    
    print("\n" + "=" * 60)
    print("📊 FACTOR ETF DATA FETCH SUMMARY")
    print("=" * 60)
    
    total_etfs = len(results['etfs_processed']) + len(results['etfs_skipped']) + len(results['etfs_failed'])
    
    if results['etfs_processed']:
        print(f"✅ Successfully fetched: {len(results['etfs_processed'])}/{total_etfs} ETFs")
        for etf in results['etfs_processed']:
            validation = results['validation_results'].get(etf, {})
            print(f"   - {etf}: {validation.get('record_count', 'N/A')} records")
    
    if results['etfs_skipped']:
        print(f"⏭️ Skipped (already sufficient): {len(results['etfs_skipped'])}/{total_etfs} ETFs")
        for etf in results['etfs_skipped']:
            validation = results['validation_results'].get(etf, {})
            print(f"   - {etf}: {validation.get('record_count', 'N/A')} records")
    
    if results['etfs_failed']:
        print(f"❌ Failed: {len(results['etfs_failed'])}/{total_etfs} ETFs")
        for etf in results['etfs_failed']:
            validation = results['validation_results'].get(etf, {})
            error = validation.get('error', 'Insufficient data')
            print(f"   - {etf}: {error}")
    
    print("\n" + "=" * 60)
    
    # Overall status
    if not results['etfs_failed']:
        print("✅ All factor ETFs have sufficient data for regression calculations!")
        print("You can now run batch calculations with all factor analyses enabled.")
    else:
        print("⚠️ Some ETFs need attention. You may need to:")
        print("1. Check API keys and rate limits")
        print("2. Try a different data provider")
        print("3. Increase the days_back parameter")
        print("4. Run with --force flag to refresh all data")


async def main():
    """Main entry point with CLI arguments"""
    
    parser = argparse.ArgumentParser(
        description='Fetch historical data for factor ETFs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all factor ETFs with default settings
  %(prog)s
  
  # Fetch specific ETFs
  %(prog)s --etf IWM --etf SPY
  
  # Fetch with custom time period
  %(prog)s --days 365
  
  # Force refresh all data
  %(prog)s --force
  
  # List available factor ETFs
  %(prog)s --list
        """
    )
    
    parser.add_argument(
        '--etf', 
        action='append',
        dest='etfs',
        help='Specific ETF to fetch (can be used multiple times)'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        help=f'Number of days to fetch (default: {REGRESSION_WINDOW_DAYS + 30})'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force refresh even if data exists'
    )
    
    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Skip validation after fetching'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available factor ETFs and exit'
    )
    
    args = parser.parse_args()
    
    # List ETFs if requested
    if args.list:
        print("\n📊 Available Factor ETFs:")
        print("=" * 40)
        for factor_name, etf_symbol in FACTOR_ETFS.items():
            print(f"  {factor_name:20s} → {etf_symbol}")
        print(f"\nTotal: {len(FACTOR_ETFS)} factor ETFs")
        print(f"Required days: {REGRESSION_WINDOW_DAYS} minimum for regression")
        return
    
    # Run the fetch
    results = await fetch_factor_etf_data(
        etfs=args.etfs,
        days_back=args.days,
        validate_coverage=not args.no_validate,
        force_refresh=args.force
    )
    
    # Exit code based on results
    if results['etfs_failed']:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())