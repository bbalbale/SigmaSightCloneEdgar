# Fix Railway Cron Batch Processing Issues

**Created**: 2025-11-26
**Status**: IMPLEMENTED
**Priority**: High

---

## Implementation Plan (5 Changes)

### Change 1: Standardize on "IR Beta" in seed_factors.py ✅ DONE

**File**: `backend/app/db/seed_factors.py` (Line 38)

```python
# BEFORE:
    {
        "name": "Interest Rate",
        "description": "Interest rate sensitivity via regression vs TLT (20+ year treasury bonds)",
        "factor_type": "macro",
        "calculation_method": "ridge_regression",
        "etf_proxy": "TLT",
        "display_order": 2
    },

# AFTER:
    {
        "name": "IR Beta",
        "description": "Interest rate sensitivity via regression vs TLT (20+ year treasury bonds)",
        "factor_type": "macro",
        "calculation_method": "rolling_regression",
        "etf_proxy": "TLT",
        "display_order": 2
    },
```

---

### Change 2: Standardize on "IR Beta" in stress_testing.py ✅ DONE

**File**: `backend/app/calculations/stress_testing.py` (Line 285)

```python
# BEFORE:
        FACTOR_NAME_MAP = {
            'Market': 'Market Beta (90D)',
            'Interest_Rate': 'Interest Rate',
        }

# AFTER:
        FACTOR_NAME_MAP = {
            'Market': 'Market Beta (90D)',
            'Interest_Rate': 'IR Beta',
        }
```

---

### Change 3: Add Factor Seeding to Railway Cron ✅ DONE

**File**: `backend/scripts/automation/railway_daily_batch.py`

**Add imports after line 51**:
```python
from app.database import AsyncSessionLocal
from app.db.seed_factors import seed_factors
```

**Add function after line 53**:
```python
async def ensure_factor_definitions():
    """Ensure factor definitions exist before running batch."""
    logger.info("Verifying factor definitions...")
    async with AsyncSessionLocal() as db:
        await seed_factors(db)
        await db.commit()
    logger.info("Factor definitions verified/seeded")
```

**Update main() - add call before batch orchestrator (around line 65)**:
```python
    try:
        # Ensure factor definitions exist before running batch
        await ensure_factor_definitions()

        # Run the batch orchestrator
        logger.info("Starting batch orchestrator with automatic backfill...")
        results = await batch_orchestrator.run_daily_batch_with_backfill()
```

---

### Change 4: Restructure Batch Orchestrator - Run All Phase 1s Before Loading Cache ✅ DONE

**File**: `backend/app/batch/batch_orchestrator.py`

**Current flow (broken)**:
```
1. Load price cache from market_data_cache
2. For each date:
   - Phase 1: Fetch market data → writes to DB
   - Phases 2-6: Use price cache (missing today's data!)
```

**New flow (correct)**:
```
1. For each date: Run Phase 1 ONLY (fill market_data_cache for all dates)
2. Load price cache ONCE (now has all data including today)
3. For each date: Run Phases 2-6 (use fully populated cache)
```

**Implementation**: Restructure `run_daily_batch_with_backfill()` to separate market data collection from analytics:

```python
async def run_daily_batch_with_backfill(self, ...):
    # ... existing date detection logic ...

    # STEP 1: Run Phase 1 (Market Data) for ALL dates first
    logger.info(f"[PHASE 1] Collecting market data for {len(missing_dates)} dates...")
    for calc_date in missing_dates:
        async with AsyncSessionLocal() as db:
            await market_data_collector.collect_daily_market_data(
                calculation_date=calc_date,
                lookback_days=365,
                db=db,
                portfolio_ids=portfolio_ids,
                skip_company_profiles=(calc_date != target_date)
            )

    # STEP 2: Load price cache AFTER all market data is collected
    logger.info(f"[CACHE] Loading price cache after market data collection...")
    price_cache = PriceCache()
    async with AsyncSessionLocal() as cache_db:
        symbols = await self._get_all_symbols(cache_db)
        cache_start = missing_dates[0] - timedelta(days=366)
        loaded_count = await price_cache.load_date_range(
            db=cache_db,
            symbols=symbols,
            start_date=cache_start,
            end_date=missing_dates[-1]
        )
        logger.info(f"[OK] Price cache loaded: {loaded_count} prices")

    # STEP 3: Run Phases 2-6 for all dates (using populated cache)
    results = []
    for calc_date in missing_dates:
        async with AsyncSessionLocal() as db:
            result = await self._run_phases_2_through_6(
                db=db,
                calculation_date=calc_date,
                portfolio_ids=portfolio_ids,
                price_cache=price_cache,
                run_sector_analysis=(calc_date == target_date)
            )
            results.append(result)
            if result['success']:
                await self._mark_batch_run_complete(db, calc_date, result)
            await db.commit()

    return {...}
```

