#!/usr/bin/env python3
"""
Verify the exposure calculation fix for snapshot generation
Tests that short positions have negative exposure values
"""
import asyncio
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.database import get_db
from app.models.positions import Position, PositionType
from app.calculations.market_data import calculate_position_market_value
from app.core.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger("verify_exposure_fix")


async def test_exposure_calculations():
    """Test exposure calculations for different position types"""
    logger.info("=== Testing Exposure Calculations ===")
    
    # Test cases
    test_positions = [
        {
            "name": "Long Stock Position",
            "position": Position(
                symbol="AAPL",
                position_type=PositionType.LONG,
                quantity=Decimal("100"),
                entry_price=Decimal("150.00")
            ),
            "current_price": Decimal("155.00"),
            "expected_market_value": Decimal("15500.00"),  # Always positive
            "expected_exposure": Decimal("15500.00")       # Positive for long
        },
        {
            "name": "Short Stock Position",
            "position": Position(
                symbol="GOOGL",
                position_type=PositionType.SHORT,
                quantity=Decimal("-50"),
                entry_price=Decimal("2800.00")
            ),
            "current_price": Decimal("2850.00"),
            "expected_market_value": Decimal("142500.00"),  # Always positive
            "expected_exposure": Decimal("-142500.00")      # Negative for short
        },
        {
            "name": "Long Call Option",
            "position": Position(
                symbol="AAPL_240119C150",
                position_type=PositionType.LC,
                quantity=Decimal("10"),
                entry_price=Decimal("5.00"),
                strike_price=Decimal("150.00")
            ),
            "current_price": Decimal("7.50"),
            "expected_market_value": Decimal("7500.00"),    # 10 * 7.50 * 100
            "expected_exposure": Decimal("7500.00")         # Positive for long call
        },
        {
            "name": "Short Put Option",
            "position": Position(
                symbol="SPY_240119P400",
                position_type=PositionType.SP,
                quantity=Decimal("-5"),
                entry_price=Decimal("3.00"),
                strike_price=Decimal("400.00")
            ),
            "current_price": Decimal("2.50"),
            "expected_market_value": Decimal("1250.00"),    # abs(-5) * 2.50 * 100
            "expected_exposure": Decimal("-1250.00")        # Negative for short put
        }
    ]
    
    all_passed = True
    
    for test_case in test_positions:
        logger.info(f"\n--- Testing: {test_case['name']} ---")
        
        position = test_case["position"]
        current_price = test_case["current_price"]
        
        # Calculate market value and exposure
        result = await calculate_position_market_value(
            position=position,
            current_price=current_price
        )
        
        # Verify market value (always positive)
        market_value = result["market_value"]
        expected_mv = test_case["expected_market_value"]
        mv_correct = abs(market_value - expected_mv) < Decimal("0.01")
        
        logger.info(f"  Market Value: ${market_value} (Expected: ${expected_mv}) {'✅' if mv_correct else '❌'}")
        
        # Verify exposure (signed)
        exposure = result["exposure"]
        expected_exp = test_case["expected_exposure"]
        exp_correct = abs(exposure - expected_exp) < Decimal("0.01")
        
        logger.info(f"  Exposure: ${exposure} (Expected: ${expected_exp}) {'✅' if exp_correct else '❌'}")
        
        if not mv_correct or not exp_correct:
            all_passed = False
            logger.error(f"  ❌ Test failed for {test_case['name']}")
        else:
            logger.info(f"  ✅ Test passed")
    
    return all_passed


