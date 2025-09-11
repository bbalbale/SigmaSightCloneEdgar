"""
Manual testing script for portfolio aggregation functions.

This script demonstrates all portfolio aggregation capabilities with
sample data and various scenarios.

Usage:
    python scripts/test_portfolio_aggregation.py
"""

import json
from decimal import Decimal
from datetime import datetime
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.calculations.portfolio import (
    calculate_portfolio_exposures,
    aggregate_portfolio_greeks,
    calculate_delta_adjusted_exposure,
    aggregate_by_tags,
    aggregate_by_underlying,
    clear_portfolio_cache
)


def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"{title}")
    print(f"{'=' * 80}\n")


def create_sample_portfolio():
    """Create a sample portfolio with various position types."""
    return [
        # Long stocks
        {
            "position_id": 1,
            "symbol": "AAPL",
            "quantity": Decimal("100"),
            "market_value": Decimal("17500"),
            "exposure": Decimal("17500"),
            "position_type": "LONG",
            "tags": ["tech", "large-cap", "momentum"],
            "greeks": None
        },
        {
            "position_id": 2,
            "symbol": "MSFT",
            "quantity": Decimal("50"),
            "market_value": Decimal("18750"),
            "exposure": Decimal("18750"),
            "position_type": "LONG",
            "tags": ["tech", "large-cap", "quality"],
            "greeks": None
        },
        
        # Short stock
        {
            "position_id": 3,
            "symbol": "TSLA",
            "quantity": Decimal("-30"),
            "market_value": Decimal("-6000"),
            "exposure": Decimal("-6000"),
            "position_type": "SHORT",
            "tags": ["auto", "volatile", "momentum"],
            "greeks": None
        },
        
        # Long call options
        {
            "position_id": 4,
            "symbol": "SPY_240119C450",
            "underlying_symbol": "SPY",
            "quantity": Decimal("10"),
            "market_value": Decimal("5000"),
            "exposure": Decimal("5000"),
            "position_type": "LC",
            "tags": ["index", "hedge"],
            "greeks": {
                "delta": Decimal("0.65"),
                "gamma": Decimal("0.015"),
                "theta": Decimal("-25.50"),
                "vega": Decimal("12.30"),
                "rho": Decimal("8.75")
            }
        },
        {
            "position_id": 5,
            "symbol": "AAPL_240119C180",
            "underlying_symbol": "AAPL",
            "quantity": Decimal("5"),
            "market_value": Decimal("2500"),
            "exposure": Decimal("2500"),
            "position_type": "LC",
            "tags": ["tech", "leverage"],
            "greeks": {
                "delta": Decimal("0.55"),
                "gamma": Decimal("0.025"),
                "theta": Decimal("-15.00"),
                "vega": Decimal("8.50"),
                "rho": Decimal("4.25")
            }
        },
        
        # Short call option
        {
            "position_id": 6,
            "symbol": "QQQ_240119C380",
            "underlying_symbol": "QQQ",
            "quantity": Decimal("-5"),
            "market_value": Decimal("-1500"),
            "exposure": Decimal("-1500"),
            "position_type": "SC",
            "tags": ["index", "income"],
            "greeks": {
                "delta": Decimal("-0.30"),
                "gamma": Decimal("-0.020"),
                "theta": Decimal("18.00"),
                "vega": Decimal("-7.50"),
                "rho": Decimal("-3.00")
            }
        },
        
        # Long put option
        {
            "position_id": 7,
            "symbol": "SPY_240119P440",
            "underlying_symbol": "SPY",
            "quantity": Decimal("8"),
            "market_value": Decimal("3200"),
            "exposure": Decimal("3200"),
            "position_type": "LP",
            "tags": ["index", "hedge", "protection"],
            "greeks": {
                "delta": Decimal("-0.35"),
                "gamma": Decimal("0.018"),
                "theta": Decimal("-20.00"),
                "vega": Decimal("10.00"),
                "rho": Decimal("-5.50")
            }
        },
        
        # Short put option
        {
            "position_id": 8,
            "symbol": "MSFT_240119P360",
            "underlying_symbol": "MSFT",
            "quantity": Decimal("-3"),
            "market_value": Decimal("-900"),
            "exposure": Decimal("-900"),
            "position_type": "SP",
            "tags": ["tech", "income"],
            "greeks": {
                "delta": Decimal("0.25"),
                "gamma": Decimal("-0.012"),
                "theta": Decimal("12.00"),
                "vega": Decimal("-5.00"),
                "rho": Decimal("2.50")
            }
        }
    ]


