#!/usr/bin/env python3
"""
Test script for factor analysis calculations
Tests the core factor calculation functions with real data
"""
import asyncio
from datetime import date, timedelta
import sys
from pathlib import Path

# Configure UTF-8 output handling for Windows
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.calculations.factors import (
    fetch_factor_returns, calculate_position_returns, 
    calculate_factor_betas_hybrid, store_position_factor_exposures,
    aggregate_portfolio_factor_exposures
)
from app.calculations.portfolio import calculate_portfolio_exposures
from app.constants.factors import FACTOR_ETFS, REGRESSION_WINDOW_DAYS
from app.models.users import Portfolio
from app.models.positions import Position
from sqlalchemy import select
from uuid import UUID


async def test_factor_returns():
    """Test factor return calculations"""
    print("\n1. Testing Factor Returns Calculation")
    print("=" * 50)
    
    async with AsyncSessionLocal() as db:
        # Test parameters
        end_date = date.today()
        start_date = end_date - timedelta(days=30)  # Last 30 days for quick test
        factor_symbols = list(FACTOR_ETFS.values())
        
        print(f"Testing with symbols: {factor_symbols}")
        print(f"Date range: {start_date} to {end_date}")
        
        try:
            factor_returns = await fetch_factor_returns(
                db=db,
                symbols=factor_symbols,
                start_date=start_date,
                end_date=end_date
            )
            
            if not factor_returns.empty:
                print(f"✓ Factor returns calculated: {len(factor_returns)} days")
                print(f"✓ Factors available: {list(factor_returns.columns)}")
                print(f"✓ Sample data (last 3 days):")
                print(factor_returns.tail(3).round(4))
                return True
            else:
                print("❌ No factor returns data calculated")
                return False
                
        except Exception as e:
            print(f"❌ Error calculating factor returns: {str(e)}")
            return False


async def test_position_returns():
    """Test position return calculations"""
    print("\n2. Testing Position Returns Calculation")
    print("=" * 50)
    
    async with AsyncSessionLocal() as db:
        # Get first portfolio with positions
        stmt = select(Portfolio).limit(1)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            print("❌ No portfolios found in database")
            return False
        
        print(f"Testing with portfolio: {portfolio.name} (ID: {portfolio.id})")
        
        # Test parameters
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        try:
            # Test both exposure types
            for use_delta_adjusted in [False, True]:
                exposure_type = "delta-adjusted" if use_delta_adjusted else "dollar"
                print(f"\nTesting {exposure_type} exposures...")
                
                position_returns = await calculate_position_returns(
                    db=db,
                    portfolio_id=portfolio.id,
                    start_date=start_date,
                    end_date=end_date,
                    use_delta_adjusted=use_delta_adjusted
                )
                
                if not position_returns.empty:
                    print(f"✓ Position returns ({exposure_type}): {len(position_returns)} days, {len(position_returns.columns)} positions")
                    print(f"✓ Sample data (last 3 days, first 3 positions):")
                    print(position_returns.iloc[-3:, :3].round(4))
                else:
                    print(f"⚠ No position returns data for {exposure_type} exposures")
            
            return True
            
        except Exception as e:
            print(f"❌ Error calculating position returns: {str(e)}")
            return False


async def test_factor_betas():
    """Test factor beta calculations"""
    print("\n3. Testing Factor Beta Calculations")
    print("=" * 50)
    
    async with AsyncSessionLocal() as db:
        # Get first portfolio with positions
        stmt = select(Portfolio).limit(1)
        result = await db.execute(stmt)
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            print("❌ No portfolios found in database")
            return False
        
        print(f"Testing with portfolio: {portfolio.name} (ID: {portfolio.id})")
        
        try:
            calculation_date = date.today()
            
            # Test factor beta calculation
            results = await calculate_factor_betas_hybrid(
                db=db,
                portfolio_id=portfolio.id,
                calculation_date=calculation_date,
                use_delta_adjusted=False
            )
            
            print("✓ Factor beta calculation completed")
            print(f"✓ Data quality: {results['data_quality']['quality_flag']}")
            print(f"✓ Regression days: {results['data_quality']['regression_days']}")
            print(f"✓ Positions processed: {results['data_quality']['positions_processed']}")
            print(f"✓ Factors processed: {results['data_quality']['factors_processed']}")
            
            # Display portfolio-level factor betas
            print(f"\nPortfolio Factor Betas:")
            for factor, beta in results['factor_betas'].items():
                print(f"  {factor}: {beta:.4f}")
            
            # Display sample position-level betas
            if results['position_betas']:
                sample_position = list(results['position_betas'].keys())[0]
                print(f"\nSample Position Betas (Position {sample_position[:8]}...):")
                for factor, beta in results['position_betas'][sample_position].items():
                    print(f"  {factor}: {beta:.4f}")
            
            return results
            
        except Exception as e:
            print(f"❌ Error calculating factor betas: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


async def test_storage_functions(factor_results):
    """Test storage of factor exposures"""
    print("\n4. Testing Factor Exposure Storage")
    print("=" * 50)
    
    if not factor_results:
        print("❌ No factor results to store")
        return False
    
    async with AsyncSessionLocal() as db:
        try:
            calculation_date = date.today()
            quality_flag = factor_results['data_quality']['quality_flag']
            
            # Test position factor exposure storage
            print("Testing position factor exposure storage...")
            storage_results = await store_position_factor_exposures(
                db=db,
                position_betas=factor_results['position_betas'],
                calculation_date=calculation_date,
                quality_flag=quality_flag
            )
            
            print(f"✓ Position exposures stored: {storage_results['records_stored']} records")
            print(f"✓ Positions processed: {storage_results['positions_processed']}")
            
            if storage_results['errors']:
                print(f"⚠ Errors encountered: {len(storage_results['errors'])}")
                for error in storage_results['errors'][:3]:  # Show first 3 errors
                    print(f"  - {error}")
            
            # Test portfolio aggregation (need portfolio exposures)
            portfolio_id = UUID(factor_results['metadata']['portfolio_id'])
            
            # Get current portfolio exposures (simplified for test)
            portfolio_exposures = {"gross_exposure": 100000}  # Mock $100k portfolio
            
            print("\nTesting portfolio factor exposure aggregation...")
            agg_results = await aggregate_portfolio_factor_exposures(
                db=db,
                position_betas=factor_results['position_betas'],
                portfolio_exposures=portfolio_exposures,
                portfolio_id=portfolio_id,
                calculation_date=calculation_date
            )
            
            print(f"✓ Portfolio aggregation completed: {agg_results['records_stored']} records")
            print("✓ Portfolio factor betas stored in database")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in storage functions: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Run all factor calculation tests"""
    print("Factor Analysis Calculation Tests")
    print("================================")
    
    test_results = {
        "factor_returns": False,
        "position_returns": False,
        "factor_betas": None,
        "storage": False
    }
    
    # Run tests in sequence
    test_results["factor_returns"] = await test_factor_returns()
    test_results["position_returns"] = await test_position_returns()
    test_results["factor_betas"] = await test_factor_betas()
    
    if test_results["factor_betas"]:
        test_results["storage"] = await test_storage_functions(test_results["factor_betas"])
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    tests = [
        ("Factor Returns", test_results["factor_returns"]),
        ("Position Returns", test_results["position_returns"]),
        ("Factor Betas", test_results["factor_betas"] is not None),
        ("Storage Functions", test_results["storage"])
    ]
    
    passed = 0
    for test_name, result in tests:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20}: {status}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("🎉 All factor calculation tests passed!")
        return True
    else:
        print("⚠ Some tests failed - check implementation")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)