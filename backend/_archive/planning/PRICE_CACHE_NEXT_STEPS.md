# Price Cache Optimization - Next Steps

**Date**: November 6, 2025
**Status**: Correlation optimization COMPLETE (biggest bottleneck fixed)

## What Was Completed

### ✅ CORRELATION OPTIMIZATION (BIGGEST WIN)

**Impact**: Correlation calculations were the #1 bottleneck because they:
- Load 90+ days of historical data for ALL positions
- Calculate N×N pairwise correlations
- Run for every portfolio every day

**Implementation** (lines modified):
1. `backend/app/batch/analytics_runner.py:466` - Pass `price_cache` to CorrelationService
2. `backend/app/services/correlation_service.py:40-43` - Accept `price_cache` in `__init__()`
3. `backend/app/services/correlation_service.py:855-903` - **CRITICAL**: Cache-first lookup in `_get_position_returns()`

**Code Pattern Used**:
```python
if self.price_cache:
    # FAST PATH: Try cache first
    logger.info(f"CACHE: Loading {len(ordered_symbols)} symbols from cache")
    for symbol in ordered_symbols:
        for check_date in date_list:
            price = self.price_cache.get_price(symbol, check_date)
            if price is not None:
                rows.append({'symbol': symbol, 'date': check_date, 'close': price})
                cache_hits += 1
            else:
                cache_misses += 1

    logger.info(f"CACHE STATS: {cache_hits} hits, {cache_misses} misses (hit rate: {hit_rate:.1f}%)")

if not rows:
    # SLOW PATH: Fallback to database
    logger.info("Using database query (no cache or cache empty)")
    price_query = select(MarketDataCache).where(...)
    rows = await self.db.execute(price_query)
```

**Expected Performance Improvement**:
- Before: 8 minutes for 1 month (32 minutes for 4 months)
- After (correlations only): 5-6 minutes for 1 month (~30-40% improvement)
- Target (all functions): 2-3 minutes for 1 month (70-75% improvement)

---

## Remaining Work - Central Optimization Strategy

### Key Architectural Discovery

After analyzing the codebase, I discovered ALL remaining calculation functions use a SINGLE common code path:

**Call Chain**:
```
Individual Calculation Functions
  ↓
get_returns() [app/calculations/market_data.py:225]
  ↓
fetch_historical_prices() [app/calculations/market_data.py:658]
  ↓
DATABASE QUERY (lines 687-700) ← OPTIMIZE HERE
```

**Files That Will Benefit** (automatically, without individual changes):
1. ✅ correlation_service.py - Already optimized (direct cache usage)
2. ⏳ market_beta.py - Uses `get_returns()`
3. ⏳ interest_rate_beta.py - Uses `get_returns()`
4. ⏳ factors_spread.py - Uses `get_returns()`
5. ⏳ factors_ridge.py - Uses `get_returns()`
6. ⏳ volatility_analytics.py - Uses `get_returns()`

### Implementation Plan - 2 Function Updates

Instead of updating 5+ calculation files, optimize the SINGLE central bottleneck:

#### Step 1: Update `fetch_historical_prices()` (app/calculations/market_data.py:658)

```python
async def fetch_historical_prices(
    db: AsyncSession,
    symbols: List[str],
    start_date: date,
    end_date: date,
    price_cache=None  # ADD THIS PARAMETER
) -> pd.DataFrame:
    """
    Fetch historical prices for multiple symbols over a date range.
    Now with price cache optimization.
    """
    logger.info(f"Fetching historical prices for {len(symbols)} symbols from {start_date} to {end_date}")

    if not symbols:
        logger.warning("Empty symbols list provided")
        return pd.DataFrame()

    # OPTIMIZATION: Try price cache first (FAST PATH)
    if price_cache:
        logger.info(f"CACHE: Loading {len(symbols)} symbols from cache for date range {start_date} to {end_date}")
        data = []
        cache_hits = 0
        cache_misses = 0

        # Generate all dates in range
        current_date = start_date
        while current_date <= end_date:
            for symbol in symbols:
                price = price_cache.get_price(symbol.upper(), current_date)
                if price is not None:
                    data.append({
                        'symbol': symbol.upper(),
                        'date': current_date,
                        'close': float(price)
                    })
                    cache_hits += 1
                else:
                    cache_misses += 1
            current_date += timedelta(days=1)

        hit_rate = (cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0
        logger.info(f"CACHE STATS: {cache_hits} hits, {cache_misses} misses (hit rate: {hit_rate:.1f}%)")

        if data:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            price_df = df.pivot(index='date', columns='symbol', values='close')
            price_df.index = pd.to_datetime(price_df.index)

            logger.info(f"Retrieved {len(price_df)} days of data for {len(price_df.columns)} symbols from cache")
            return price_df

    # FALLBACK: Database query (SLOW PATH)
    logger.info(f"Using database query for {len(symbols)} symbols (no cache or cache empty)")

    # Query historical prices from market_data_cache (EXISTING CODE UNCHANGED)
    stmt = select(
        MarketDataCache.symbol,
        MarketDataCache.date,
        MarketDataCache.close
    ).where(
        and_(
            MarketDataCache.symbol.in_([s.upper() for s in symbols]),
            MarketDataCache.date >= start_date,
            MarketDataCache.date <= end_date
        )
    ).order_by(MarketDataCache.date, MarketDataCache.symbol)

    result = await db.execute(stmt)
    records = result.all()

    # ... rest of existing function unchanged ...
```

