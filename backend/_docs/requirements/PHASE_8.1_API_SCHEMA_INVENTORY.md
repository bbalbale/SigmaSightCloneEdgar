# Phase 8.1 API Schema Inventory (Tasks 12a-12b)

**Date**: 2025-10-07
**Purpose**: Document current API endpoints and response schemas BEFORE adding data quality fields
**Related**: Phase 8.1 Tasks 12-13 (Data Quality Schema Enhancement)

---

## Executive Summary

**Endpoints Returning Calculation Results**: 4 endpoints identified
**Current Schema Status**: **NONE have data_quality fields**
**Impact**: All 4 endpoints need schema updates to expose skip/quality information

---

## 1. Correlation Matrix Endpoint

### Endpoint Details
- **Path**: `GET /api/v1/analytics/{portfolio_id}/correlation-matrix`
- **File**: `app/api/v1/analytics/portfolio.py:96`
- **Response Model**: `CorrelationMatrixResponse`
- **Schema File**: `app/schemas/analytics.py:97`

### Current Response Schema

```python
class CorrelationMatrixResponse(BaseModel):
    """
    Correlation matrix response for portfolio positions

    Returns pre-calculated pairwise correlations between portfolio positions
    ordered by position weight (gross market value).
    """
    data: Optional[CorrelationMatrixData] = Field(None, description="Correlation data when available")
    available: Optional[bool] = Field(None, description="Whether correlation data is available")
    metadata: Optional[Dict[str, Union[str, int]]] = Field(None, description="Error or status metadata")
```

### Current Response Example

```json
{
  "available": true,
  "data": {
    "matrix": {
      "AAPL": {"AAPL": 1.0, "MSFT": 0.82, "NVDA": 0.75},
      "MSFT": {"AAPL": 0.82, "MSFT": 1.0, "NVDA": 0.68},
      "NVDA": {"AAPL": 0.75, "MSFT": 0.68, "NVDA": 1.0}
    },
    "average_correlation": 0.75
  },
  "metadata": {
    "calculation_date": "2025-09-05",
    "duration_days": 90,
    "symbols_included": 3,
    "lookback_days": 90,
    "min_overlap": 30,
    "max_symbols": 25,
    "selection_method": "weight"
  }
}
```

### Service Layer Return (Internal)

```python
# From correlation_service.py:get_matrix()
# Currently returns dict, can return None when skipped (Phase 8.1 Task 7)
{
    "available": False,
    "metadata": {
        "reason": "no_calculation_available" | "insufficient_data" | "insufficient_symbols"
    }
}
```

### Data Quality Gap

**Missing Information**:
- Why was correlation not calculated? (PRIVATE positions filtered out)
- How many positions were skipped?
- Was calculation skipped due to investment_class filtering or insufficient data?

**Status**: ❌ NO data_quality field

---

## 2. Portfolio Factor Exposures Endpoint

### Endpoint Details
- **Path**: `GET /api/v1/analytics/{portfolio_id}/factor-exposures`
- **File**: `app/api/v1/analytics/portfolio.py:206`
- **Response Model**: `PortfolioFactorExposuresResponse`
- **Schema File**: `app/schemas/analytics.py:212`

### Current Response Schema

```python
class PortfolioFactorExposuresResponse(BaseModel):
    available: bool = Field(..., description="Whether factor exposures are available")
    portfolio_id: str = Field(..., description="Portfolio UUID")
    calculation_date: Optional[str] = Field(None, description="ISO date of the factor exposure calculation")
    factors: Optional[List[PortfolioFactorItem]] = Field(None, description="List of factor exposures")
    metadata: Optional[Dict[str, Union[str, int]]] = Field(None, description="Additional metadata such as factor model details")

class PortfolioFactorItem(BaseModel):
    name: str = Field(..., description="Factor name")
    beta: float = Field(..., description="Portfolio beta to the factor")
    exposure_dollar: Optional[float] = Field(None, description="Dollar exposure to the factor, if available")
```

### Current Response Example

```json
{
  "available": true,
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "calculation_date": "2025-09-05",
  "factors": [
    {"name": "Growth", "beta": 0.67, "exposure_dollar": 837500.0},
    {"name": "Value", "beta": -0.15, "exposure_dollar": -187500.0}
  ],
  "metadata": {
    "factor_model": "7-factor",
    "calculation_method": "ETF-proxy regression"
  }
}
```

