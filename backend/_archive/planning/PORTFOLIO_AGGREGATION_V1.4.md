# Portfolio Aggregation Design V1.4

> ⚠️ **IMPLEMENTATION STATUS (2025-08-26 15:55 PST)**: Portfolio aggregation has been fully implemented as part of Phase 1. See [TODO1.md](../../TODO1.md) Section 1.4.3 for completion details. This functionality is used by the Raw Data APIs.

## Overview
This document defines the detailed design decisions for portfolio aggregation functionality in SigmaSight V1.4. These decisions prioritize simplicity, performance, and alignment with the batch-first architecture.

## Design Decisions (Questions 1-15)

### 1. Position Data Structure
**Decision**: Use already-calculated values from ~~Section 1.4.1~~ **market data calculations (implemented)**

```python
{
    "position_id": int,
    "symbol": str,
    "quantity": Decimal,
    "market_value": Decimal,  # Already calculated by Section 1.4.1
    "exposure": Decimal,      # abs(market_value) - already calculated
    "position_type": str,     # "LONG", "SHORT", "LC", "LP", "SC", "SP"
    "underlying_symbol": str, # For options only
    "tags": List[str],        # ["momentum", "tech", "#strategy:pairs-trade"]
    "greeks": {              # None for stocks
        "delta": Decimal,
        "gamma": Decimal,
        "theta": Decimal,
        "vega": Decimal,
        "rho": Decimal
    }
}
```

**Important**: Aggregation functions should NOT recalculate market_value or exposure. These values are computed once in Section 1.4.1 and passed through the pipeline.

### 2. Greeks Aggregation Input
**Decision**: List of position dictionaries with Greeks already embedded

- No separate Greeks lookup needed
- Greeks are embedded in the position dict from Section 1.4.2
- Positions without Greeks (stocks) have `greeks: None`

### 3. Exposure Breakdown Structure
**Decision**: Comprehensive metrics including counts

```python
{
    "gross_exposure": Decimal,     # Sum of absolute exposures
    "net_exposure": Decimal,       # Sum of signed exposures
    "long_exposure": Decimal,      # Sum of positive exposures
    "short_exposure": Decimal,     # Sum of negative exposures (stored as negative)
    "long_count": int,            # Number of long positions
    "short_count": int,           # Number of short positions
    "options_exposure": Decimal,   # Exposure from options only
    "stock_exposure": Decimal      # Exposure from stocks only
}
```

### 4. Delta-Adjusted Exposure
**Decision**: Calculate both raw and delta-adjusted exposures