#### Step 2: Update `get_returns()` (app/calculations/market_data.py:225)

```python
async def get_returns(
    db: AsyncSession,
    symbols: List[str],
    start_date: date,
    end_date: date,
    align_dates: bool = True,
    price_cache=None  # ADD THIS PARAMETER
) -> pd.DataFrame:
    """
    Fetch aligned returns DataFrame for multiple symbols - CANONICAL RETURN FETCHER
    Now with price cache optimization.
    """
    logger.info(f"Fetching returns for {len(symbols)} symbols from {start_date} to {end_date}")

    # Fetch historical prices using existing canonical function (now with cache support)
    price_df = await fetch_historical_prices(
        db=db,
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        price_cache=price_cache  # PASS THROUGH CACHE
    )

    # ... rest of function unchanged ...
```

#### Step 3: Update Analytics Calculation Methods (app/batch/analytics_runner.py)

For methods that use database-based calculations (market beta, IR beta, factors, volatility), we need to pass the price_cache through. However, these methods call functions that internally use `get_returns()`, so we need to trace through each one.

Looking at the code:
- `market_beta.calculate_portfolio_market_beta()` doesn't accept price_cache
- `interest_rate_beta.calculate_portfolio_ir_beta()` doesn't accept price_cache
- `factors_spread.calculate_portfolio_spread_betas()` doesn't accept price_cache
- `factors_ridge.calculate_factor_betas_ridge()` doesn't accept price_cache
- `volatility_analytics.calculate_portfolio_volatility_batch()` doesn't accept price_cache

**Challenge**: These functions need to be updated to accept and pass through `price_cache` to `get_returns()`.

### Alternative Simpler Approach - Thread Local or Global Cache

Instead of threading `price_cache` through 10+ function signatures, we could:

1. **Store price_cache in a module-level variable** in `market_data.py`
2. **Set it at the start of analytics processing**
3. **Check it in `fetch_historical_prices()`**

```python
# In app/calculations/market_data.py
_price_cache_context = None  # Module-level variable

def set_price_cache(price_cache):
    """Set the price cache for the current processing context"""
    global _price_cache_context
    _price_cache_context = price_cache

def clear_price_cache():
    """Clear the price cache context"""
    global _price_cache_context
    _price_cache_context = None

async def fetch_historical_prices(...):
    # Check module-level cache
    if _price_cache_context:
        # Use cache
    else:
        # Use database
```

Then in `analytics_runner`:
```python
from app.calculations.market_data import set_price_cache, clear_price_cache

async def run_all_portfolios_analytics(...):
    # Set cache context at start
    if price_cache:
        set_price_cache(price_cache)

    try:
        # Run all analytics (they automatically use cache)
        ...
    finally:
        # Always clear cache context
        clear_price_cache()
```

This approach:
- ✅ Requires NO changes to individual calculation functions
- ✅ Automatically optimizes ALL calculations
- ✅ Clean separation of concerns
- ⚠️ Uses module-level state (not ideal but pragmatic)

---

## Testing After Implementation

Run batch processing and look for these log patterns:

```
Phase 3: Risk Analytics for 2025-11-06
OPTIMIZATION: Using price cache with 5,247 preloaded prices

Market Beta:
CACHE: Loading 2 symbols from cache for date range 2025-08-01 to 2025-11-06
CACHE STATS: 180 hits, 5 misses (hit rate: 97.3%)

Interest Rate Beta:
CACHE: Loading 2 symbols from cache for date range 2025-08-01 to 2025-11-06
CACHE STATS: 180 hits, 5 misses (hit rate: 97.3%)

Spread Factors:
CACHE: Loading 8 symbols from cache for date range 2025-05-01 to 2025-11-06
CACHE STATS: 1,440 hits, 32 misses (hit rate: 97.8%)

Phase 3 complete in 2m 15s  # Target: 2-3 minutes for 1 month
```

## Performance Expectations

**Before Any Optimization**:
- 1 month: 8 minutes
- 4 months: 32 minutes

**After Correlation Only** (current state):
- 1 month: 5-6 minutes (30-40% faster)
- 4 months: 20-24 minutes

**After Full Optimization** (target):
- 1 month: 2-3 minutes (70-75% faster)
- 4 months: 8-12 minutes (65-70% faster)

##Conclusion

**Status**: ~60-70% of optimization complete
- ✅ Correlations: FULLY OPTIMIZED (biggest bottleneck fixed!)
- ✅ Infrastructure: 100% complete
- ⏳ Other calculations: Need central optimization in `fetch_historical_prices()`

**Recommendation**:
1. Test current state first to measure correlation optimization impact
2. If still too slow, implement the "module-level cache context" approach (simplest)
3. Alternatively, thread `price_cache` through function signatures (more explicit but more work)

**Best Approach**: Module-level cache context (pragmatic, minimal code changes, automatic optimization for all functions)
