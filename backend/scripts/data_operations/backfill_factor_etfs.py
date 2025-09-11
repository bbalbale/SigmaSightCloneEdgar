#!/usr/bin/env python3
"""
Automatic backfill script for factor ETF historical data
Fetches 365+ days of historical data for all factor ETFs using YFinance API (free)
Uses YFinance instead of Polygon.io to avoid free-tier limitations on ETF data
"""
import asyncio
from datetime import date, timedelta
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.services.market_data_service import market_data_service
from app.constants.factors import FACTOR_ETFS, REGRESSION_WINDOW_DAYS
from app.calculations.market_data import validate_historical_data_availability
from app.core.logging import get_logger

logger = get_logger(__name__)


class FactorETFBackfiller:
    """Handles automatic backfill of factor ETF historical data"""
    
    def __init__(self, days_to_fetch: int = 400):
        self.days_to_fetch = days_to_fetch
        self.factor_symbols = list(FACTOR_ETFS.values())
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=days_to_fetch)
        
    async def run_backfill(self) -> Dict[str, Any]:
        """
        Main backfill process
        
        Returns:
            Dictionary with backfill results and statistics
        """
        logger.info(f"Starting automatic backfill for {len(self.factor_symbols)} factor ETFs")
        logger.info(f"Date range: {self.start_date} to {self.end_date} ({self.days_to_fetch} days)")
        logger.info(f"Factor ETFs: {', '.join(self.factor_symbols)}")
        
        results = {
            "success": False,
            "symbols_processed": 0,
            "total_symbols": len(self.factor_symbols),
            "data_points_added": 0,
            "errors": [],
            "summary": {}
        }
        
        async with AsyncSessionLocal() as db:
            try:
                # Step 1: Check current data availability
                logger.info("Checking current data availability...")
                current_data = await validate_historical_data_availability(
                    db=db,
                    symbols=self.factor_symbols,
                    required_days=REGRESSION_WINDOW_DAYS
                )
                
                # Log current state
                symbols_with_data = sum(1 for has_data, _, _, _ in current_data.values() if has_data)
                logger.info(f"Current state: {symbols_with_data}/{len(self.factor_symbols)} symbols have sufficient data")
                
                # Step 2: Perform backfill for each symbol
                for symbol in self.factor_symbols:
                    logger.info(f"Processing {symbol}...")
                    
                    try:
                        # Use FMP hybrid approach for factor ETFs
                        result = await market_data_service.bulk_fetch_and_cache(
                            db=db,
                            symbols=[symbol],
                            days_back=self.days_to_fetch
                        )
                        
                        # Extract data points from result
                        data_points = result.get('total_records', 0)
                        
                        results["symbols_processed"] += 1
                        results["data_points_added"] += data_points
                        results["summary"][symbol] = {
                            "success": True,
                            "data_points": data_points
                        }
                        
                        logger.info(f"✓ {symbol}: Added {data_points} data points")
                        
                        # Small delay to respect rate limits
                        await asyncio.sleep(0.2)
                        
                    except Exception as e:
                        error_msg = f"Failed to backfill {symbol}: {str(e)}"
                        logger.error(error_msg)
                        results["errors"].append(error_msg)
                        results["summary"][symbol] = {
                            "success": False,
                            "error": str(e)
                        }
                
                # Step 3: Validate final data availability
                logger.info("Validating backfill results...")
                final_data = await validate_historical_data_availability(
                    db=db,
                    symbols=self.factor_symbols,
                    required_days=REGRESSION_WINDOW_DAYS
                )
                
                # Check success criteria
                symbols_with_sufficient_data = sum(1 for has_data, _, _, _ in final_data.values() if has_data)
                results["success"] = symbols_with_sufficient_data == len(self.factor_symbols)
                results["final_coverage"] = f"{symbols_with_sufficient_data}/{len(self.factor_symbols)}"
                
                # Log results
                if results["success"]:
                    logger.info("✓ Backfill completed successfully!")
                    logger.info(f"All {len(self.factor_symbols)} factor ETFs now have sufficient historical data")
                else:
                    logger.warning(f"⚠ Partial success: {symbols_with_sufficient_data}/{len(self.factor_symbols)} symbols have sufficient data")
                
                # Detailed summary
                logger.info("Backfill Summary:")
                logger.info(f"- Symbols processed: {results['symbols_processed']}")
                logger.info(f"- Data points added: {results['data_points_added']}")
                logger.info(f"- Errors: {len(results['errors'])}")
                
                return results
                
            except Exception as e:
                logger.error(f"Backfill process failed: {str(e)}")
                results["errors"].append(f"Process failure: {str(e)}")
                return results
    
    async def validate_and_report(self) -> None:
        """Validate data and generate detailed report"""
        logger.info("Generating data validation report...")
        
        async with AsyncSessionLocal() as db:
            validation_results = await validate_historical_data_availability(
                db=db,
                symbols=self.factor_symbols,
                required_days=REGRESSION_WINDOW_DAYS
            )
            
            print("\n" + "="*80)
            print("FACTOR ETF DATA VALIDATION REPORT")
            print("="*80)
            print(f"Required minimum days: {REGRESSION_WINDOW_DAYS}")
            print(f"Validation date: {date.today()}")
            print("-"*80)
            print(f"{'Factor':<15} {'ETF':<10} {'Status':<15} {'Days':<10} {'Date Range':<30}")
            print("-"*80)
            
            all_sufficient = True
            for factor_name, etf_symbol in FACTOR_ETFS.items():
                if etf_symbol in validation_results:
                    has_data, days, first_date, last_date = validation_results[etf_symbol]
                    status = "✓ Sufficient" if has_data else "✗ Insufficient"
                    date_range = f"{first_date} to {last_date}" if first_date else "No data"
                    
                    print(f"{factor_name:<15} {etf_symbol:<10} {status:<15} {days:<10} {date_range:<30}")
                    
                    if not has_data:
                        all_sufficient = False
                else:
                    print(f"{factor_name:<15} {etf_symbol:<10} {'✗ No data':<15} {'0':<10} {'No data':<30}")
                    all_sufficient = False
            
            print("-"*80)
            
            if all_sufficient:
                print("✓ ALL FACTOR ETFs READY FOR FACTOR CALCULATIONS")
                print("  Factor analysis can now proceed with sufficient historical data.")
            else:
                print("✗ Some factor ETFs still lack sufficient data")
                print("  Factor calculations may produce quality warnings.")
            
            print("="*80 + "\n")


async def main():
    """Main execution function"""
    print("Factor ETF Automatic Backfill Script")
    print("=" * 50)
    
    # Initialize backfiller
    backfiller = FactorETFBackfiller(days_to_fetch=400)
    
    # Run backfill process
    results = await backfiller.run_backfill()
    
    # Generate validation report
    await backfiller.validate_and_report()
    
    # Exit with appropriate code
    if results["success"]:
        print("✓ Backfill completed successfully - factor calculations can proceed")
        sys.exit(0)
    else:
        print("⚠ Backfill completed with issues - check logs for details")
        sys.exit(1)


if __name__ == "__main__":
    # Run the backfill process
    asyncio.run(main())