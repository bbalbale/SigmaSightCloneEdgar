# TODO4.md

## Phase 1.0: API Development v1.4.6 Corrections

**Phase**: 1.0 - API Documentation & Implementation Alignment
**Version**: v1.4.6
**Status**: 🟡 **PHASE 1.1 COMPLETE** - Phases 1.2 & 1.3 Pending
**Start Date**: October 4, 2025
**Goal**: Align API documentation with actual implementation, fix critical gaps

---

## Overview

Analysis of API_REFERENCE_V1.4.6.md revealed significant discrepancies between documented and actual API behavior. This phase addresses:
- 2 **CRITICAL** missing implementations ✅ **RESOLVED** (Phase 1.1)
- 5 **MAJOR** implementation gaps requiring feature work ⏳ **PENDING** (Phase 1.2)
- 11 **DOCUMENTATION** mismatches requiring doc updates ⏳ **PENDING** (Phase 1.3)

**Source**: External code review feedback (October 4, 2025)

### Phase Progress
- ✅ **Phase 1.1**: CRITICAL - Missing Implementations (COMPLETED October 4, 2025)
- ⏳ **Phase 1.2**: MAJOR - Implementation Gaps (PENDING - Decision Needed)
- ⏳ **Phase 1.3**: DOCUMENTATION - Update Docs to Match Reality (PENDING)

---

## Phase 1.1: CRITICAL - Missing Implementations ✅ **COMPLETED**

**Completion Date**: October 4, 2025
**Git Commit**: `2087352` - "docs: complete Phase 1.1 API documentation cleanup"

### 1.1.1 ✅ Tag Management: Missing Endpoints - COMPLETED
**Status**: ✅ **COMPLETED**
**Severity**: CRITICAL
**Location**: `_docs/reference/API_REFERENCE_V1.4.6.md`

**Problem**:
Two documented tag management endpoints **do not exist** in codebase:
1. `POST /tags/reorder` - Reorder tags for display
2. `POST /tags/batch-update` - Batch update multiple tags

**Evidence**:
- Not found in `app/api/v1/tags.py:1-489`
- Repository-wide search confirms absence
- Documentation claims "✅ Fully Implemented"

**Action Items**:
- [x] **IMMEDIATE**: Remove documentation for these two endpoints from API_REFERENCE_V1.4.6.md
  - [x] Remove section 40: POST /tags/reorder (lines ~2208-2236)
  - [x] Remove section 42: POST /tags/batch-update (lines ~2249-2283)
  - [x] Update endpoint count from 10 → 8 for Tag Management
  - [x] Update total endpoint count from 53 → 51
  - [x] Add explicit total count header: "**Total: 51 implemented endpoints**"

**Completion Notes**:
- Removed both non-existent endpoint documentation sections
- Updated Tag Management category: 10 → 8 endpoints
- Renumbered Position Tagging sections: 43-47 → 41-45
- Added explicit total count in Complete Endpoint List section
- Documentation now accurately reflects implemented endpoints only

**Decision Needed**: Do we want these features?
- If **YES**: Create implementation tickets for Phase 2.0
- If **NO**: Keep removed from docs permanently (current state)

---

### 1.1.2 ✅ Market Data Endpoints - REMOVED BUT DOCUMENTED - COMPLETED
**Status**: ✅ **COMPLETED**
**Severity**: CRITICAL
**Location**: API router removed these in v1.2

**Problem**:
Market data endpoints documented but **removed from router since v1.2**:
- All `/market-data/*` endpoints
- Not registered in `app/api/v1/router.py:25-44`

**Evidence**:
- Endpoints existed in earlier versions
- Removed in v1.2 cleanup
- Documentation never updated

**Action Items**:
- [x] **IMMEDIATE**: Remove market data endpoints section from API_REFERENCE_V1.4.6.md
  - [x] Verified endpoints not registered in router.py
  - [x] Removed entire market data endpoints section (lines 124-129)
  - [x] Removed documentation for GET /market-data/prices/{symbol}
  - [x] Removed documentation for GET /market-data/current-prices
  - [x] Removed documentation for GET /market-data/sectors
  - [x] Removed documentation for POST /market-data/refresh

**Completion Notes**:
- Verified via `app/api/v1/router.py` that market data router is not included
- Router comments confirm: "Legacy placeholder and market-data routers are intentionally not registered in v1.2"
- Removed entire market data endpoints section from documentation
- Documentation now aligns with v1.2 API structure