### Service Layer Return (Internal)

```python
# From calculate_factor_betas_hybrid() in app/calculations/factors.py
# Phase 8.1 Task 5 added skip payload:
{
    'factor_betas': {},  # Empty when skipped
    'position_betas': {},
    'data_quality': {  # INTERNAL - Not exposed to API yet!
        'flag': 'no_public_positions',
        'quality_flag': 'no_public_positions',
        'message': 'Portfolio contains no public positions with sufficient price history',
        'positions_analyzed': 0,
        'positions_total': 8,
        'data_days': 0
    },
    'metadata': {
        'calculation_date': '2025-09-05',
        'regression_window_days': 0,
        'status': 'SKIPPED_NO_PUBLIC_POSITIONS',
        'portfolio_id': 'uuid'
    },
    'regression_stats': {},
    'storage_results': {...}
}
```

### Data Quality Gap

**Missing Information**:
- Internal `data_quality` dict exists but NOT exposed to API
- Frontend has no way to know why factor_betas is empty
- Cannot distinguish between "no data yet" vs "all PRIVATE positions"

**Status**: ❌ NO data_quality field (but internal data exists!)

---

## 3. Position Factor Exposures Endpoint (Position-Level)

### Endpoint Details
- **Path**: `GET /api/v1/analytics/{portfolio_id}/positions/factor-exposures`
- **File**: `app/api/v1/analytics/portfolio.py:238`
- **Response Model**: `PositionFactorExposuresResponse`
- **Schema File**: `app/schemas/analytics.py:243`

### Current Response Schema

```python
class PositionFactorExposuresResponse(BaseModel):
    available: bool = Field(..., description="Whether position factor exposures are available")
    portfolio_id: str = Field(..., description="Portfolio UUID")
    calculation_date: Optional[str] = Field(None, description="ISO date used for exposures")
    total: Optional[int] = Field(None, description="Total positions matched")
    limit: Optional[int] = Field(None, description="Page size")
    offset: Optional[int] = Field(None, description="Pagination offset")
    positions: Optional[List[PositionFactorItem]] = Field(None, description="List of positions with factor exposures")

class PositionFactorItem(BaseModel):
    position_id: str = Field(..., description="Position UUID")
    symbol: str = Field(..., description="Position symbol")
    exposures: Dict[str, float] = Field(..., description="Map of factor name to beta")
```

### Current Response Example

```json
{
  "available": true,
  "portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e",
  "calculation_date": "2025-09-05",
  "total": 120,
  "limit": 50,
  "offset": 0,
  "positions": [
    {
      "position_id": "e5e29f33-ac9f-411b-9494-bff119f435b2",
      "symbol": "AAPL",
      "exposures": {
        "Market Beta": 0.95,
        "Value": -0.12,
        "Momentum": 0.18
      }
    }
  ]
}
```

### Data Quality Gap

**Missing Information**:
- How many positions were skipped due to PRIVATE investment_class?
- Per-position data quality (e.g., "insufficient history" vs "PRIVATE asset")
- Total positions vs positions with exposures

**Status**: ❌ NO data_quality field

**Note**: This endpoint shows position-level data, so data quality might be per-position rather than portfolio-level.

---

## 4. Stress Test Results Endpoint

### Endpoint Details
- **Path**: `GET /api/v1/analytics/{portfolio_id}/stress-test`
- **File**: `app/api/v1/analytics/portfolio.py:277`
- **Response Model**: `StressTestResponse`
- **Schema File**: `app/schemas/analytics.py:176`

### Current Response Schema

```python
class StressTestResponse(BaseModel):
    available: bool = Field(..., description="Whether stress test results are available")
    data: Optional[StressTestPayload] = Field(None, description="Stress test payload when available")
    metadata: Optional[Dict[str, Union[str, List[str]]]] = Field(None, description="Additional metadata, including scenarios_requested if provided")

class StressTestPayload(BaseModel):
    scenarios: List[StressScenarioItem]
    portfolio_value: float
    calculation_date: str

class StressScenarioItem(BaseModel):
    id: str = Field(..., description="Scenario identifier string")
    name: str = Field(..., description="Scenario display name")
    description: Optional[str] = Field(None, description="Scenario description")
    category: Optional[str] = Field(None, description="Scenario category")
    impact_type: str = Field("correlated", description="Impact type used (correlated)")
    impact: StressImpact
    severity: Optional[str] = Field(None, description="Scenario severity")

class StressImpact(BaseModel):
    dollar_impact: float = Field(..., description="Dollar P&L impact from scenario (correlated)")
    percentage_impact: float = Field(..., description="Impact as percentage points of portfolio value")
    new_portfolio_value: float = Field(..., description="Baseline portfolio value plus dollar_impact")
```