def test_portfolio_exposures():
    """Test portfolio exposure calculations."""
    print_section("Portfolio Exposure Calculations")
    
    positions = create_sample_portfolio()
    result = calculate_portfolio_exposures(positions)
    
    print("Portfolio Exposure Summary:")
    print(json.dumps(decimal_to_float(result), indent=2))
    
    # Show breakdown
    print("\nBreakdown Analysis:")
    print(f"Total Positions: {result['metadata']['position_count']}")
    print(f"Long Positions: {result['long_count']} (${result['long_exposure']:,.2f})")
    print(f"Short Positions: {result['short_count']} (${result['short_exposure']:,.2f})")
    print(f"Net Direction: ${result['net_exposure']:,.2f}")
    print(f"Gross Leverage: ${result['gross_exposure']:,.2f}")
    print(f"Notional Exposure: ${result['notional']:,.2f}")


def test_greeks_aggregation():
    """Test Greeks aggregation."""
    print_section("Portfolio Greeks Aggregation")
    
    positions = create_sample_portfolio()
    result = aggregate_portfolio_greeks(positions)
    
    print("Portfolio Greeks Summary:")
    print(json.dumps(decimal_to_float(result), indent=2))
    
    print("\nGreeks Interpretation:")
    print(f"Delta: {result['delta']} (equivalent stock shares)")
    print(f"Gamma: {result['gamma']} (delta change per $1 move)")
    print(f"Theta: ${result['theta']} (daily time decay)")
    print(f"Vega: ${result['vega']} (per 1% volatility change)")
    print(f"Rho: ${result['rho']} (per 1% interest rate change)")


def test_delta_adjusted_exposure():
    """Test delta-adjusted exposure calculation."""
    print_section("Delta-Adjusted Exposure")
    
    positions = create_sample_portfolio()
    result = calculate_delta_adjusted_exposure(positions)
    
    print("Delta-Adjusted Exposure:")
    print(json.dumps(decimal_to_float(result), indent=2))
    
    print("\nExposure Comparison:")
    print(f"Raw Exposure: ${result['raw_exposure']:,.2f}")
    print(f"Delta-Adjusted: ${result['delta_adjusted_exposure']:,.2f}")
    
    # Calculate adjustment percentage
    if result['raw_exposure'] > 0:
        adjustment_pct = ((result['delta_adjusted_exposure'] / result['raw_exposure']) - 1) * 100
        print(f"Adjustment: {adjustment_pct:+.1f}%")


def test_tag_aggregation():
    """Test aggregation by tags."""
    print_section("Tag-Based Aggregation")
    
    positions = create_sample_portfolio()
    
    # Test 1: All tags
    print("1. All Tags Aggregation:")
    result = aggregate_by_tags(positions)
    
    # Sort tags by exposure for better display
    tags_sorted = sorted(
        [(k, v) for k, v in result.items() if k != "metadata"],
        key=lambda x: x[1]["gross_exposure"],
        reverse=True
    )
    
    for tag, metrics in tags_sorted:
        print(f"\n  Tag: {tag}")
        print(f"    Positions: {metrics['position_count']}")
        print(f"    Gross Exposure: ${metrics['gross_exposure']:,.2f}")
        print(f"    Net Exposure: ${metrics['net_exposure']:,.2f}")
    
    # Test 2: Filtered tags with ANY mode
    print("\n2. Filtered Tags (tech OR index):")
    result = aggregate_by_tags(positions, tag_filter=["tech", "index"], tag_mode="any")
    
    for tag in ["tech", "index"]:
        if tag in result:
            metrics = result[tag]
            print(f"\n  Tag: {tag}")
            print(f"    Positions: {metrics['position_count']}")
            print(f"    Gross Exposure: ${metrics['gross_exposure']:,.2f}")
    
    # Test 3: Single tag filter
    print("\n3. Single Tag Filter (hedge):")
    result = aggregate_by_tags(positions, tag_filter="hedge")
    
    if "hedge" in result:
        metrics = result["hedge"]
        print(f"  Hedge Positions: {metrics['position_count']}")
        print(f"  Total Hedge Exposure: ${metrics['gross_exposure']:,.2f}")