**Decision Needed**: Do we need market data endpoints?
- If **YES**: Define requirements and create implementation plan for Phase 2.0
- If **NO**: Permanent removal confirmed (current state)

---

## Phase 1.2: MAJOR - Implementation Gaps

These endpoints exist but are **significantly simplified** compared to documentation. Implementing documented features would require substantial work.

---

### 1.2.1 🔴 GET `/data/portfolio/{id}/complete` - Placeholder Implementation
**Status**: 🔴 **NEEDS WORK**
**Severity**: MAJOR
**File**: `app/api/v1/data.py:83-294`

**Current State**:
- Built entirely in-route with basic aggregation
- No `PortfolioDataService` usage
- Timeseries data is placeholder
- Attribution calculations missing
- Simple position list, no rich analytics

**Documented Promises**:
- Service layer orchestration via `PortfolioDataService`
- Rich cash/margin summary
- Historical timeseries data
- Attribution analysis
- Performance metrics

**What's Needed to Implement Documentation**:

1. **Create/Refactor PortfolioDataService** (~400 lines)
   ```python
   # app/services/portfolio_data_service.py
   class PortfolioDataService:
       async def get_complete_portfolio(portfolio_id, as_of_date):
           # Orchestrate data from multiple sources
           - positions with greeks
           - historical snapshots for timeseries
           - attribution calculations
           - cash/margin tracking
           - performance metrics
   ```

2. **Add Historical Timeseries Support** (~200 lines)
   - Query `portfolio_snapshots` table for date range
   - Calculate returns, volatility, sharpe
   - Format for chart consumption

3. **Add Attribution Calculations** (~300 lines)
   - Factor attribution (existing factor data)
   - Position-level contribution analysis
   - Sector/style attribution
   - Time-period comparisons

4. **Add Cash/Margin Summary** (~150 lines)
   - Track cash positions
   - Calculate margin usage
   - Buying power calculations
   - Separate from equity positions

**Effort Estimate**: 2-3 days for full implementation

**Decision Options**:
- **A**: Implement full features (2-3 days work)
- **B**: Update docs to match current simple implementation
- **C**: Mark as "simplified" in docs, plan Phase 2 enhancement

---

### 1.2.2 🔴 GET `/data/portfolio/{id}/data-quality` - Binary Heuristic
**Status**: 🔴 **NEEDS WORK**
**Severity**: MAJOR
**File**: `app/api/v1/data.py:295-379`

**Current State**:
- Binary check: "150 days or zero days"
- No overall quality score
- No recommendations
- Simple pass/fail per position

**Documented Promises**:
- Detailed metric tables per position
- Overall portfolio quality score (0-100)
- Specific recommendations for improvement
- Completeness, recency, and accuracy metrics
- Data provider coverage analysis

**What's Needed to Implement Documentation**:

1. **Add Quality Scoring System** (~250 lines)
   ```python
   class DataQualityAnalyzer:
       def calculate_quality_score(position):
           completeness_score = check_required_fields()  # 0-40 points
           recency_score = check_data_freshness()        # 0-30 points
           accuracy_score = check_data_validation()      # 0-30 points
           return total_score  # 0-100
   ```

2. **Add Recommendation Engine** (~200 lines)
   - Identify missing data fields
   - Suggest data provider alternatives
   - Flag stale data (>7 days old)
   - Recommend batch refresh

3. **Add Overall Portfolio Score** (~100 lines)
   - Weight positions by market value
   - Aggregate individual scores
   - Identify weakest positions

4. **Add Provider Coverage Analysis** (~150 lines)
   - Check which providers have data
   - Identify gaps by asset type
   - Suggest provider additions

**Effort Estimate**: 1-2 days for full implementation

**Decision Options**:
- **A**: Implement full quality analysis system
- **B**: Update docs to match current binary check
- **C**: Keep current, add to Phase 2 enhancement backlog

---

### 1.2.3 🔴 GET `/data/prices/quotes` - Mock Data Only
**Status**: 🔴 **NEEDS WORK**
**Severity**: MAJOR
**File**: `app/api/v1/data.py:732-807`

**Current State**:
- Simulated bid/ask spreads
- All change fields zeroed out
- No real-time market data
- Placeholder implementation

**Documented Promises**:
- Real-time bid/ask/last prices
- Day change statistics ($ and %)
- 52-week high/low ranges
- Volume data
- Market status indicators