async def test_portfolio_aggregation():
    """Test portfolio aggregation with mixed long/short positions"""
    logger.info("\n=== Testing Portfolio Aggregation ===")
    
    from app.calculations.portfolio import calculate_portfolio_exposures
    
    # Create a mixed portfolio
    positions_data = [
        {
            "id": "1",
            "symbol": "AAPL",
            "quantity": Decimal("100"),
            "market_value": Decimal("15500.00"),
            "exposure": Decimal("15500.00"),  # Long position
            "position_type": PositionType.LONG
        },
        {
            "id": "2",
            "symbol": "GOOGL",
            "quantity": Decimal("-50"),
            "market_value": Decimal("142500.00"),
            "exposure": Decimal("-142500.00"),  # Short position (negative exposure)
            "position_type": PositionType.SHORT
        },
        {
            "id": "3",
            "symbol": "MSFT",
            "quantity": Decimal("200"),
            "market_value": Decimal("70000.00"),
            "exposure": Decimal("70000.00"),  # Another long
            "position_type": PositionType.LONG
        }
    ]
    
    # Calculate portfolio exposures
    result = calculate_portfolio_exposures(positions_data)
    
    logger.info(f"\nPortfolio Aggregation Results:")
    logger.info(f"  Gross Exposure: ${result['gross_exposure']} (Expected: $228,000)")
    logger.info(f"  Net Exposure: ${result['net_exposure']} (Expected: -$57,000)")
    logger.info(f"  Long Exposure: ${result['long_exposure']} (Expected: $85,500)")
    logger.info(f"  Short Exposure: ${result['short_exposure']} (Expected: -$142,500)")
    
    # Verify calculations
    expected_gross = Decimal("228000.00")  # 15,500 + 142,500 + 70,000
    expected_net = Decimal("-57000.00")    # 15,500 - 142,500 + 70,000
    expected_long = Decimal("85500.00")    # 15,500 + 70,000
    expected_short = Decimal("-142500.00") # -142,500
    
    gross_correct = abs(result['gross_exposure'] - expected_gross) < Decimal("0.01")
    net_correct = abs(result['net_exposure'] - expected_net) < Decimal("0.01")
    long_correct = abs(result['long_exposure'] - expected_long) < Decimal("0.01")
    short_correct = abs(result['short_exposure'] - expected_short) < Decimal("0.01")
    
    all_correct = gross_correct and net_correct and long_correct and short_correct
    
    if all_correct:
        logger.info("\n✅ Portfolio aggregation calculations are correct!")
    else:
        logger.error("\n❌ Portfolio aggregation calculations have errors!")
        
    return all_correct


async def test_snapshot_integration():
    """Test the full snapshot generation with real data"""
    logger.info("\n=== Testing Snapshot Integration ===")
    
    async for db in get_db():
        try:
            # Get a test portfolio with both long and short positions
            from sqlalchemy import select
            from app.models.users import Portfolio
            
            portfolio_query = select(Portfolio).limit(1)
            result = await db.execute(portfolio_query)
            portfolio = result.scalar_one_or_none()
            
            if not portfolio:
                logger.warning("No portfolio found for integration test")
                return False
            
            logger.info(f"Testing with portfolio: {portfolio.id}")
            
            # Test the snapshot preparation
            from app.calculations.snapshots import _prepare_position_data, _fetch_active_positions
            
            calculation_date = date.today()
            positions = await _fetch_active_positions(db, portfolio.id, calculation_date)
            
            if not positions:
                logger.warning("No positions found in portfolio")
                return False
            
            logger.info(f"Found {len(positions)} positions")
            
            # Prepare position data
            position_data = await _prepare_position_data(db, positions, calculation_date)
            
            # Check results
            logger.info(f"\nPosition Data Results:")
            logger.info(f"  Processed: {len(position_data['positions'])} positions")
            logger.info(f"  Warnings: {len(position_data['warnings'])}")
            
            if position_data['warnings']:
                for warning in position_data['warnings']:
                    logger.warning(f"    - {warning}")
            
            # Verify each position has correct fields
            for pos_data in position_data['positions']:
                symbol = pos_data['symbol']
                market_value = pos_data['market_value']
                exposure = pos_data['exposure']
                quantity = pos_data['quantity']
                
                # Check if exposure is correctly signed
                if quantity < 0:  # Short position
                    if exposure >= 0:
                        logger.error(f"  ❌ {symbol}: Short position has positive exposure!")
                        return False
                    else:
                        logger.info(f"  ✅ {symbol}: Short position correctly has negative exposure")
                else:  # Long position
                    if exposure < 0:
                        logger.error(f"  ❌ {symbol}: Long position has negative exposure!")
                        return False
                    else:
                        logger.info(f"  ✅ {symbol}: Long position correctly has positive exposure")
            
            return True
            
        except Exception as e:
            logger.error(f"Integration test error: {str(e)}")
            return False
        finally:
            await db.close()


async def main():
    """Run all verification tests"""
    logger.info("🚀 Starting Exposure Calculation Verification")
    
    try:
        # Test 1: Basic exposure calculations
        test1_passed = await test_exposure_calculations()
        
        # Test 2: Portfolio aggregation
        test2_passed = await test_portfolio_aggregation()
        
        # Test 3: Full integration
        test3_passed = await test_snapshot_integration()
        
        if test1_passed and test2_passed and test3_passed:
            logger.info("\n✅ All exposure calculation tests passed!")
            logger.info("The bug fix is working correctly.")
        else:
            logger.error("\n❌ Some tests failed. Please review the implementation.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Test suite failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())