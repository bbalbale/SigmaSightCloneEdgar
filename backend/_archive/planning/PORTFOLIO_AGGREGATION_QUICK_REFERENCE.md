# Portfolio Aggregation Quick Reference

## Function Signatures

### 1. calculate_portfolio_exposures
```python
def calculate_portfolio_exposures(positions: List[Dict]) -> Dict[str, Any]:
    """
    Calculate portfolio-level exposure metrics.
    
    Returns:
    {
        'gross_exposure': Decimal,      # Sum of all absolute exposures
        'net_exposure': Decimal,        # Sum of signed exposures
        'long_exposure': Decimal,       # Sum of long exposures
        'short_exposure': Decimal,      # Sum of short exposures (negative)
        'long_count': int,              # Number of long positions
        'short_count': int,             # Number of short positions
        'options_exposure': Decimal,    # Sum of options exposures
        'stock_exposure': Decimal,      # Sum of stock exposures
        'notional_exposure': Decimal,   # Sum of abs(qty * price * multiplier)
        'metadata': {
            'calculated_at': str,
            'excluded_positions': int,
            'warnings': List[str]
        }
    }
    """
```

### 2. aggregate_portfolio_greeks
```python
def aggregate_portfolio_greeks(positions: List[Dict]) -> Dict[str, Decimal]:
    """
    Sum portfolio Greeks (options only).
    
    Returns:
    {
        'delta': Decimal,
        'gamma': Decimal,
        'theta': Decimal,
        'vega': Decimal,
        'rho': Decimal,
        'metadata': {
            'positions_with_greeks': int,
            'excluded_positions': int,
            'warnings': List[str]
        }
    }
    """
```

### 3. calculate_delta_adjusted_exposure
```python
def calculate_delta_adjusted_exposure(positions: List[Dict]) -> Dict[str, Decimal]:
    """
    Calculate both raw and delta-adjusted exposures.
    
    Returns:
    {
        'raw_exposure': Decimal,            # Same as gross_exposure
        'delta_adjusted_exposure': Decimal, # Sum of exposure * delta
        'metadata': {...}
    }
    """
```

### 4. aggregate_by_tags
```python
def aggregate_by_tags(
    positions: List[Dict], 
    tag_filter: Optional[List[str]] = None,
    tag_mode: str = 'any'
) -> Dict[str, Dict]:
    """
    Aggregate positions by tags.
    
    tag_mode: 'any' (OR) or 'all' (AND)
    
    Returns:
    {
        'tech': {
            'exposure': Decimal,
            'positions': int,
            'greeks': {...}
        },
        'growth': {...},
        ...
    }
    """
```

### 5. aggregate_by_underlying
```python
def aggregate_by_underlying(positions: List[Dict]) -> Dict[str, Dict]:
    """
    Group positions by underlying symbol.
    
    Returns:
    {
        'SPY': {
            'exposure': Decimal,
            'positions': int,
            'stock_exposure': Decimal,
            'options_exposure': Decimal,
            'greeks': {...}
        },
        'AAPL': {...},
        ...
    }
    """
```

## Position Dictionary Structure
```python
{
    'position_id': int,
    'symbol': str,
    'position_type': str,  # 'LONG', 'SHORT', 'LC', 'SC', 'LP', 'SP'
    'quantity': Decimal,
    'market_value': Decimal,      # Pre-calculated from 1.4.1
    'exposure': Decimal,          # Pre-calculated from 1.4.1
    'current_price': Decimal,     # For notional calculation
    'multiplier': int,            # 1 for stocks, 100 for options
    'underlying_symbol': str,     # For options only
    'tags': List[str],           # e.g., ['tech', 'growth']
    'greeks': Optional[Dict[str, Decimal]]  # None for stocks
}
```

## Key Implementation Rules
1. **Never recalculate** market_value or exposure
2. **Use Decimal** throughout, convert to float at API only
3. **Handle None Greeks** gracefully (stocks have no Greeks)
4. **Cache with 60s TTL** using @lru_cache
5. **Return metadata** with warnings and excluded counts
6. **Performance target**: <1 second for 10,000 positions

## Error Handling
- Missing required fields → exclude position, add warning
- Invalid Greek values → exclude position, add warning
- Empty portfolio → return zeros with empty metadata
- Never raise exceptions, always return valid structure