**What's Needed to Implement Documentation**:

1. **Integrate Real-Time Market Data Provider** (~300 lines)
   ```python
   # Use existing Polygon or FMP integration
   class RealtimeQuoteService:
       async def get_quotes(symbols):
           # Call Polygon real-time API
           # Or FMP quotes endpoint
           # Transform to standard format
   ```

2. **Add Change Calculations** (~150 lines)
   - Previous close lookup
   - Calculate $ change and % change
   - Intraday high/low tracking

3. **Add 52-Week Statistics** (~100 lines)
   - Query historical data for 52-week period
   - Calculate high/low ranges
   - Add to response

4. **Add Caching Layer** (~100 lines)
   - Cache quotes for 1-5 seconds
   - Prevent API rate limit issues
   - Balance freshness vs cost

**Effort Estimate**: 1-2 days (depends on API integration complexity)

**Blockers**:
- Requires active Polygon/FMP API subscription
- Rate limits may apply
- Real-time data may have additional costs

**Decision Options**:
- **A**: Implement with real market data (requires API costs)
- **B**: Update docs to clearly state "simulated quotes"
- **C**: Make real-time optional feature flag

---

### 1.2.4 🔴 Position Tag `removed_count` - Inaccurate Reporting
**Status**: 🔴 **NEEDS WORK**
**Severity**: MAJOR
**File**: `app/services/position_tag_service.py:240-267`

**Current State**:
```python
# Always returns count of tags REQUESTED, not actually deleted
removed_count = len(tag_ids)  # Wrong!
return removed_count
```

**Documented Promise**:
- Returns count of tags **actually removed**
- Accurate feedback for frontend

**What's Needed to Implement Documentation**:

1. **Fix `bulk_remove_tags` Method** (~20 lines)
   ```python
   # Before: Returns requested count
   removed_count = len(tag_ids)

   # After: Return actual deletion count
   result = await db.execute(
       delete(PositionTag)
       .where(PositionTag.position_id == position_id)
       .where(PositionTag.tag_id.in_(tag_ids))
   )
   removed_count = result.rowcount  # Actual deletions
   ```

2. **Add Idempotency Handling** (~30 lines)
   - Handle case where tags don't exist
   - Return accurate count
   - Log warnings for non-existent tags

**Effort Estimate**: 1 hour (simple fix)

**Decision Options**:
- **A**: Fix immediately (recommended - simple change)
- **B**: Update docs to match current behavior (not recommended)

---

### 1.2.5 🔴 Tag `usage_count` - Only Counts Strategy Tags
**Status**: 🔴 **NEEDS WORK**
**Severity**: MAJOR
**File**: `app/services/tag_service.py:160-188`

**Current State**:
```python
# Only counts legacy strategy_tags, not position_tags
usage_count = db.query(strategy_tags).filter(tag_id=tag.id).count()
```

**Documented Promise**:
- `usage_count` includes position tags
- Reflects actual tag usage across system

**What's Needed to Implement Documentation**:

1. **Update `get_user_tags` Query** (~40 lines)
   ```python
   # Current: Only strategy_tags
   usage_count = strategy_tags_count

   # Needed: Both sources
   usage_count = (
       strategy_tags_count +  # Legacy
       position_tags_count    # New preferred method
   )
   ```

2. **Add Position Tags Count Subquery** (~30 lines)
   ```python
   position_tags_count = (
       select(func.count(PositionTag.id))
       .where(PositionTag.tag_id == TagV2.id)
       .scalar_subquery()
   )
   ```

3. **Update TagResponse Schema** (~10 lines)
   - Optionally separate counts
   - `position_count` and `strategy_count`
   - Or keep combined `usage_count`

**Effort Estimate**: 2-3 hours

**Decision Options**:
- **A**: Fix to count both sources (recommended)
- **B**: Update docs to note strategy-only counting
- **C**: Add separate count fields for transparency

---

## Phase 1.3: DOCUMENTATION - Update Docs to Match Reality

These are documentation-only fixes. Code works correctly but docs are wrong.

### 1.3.1 📝 POST `/auth/register` - Response Schema Mismatch
**Status**: 🟡 **DOC UPDATE NEEDED**
**File**: `app/schemas/auth.py:33-57`
**Location**: API_REFERENCE_V1.4.6.md

**Issue**:
- **Code**: Returns `UserResponse` with fields: `id`, `email`, `full_name`, `is_active`, `created_at`
- **Docs**: Example includes `portfolio_id` field