def test_underlying_aggregation():
    """Test aggregation by underlying symbol."""
    print_section("Underlying Symbol Aggregation")
    
    positions = create_sample_portfolio()
    result = aggregate_by_underlying(positions)
    
    print("Positions by Underlying Symbol:")
    
    # Sort by gross exposure
    underlyings_sorted = sorted(
        [(k, v) for k, v in result.items() if k != "metadata"],
        key=lambda x: x[1]["gross_exposure"],
        reverse=True
    )
    
    for symbol, metrics in underlyings_sorted:
        print(f"\n{symbol}:")
        print(f"  Total Positions: {metrics['position_count']}")
        print(f"  Stocks: {metrics['stock_count']}, Options: {metrics['option_count']}")
        if metrics['option_count'] > 0:
            print(f"  Calls: {metrics['call_count']}, Puts: {metrics['put_count']}")
        print(f"  Gross Exposure: ${metrics['gross_exposure']:,.2f}")
        print(f"  Net Exposure: ${metrics['net_exposure']:,.2f}")
        
        # Show Greeks if available
        if any(metrics['greeks'][g] != 0 for g in metrics['greeks']):
            print(f"  Combined Greeks:")
            print(f"    Delta: {metrics['greeks']['delta']}")
            print(f"    Gamma: {metrics['greeks']['gamma']}")
            print(f"    Theta: ${metrics['greeks']['theta']}")


def test_empty_portfolio():
    """Test edge case with empty portfolio."""
    print_section("Edge Case: Empty Portfolio")
    
    result = calculate_portfolio_exposures([])
    print("Empty Portfolio Exposures:")
    print(json.dumps(decimal_to_float(result), indent=2))


def test_performance():
    """Test performance with larger portfolio."""
    print_section("Performance Test")
    
    # Create a larger portfolio
    large_positions = []
    for i in range(1000):
        position_type = ["LONG", "SHORT", "LC", "LP", "SC", "SP"][i % 6]
        is_option = position_type in ["LC", "LP", "SC", "SP"]
        
        position = {
            "position_id": i,
            "symbol": f"SYM{i % 50}" if not is_option else f"SYM{i % 50}_240119C{100 + i % 20}",
            "quantity": Decimal(str(10 + i % 90)),
            "market_value": Decimal(str(1000 + i * 10)),
            "exposure": Decimal(str(1000 + i * 10)) * (1 if i % 3 != 0 else -1),
            "position_type": position_type,
            "tags": [f"sector{i % 5}", f"strategy{i % 3}"]
        }
        
        if is_option:
            position["underlying_symbol"] = f"SYM{i % 50}"
            position["greeks"] = {
                "delta": Decimal(str(0.5 - (i % 10) / 20)),
                "gamma": Decimal(str(0.01 + (i % 5) / 100)),
                "theta": Decimal(str(-10 - i % 20)),
                "vega": Decimal(str(5 + i % 10)),
                "rho": Decimal(str(1 + i % 5))
            }
        else:
            position["greeks"] = None
        
        large_positions.append(position)
    
    print(f"Testing with {len(large_positions)} positions...")
    
    import time
    
    # Test exposure calculation
    start = time.time()
    result = calculate_portfolio_exposures(large_positions)
    elapsed = time.time() - start
    print(f"\nExposure calculation: {elapsed:.3f} seconds")
    print(f"  Gross Exposure: ${result['gross_exposure']:,.2f}")
    
    # Test Greeks aggregation
    start = time.time()
    result = aggregate_portfolio_greeks(large_positions)
    elapsed = time.time() - start
    print(f"\nGreeks aggregation: {elapsed:.3f} seconds")
    print(f"  Portfolio Delta: {result['delta']}")
    
    # Test tag aggregation
    start = time.time()
    result = aggregate_by_tags(large_positions)
    elapsed = time.time() - start
    print(f"\nTag aggregation: {elapsed:.3f} seconds")
    print(f"  Unique tags found: {result['metadata']['tags_found']}")
    
    # Test underlying aggregation
    start = time.time()
    result = aggregate_by_underlying(large_positions)
    elapsed = time.time() - start
    print(f"\nUnderlying aggregation: {elapsed:.3f} seconds")
    print(f"  Unique underlyings: {result['metadata']['underlyings_found']}")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("PORTFOLIO AGGREGATION TESTING")
    print("="*80)
    print(f"Test started at: {datetime.now().isoformat()}")
    
    try:
        test_portfolio_exposures()
        test_greeks_aggregation()
        test_delta_adjusted_exposure()
        test_tag_aggregation()
        test_underlying_aggregation()
        test_empty_portfolio()
        test_performance()
        
        print_section("Testing Complete")
        print("All portfolio aggregation functions tested successfully!")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()