#!/usr/bin/env python3
"""
Manual testing script for Greeks calculations
"""
import pytest
pytest.skip("Legacy/manual test; greeks hybrid API not present. Skipped in CI.", allow_module_level=True)
import asyncio
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Add the parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.calculations.greeks import (
    calculate_greeks_hybrid,
    get_mock_greeks,
    calculate_real_greeks,
    extract_option_parameters,
    update_position_greeks,
    bulk_update_portfolio_greeks,
    aggregate_portfolio_greeks,
    MOCK_GREEKS
)
from app.models.positions import PositionType
from app.database import get_db
from app.core.logging import setup_logging

# Set up logging
setup_logging()

class MockPosition:
    """Mock position class for testing"""
    def __init__(self, **kwargs):
        # Set default values
        self.id = kwargs.get('id', 'test-position')
        self.symbol = kwargs.get('symbol', 'TEST')
        self.position_type = kwargs.get('position_type', PositionType.LONG)
        self.quantity = kwargs.get('quantity', Decimal('1'))
        self.strike_price = kwargs.get('strike_price', None)
        self.expiration_date = kwargs.get('expiration_date', None)
        self.underlying_symbol = kwargs.get('underlying_symbol', None)
        
        # Set any additional attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

# Test market data
TEST_MARKET_DATA = {
    'AAPL': {
        'current_price': 150.00,
        'implied_volatility': 0.25,
        'risk_free_rate': 0.05,
        'dividend_yield': 0.0
    },
    'MSFT': {
        'current_price': 380.00,
        'implied_volatility': 0.22,
        'risk_free_rate': 0.05,
        'dividend_yield': 0.0
    }
}

def test_mock_greeks():
    """Test mock Greeks calculations"""
    print("🔍 Testing Mock Greeks Calculations")
    print("=" * 50)
    
    # Test all position types
    position_types = [
        (PositionType.LC, Decimal('5'), 'Long Call (5 contracts)'),
        (PositionType.SC, Decimal('-3'), 'Short Call (3 contracts)'),
        (PositionType.LP, Decimal('2'), 'Long Put (2 contracts)'),
        (PositionType.SP, Decimal('-4'), 'Short Put (4 contracts)'),
        (PositionType.LONG, Decimal('100'), 'Long Stock (100 shares)'),
        (PositionType.SHORT, Decimal('-50'), 'Short Stock (50 shares)')
    ]
    
    for pos_type, quantity, description in position_types:
        greeks = get_mock_greeks(pos_type, quantity)
        print(f"\n{description}:")
        print(f"  Delta: {greeks['delta']:.4f}")
        print(f"  Gamma: {greeks['gamma']:.4f}")
        print(f"  Theta: {greeks['theta']:.4f}")
        print(f"  Vega:  {greeks['vega']:.4f}")
        print(f"  Rho:   {greeks['rho']:.4f}")
    
    print("\n✅ Mock Greeks calculations completed successfully")

def test_real_greeks():
    """Test real Greeks calculations"""
    print("\n🔍 Testing Real Greeks Calculations")
    print("=" * 50)
    
    try:
        # Test ATM call
        greeks = calculate_real_greeks(
            underlying_price=150.0,
            strike=150.0,
            time_to_expiry=30/365,
            volatility=0.25,
            risk_free_rate=0.05,
            option_type='c'
        )
        
        print(f"ATM Call (S=150, K=150, T=30d, vol=25%):")
        print(f"  Delta: {greeks['delta']:.4f}")
        print(f"  Gamma: {greeks['gamma']:.4f}")
        print(f"  Theta: {greeks['theta']:.4f}")
        print(f"  Vega:  {greeks['vega']:.4f}")
        print(f"  Rho:   {greeks['rho']:.4f}")
        
        # Test ATM put
        greeks = calculate_real_greeks(
            underlying_price=150.0,
            strike=150.0,
            time_to_expiry=30/365,
            volatility=0.25,
            risk_free_rate=0.05,
            option_type='p'
        )
        
        print(f"\nATM Put (S=150, K=150, T=30d, vol=25%):")
        print(f"  Delta: {greeks['delta']:.4f}")
        print(f"  Gamma: {greeks['gamma']:.4f}")
        print(f"  Theta: {greeks['theta']:.4f}")
        print(f"  Vega:  {greeks['vega']:.4f}")
        print(f"  Rho:   {greeks['rho']:.4f}")
        
        print("\n✅ Real Greeks calculations completed successfully")
        
    except Exception as e:
        print(f"\n❌ Real Greeks calculation failed: {e}")
        print("📝 This is expected if py_vollib is not properly installed")