**Fix**:
- [ ] Remove `portfolio_id` from example response
- [ ] Update response schema to match `UserResponse`

---

### 1.3.2 📝 GET `/data/portfolios` - Response Structure Mismatch
**Status**: 🟡 **DOC UPDATE NEEDED**
**File**: `app/api/v1/data.py:34-81`

**Issue**:
- **Code**: Returns bare array `[{...}, {...}]` with `equity_balance`, `position_count`
- **Docs**: Shows wrapped `{ "data": [...] }` with different field names

**Fix**:
- [ ] Update docs to show bare array response
- [ ] Update field names to match actual response:
  - Include: `equity_balance`, `position_count`, etc.
  - Remove: wrapper structure

---

### 1.3.3 📝 GET `/data/positions/details` - Missing Day Change
**Status**: 🟡 **DOC UPDATE NEEDED**
**File**: `app/api/v1/data.py:433-626`

**Issue**:
- **Code**: Returns `{"positions": [...], "summary": ...}` without day-change metrics
- **Docs**: Shows `data` array with day change statistics

**Fix**:
- [ ] Remove day-change fields from documented response
- [ ] Update response structure: `positions` not `data`
- [ ] Remove `day_change_percent`, `day_change_value` fields

---

### 1.3.4 📝 GET `/data/prices/historical/{portfolio_id}` - Path Parameter Mismatch
**Status**: 🟡 **DOC UPDATE NEEDED**
**File**: `app/api/v1/data.py:627-722`

**Issue**:
- **Code**: Path parameter is `{portfolio_id}`, aggregates all portfolio symbols
- **Docs**: Shows `{symbol_or_position_id}`, includes statistics block

**Fix**:
- [ ] Update path to `{portfolio_id}` (not `{symbol_or_position_id}`)
- [ ] Remove statistics block from response schema
- [ ] Clarify: returns all symbols in portfolio

---

### 1.3.5 📝 GET `/data/factors/etf-prices` - Historical vs Current
**Status**: 🟡 **DOC UPDATE NEEDED**
**File**: `app/api/v1/data.py:813-875`

**Issue**:
- **Code**: Returns map of current snapshots only
- **Docs**: Shows list of historical prices per ETF

**Fix**:
- [ ] Update response to show current snapshot structure
- [ ] Remove historical price arrays
- [ ] Clarify: single point-in-time data

---

### 1.3.6 📝 GET `/analytics/portfolio/{id}/diversification-score` - Field Names
**Status**: 🟡 **DOC UPDATE NEEDED**
**File**: `app/schemas/analytics.py:73-114`

**Issue**:
- **Code**: Returns `portfolio_correlation`, `duration_days`
- **Docs**: Shows `diversification_score`, `weighted_correlation`

**Fix**:
- [ ] Update response schema field names to match code:
  - `portfolio_correlation` (not `diversification_score`)
  - `duration_days` (not just in metadata)
  - Verify all field names in `DiversificationScoreResponse` schema

---

### 1.3.7 📝 GET `/analytics/portfolio/{id}/factor-exposures` - Overstated Guarantee
**Status**: 🟡 **DOC UPDATE NEEDED**
**File**: `app/services/factor_exposure_service.py:52-143`

**Issue**:
- **Code**: Returns available factors, reports completeness in metadata
- **Docs**: Claims "enforces all active factors"

**Fix**:
- [ ] Remove "enforces all active factors" claim
- [ ] Add: "Returns available factors only"
- [ ] Clarify metadata includes completeness flag

---

### 1.3.8 📝 GET `/analytics/portfolio/{id}/overview` - Missing Cache Claim
**Status**: 🟡 **DOC UPDATE NEEDED**
**File**: `app/api/v1/analytics/portfolio.py:23-78`

**Issue**:
- **Code**: No caching implemented, realized P&L = 0
- **Docs**: Claims 5-minute cache, batch-data reuse

**Fix**:
- [ ] Remove "5-minute cache" claim
- [ ] Remove "batch-data reuse" claim
- [ ] Note: Realized P&L currently returns 0 (placeholder)

---

### 1.3.9 📝 Target Prices Bulk Update - Optimization Layer
**Status**: 🟡 **DOC UPDATE NEEDED**
**File**: `app/api/v1/target_prices.py:278-319`

**Issue**:
- **Code**: O(1) lookup via in-route index
- **Docs**: Claims "service-level optimization"