---

### Change 5: Handle PRIVATE-only Portfolios Gracefully ✅ DONE

**File**: `backend/app/calculations/market_beta.py` (around line 618)

```python
# BEFORE:
if not positions:
    raise ValueError(f"No active positions found for portfolio {portfolio_id}")

# AFTER:
if not positions:
    logger.info(f"No PUBLIC positions found for portfolio {portfolio_id} - skipping provider beta")
    return {
        'portfolio_id': str(portfolio_id),
        'success': True,
        'skipped': True,
        'reason': 'no_public_positions',
        'portfolio_beta': None,
    }
```

**File**: `backend/app/calculations/market_risk.py` (around line 181)

```python
# BEFORE:
if not positions:
    raise ValueError(f"No active positions found for portfolio {portfolio_id}")

# AFTER:
if not positions:
    logger.info(f"No active positions found for portfolio {portfolio_id} - skipping market risk scenarios")
    return {
        'portfolio_id': str(portfolio_id),
        'success': True,
        'skipped': True,
        'reason': 'no_active_positions',
    }
```

---

### Post-Deploy: Database Cleanup

Run SQL to remove duplicate factor definition:

```sql
-- Check current state
SELECT id, name, factor_type, created_at
FROM factor_definitions
WHERE name IN ('Interest Rate', 'IR Beta')
ORDER BY created_at;

-- Delete old "Interest Rate" factor (if exists)
DELETE FROM factor_definitions WHERE name = 'Interest Rate';
```

---

## Testing Plan (Railway Only)

1. Deploy changes to Railway sandbox
2. Trigger manual fix: `uv run python scripts/railway/trigger_railway_fix.py --base-url https://sandbox-url`
3. Check logs for:
   - `[PHASE 1] Collecting market data for X dates...`
   - `[CACHE] Loading price cache after market data collection...`
   - `Factor definitions verified/seeded`
   - No "No exposure found for shocked factor: Interest_Rate" warnings
4. Verify frontend Risk Metrics page shows:
   - IR Beta in Factor Exposures section
   - Stress test scenarios with non-zero impacts
   - Volatility metrics populated
5. Run daily cron and verify completes in <5 minutes for single-day

---

## Success Criteria

- [ ] Daily cron completes in <5 minutes for single-day runs
- [ ] No "No exposure found for shocked factor: Interest_Rate" warnings
- [ ] Volatility metrics appear in portfolio snapshots
- [ ] Stress testing returns non-zero scenarios with IR impacts
- [ ] PRIVATE-only portfolios skip gracefully (info log, not error)
- [ ] Frontend Risk Metrics page displays IR Beta correctly

---

## Files Changed Summary

| File | Change |
|------|--------|
| `backend/app/db/seed_factors.py` | `"Interest Rate"` → `"IR Beta"` |
| `backend/app/calculations/stress_testing.py` | Mapping to `"IR Beta"` |
| `backend/scripts/automation/railway_daily_batch.py` | Add factor seeding |
| `backend/app/batch/batch_orchestrator.py` | Run all Phase 1s before cache load |
| `backend/app/calculations/market_beta.py` | Graceful skip for PRIVATE portfolios |
| `backend/app/calculations/market_risk.py` | Graceful skip for no positions |

---

---

# Analysis & Background

## Executive Summary

The Railway cron job (`railway_daily_batch.py`) has multiple issues causing:
- Volatility metrics disappearing
- Stress testing failures with "No exposure found for Interest_Rate" warnings
- 20-minute runtime for 3-day processing (vs 10 min for 101-day backfill)
- "No active positions found" errors

**Root causes**:
1. Missing factor definition seeding in cron job
2. Factor naming inconsistency: `"Interest Rate"` vs `"IR Beta"` in different files
3. Price cache loaded BEFORE Phase 1 fills market data
4. PRIVATE-only portfolios not handled gracefully

---

## Issue 1: Missing Factor Definition Seeding