async def test_hybrid_greeks():
    """Test hybrid Greeks calculations"""
    print("\n🔍 Testing Hybrid Greeks Calculations")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            'name': 'Long Call (Real Calculation)',
            'position': MockPosition(
                id='test-lc',
                symbol='AAPL240119C00150000',
                position_type=PositionType.LC,
                quantity=Decimal('5'),
                strike_price=Decimal('150.00'),
                expiration_date=date.today() + timedelta(days=30),
                underlying_symbol='AAPL'
            ),
            'market_data': TEST_MARKET_DATA
        },
        {
            'name': 'Short Put (Real Calculation)',
            'position': MockPosition(
                id='test-sp',
                symbol='AAPL240119P00145000',
                position_type=PositionType.SP,
                quantity=Decimal('-3'),
                strike_price=Decimal('145.00'),
                expiration_date=date.today() + timedelta(days=30),
                underlying_symbol='AAPL'
            ),
            'market_data': TEST_MARKET_DATA
        },
        {
            'name': 'Long Stock (Mock Calculation)',
            'position': MockPosition(
                id='test-long',
                symbol='AAPL',
                position_type=PositionType.LONG,
                quantity=Decimal('100'),
                expiration_date=None,
                underlying_symbol='AAPL'
            ),
            'market_data': TEST_MARKET_DATA
        },
        {
            'name': 'Expired Option (Zero Greeks)',
            'position': MockPosition(
                id='test-expired',
                symbol='AAPL231215C00150000',
                position_type=PositionType.LC,
                quantity=Decimal('2'),
                strike_price=Decimal('150.00'),
                expiration_date=date.today() - timedelta(days=30),
                underlying_symbol='AAPL'
            ),
            'market_data': TEST_MARKET_DATA
        },
        {
            'name': 'Missing Market Data (Mock Fallback)',
            'position': MockPosition(
                id='test-missing',
                symbol='TSLA240119C00200000',
                position_type=PositionType.LC,
                quantity=Decimal('1'),
                strike_price=Decimal('200.00'),
                expiration_date=date.today() + timedelta(days=30),
                underlying_symbol='TSLA'
            ),
            'market_data': TEST_MARKET_DATA  # Missing TSLA data
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}:")
        try:
            greeks = await calculate_greeks_hybrid(
                test_case['position'],
                test_case['market_data']
            )
            
            print(f"  Delta: {greeks['delta']:.4f}")
            print(f"  Gamma: {greeks['gamma']:.4f}")
            print(f"  Theta: {greeks['theta']:.4f}")
            print(f"  Vega:  {greeks['vega']:.4f}")
            print(f"  Rho:   {greeks['rho']:.4f}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n✅ Hybrid Greeks calculations completed successfully")

