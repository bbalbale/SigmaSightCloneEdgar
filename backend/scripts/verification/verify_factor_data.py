#!/usr/bin/env python3
"""
Script to verify historical data availability for factor ETFs
Checks if we have sufficient historical data (252+ days) for factor calculations
"""
import asyncio
from datetime import date, timedelta
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.calculations.market_data import validate_historical_data_availability
from app.constants.factors import FACTOR_ETFS, REGRESSION_WINDOW_DAYS


async def verify_factor_etf_data():
    """Verify that all factor ETFs have sufficient historical data"""
    print(f"\nVerifying historical data availability for factor ETFs")
    print(f"Required minimum days: {REGRESSION_WINDOW_DAYS}")
    print("=" * 80)
    
    # Get all factor ETF symbols
    factor_symbols = list(FACTOR_ETFS.values())
    print(f"\nFactor ETFs to check: {', '.join(factor_symbols)}")
    
    async with AsyncSessionLocal() as db:
        # Validate data availability
        results = await validate_historical_data_availability(
            db=db,
            symbols=factor_symbols,
            required_days=REGRESSION_WINDOW_DAYS,
            as_of_date=date.today()
        )
        
        # Display results
        print("\nData Availability Summary:")
        print("-" * 80)
        print(f"{'Factor':<15} {'ETF':<10} {'Status':<15} {'Days':<10} {'Date Range':<30}")
        print("-" * 80)
        
        all_sufficient = True
        missing_etfs = []
        
        for factor_name, etf_symbol in FACTOR_ETFS.items():
            if etf_symbol in results:
                has_data, days, first_date, last_date = results[etf_symbol]
                status = "✓ Sufficient" if has_data else "✗ Insufficient"
                date_range = f"{first_date} to {last_date}" if first_date else "No data"
                
                print(f"{factor_name:<15} {etf_symbol:<10} {status:<15} {days:<10} {date_range:<30}")
                
                if not has_data:
                    all_sufficient = False
                    missing_etfs.append((factor_name, etf_symbol, days))
            else:
                print(f"{factor_name:<15} {etf_symbol:<10} {'✗ No data':<15} {'0':<10} {'No data':<30}")
                all_sufficient = False
                missing_etfs.append((factor_name, etf_symbol, 0))
        
        print("-" * 80)
        
        # Summary and recommendations
        if all_sufficient:
            print("\n✓ All factor ETFs have sufficient historical data!")
            print("  Factor calculations can proceed without data backfill.")
        else:
            print("\n✗ Some factor ETFs have insufficient historical data:")
            for factor_name, etf_symbol, days in missing_etfs:
                needed = REGRESSION_WINDOW_DAYS - days
                print(f"  - {factor_name} ({etf_symbol}): Need {needed} more days of data")
            
            print("\nRecommendations:")
            print("1. Run the market data backfill script to fetch missing historical data")
            print("2. Use the following command:")
            print("   python scripts/backfill_market_data.py --symbols " + 
                  ",".join([etf for _, etf, _ in missing_etfs]))
            
            # Calculate date range for backfill
            earliest_needed = date.today() - timedelta(days=REGRESSION_WINDOW_DAYS + 30)  # Add buffer
            print(f"3. Backfill from {earliest_needed} to ensure sufficient data")
        
        # Check for recent data
        print("\nRecent Data Check (last 5 trading days):")
        print("-" * 40)
        recent_cutoff = date.today() - timedelta(days=7)
        
        for factor_name, etf_symbol in FACTOR_ETFS.items():
            if etf_symbol in results:
                _, _, _, last_date = results[etf_symbol]
                if last_date and last_date >= recent_cutoff:
                    print(f"{etf_symbol}: ✓ Up to date (last: {last_date})")
                elif last_date:
                    days_behind = (date.today() - last_date).days
                    print(f"{etf_symbol}: ⚠ {days_behind} days behind (last: {last_date})")
                else:
                    print(f"{etf_symbol}: ✗ No data")
        
        return all_sufficient


async def check_sample_portfolio_data():
    """Check if any existing portfolios have sufficient data"""
    print("\n\nChecking sample portfolio positions...")
    print("=" * 80)
    
    from app.models.positions import Position
    from app.models.users import Portfolio
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as db:
        # Get first portfolio with positions
        stmt = select(Portfolio).limit(1)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            print("No portfolios found in database")
            return
        
        print(f"Checking portfolio: {portfolio.name} (ID: {portfolio.id})")
        
        # Get portfolio positions
        stmt = select(Position).where(
            Position.portfolio_id == portfolio.id,
            Position.exit_date.is_(None)  # Only active positions
        ).limit(10)
        
        result = await db.execute(stmt)
        positions = result.scalars().all()
        
        if not positions:
            print("No active positions found")
            return
        
        # Get unique symbols
        symbols = list(set(p.symbol for p in positions))
        print(f"Found {len(symbols)} unique symbols: {', '.join(symbols[:5])}...")
        
        # Check data availability
        results = await validate_historical_data_availability(
            db=db,
            symbols=symbols,
            required_days=REGRESSION_WINDOW_DAYS
        )
        
        sufficient_count = sum(1 for r in results.values() if r[0])
        print(f"\nData availability: {sufficient_count}/{len(symbols)} symbols have sufficient data")
        
        if sufficient_count < len(symbols):
            print("\nSymbols with insufficient data:")
            for symbol, (has_data, days, _, _) in results.items():
                if not has_data:
                    print(f"  - {symbol}: {days} days (need {REGRESSION_WINDOW_DAYS - days} more)")


if __name__ == "__main__":
    print("Factor Data Verification Script")
    print("==============================")
    
    # Run verification
    loop = asyncio.get_event_loop()
    
    # Check factor ETFs
    factor_data_ok = loop.run_until_complete(verify_factor_etf_data())
    
    # Check sample portfolio
    loop.run_until_complete(check_sample_portfolio_data())
    
    # Exit with appropriate code
    sys.exit(0 if factor_data_ok else 1)