- Stocks: delta = 1.0 (long) or -1.0 (short)
- Skip positions with None Greeks (don't use mock values)
- Return structure:
```python
{
    "raw_exposure": Decimal,
    "delta_adjusted_exposure": Decimal
}
```

### 5. Sector/Industry Aggregation
**Decision**: NO sector/industry functions for V1.4

- Do NOT implement `aggregate_by_sector()` or `aggregate_by_industry()`
- Users can use tags like "tech", "financials" for sector-like grouping
- This simplifies the implementation and avoids dependency on market data enrichment

### 6. Tag-Based Aggregation
**Decision**: Single flexible function

```python
def aggregate_by_tags(
    positions: List[Dict],
    tag_filter: Optional[Union[str, List[str]]] = None,
    tag_mode: str = "any"  # "any" or "all"
) -> Dict[str, Dict]:
    """
    Aggregate positions by tags with flexible filtering.
    
    Args:
        positions: List of position dictionaries
        tag_filter: Optional tag(s) to filter by
        tag_mode: "any" (OR logic) or "all" (AND logic)
    
    Returns:
        Dict mapping tags to aggregated metrics
    """
```

### 7. Database Integration
**Decision**: Functions accept pre-loaded data, not database sessions

- No SQLAlchemy sessions or database queries inside aggregation functions
- All data is pre-loaded by the caller
- This enables easier testing and batch processing

### 8. Currency and Multiplier Handling
**Decision**: Values already in USD with multipliers applied

- No currency conversion logic in aggregation functions
- Option multipliers (100) already applied in market_value
- All values are in USD

### 9. Performance Considerations
**Decision**: Use pandas DataFrames for vectorized operations

- Target: < 1 second for 10,000 positions
- Use DataFrame operations for efficient aggregation
- Profile and optimize hot paths

### 10. Error Handling
**Decision**: Return zero values with metadata for empty portfolios

```python
{
    "data": {
        "gross_exposure": Decimal("0.00"),
        "net_exposure": Decimal("0.00"),
        # ... other fields with zero values
    },
    "metadata": {
        "calculated_at": "2024-01-15T10:30:00Z",
        "excluded_positions": 5,
        "warnings": ["5 positions excluded due to missing Greeks"]
    }
}
```

### 11. Return Value Consistency
**Decision**: Use Decimal throughout, convert to float only at API layer

- All monetary values as Decimal
- Greeks as Decimal for consistency
- Conversion to float happens in Pydantic response models

### 12. Batch Job Integration
**Decision**: Stateless functions for full recalculation

- No incremental updates
- Always recalculate from full position list
- Batch job calls these functions during nightly processing

### 13. Historical Aggregations
**Decision**: Current positions only for V1.4

```python
# TODO: Future enhancement for historical analysis
# def aggregate_portfolio_historical(positions, as_of_date):
#     """Calculate aggregations for a specific historical date"""
#     pass
```

### 14. API Response Format
**Decision**: Structured response with metadata

```python
{
    "summary": {
        "gross_exposure": Decimal,
        "net_exposure": Decimal,
        "long_exposure": Decimal,
        "short_exposure": Decimal,
        "position_count": int
    },
    "greeks": {
        "delta": Decimal,
        "gamma": Decimal,
        "theta": Decimal,
        "vega": Decimal,
        "rho": Decimal
    },
    "by_asset_type": {
        "stocks": {...},
        "options": {...}
    },
    "by_underlying": {  # Critical for options analysis
        "AAPL": {...},
        "SPY": {...}
    },
    "metadata": {
        "calculated_at": str,
        "cache_ttl": int,
        "warnings": List[str]
    }
}
```

### 15. Testing Data Requirements
**Decision**: Comprehensive test scenarios

1. **Mixed Portfolio**: 50 stocks, 50 options across different sectors
2. **Edge Cases**:
   - Empty portfolio
   - Single position
   - All long positions
   - All short positions
3. **Missing Greeks**: Positions without Greeks data
4. **Large Portfolio**: 1000+ positions for performance testing
5. **Complex Tags**: Multiple strategy tags, overlapping categories

## Implementation Guidelines

### Function Signatures

```python
# Core aggregation functions
def calculate_portfolio_exposures(positions: List[Dict]) -> Dict[str, Any]
def aggregate_portfolio_greeks(positions: List[Dict]) -> Dict[str, Decimal]
def calculate_delta_adjusted_exposure(positions: List[Dict]) -> Dict[str, Decimal]
def aggregate_by_tags(positions: List[Dict], tag_filter: Optional[Union[str, List[str]]] = None, tag_mode: str = "any") -> Dict[str, Dict]
def aggregate_by_underlying(positions: List[Dict]) -> Dict[str, Dict]
```

### Batch Job Integration

The nightly batch job (5:30 PM EST) will:
1. Load all positions with current market values
2. Call aggregation functions
3. Store results in `portfolio_snapshots` table
4. Cache results for API responses

### Performance Optimization

1. Use pandas DataFrames for vectorized operations
2. Pre-filter positions before aggregation
3. Cache results with 60-second TTL
4. Profile with 10,000 position datasets

## What We're NOT Implementing

1. **Sector/Industry Aggregation**: Use tags instead
2. **Real-time Updates**: Batch-first approach only
3. **Historical Aggregations**: Deferred to future phases
4. **Currency Conversion**: All values in USD
5. **Recalculation of Base Values**: Use pre-calculated values

## Dependencies

- Section 1.4.1: Provides market_value and exposure
- Section 1.4.2: Provides Greeks calculations
- Batch Processing: Calls these functions nightly
- API Layer: Converts Decimal to float for responses

## Testing Requirements

### Test Scenarios
1. **Mixed Portfolio**: 50 stocks + 50 options with various tags
2. **Edge Cases**: Empty portfolio, single position, all long/short
3. **Missing Greeks**: Options without Greeks data
4. **Large Portfolio**: 10,000 positions for performance testing
5. **Complex Tags**: Positions with multiple overlapping tags

### Expected Behaviors
- Empty portfolios return zero values with metadata
- Missing Greeks positions are excluded from Greeks aggregation
- Performance target: <1 second for 10,000 positions
- All monetary values use Decimal with proper precision
- Tag aggregation supports both "any" and "all" modes

---

## Implementation Decisions (Questions 16-25)

### 16. Precision & Rounding
**Decision**: Apply different precision for different value types
- Monetary values: 2 decimal places (stored as DECIMAL in database)
- Greeks: 4 decimal places (for accuracy in aggregations)
- Percentages: 2 decimal places
- Apply rounding at the API response layer, not in calculations or storage

### 17. Underlying-Symbol Breakdowns
**Decision**: Yes, implement `aggregate_by_underlying()`
- Critical for options portfolios (e.g., all SPY positions together)
- Include both stock and options positions for each underlying
- Required for proper risk analysis in options-heavy portfolios

### 18. Option Sign Conventions
**Decision**: Use signed-by-quantity Greeks consistently
- Maintain mathematical correctness from `calculate_position_greeks()`
- Short call delta remains negative, short put delta remains positive
- No overrides or transformations - preserve the signs for accurate hedging calculations

### 19. Point-in-Time Parameter
**Decision**: Current positions only for V1.4
- No `as_of_date` parameter needed for the demo
- All aggregations work on current positions from latest batch job
- Add comment for future enhancement: `# TODO: Add as_of_date support for historical analysis`

### 20. Storage vs. On-Demand
**Decision**: Hybrid approach

**Store in portfolio_snapshots** (via 5:30 PM batch job):
- Portfolio-level exposures (gross/net/long/short)
- Aggregated Greeks totals
- Position counts by type

**Compute on-demand** for API requests:
- Tag-based aggregations
- Underlying-based aggregations
- Any custom groupings

### 21. Notional vs. Dollar Exposures
**Decision**: Include both notional and dollar exposures
```python
{
    "exposures": {
        "gross": Decimal,     # Dollar exposure
        "net": Decimal,       # Dollar exposure
        "notional": Decimal   # Sum of abs(quantity × price × multiplier)
    }
}
```
Notional exposure helps assess leverage, especially for options positions.

### 22. API Pagination/Filtering
**Decision**: Basic filtering only, no pagination for V1.4
- Support query parameters: `?tag=momentum` or `?underlying=AAPL`
- Return all results (unlikely to exceed 100 items in demo)
- Document pagination structure for future: `# TODO: Add pagination for production`

### 23. Concurrency Requirements
**Decision**: No special concurrency handling for V1.4
- Single-threaded batch processing is sufficient
- Read-only aggregations don't need locking
- Demo is single-user per portfolio

### 24. Caching & TTL
**Decision**: Simple in-memory caching with 60-second TTL
```python
# Cache configuration
AGGREGATION_CACHE_TTL = 60  # seconds
CACHE_KEY_FORMAT = "portfolio_agg:{user_id}:{agg_type}:{filters}"
```
Use `functools.lru_cache` for simple method-level caching.

### 25. Configurability
**Decision**: Hard-code with named constants
```python
# app/constants/portfolio.py
OPTIONS_MULTIPLIER = 100
DEFAULT_SECTOR = "Unknown"
DEFAULT_INDUSTRY = "Unknown"

# Greeks precision
GREEKS_DECIMAL_PLACES = 4
MONETARY_DECIMAL_PLACES = 2

# Cache settings
AGGREGATION_CACHE_TTL = 60
```

## Summary

These decisions prioritize simplicity and performance for the demo while maintaining accuracy in calculations. The hybrid storage approach ensures fast API responses while allowing flexibility for detailed analysis. Key principles:

1. **Precision**: Different decimal places for different value types
2. **Storage**: Hybrid approach - store summaries, compute details on-demand
3. **Performance**: Target <1 second for 10,000 positions using pandas
4. **Simplicity**: No complex concurrency or pagination for V1.4
5. **Flexibility**: Support tag-based and underlying-based aggregations