**Symptom**: Phase 6 analytics fail silently, no factor exposures created

| Script | Calls seed_factors()? | Result |
|--------|----------------------|--------|
| `trigger_railway_fix.py` | Yes (via admin_fix.py:64) | Factor definitions exist |
| `railway_daily_batch.py` | **No** | Factor definitions may be missing |

---

## Issue 2: Interest Rate Factor Name Mismatch

**Symptom**: `No exposure found for shocked factor: Interest_Rate`

### Audit Results

**Files using `"IR Beta"` (CORRECT - matches frontend)**:
| File | Usage |
|------|-------|
| `analytics_runner.py:191,456,465` | Creates and stores as "IR Beta" |
| `FactorExposureCards.tsx:17,99` | Frontend expects "IR Beta" |
| `FactorExposureHeroRow.tsx:10` | Frontend expects "IR Beta" |

**Files using `"Interest Rate"` (INCORRECT)**:
| File | Usage |
|------|-------|
| `seed_factors.py:38` | Seeds as "Interest Rate" |
| `stress_testing.py:285` | Maps to "Interest Rate" |

### The Bug Flow

```
1. seed_factors.py creates factor named "Interest Rate" (empty)
2. analytics_runner.py looks for "IR Beta", doesn't find it
3. analytics_runner.py creates NEW factor "IR Beta" with data
4. Database now has TWO factors:
   - "Interest Rate" (from seed, empty)
   - "IR Beta" (from analytics, has data)
5. stress_testing.py maps Interest_Rate → "Interest Rate" factor
6. Lookup finds empty factor → WARNING
```

**Decision**: Standardize on `"IR Beta"` (fewest files to change, matches frontend).

---

## Issue 3: Price Cache Timing

**Symptom**: Daily cron for 3 days takes ~20 minutes, but 101-day backfill takes ~10 minutes

### Current Flow (Broken)

```
1. Load price cache from market_data_cache table
   → Loads historical data (exists)
   → Does NOT have today's data (not fetched yet)

2. For each missing date:
   - Phase 1: Fetch market data → writes to market_data_cache DB table
   - Phases 2-6: Use price cache (in-memory dictionary)
     → Cache doesn't have today's data!
     → Falls back to individual DB queries
     → Slower, potential rate limiting
```

### Key Insight

The price cache is an **in-memory dictionary** loaded ONCE at the start. When Phase 1 writes new data to the `market_data_cache` table, the in-memory cache doesn't see it.

Note: `clear_calculations_comprehensive()` does NOT clear `market_data_cache` - it only clears analytics tables. So historical price data is preserved.

### Correct Flow

```
1. Run Phase 1 for ALL dates (fill market_data_cache table)
2. Load price cache ONCE (now includes all dates including today)
3. Run Phases 2-6 for all dates (use fully populated cache)
```

This matches your stated goal: **daily cron should follow the same process as multi-day backfill**.

---

## Issue 4: PRIVATE-only Portfolios

**Symptom**: `No active positions found for portfolio 2c251ae0-...`

Portfolio `2c251ae0-bdd2-4354-ba29-3e4ce929ad38` is the **Family Office Private** portfolio with only PRIVATE investment class positions. The beta calculation filters to `Position.investment_class == 'PUBLIC'`, returning no positions.

**Fix**: Return graceful skip result instead of raising error.

---

## Related Files Reference

### Backend - Core Changes
- `backend/app/db/seed_factors.py` - Factor definition seeding
- `backend/app/calculations/stress_testing.py` - Stress test factor mapping
- `backend/scripts/automation/railway_daily_batch.py` - Railway cron entry point
- `backend/app/batch/batch_orchestrator.py` - Batch processing orchestration
- `backend/app/calculations/market_beta.py` - Beta calculations
- `backend/app/calculations/market_risk.py` - Market risk scenarios

### Backend - Reference (no changes needed)
- `backend/app/batch/analytics_runner.py` - Already uses "IR Beta"
- `backend/app/cache/price_cache.py` - Price cache implementation
- `backend/scripts/database/clear_calculation_data.py` - Does NOT clear market_data_cache

### Frontend - Reference (no changes needed)
- `frontend/src/components/risk-metrics/FactorExposureCards.tsx` - Already expects "IR Beta"
- `frontend/src/components/risk-metrics/FactorExposureHeroRow.tsx` - Already expects "IR Beta"