### Current Response Example

```json
{
  "available": true,
  "data": {
    "scenarios": [
      {
        "id": "market_crash_35",
        "name": "Market Crash 35%",
        "category": "market_risk",
        "impact_type": "correlated",
        "impact": {
          "dollar_impact": -372010.85,
          "percentage_impact": -35.0,
          "new_portfolio_value": 691049.15
        }
      }
    ],
    "portfolio_value": 1063060.0,
    "calculation_date": "2025-09-05"
  }
}
```

### Service Layer Return (Internal)

```python
# From run_comprehensive_stress_test() in app/calculations/stress_testing.py
# Phase 8.1 Task 8 added skip payload:
{
    'portfolio_id': 'uuid',
    'calculation_date': '2025-09-05',
    'stress_test_results': {
        'skipped': True,  # INTERNAL - Not exposed to API yet!
        'reason': 'no_factor_exposures',
        'message': 'Portfolio has no factor exposures (likely all PRIVATE positions)',
        'direct_impacts': {},
        'correlated_impacts': {},
        'summary_stats': {},
        'scenarios_tested': 0,
        'scenarios_skipped': 0
    },
    'config_metadata': {...}
}
```

### Data Quality Gap

**Missing Information**:
- Internal `skipped` flag and `reason` not exposed to API
- Frontend cannot distinguish "no results yet" from "skipped due to PRIVATE positions"
- Cannot show helpful message to user explaining why stress tests unavailable

**Status**: ❌ NO data_quality field (but internal skip info exists!)

---

## Summary Table

| Endpoint | Path | Response Model | Has data_quality? | Internal Data Exists? |
|----------|------|----------------|-------------------|----------------------|
| Correlation Matrix | `/analytics/{id}/correlation-matrix` | `CorrelationMatrixResponse` | ❌ No | Partial (reason in metadata) |
| Portfolio Factor Exposures | `/analytics/{id}/factor-exposures` | `PortfolioFactorExposuresResponse` | ❌ No | ✅ Yes (Phase 8.1 Task 5) |
| Position Factor Exposures | `/analytics/{id}/positions/factor-exposures` | `PositionFactorExposuresResponse` | ❌ No | Unknown |
| Stress Test Results | `/analytics/{id}/stress-test` | `StressTestResponse` | ❌ No | ✅ Yes (Phase 8.1 Task 8) |

---

## Key Findings

### 1. Schema Pattern Already Established

All 4 endpoints follow the same pattern:
```python
class XxxResponse(BaseModel):
    available: bool  # Whether data is available
    data: Optional[XxxPayload]  # The actual data (None when unavailable)
    metadata: Optional[Dict[str, Any]]  # Additional context
```

**Recommendation**: Add `data_quality` field as optional 4th field to maintain consistency.

### 2. Internal Data Quality Already Exists

- **Factor Analysis** (Task 5): Full `data_quality` dict in calculation results
- **Stress Tests** (Task 8): Skip flag with reason in calculation results
- **Correlations** (Task 7): Partial reason in metadata

**Gap**: This rich internal information is **NOT exposed** to API consumers!

### 3. Backward Compatibility Critical

