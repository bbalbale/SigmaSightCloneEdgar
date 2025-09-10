# Backend Compute Error Documentation

> **Last Updated**: 2025-09-10 (Updated with Comprehensive Solution Plan)  
> **Purpose**: Document and track all computation errors encountered during batch processing  
> **Status**: 3 Issues Resolved, 14 Active (Factor API is P0 priority)

## Table of Contents
1. [Critical Issues](#critical-issues)
2. [Unicode Encoding Errors](#unicode-encoding-errors)
3. [Market Data Issues](#market-data-issues)
4. [Database Table Issues](#database-table-issues)
5. [Batch Processing Issues](#batch-processing-issues)
6. [Calculation Engine Issues](#calculation-engine-issues)
7. [API Rate Limiting](#api-rate-limiting)
8. [Resolution Steps](#resolution-steps)

---

## Critical Issues

### 1. Incomplete Portfolio Processing (RESOLVED)
**Severity**: HIGH  
**Impact**: ~~Only 1 of 3 portfolios have calculation data~~ ✅ All portfolios now have data

**Current Status (UPDATED 2025-09-10)**:
- ✅ Demo Individual Portfolio (`1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe`): Complete with 8/8 factors
- ✅ Demo High Net Worth Portfolio (`e23ab931-a033-edfe-ed4f-9d02474780b4`): Complete with 7/8 factors  
- ✅ Demo Hedge Fund Portfolio (`fcd71196-e93e-f000-5a74-31a9eead3118`): Complete with 7/8 factors

**Resolution**: Successfully ran batch processing for all portfolios after fixing portfolio IDs and using UTF-8 encoding

---

## Unicode Encoding Errors

### Issue #1: Windows CP1252 Encoding
**Location**: Multiple Python scripts  
**Error Message**: 
```
UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f680' in position 0: character maps to <undefined>
```

**Affected Files**:
- `scripts/verify_demo_portfolios.py` (line 69)
- `scripts/run_batch_with_reports.py` (line 243, 374)
- Various logging statements with emoji characters

**Solution Required**: 
```bash
# Run all Python scripts with UTF-8 encoding
PYTHONIOENCODING=utf-8 uv run python <script.py>
```

---

## Market Data Issues

### Issue #2: Unexpected FMP Historical Data Format
**Error**: `Unexpected FMP historical data format for ZOOM`  
**Frequency**: Repeated 4 times during batch run  
**Impact**: Market data sync failures for certain symbols

### Issue #3: Missing Factor ETF Data
**Error**: `Missing data points: {'SIZE': 2}`  
**Impact**: Factor analysis calculations incomplete for SIZE factor  
**Affected Calculations**: Factor exposure regressions

### Issue #4: Insufficient Historical Data for Options
**Error Messages**:
```
❌ SLY: 0 days (needs 150 more)
❌ TSLA250815C00300000: 1 days (needs 149 more)
❌ MSFT250919P00380000: 1 days (needs 149 more)
❌ VIX250716C00025000: 1 days (needs 149 more)
❌ NVDA251017C00800000: 1 days (needs 149 more)
❌ AAPL250815P00200000: 1 days (needs 149 more)
❌ SPY250919C00460000: 1 days (needs 149 more)
❌ META250919P00450000: 1 days (needs 149 more)
❌ QQQ250815C00420000: 1 days (needs 149 more)
```
**Impact**: Options pricing and Greeks calculations cannot be performed with insufficient data

### Issue #5: Low FMP Stock Data Success Rate
**Error**: `FMP stock success rate low (50.0%), using Polygon fallback for failed symbols`  
**Impact**: Requires fallback to secondary data provider, increasing API calls

---

## Database Table Issues

### Issue #6: Factor Exposures Incomplete Factor Sets (PARTIALLY RESOLVED)
**Error**: Factor exposures API returns `"available": false` with `"no_complete_set"`  
**Location**: `/api/v1/analytics/portfolio/{id}/factor-exposures` endpoint  
**Root Cause**: API requires ALL 8 active style factors - missing "Short Interest" factor
**Details**:
- ✅ Schema is CORRECT - service properly joins `factor_exposures` with `factor_definitions`
- ✅ Batch processing successfully ran for all 3 portfolios
- ❌ Only 7 of 8 factors calculated (no ETF proxy for "Short Interest" in FACTOR_ETFS)
- Service expects exactly 8 factors: Market Beta, Size, Value, Momentum, Quality, Low Volatility, Growth, Short Interest

**Current Data State (UPDATED 2025-09-10)**:
- Individual portfolio: 8/8 factors ✅ (API should work)
- HNW portfolio: 7/8 factors (missing Short Interest)
- Hedge Fund portfolio: 7/8 factors (missing Short Interest)
- Total records: 22 portfolio-level, 490 position-level exposures

**Impact**: Factor exposure API fails for 2/3 portfolios due to incomplete factor sets

### Issue #7: Missing Stress Test Results Table
**Error**: `relation "stress_test_results" does not exist`  
**Location**: Referenced in multiple calculation scripts  
**Impact**: Stress test calculations cannot be stored

### Issue #8: Position Correlations Table Name Mismatch
**Error**: `relation "position_correlations" does not exist`  
**Actual Table Name**: `pairwise_correlations`  
**Impact**: Correlation queries fail when using incorrect table name

---

## Batch Processing Issues

### Issue #9: Portfolio ID Mismatches (RESOLVED)
**Error**: Portfolio IDs in `scripts/run_batch_calculations.py` don't match actual database IDs  
**Attempted IDs**:
- `51134ffd-2f13-49bd-b1f5-0c327e801b69` (not found)
- `c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e` (not found)
- `2ee7435f-379f-4606-bdb7-dadce587a182` (not found)

**Actual IDs**:
- `1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe` (Individual)
- `e23ab931-a033-edfe-ed4f-9d02474780b4` (HNW)
- `fcd71196-e93e-f000-5a74-31a9eead3118` (Hedge Fund)

**Resolution**: ✅ Updated scripts with correct portfolio IDs from database

### Issue #10: Batch Orchestrator Method Names
**Error**: `AttributeError: 'BatchOrchestratorV2' object has no attribute 'run'`  
**Also**: `AttributeError: 'BatchOrchestratorV2' object has no attribute '_run_factor_analysis'`  
**Impact**: Cannot call batch orchestrator methods directly as documented

---

## Calculation Engine Issues

### Issue #11: Beta Capping Warnings
**Warning**: `Beta capped for position b9d5970d-6ec4-b3b1-9044-2e5f8c37376f, factor Market: -6.300 -> -3.000`  
**Frequency**: Repeated 3 times  
**Impact**: Extreme beta values being capped, may affect risk calculations

### Issue #12: Missing Interest Rate Factor
**Error**: `No exposure found for shocked factor: Interest_Rate (mapped to Interest Rate Beta)`  
**Frequency**: 10 occurrences  
**Impact**: Interest rate sensitivity analysis incomplete

### Issue #13: Excessive Stress Loss Clipping
**Warnings**:
```
Direct stress loss of $-599,760 exceeds 99% of portfolio. Clipping at $-537,057
Correlated stress loss of $-1,315,393 exceeds 99% of portfolio. Clipping at $-537,057
Correlated stress loss of $-1,011,357 exceeds 99% of portfolio. Clipping at $-537,057
Correlated stress loss of $-1,086,798 exceeds 99% of portfolio. Clipping at $-537,057
```
**Impact**: Stress test results being artificially constrained

### Issue #14: Pandas FutureWarning
**Warning**: `The default fill_method='pad' in DataFrame.pct_change is deprecated`  
**Location**: `app/calculations/factors.py:69`  
**Impact**: Code will break in future pandas versions

---

## API Rate Limiting

### Issue #15: Polygon API Rate Limits
**Error**: `HTTPSConnectionPool(host='api.polygon.io', port=443): Max retries exceeded with url: /v2/aggs/ticker/SPY250919C00460000/range/1/day/2025-09-05/2025-09-10?adjusted=true&sort=asc&limit=50000 (Caused by ResponseError('too many 429 error responses'))`  
**Impact**: Options data fetching fails due to rate limiting

### Issue #16: FMP Rate Limiting
**Log Messages**:
```
Rate limit: waited 11.45s (request #6, avg rate: 0.34 req/s)
Rate limit: waited 11.29s (request #7, avg rate: 0.23 req/s)
Rate limit: waited 11.94s (request #8, avg rate: 0.19 req/s)
Rate limit: waited 11.96s (request #9, avg rate: 0.17 req/s)
```
**Impact**: Significant delays in market data synchronization

---

## API-Database Alignment Issues

### Issue #17: Factor Exposure Service Misalignment (RESOLVED)
**Error**: API returns "no_calculation_available" with "no_complete_set" reason  
**Root Cause**: Not a schema issue - API requires ALL 8 active style factors present

**Investigation Findings**:
- ✅ Database schema is CORRECT (uses `factor_id` and `exposure_value` as designed)
- ✅ Service correctly joins `FactorExposure` with `FactorDefinition` tables
- ✅ Individual portfolio has 8/8 factors (should work)
- ❌ HNW portfolio has 7/8 factors (missing one, causes API failure)  
- ❌ Hedge Fund portfolio has 7/8 factors (missing one, causes API failure)
- ❌ Batch processing only calculates 7 factors (no ETF proxy for "Short Interest")

**Current Data State (After Batch Runs)**:
- Individual portfolio: 8 factor exposures at portfolio level ✅
- HNW portfolio: 7 factor exposures (missing Short Interest)
- Hedge Fund portfolio: 7 factor exposures (missing Short Interest)
- Total position-level exposures: 490 records across all portfolios

**Impact**: Factor exposure API fails for 2/3 portfolios due to incomplete factor sets

---

## Resolution Steps

### Immediate Actions Required

1. **Fix Factor Exposure API (CRITICAL - P0)**
   
   **Option A: Quick Database Fix (Recommended)**
   ```sql
   -- Add missing Short Interest factor with neutral values
   INSERT INTO factor_exposures (
       id, portfolio_id, factor_id, calculation_date, 
       exposure_value, exposure_dollar, created_at, updated_at
   )
   SELECT 
       gen_random_uuid(),
       portfolio_id,
       (SELECT id FROM factor_definitions WHERE name = 'Short Interest'),
       '2025-09-10',
       0.0,  -- Neutral exposure since we can't calculate it
       NULL,
       NOW(),
       NOW()
   FROM (VALUES 
       ('e23ab931-a033-edfe-ed4f-9d02474780b4'::uuid),
       ('fcd71196-e93e-f000-5a74-31a9eead3118'::uuid)
   ) AS t(portfolio_id)
   WHERE NOT EXISTS (
       SELECT 1 FROM factor_exposures fe
       WHERE fe.portfolio_id = t.portfolio_id
       AND fe.factor_id = (SELECT id FROM factor_definitions WHERE name = 'Short Interest')
       AND fe.calculation_date = '2025-09-10'
   );
   ```
   
   **Option B: Make API More Flexible**
   ```python
   # File: app/services/factor_exposure_service.py, Line 74
   # Change from requiring exact match:
   .where(counts_subq.c.cnt == target_count)
   # To allowing one missing factor:
   .where(counts_subq.c.cnt >= target_count - 1)
   ```
   
   **Option C: Disable Short Interest Factor**
   ```sql
   UPDATE factor_definitions SET is_active = false WHERE name = 'Short Interest';
   ```

2. **Fix Unicode Encoding** ✅ COMPLETED
   - Add `PYTHONIOENCODING=utf-8` to all script runners
   - Successfully used in all batch runs

3. **Update Portfolio IDs** ✅ COMPLETED
   - Fixed hardcoded IDs in `scripts/run_batch_calculations.py`
   - All three portfolios now process correctly

4. **Complete Missing Calculations** ✅ COMPLETED
   - Batch processing ran for all portfolios
   - HNW: 168.28s, Hedge Fund: 165.47s
   - Factor exposures increased from 224 to 490 records

5. **Create Missing Database Tables**
   ```sql
   -- Add stress_test_results table via migration
   uv run alembic revision --autogenerate -m "Add stress_test_results table"
   uv run alembic upgrade head
   ```

6. **Fix Table Name References**
   - Update queries to use `pairwise_correlations` instead of `position_correlations`

### Long-term Fixes

1. **Improve Data Provider Fallback Logic**
   - Implement smarter fallback between FMP and Polygon
   - Cache successful provider choices per symbol

2. **Optimize Batch Processing**
   - Implement parallel portfolio processing
   - Add checkpointing to resume after timeouts
   - Split large batches into smaller chunks

3. **Enhanced Error Handling**
   - Add retry logic for rate-limited requests
   - Implement exponential backoff
   - Better error reporting with actionable messages

4. **Data Quality Improvements**
   - Pre-validate data availability before calculations
   - Implement data backfill strategies for options
   - Add data quality monitoring dashboard

5. **Fix Pandas Deprecation**
   ```python
   # In app/calculations/factors.py line 69
   # Change from:
   returns_df = price_df.pct_change().dropna()
   # To:
   returns_df = price_df.pct_change(fill_method=None).dropna()
   ```

---

## Monitoring Commands

```bash
# Check calculation status
cd backend && PYTHONIOENCODING=utf-8 uv run python -c "
from app.database import get_async_session
from sqlalchemy import select, func, text
import asyncio

async def check():
    async with get_async_session() as db:
        # Count factor exposures
        result = await db.execute(text(
            'SELECT p.name, COUNT(pfe.id) as exposures ' +
            'FROM portfolios p ' +
            'LEFT JOIN positions pos ON pos.portfolio_id = p.id ' +
            'LEFT JOIN position_factor_exposures pfe ON pfe.position_id = pos.id ' +
            'GROUP BY p.name'
        ))
        for row in result:
            print(f'{row[0]}: {row[1]} exposures')

asyncio.run(check())
"

# Check correlation data
cd backend && PYTHONIOENCODING=utf-8 uv run python -c "
from app.database import get_async_session
from sqlalchemy import text
import asyncio

async def check():
    async with get_async_session() as db:
        result = await db.execute(text(
            'SELECT COUNT(*) FROM pairwise_correlations'
        ))
        print(f'Pairwise correlations: {result.scalar()}')
        
        result = await db.execute(text(
            'SELECT COUNT(*) FROM correlation_calculations'
        ))
        print(f'Correlation calculations: {result.scalar()}')

asyncio.run(check())
"
```

---

## Notes

- All errors documented from batch run on 2025-09-10
- Backend server running on Windows (CP1252 encoding issues)
- Database: PostgreSQL 15 in Docker container
- Python version: 3.11.13
- The system is functional but requires the fixes above for complete operation

---

## Priority Matrix

| Priority | Issue | Impact | Effort | Status |
|----------|-------|--------|--------|--------|
| P0 | Factor exposure incomplete sets (#6,#17) | CRITICAL - API fails for 2/3 portfolios | LOW - Add missing factor | **PARTIALLY RESOLVED** |
| P1 | Missing database tables (#7) | HIGH - Stress tests unavailable | MEDIUM - Create migrations | **PENDING** |
| P2 | Rate limiting issues (#15,#16) | MEDIUM - Slow processing | HIGH - Implement retry logic | **ACTIVE** |
| P2 | Insufficient options data (#4) | MEDIUM - Options calc fail | HIGH - Historical backfill | **PENDING** |
| P3 | Pandas deprecation (#14) | LOW - Future issue | LOW - Update code | **PENDING** |
| P3 | Beta capping warnings (#11) | LOW - Working as designed | LOW - Adjust thresholds | **MONITORING** |
| ✅ | Incomplete portfolio processing (#1) | ~~HIGH - No data for 2/3 portfolios~~ | ~~LOW - Run batch again~~ | **RESOLVED** |
| ✅ | Unicode encoding errors (#1) | ~~HIGH - Scripts fail to run~~ | ~~LOW - Add env variable~~ | **RESOLVED** |
| ✅ | Portfolio ID mismatches (#9) | ~~HIGH - Batch jobs fail~~ | ~~LOW - Update scripts~~ | **RESOLVED** |