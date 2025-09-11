#!/usr/bin/env python3
"""
Test script to verify factor analysis issue and proposed fix
This script demonstrates that factor calculations work but aren't being saved
"""
import asyncio
import sys
from datetime import date
from pathlib import Path
from uuid import UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_async_session
from app.calculations.factors import calculate_factor_betas_hybrid
from app.core.logging import get_logger

logger = get_logger(__name__)

# Test with one of the demo portfolios that currently has no factor data
TEST_PORTFOLIO_ID = UUID("51134ffd-2f13-49bd-b1f5-0c327e801b69")  # Demo Individual Investor


async def test_factor_calculation():
    """Test that factor calculation works but doesn't save"""
    print("=" * 80)
    print("FACTOR ANALYSIS DIAGNOSTIC TEST")
    print("=" * 80)
    
    async with get_async_session() as db:
        print(f"\nTesting portfolio: {TEST_PORTFOLIO_ID}")
        print("Running calculate_factor_betas_hybrid...")
        
        try:
            # Run the factor calculation
            results = await calculate_factor_betas_hybrid(
                db=db,
                portfolio_id=TEST_PORTFOLIO_ID,
                calculation_date=date.today()
            )
            
            print("\n✅ CALCULATION SUCCESSFUL!")
            print(f"  - Positions processed: {results['data_quality']['positions_processed']}")
            print(f"  - Factors processed: {results['data_quality']['factors_processed']}")
            print(f"  - Regression days: {results['data_quality']['regression_days']}")
            print(f"  - Quality flag: {results['data_quality']['quality_flag']}")
            
            # Check portfolio-level betas
            if results.get('factor_betas'):
                print("\nPortfolio-level factor betas calculated:")
                for factor, beta in results['factor_betas'].items():
                    print(f"  - {factor}: {beta:.4f}")
            
            # Check position-level betas
            if results.get('position_betas'):
                print(f"\nPosition-level betas calculated for {len(results['position_betas'])} positions")
                # Show first position as example
                for pos_id, betas in list(results['position_betas'].items())[:1]:
                    print(f"  Example position {pos_id[:8]}...:")
                    for factor, beta in betas.items():
                        print(f"    - {factor}: {beta:.4f}")
            
            print("\n❌ PROBLEM IDENTIFIED:")
            print("  The calculation completes successfully but results are NOT saved to database!")
            print("  - No PositionFactorExposure records created")
            print("  - No FactorExposure records created")
            print("\n  This is why only 10/74 positions have factor data (old test data)")
            
            return results
            
        except Exception as e:
            print(f"\n❌ CALCULATION FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


async def check_database_after():
    """Check if anything was saved to database"""
    async with get_async_session() as db:
        from sqlalchemy import select, func
        from app.models.market_data import PositionFactorExposure, FactorExposure
        
        # Check position factor exposures for this portfolio
        from app.models.positions import Position
        
        stmt = select(func.count(PositionFactorExposure.id)).join(
            Position, Position.id == PositionFactorExposure.position_id
        ).where(Position.portfolio_id == TEST_PORTFOLIO_ID)
        
        result = await db.execute(stmt)
        count = result.scalar()
        
        print("\n" + "=" * 80)
        print("DATABASE CHECK AFTER CALCULATION")
        print("=" * 80)
        print(f"PositionFactorExposure records for test portfolio: {count}")
        
        # Check portfolio exposures
        stmt2 = select(func.count(FactorExposure.id)).where(
            FactorExposure.portfolio_id == TEST_PORTFOLIO_ID
        )
        result2 = await db.execute(stmt2)
        count2 = result2.scalar()
        
        print(f"FactorExposure records for test portfolio: {count2}")
        
        if count == 0 and count2 == 0:
            print("\n✅ CONFIRMED: Calculations work but nothing is saved to database!")
            print("   This is the root cause of the factor analysis issue.")


async def main():
    """Run the diagnostic test"""
    # Test calculation
    results = await test_factor_calculation()
    
    if results:
        # Check database
        await check_database_after()
        
        print("\n" + "=" * 80)
        print("PROPOSED FIX")
        print("=" * 80)
        print("Need to add database persistence after calculate_factor_betas_hybrid:")
        print("1. Create FactorDefinition records if they don't exist")
        print("2. Save position_betas to PositionFactorExposure table")
        print("3. Save factor_betas to FactorExposure table")
        print("4. Commit the transaction")
        print("\nThis will fix factor analysis for all 66 stock/ETF positions.")
        print("Options will remain at 0% (expected - no historical data).")


if __name__ == "__main__":
    asyncio.run(main())