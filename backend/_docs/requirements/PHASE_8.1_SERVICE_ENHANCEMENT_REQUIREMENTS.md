# Phase 8.1 Service Enhancement Requirements (Post-Task 13)

## Status

✅ **Task 13 Schemas Complete**: All 4 response schemas now include optional `data_quality` field
⏳ **Service Implementation**: Future work required to populate `data_quality` from stored data

---

## Current State After Phase 8.1 Task 13

### Completed
1. ✅ **DataQualityInfo Schema** (`app/schemas/analytics.py:12-38`)
   - Fields: flag, message, positions_analyzed, positions_total, positions_skipped, data_days
   - All fields required (per API contract)
   - Example schema provided

2. ✅ **Response Schema Updates** (all with optional data_quality field)
   - `PortfolioFactorExposuresResponse` (line 245)
   - `StressTestResponse` (line 208)
   - `CorrelationMatrixResponse` (line 135)
   - `PositionFactorExposuresResponse` (line 279)

3. ✅ **Backward Compatibility**
   - All data_quality fields are Optional[DataQualityInfo]
   - Default value: None
   - Existing API consumers unaffected

### Current Behavior
- **All endpoints return `data_quality: null`** until services are enhanced
- Endpoints function normally (no breaking changes)
- API contract forward-compatible for future service enhancements

---

## Architecture Context

### How Calculations Work
1. **Batch Process** calls calculation functions (e.g., `calculate_factor_betas_hybrid`)
2. **Calculation Functions** return rich dict including `data_quality` metrics
3. **Storage Functions** write to database tables (FactorExposure, StressTestResult, etc.)
4. **API Services** read from database and return data to endpoints
5. **Problem**: data_quality dict is NOT stored in database (only quality_flag in some cases)

### Data Flow Diagram
```
Batch Process
  ↓
Calculate (returns data_quality dict)
  ↓
Store to DB (quality_flag only, loses data_quality dict)
  ↓
API Service reads from DB (no data_quality available)
  ↓
API Endpoint (returns data_quality: null)
```

---

## Required Service Enhancements

### Option A: Compute On-the-Fly (Recommended for MVP)
**Approach**: Services compute data_quality metrics from database when serving API requests

**Advantages**:
- No database schema changes
- No migration required
- No batch process changes
- Can be implemented incrementally

**Implementation**:

#### 1. Factor Exposures Service Enhancement
**File**: `app/services/factor_exposure_service.py`
**Method**: `get_portfolio_exposures()` (line 31)

```python
async def get_portfolio_exposures(self, portfolio_id: UUID) -> Dict:
    # ... existing code to get factor exposures ...

    # NEW: Compute data_quality when available=False
    if latest_date is None or len(rows) == 0:
        # Count positions in portfolio
        positions_stmt = select(func.count(Position.id)).where(
            Position.portfolio_id == portfolio_id
        )
        positions_total = (await self.db.execute(positions_stmt)).scalar() or 0

        return {
            "available": False,
            "portfolio_id": str(portfolio_id),
            "calculation_date": None,
            "data_quality": {
                "flag": "NO_CALCULATIONS",
                "message": "No factor calculations available for this portfolio",
                "positions_analyzed": 0,
                "positions_total": positions_total,
                "positions_skipped": positions_total,
                "data_days": 0
            },
            "factors": [],
            "metadata": {"reason": "no_calculation_available"},
        }

    # When available=True, data_quality remains None (future enhancement)
    return {
        "available": True,
        "portfolio_id": str(portfolio_id),
        "calculation_date": str(latest_date),
        "data_quality": None,  # Future: compute from position counts
        "factors": [...],
        "metadata": {...}
    }
```

**Estimated Effort**: 2-3 hours per service

#### 2. Stress Test Service Enhancement
**File**: `app/services/stress_test_service.py`
**Method**: `get_portfolio_results()`

Similar pattern: when available=False, compute position counts and populate data_quality.

#### 3. Correlation Service Enhancement
**File**: `app/services/correlation_service.py`
**Method**: `get_correlation_matrix_api()`

Similar pattern: when available=False, compute position counts and populate data_quality.

#### 4. Position Factor Exposures Service Enhancement
**File**: `app/services/factor_exposure_service.py`
**Method**: `list_position_exposures()`

Similar pattern: when available=False, compute position counts and populate data_quality.

---

### Option B: Store in Database (More Robust, Requires Migrations)
**Approach**: Extend database tables to store full data_quality dict

**Required Changes**:

#### 1. Database Schema Changes
Add JSONB columns to result tables:

```sql
-- Factor Exposures (portfolio-level)
ALTER TABLE factor_exposures
ADD COLUMN data_quality JSONB;

-- Stress Test Results
ALTER TABLE stress_test_results
ADD COLUMN data_quality JSONB;

-- Correlation Calculations
ALTER TABLE correlation_calculations
ADD COLUMN data_quality JSONB;

-- Position Factor Exposures (already has quality_flag)
-- Consider adding full data_quality JSONB for consistency
```

#### 2. Batch Process Updates
Update storage functions to persist data_quality:

**File**: `app/calculations/factors.py`
**Method**: `aggregate_portfolio_factor_exposures()` (line 667)

```python
# BEFORE (line ~700)
factor_exposure = FactorExposure(
    portfolio_id=portfolio_id,
    factor_id=factor_id,
    calculation_date=calculation_date,
    exposure_value=beta_value,
    exposure_dollar=dollar_exposure
)

# AFTER
factor_exposure = FactorExposure(
    portfolio_id=portfolio_id,
    factor_id=factor_id,
    calculation_date=calculation_date,
    exposure_value=beta_value,
    exposure_dollar=dollar_exposure,
    data_quality=data_quality_dict  # NEW: store full dict
)
```

Similar changes needed in:
- `app/calculations/stress_testing.py:save_stress_test_results()`
- `app/services/correlation_service.py:calculate_portfolio_correlations()`

#### 3. Service Updates
Update services to retrieve and return data_quality from database:

```python
# BEFORE
result = await self.db.execute(stmt)
exposure = result.scalar_one_or_none()

# AFTER
result = await self.db.execute(stmt)
exposure = result.scalar_one_or_none()
data_quality_dict = exposure.data_quality if exposure else None
```

**Estimated Effort**: 8-12 hours (migrations + batch + services)

---

## Recommendation

**Start with Option A (Compute On-the-Fly)**:
1. Provides immediate value (explains why calculations are missing)
2. No migration risk
3. Can implement one endpoint at a time
4. Later migrate to Option B if performance becomes concern

**When to Use Option B**:
- After Option A is stable
- If on-the-fly computation impacts performance
- When full historical data_quality tracking is needed

---

## Testing Requirements

### Unit Tests
```python
# Test data_quality populated when available=False
async def test_factor_exposures_no_data():
    response = await client.get(f"/api/v1/analytics/{portfolio_id}/factor-exposures")
    assert response.json()["available"] == False
    assert response.json()["data_quality"] is not None
    assert response.json()["data_quality"]["flag"] == "NO_CALCULATIONS"
    assert response.json()["data_quality"]["positions_total"] > 0

# Test data_quality is None when available=True (until enhanced)
async def test_factor_exposures_with_data():
    response = await client.get(f"/api/v1/analytics/{portfolio_id}/factor-exposures")
    assert response.json()["available"] == True
    assert response.json()["data_quality"] is None  # Future enhancement
```

### Integration Tests
- Test all 4 endpoints return valid JSON with data_quality field
- Test backward compatibility (existing consumers don't break)
- Test data_quality values are accurate when populated

---

## Next Steps

### Immediate (No Dependencies)
1. Document this enhancement plan ✅ (this file)
2. Create tracking issue for service enhancements
3. Prioritize endpoints (Factor Exposures first, then others)

### Short-term (Option A Implementation)
1. Enhance Factor Exposures service (highest value)
2. Add unit tests
3. Test with frontend
4. Enhance remaining 3 services incrementally

### Medium-term (Option B Migration)
1. Create Alembic migration for data_quality columns
2. Update batch processes to store data_quality
3. Update services to retrieve data_quality
4. Deploy with backward compatibility

---

## Related Files

**Schemas**:
- `app/schemas/analytics.py` - DataQualityInfo and response schemas

**Services** (need enhancement):
- `app/services/factor_exposure_service.py` - Factor exposures
- `app/services/stress_test_service.py` - Stress tests
- `app/services/correlation_service.py` - Correlations

**Calculations** (already compute data_quality):
- `app/calculations/factors.py` - Returns data_quality dict (line 278-300, 437-451)
- `app/calculations/stress_testing.py` - Returns data_quality info
- `app/services/correlation_service.py` - Returns None when skipped

**Models** (for Option B):
- `app/models/market_data.py` - FactorExposure (line 186), PositionFactorExposure (line 211)

---

## Conclusion

Phase 8.1 Task 13 API schema enhancements are **complete and production-ready**. The optional `data_quality` field is forward-compatible and will remain null until services are enhanced via Option A or Option B above.

Frontend can start consuming these endpoints immediately, with the understanding that `data_quality` will be populated in future releases when calculations are missing or skipped.