**Fix**:
- [ ] Update to say "route-level optimization" or "in-route indexing"
- [ ] Remove "service-level" claim

---

### 1.3.10 📝 Default Tags Count - 10 vs 7
**Status**: 🟡 **DOC UPDATE NEEDED**
**File**: `app/models/tags_v2.py:135-149`

**Issue**:
- **Code**: Creates 10 default tags
- **Docs**: Lists 7 tags (Growth, Value, Dividend, Speculative, Core, Satellite, Defensive)

**Fix**:
- [ ] Verify actual default tags from code
- [ ] Update doc to list all 10 tags
- [ ] Match exact naming from `TagV2.default_tags()`

---

### 1.3.11 📝 Market Data Endpoints - Removed but Documented
**Status**: 🟡 **DOC UPDATE NEEDED** (covered in 1.1.2)

**Fix**:
- [ ] Create "Removed Endpoints" section
- [ ] Mark all `/market-data/*` as removed in v1.2
- [ ] Add decision needed note

---

## Progress Tracking

### Phase 1.1: Critical Issues
- [ ] 1.1.1: Remove missing tag endpoint docs (reorder, batch-update)
- [ ] 1.1.2: Add warning about removed market data endpoints

### Phase 1.2: Implementation Gaps (Decision Needed)
- [ ] 1.2.1: `/data/portfolio/{id}/complete` - Decide: Implement vs Update Docs
- [ ] 1.2.2: `/data/portfolio/{id}/data-quality` - Decide: Implement vs Update Docs
- [ ] 1.2.3: `/data/prices/quotes` - Decide: Implement vs Update Docs
- [ ] 1.2.4: Position tag `removed_count` - Fix (simple, 1 hour)
- [ ] 1.2.5: Tag `usage_count` - Fix to count both sources

### Phase 1.3: Documentation Updates (11 items)
- [ ] 1.3.1: `/auth/register` response schema
- [ ] 1.3.2: `/data/portfolios` structure
- [ ] 1.3.3: `/data/positions/details` day change
- [ ] 1.3.4: `/data/prices/historical` path parameter
- [ ] 1.3.5: `/data/factors/etf-prices` historical vs current
- [ ] 1.3.6: Diversification score field names
- [ ] 1.3.7: Factor exposures guarantee
- [ ] 1.3.8: Overview cache claim
- [ ] 1.3.9: Bulk update optimization layer
- [ ] 1.3.10: Default tags count
- [ ] 1.3.11: Market data removed (duplicate of 1.1.2)

---

## Decisions Needed

### Priority 1: Critical Removals (Do First)
1. **Remove missing tag endpoints** (reorder, batch-update) - NO CODE EXISTS
2. **Mark market data endpoints** as removed - NEED DECISION ON REIMPLEMENTATION

### Priority 2: Implementation vs Documentation (Choose Path)
For each of these, decide: **Fix Code** or **Fix Docs**?

| Endpoint | Implement (Effort) | Update Docs (Effort) | Recommendation |
|----------|-------------------|----------------------|----------------|
| Portfolio Complete | 2-3 days | 30 min | **Update Docs** (too much work) |
| Data Quality | 1-2 days | 15 min | **Update Docs** (too much work) |
| Real-time Quotes | 1-2 days + API costs | 15 min | **Update Docs** (cost concern) |
| Tag removed_count | 1 hour | 5 min | **Fix Code** (simple fix) |
| Tag usage_count | 2-3 hours | 10 min | **Fix Code** (important fix) |

### Priority 3: Documentation Batch Updates
- All 11 doc mismatches can be fixed in single doc update pass (~2 hours total)

---

## Next Steps

1. **Get Approval**: Review this TODO with stakeholders
2. **Phase 1.1**: Remove critical missing endpoint docs (30 min)
3. **Decisions**: Choose fix-code vs fix-docs for each major gap
4. **Phase 1.2**: Implement chosen code fixes
5. **Phase 1.3**: Batch update all documentation mismatches
6. **Final Review**: Code review + QA on updated API_REFERENCE_V1.4.6.md

---

## Success Criteria

✅ API_REFERENCE_V1.4.6.md accurately reflects all implemented endpoints
✅ No documented endpoints that don't exist in code
✅ All response schemas match actual code behavior
✅ Clear warnings on removed/deprecated endpoints
✅ Decision logged on reimplementation of market data endpoints

**Target Completion**: TBD based on decisions made