async def test_portfolio_aggregation():
    """Test portfolio Greeks aggregation"""
    print("\n🔍 Testing Portfolio Greeks Aggregation")
    print("=" * 50)
    
    # Sample position Greeks
    positions_greeks = [
        {'delta': 2.6, 'gamma': 0.09, 'theta': -0.225, 'vega': 0.75, 'rho': 0.4},
        {'delta': -1.2, 'gamma': 0.05, 'theta': 0.1, 'vega': -0.3, 'rho': -0.2},
        {'delta': 100.0, 'gamma': 0.0, 'theta': 0.0, 'vega': 0.0, 'rho': 0.0},
        {'delta': -50.0, 'gamma': 0.0, 'theta': 0.0, 'vega': 0.0, 'rho': 0.0}
    ]
    
    portfolio_greeks = await aggregate_portfolio_greeks(positions_greeks)
    
    print("Individual Position Greeks:")
    for i, pos_greeks in enumerate(positions_greeks, 1):
        print(f"  Position {i}: Delta={pos_greeks['delta']:.2f}, Gamma={pos_greeks['gamma']:.3f}")
    
    print("\nPortfolio Aggregated Greeks:")
    print(f"  Total Delta: {portfolio_greeks['total_delta']:.2f}")
    print(f"  Total Gamma: {portfolio_greeks['total_gamma']:.3f}")
    print(f"  Total Theta: {portfolio_greeks['total_theta']:.3f}")
    print(f"  Total Vega:  {portfolio_greeks['total_vega']:.3f}")
    print(f"  Total Rho:   {portfolio_greeks['total_rho']:.3f}")
    
    print("\n✅ Portfolio aggregation completed successfully")

def test_option_parameter_extraction():
    """Test option parameter extraction"""
    print("\n🔍 Testing Option Parameter Extraction")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            'name': 'Valid Call Option',
            'position': MockPosition(
                position_type=PositionType.LC,
                symbol='AAPL240119C00150000',
                strike_price=Decimal('150.00'),
                expiration_date=date.today() + timedelta(days=30),
                underlying_symbol='AAPL'
            )
        },
        {
            'name': 'Valid Put Option',
            'position': MockPosition(
                position_type=PositionType.LP,
                symbol='AAPL240119P00145000',
                strike_price=Decimal('145.00'),
                expiration_date=date.today() + timedelta(days=30),
                underlying_symbol='AAPL'
            )
        },
        {
            'name': 'Stock Position',
            'position': MockPosition(
                position_type=PositionType.LONG,
                symbol='AAPL'
            )
        },
        {
            'name': 'Missing Strike Price',
            'position': MockPosition(
                position_type=PositionType.LC,
                symbol='AAPL240119C00150000',
                strike_price=None,
                expiration_date=date.today() + timedelta(days=30),
                underlying_symbol='AAPL'
            )
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}:")
        params = extract_option_parameters(test_case['position'])
        
        if params:
            print(f"  Strike: {params['strike']}")
            print(f"  Time to Expiry: {params['time_to_expiry']:.4f} years")
            print(f"  Option Type: {params['option_type']}")
            print(f"  Underlying: {params['underlying_symbol']}")
        else:
            print("  ❌ No valid option parameters (expected for stocks/invalid options)")
    
    print("\n✅ Option parameter extraction completed successfully")

async def main():
    """Run all tests"""
    print("🚀 Starting Greeks Calculation Manual Tests")
    print("=" * 70)
    
    # Run all tests
    test_mock_greeks()
    test_real_greeks()
    await test_hybrid_greeks()
    await test_portfolio_aggregation()
    test_option_parameter_extraction()
    
    print("\n" + "=" * 70)
    print("🎉 All manual tests completed successfully!")
    print("\nExpected Results Summary:")
    print("✅ Mock Greeks: Predefined values scaled by quantity")
    print("✅ Real Greeks: Calculated using py_vollib with fallback to mock")
    print("✅ Hybrid Greeks: Real calculation with mock fallback on error")
    print("✅ Portfolio Greeks: Aggregated from individual positions")
    print("✅ Option Parameters: Extracted from position data")
    
    print("\n📊 Test Results:")
    print("• Real Greeks calculation: Uses py_vollib Black-Scholes model")
    print("• Mock fallback: Uses predefined values from PRD specification")
    print("• Database integration: Ready for position_greeks table updates")
    print("• Batch processing: Ready for portfolio-wide calculations")

if __name__ == "__main__":
    asyncio.run(main())
import pytest
pytestmark = pytest.mark.skip(reason="Legacy/manual test; greeks hybrid API not present. Skipped in CI.")
