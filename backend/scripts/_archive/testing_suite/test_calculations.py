#!/usr/bin/env python3
"""
Simple test script for market data calculations
"""
import asyncio
import sys
import os
from decimal import Decimal
from unittest.mock import Mock

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.calculations.market_data import (
    calculate_position_market_value,
    is_options_position
)
from app.models.positions import PositionType
from app.core.logging import setup_logging

# Setup logging
setup_logging()

async def test_stock_long_position():
    """Test basic stock long position calculation"""
    print("🔍 Testing stock long position calculation...")
    
    # Create mock position
    position = Mock()
    position.symbol = "AAPL"
    position.position_type = PositionType.LONG
    position.quantity = Decimal('100')
    position.entry_price = Decimal('150.00')
    
    current_price = Decimal('155.00')
    
    result = await calculate_position_market_value(position, current_price)
    
    print(f"   Symbol: {position.symbol}")
    print(f"   Quantity: {position.quantity}")
    print(f"   Entry Price: ${position.entry_price}")
    print(f"   Current Price: ${current_price}")
    print(f"   Market Value: ${result['market_value']}")
    print(f"   Exposure: ${result['exposure']}")
    print(f"   Unrealized P&L: ${result['unrealized_pnl']}")
    print(f"   Cost Basis: ${result['cost_basis']}")
    print(f"   Multiplier: {result['multiplier']}")
    
    # Verify calculations
    expected_market_value = Decimal('100') * Decimal('155.00')  # 15,500
    expected_pnl = Decimal('100') * (Decimal('155.00') - Decimal('150.00'))  # 500
    
    assert result['market_value'] == expected_market_value
    assert result['unrealized_pnl'] == expected_pnl
    assert result['multiplier'] == Decimal('1')  # Stock multiplier
    
    print("   ✅ Stock long position test passed!")
    return True

async def test_options_long_call():
    """Test options long call calculation"""
    print("\n🔍 Testing options long call calculation...")
    
    # Create mock options position
    position = Mock()
    position.symbol = "AAPL240119C00150000"
    position.position_type = PositionType.LC  # Long Call
    position.quantity = Decimal('5')  # 5 contracts
    position.entry_price = Decimal('2.50')
    
    current_price = Decimal('3.75')
    
    result = await calculate_position_market_value(position, current_price)
    
    print(f"   Symbol: {position.symbol}")
    print(f"   Type: {position.position_type}")
    print(f"   Quantity: {position.quantity} contracts")
    print(f"   Entry Price: ${position.entry_price} per contract")
    print(f"   Current Price: ${current_price} per contract")
    print(f"   Market Value: ${result['market_value']}")
    print(f"   Exposure: ${result['exposure']}")
    print(f"   Unrealized P&L: ${result['unrealized_pnl']}")
    print(f"   Multiplier: {result['multiplier']}")
    
    # Verify calculations (options have 100x multiplier)
    expected_market_value = Decimal('5') * Decimal('3.75') * Decimal('100')  # 1,875
    expected_pnl = Decimal('5') * (Decimal('3.75') - Decimal('2.50')) * Decimal('100')  # 625
    
    assert result['market_value'] == expected_market_value
    assert result['unrealized_pnl'] == expected_pnl
    assert result['multiplier'] == Decimal('100')  # Options multiplier
    
    print("   ✅ Options long call test passed!")
    return True

async def test_short_position():
    """Test short stock position calculation"""
    print("\n🔍 Testing short stock position calculation...")
    
    # Create mock short position
    position = Mock()
    position.symbol = "TSLA"
    position.position_type = PositionType.SHORT
    position.quantity = Decimal('-100')  # Negative for short
    position.entry_price = Decimal('200.00')
    
    current_price = Decimal('180.00')  # Price went down, profitable for short
    
    result = await calculate_position_market_value(position, current_price)
    
    print(f"   Symbol: {position.symbol}")
    print(f"   Type: SHORT")
    print(f"   Quantity: {position.quantity}")
    print(f"   Entry Price: ${position.entry_price}")
    print(f"   Current Price: ${current_price}")
    print(f"   Market Value: ${result['market_value']} (always positive)")
    print(f"   Exposure: ${result['exposure']} (negative for short)")
    print(f"   Unrealized P&L: ${result['unrealized_pnl']} (profit from price drop)")
    
    # Market value should be positive (abs of quantity)
    expected_market_value = abs(Decimal('-100')) * Decimal('180.00')  # 18,000
    # Exposure should be negative
    expected_exposure = Decimal('-100') * Decimal('180.00')  # -18,000
    # P&L: profit from price drop
    expected_pnl = Decimal('-100') * (Decimal('180.00') - Decimal('200.00'))  # 2,000 profit
    
    assert result['market_value'] == expected_market_value
    assert result['exposure'] == expected_exposure
    assert result['unrealized_pnl'] == expected_pnl
    
    print("   ✅ Short position test passed!")
    return True

def test_position_type_detection():
    """Test options vs stock position detection"""
    print("\n🔍 Testing position type detection...")
    
    # Test stock positions
    stock_long = Mock()
    stock_long.position_type = PositionType.LONG
    assert not is_options_position(stock_long)
    
    stock_short = Mock()
    stock_short.position_type = PositionType.SHORT
    assert not is_options_position(stock_short)
    
    # Test options positions
    long_call = Mock()
    long_call.position_type = PositionType.LC
    assert is_options_position(long_call)
    
    long_put = Mock()
    long_put.position_type = PositionType.LP
    assert is_options_position(long_put)
    
    short_call = Mock()
    short_call.position_type = PositionType.SC
    assert is_options_position(short_call)
    
    short_put = Mock()
    short_put.position_type = PositionType.SP
    assert is_options_position(short_put)
    
    print("   ✅ Position type detection test passed!")
    return True

async def main():
    """Run all tests"""
    print("🚀 Testing Market Data Calculation Functions (Section 1.4.1)")
    print("=" * 65)
    
    tests_passed = 0
    total_tests = 4
    
    try:
        # Run async tests
        if await test_stock_long_position():
            tests_passed += 1
        
        if await test_options_long_call():
            tests_passed += 1
            
        if await test_short_position():
            tests_passed += 1
        
        # Run sync test
        if test_position_type_detection():
            tests_passed += 1
        
        print("\n" + "=" * 65)
        print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("🎉 All calculation tests passed! Implementation is working correctly.")
            print("\n💡 Key Features Verified:")
            print("   ✅ Market value calculation (always positive)")
            print("   ✅ Exposure calculation (signed for long/short)")
            print("   ✅ Unrealized P&L calculation")
            print("   ✅ Options 100x multiplier")
            print("   ✅ Stock vs options position detection")
            print("   ✅ Short position handling")
        else:
            print(f"❌ {total_tests - tests_passed} tests failed")
            return False
            
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)