All schemas are currently deployed. Adding fields must be:
- **Optional** (not required)
- **Additive only** (no field removals/renames)
- **Default to None** (old cached data won't have these fields)

---

## Proposed Schema Enhancement (Task 12c Design)

### Shared Data Quality Schema

```python
# app/schemas/common.py (or app/schemas/analytics.py)
class DataQualityInfo(BaseModel):
    """
    Data quality metadata for calculation results (Phase 8.1)

    Provides transparency about data availability, filtering, and calculation status.
    """
    flag: str = Field(
        ...,
        description="Quality flag: 'full_history', 'limited_history', 'no_public_positions', 'insufficient_data'"
    )
    message: Optional[str] = Field(
        None,
        description="Human-readable explanation of data quality status"
    )
    positions_analyzed: Optional[int] = Field(
        None,
        description="Number of positions included in calculation"
    )
    positions_total: Optional[int] = Field(
        None,
        description="Total positions in portfolio"
    )
    positions_skipped: Optional[int] = Field(
        None,
        description="Number of positions excluded (PRIVATE or insufficient data)"
    )
    data_days: Optional[int] = Field(
        None,
        description="Days of historical data used"
    )

    class Config:
        schema_extra = {
            "example": {
                "flag": "limited_history",
                "message": "8 PRIVATE positions excluded from analysis",
                "positions_analyzed": 8,
                "positions_total": 16,
                "positions_skipped": 8,
                "data_days": 45
            }
        }
```

### Updated Response Schemas (Additive Only)

```python
class CorrelationMatrixResponse(BaseModel):
    available: Optional[bool] = None
    data: Optional[CorrelationMatrixData] = None
    metadata: Optional[Dict[str, Union[str, int]]] = None
    data_quality: Optional[DataQualityInfo] = None  # NEW - Phase 8.1

class PortfolioFactorExposuresResponse(BaseModel):
    available: bool
    portfolio_id: str
    calculation_date: Optional[str] = None
    factors: Optional[List[PortfolioFactorItem]] = None
    metadata: Optional[Dict[str, Union[str, int]]] = None
    data_quality: Optional[DataQualityInfo] = None  # NEW - Phase 8.1

class PositionFactorExposuresResponse(BaseModel):
    available: bool
    portfolio_id: str
    calculation_date: Optional[str] = None
    total: Optional[int] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    positions: Optional[List[PositionFactorItem]] = None
    data_quality: Optional[DataQualityInfo] = None  # NEW - Phase 8.1

class StressTestResponse(BaseModel):
    available: bool
    data: Optional[StressTestPayload] = None
    metadata: Optional[Dict[str, Union[str, List[str]]]] = None
    data_quality: Optional[DataQualityInfo] = None  # NEW - Phase 8.1
```

---

## Backward Compatibility Strategy

### 1. Make Field Optional
```python
data_quality: Optional[DataQualityInfo] = None
```

**Why**: Old clients won't break if field is missing. Old cached data won't have this field.

### 2. Pydantic Config
```python
class Config:
    # Allow extra fields (forward compatibility)
    extra = "allow"
```

### 3. Frontend Handling
```typescript
// Frontend should check if field exists
if (response.data_quality) {
    // New client - use data quality info
    displayDataQualityWarning(response.data_quality);
} else {
    // Old response or old client - graceful degradation
    displayBasicAvailability(response.available);
}
```

---

## Next Steps (Task 13)

### ⚠️ REQUIRES USER APPROVAL BEFORE IMPLEMENTATION

1. **Review this inventory document**
   - Confirm endpoints identified are correct
   - Confirm proposed schema design
   - Approve backward compatibility strategy

2. **Approve each endpoint change individually**
   - Will present each endpoint's proposed change
   - Get approval before modifying schemas
   - Get approval before modifying endpoint logic

3. **Implementation order** (if approved):
   - Create `DataQualityInfo` schema
   - Update schemas one at a time (with approval)
   - Update endpoint logic to populate field
   - Test each endpoint
   - Update API documentation

---

## Questions for User Approval

1. **Should `DataQualityInfo` be in `app/schemas/common.py` or `app/schemas/analytics.py`?**
   - common.py: Shared across API (more generic)
   - analytics.py: Specific to analytics endpoints (more cohesive)

2. **Should we add data_quality to ALL 4 endpoints or prioritize?**
   - Option A: All 4 at once (consistent but more changes)
   - Option B: Start with Factor Exposures (has most internal data)
   - Option C: Start with Stress Tests (clearest skip case)

3. **Should position-level endpoint have per-position quality or portfolio-level quality?**
   - Portfolio-level: Overall quality for all positions (simpler)
   - Per-position: Each position has its own quality info (more detailed)

4. **Naming preference for quality flags?**
   - Current internal: `'no_public_positions'`, `'limited_history'`, `'full_history'`
   - Alternative: `'NO_PUBLIC_POSITIONS'` (uppercase enum-style)
   - Alternative: `'skipped'`, `'partial'`, `'complete'` (simpler)

---

**Status**: ✅ Task 12a-12b COMPLETE (Inventory finished)
**Next**: Awaiting user approval to proceed with Task 12c-13 (Implementation)
