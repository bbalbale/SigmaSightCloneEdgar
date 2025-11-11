# Price Cache Integration Status

**Date**: November 6, 2025
**Purpose**: Document price cache optimization implementation for batch processing

## Problem Statement

Batch processing was taking 8 minutes for 1 month of data (projected 32 minutes for 4 months), even after creating database indexes. Root cause: Phase 3 (Analytics) was not using the preloaded price cache.

## What Was Implemented

### ✅ Completed

1. **Database Indexes** (All 3 Priority Indexes Created)
   - `idx_positions_active_complete` - Portfolio + active position filtering
   - `idx_market_data_valid_prices` - Valid price lookups
   - `idx_positions_symbol_active` - Symbol universe queries

2. **Price Cache Infrastructure**
   - `PriceCache` class with single-day and multi-day loading (backend/app/cache/price_cache.py)
   - Bulk date range loading in batch_orchestrator (lines 204-212)
   - Cache loaded once for entire backfill date range (ONE query instead of N queries)

3. **Price Cache Plumbing to Analytics**
   - Pass `price_cache` from batch_orchestrator to analytics_runner (line 504)
   - analytics_runner stores cache in `self._price_cache` instance variable (line 69)
   - analytics_runner logs cache stats on startup (lines 70-74)

4. **UUID JSON Serialization Fix**
   - Added UUID support to CustomJSONEncoder (backend/app/utils/json_utils.py)
   - Fixes telemetry metrics serialization errors

5. **Stress Test Scenarios Seeded**
   - 18 scenarios (6 historical + 12 hypothetical) now in database
   - Required for analytics phase stress testing

6. **PRIVATE Position Exclusion**
   - Batch orchestrator no longer tries to fetch prices for illiquid PRIVATE positions

### ⚠️ Partial - Needs Completion

**Analytics Calculation Functions Do NOT Yet Use Price Cache**

The price cache is loaded and available via `self._price_cache` in analytics_runner, but the individual calculation methods still query the database directly instead of checking the cache first.

## What Remains To Achieve Full Optimization

### Files That Need Updates

Each of these calculation functions needs to be updated to check `price_cache` (if provided) before falling back to database queries:

1. **backend/app/calculations/market_beta.py**
   - Update to use price cache for historical S&P 500 prices
   - Current: Queries MarketDataCache table for each date
   - Target: Check cache first, fall back to DB if not found

2. **backend/app/calculations/interest_rate_beta.py**
   - Update to use price cache for historical treasury rates
   - Current: Direct DB queries
   - Target: Cache-first lookups

3. **backend/app/calculations/factors_spread.py**
   - Update to use price cache for factor ETF prices (SMB, HML, UMD, etc.)
   - Current: Multiple DB queries per factor
   - Target: Bulk cache lookups

4. **backend/app/calculations/factors_ridge.py**
   - Same as factors_spread

5. **backend/app/calculations/correlations.py**
   - Update to use price cache for position price histories
   - Current: Queries for each symbol/date combination
   - Target: Cache lookups for entire date range

6. **backend/app/calculations/volatility_analytics.py**
   - Update HAR model to use cached prices
   - Current: DB queries for historical volatility calc
   - Target: Cache-based volatility calculations

### Implementation Pattern

For each calculation function, add this pattern:

```python
# Inside analytics_runner calculation methods
async def _calculate_market_beta(self, db: AsyncSession, portfolio_id: UUID, calc_date: date):
    # Check if price cache is available
    if self._price_cache:
        # Use cache for price lookups
        sp500_price = self._price_cache.get_price('^GSPC', calc_date)
        if sp500_price:
            logger.debug(f"CACHE HIT: ^GSPC on {calc_date}")
        else:
            logger.debug(f"CACHE MISS: ^GSPC on {calc_date}, falling back to DB")
            sp500_price = await fetch_from_db(db, '^GSPC', calc_date)
    else:
        # No cache available, use database
        sp500_price = await fetch_from_db(db, '^GSPC', calc_date)
```

### Expected Performance Improvement

**Current State** (with indexes but no cache usage in analytics):
- 1 month: 8 minutes
- 4 months: ~32 minutes

**Target State** (with full price cache integration):
- 1 month: 2-3 minutes (60-65% faster)
- 4 months: 8-12 minutes (60-65% faster)

### Why This Wasn't Done

The full implementation would require updating 6+ calculation files with careful testing to ensure:
1. Cache hits/misses are handled correctly
2. Graceful degradation when cache unavailable
3. No breaking changes to existing functionality
4. Proper logging of cache effectiveness

This is a significant refactoring that should be done systematically with proper testing.

## Current Optimization Status

**Indexes**: ✅ 100% Complete (3/3 indexes in place)
**Price Cache Loading**: ✅ 100% Complete (bulk loading working)
**Cache Plumbing**: ✅ 100% Complete (passed to analytics)
**Cache Usage**: ❌ 0% Complete (calculations don't use it yet)

**Overall**: ~75% infrastructure complete, 25% utilization complete

## Next Steps

1. **Quick Win**: Update `_calculate_correlations()` first - this is likely the biggest bottleneck
2. **Medium Win**: Update factor calculations (spread/ridge)
3. **Full Win**: Update all remaining calculation functions

## Testing After Implementation

Run diagnostics:
```bash
cd backend
uv run python scripts/diagnostics/check_optimizations.py
```

Expected log output with full implementation:
```
OPTIMIZATION: Using price cache with 5,000+ preloaded prices
CACHE HIT: ^GSPC on 2025-11-06
CACHE HIT: SMB on 2025-11-06
...
Cache stats: {'hits': 4500, 'misses': 50, 'hit_rate': 0.99}
```

## Files Modified This Session

1. `backend/app/batch/batch_orchestrator.py` - Pass price_cache to analytics (line 504)
2. `backend/app/batch/analytics_runner.py` - Accept and store price_cache (lines 50, 69-74, 102)
3. `backend/app/utils/json_utils.py` - UUID serialization support (lines 4, 12-13)
4. `backend/app/calculations/snapshots.py` - Fixed skip_provider_beta bug (lines 306-315)
5. `backend/scripts/database/apply_performance_indexes.py` - Manual index creation (NEW FILE)
6. `backend/scripts/database/seed_stress_scenarios_safe.py` - Stress scenarios seed (NEW FILE)

## Conclusion

The infrastructure for price cache optimization is 75% complete. The cache is loaded and available to analytics functions, but the individual calculation methods need to be updated to actually use it instead of querying the database directly.

The work done provides significant value:
- Database indexes speed up ALL queries (not just batch)
- Infrastructure is in place for easy cache integration
- Clear documentation of what remains

**Recommendation**: Implement cache usage in correlation calculations first as a pilot, then roll out to other functions systematically.
