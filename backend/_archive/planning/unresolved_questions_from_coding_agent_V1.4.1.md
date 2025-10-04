# Unresolved Questions & Resolutions - V1.4.1 (2025-07-15)

> **UPDATE**: The DATABASE_DESIGN_ADDENDUM_V1.4.1.md and PRD_TAGS_V1.4.1.md documents have resolved most of these questions. This document now tracks both the original questions and their resolutions.

> **V1.4 CALCULATION UPDATE**: All project documentation has been updated to reflect deterministic calculations. Greeks are calculated using `mibian` (Black-Scholes) only; no `py_vollib` fallback and no mock Greeks. Factor betas use `statsmodels` OLS. Risk metrics with `empyrical` are planned but not yet implemented.

## 1. Database Schema Gaps ✅ RESOLVED

### 1.1 Missing Core Tables ✅ RESOLVED
- **Users table**: ✅ RESOLVED - Complete schema provided in DATABASE_DESIGN_ADDENDUM Section 1.1
- **Portfolios table**: ✅ RESOLVED - Single portfolio per user with unique constraint (Section 1.1)
- **Tags tables**: ✅ RESOLVED - Complete `tags` and `position_tags` tables defined (Section 1.4)
- **Factor definitions**: ✅ RESOLVED - Complete `factors` table with 8 fixed factors (Section 1.3)

### 1.2 Data Mapping ✅ RESOLVED
- **CSV → Database**: ✅ RESOLVED - Complete transformation logic in Section 2.1
  - Option symbols (OCC format) parsing implemented
  - Negative quantities → SHORT positions logic defined
  - Comma-separated tags → position_tags relationships
- **GICS data storage**: ✅ RESOLVED - Added `sector` and `industry` fields to `market_data_cache` (Section 1.2)

## 2. Authentication & User Management ✅ RESOLVED
- ✅ RESOLVED - Complete users table schema provided (Section 1.1)
- ✅ RESOLVED - JWT-based authentication with 24-hour expiry
- ✅ RESOLVED - No session table needed (stateless JWTs)
- ✅ RESOLVED - Auth endpoints to be implemented in API layer

## 3. Greeks Calculation Contradiction ✅ RESOLVED
- ✅ RESOLVED - V1.4 uses mibian-only Greeks
- Real calculations using `mibian` Black-Scholes for options
- No mock fallback; on error or missing inputs, Greeks are stored as null
- `/api/v1/risk/greeks/calculate` endpoint uses the same mibian-only path
- Reflected in `PRD_V1.4.md` Section 6 and `DATABASE_DESIGN_ADDENDUM_V1.4.1.md` Section 2.2

## 4. Tag System Architecture ✅ RESOLVED
- ✅ RESOLVED - Complete schema in DATABASE_DESIGN_ADDENDUM Section 1.4
- ✅ RESOLVED - Supports regular and strategy tags
- ✅ RESOLVED - Many-to-many relationship via `position_tags`
- ✅ RESOLVED - Full API specification in PRD_TAGS_V1.4.1.md Section 8

## 5. Market Data & Batch Processing ✅ RESOLVED

### 5.1 Data Sources ✅ RESOLVED
- ✅ RESOLVED - `data_source` field added; YFinance removed from active dependencies
- ✅ RESOLVED - Polygon.io for price data; FMP introduced for ETF/historical workflows
- Note: GICS enrichment via YFinance has been removed; temporary pause while alternatives are evaluated

### 5.2 Calculation Timing ✅ RESOLVED
- ✅ RESOLVED - Batch processing schedule defined (Section 6):
  - 4 PM: Market data update
  - 5 PM: Risk metrics calculation  
  - 5:30 PM: Daily snapshots
- All calculations run in batch, API serves cached results

## 6. Async vs Sync API Design ✅ RESOLVED
- ✅ RESOLVED - SYNC ONLY for V1 (Section 8, Key Decision #3)
- No async job management needed
- API serves pre-calculated results from batch processing
- `batch_jobs` table tracks processing status

## 7. Portfolio Structure ✅ RESOLVED
- ✅ RESOLVED - SINGLE portfolio per user (Section 8, Key Decision #1)
- Enforced by unique constraint on `portfolios.user_id`
- API will use singular endpoints where appropriate

## 8. Version Numbering ✅ RESOLVED
- "V1.4" - Product version (current release)
- "V5" - Frontend prototype iteration number
- "/v1" - API version for future compatibility
- Document naming convention established

## 9. Factor Calculations ✅ RESOLVED
- ✅ RESOLVED - 7 fixed factors with ETF proxies (Short Interest postponed)
- ✅ RESOLVED - "Short Interest" marked as CUSTOM/postponed
- Factor calculations implemented with a 150-day regression window in batch processing
- Factor covariance matrix populated via batch jobs

## 10. Position Type Logic ✅ RESOLVED  
- ✅ RESOLVED - Complete transformation logic (Section 2.1)
- `determine_position_type()` function provided
- OCC symbology parsing implemented
- Clear mapping from CSV to enum values

## 11. Deployment Configuration ✅ RESOLVED
- ✅ RESOLVED - Complete configuration in Sections 4.1-4.3
- UV package manager integration via `pyproject.toml`
- Railway environment variables specified
- Pydantic settings management implemented

## 12. Demo Data Requirements ✅ RESOLVED
- ✅ RESOLVED - 3 demo users with different strategies (Section 5.1)
- ✅ RESOLVED - 20-30 positions per demo portfolio (Section 5.2)
- ✅ RESOLVED - 90 days of historical snapshots (Section 5.3)
- ✅ RESOLVED - Realistic data generation logic provided

## 13. Short Interest Calculation ✅ POSTPONED FOR V1.4
- Factor defined as "CUSTOM" calculation
- **Decision**: Use static mock values for V1.4 demo
- **V1.4 Implementation**: Set all Short Interest exposures to 0.0
- **Future Enhancement**: Implement days-to-cover or short ratio calculation in Phase 2

## 14. Factor Covariance Matrix ✅ POSTPONED FOR V1.4
- Tables exist but population method not specified
- **Decision**: Use static mock covariance matrix for V1.4 demo
- **V1.4 Implementation**: Identity matrix with 1% variance (diagonal)
- **Future Enhancement**: Implement 60-day rolling correlations of ETF proxies in Phase 2

## 15. Batch Job Implementation ✅ RESOLVED
- ✅ RESOLVED - Complete implementation details added to PRD_V1.4.md Section 3.6
- ✅ RESOLVED - Specific tasks added to TODO.md Section 1.7
- **Implementation approach**:
  - Use APScheduler instead of Celery for V1.4 simplicity
  - Three main jobs: market data (4 PM), risk metrics (5 PM), snapshots (5:30 PM)
  - Mock values for Greeks and factor exposures
  - Manual trigger endpoints for admin control

## Summary

**15 of 15 issues resolved or deferred** for V1.4:
- ✅ All database schemas complete
- ✅ Authentication strategy defined  
- ✅ Mock Greeks approach clarified
- ✅ Tag system fully specified
- ✅ Single portfolio decision made
- ✅ Sync-only API confirmed
- ✅ Deployment configuration provided
- ✅ Demo data requirements specified
- ✅ Short Interest calculation deferred (mock values)
- ✅ Factor covariance matrix deferred (static matrix)

**All 15 items now have clear resolution paths**:
- Batch job implementations documented in PRD and TODO.md
- Ready for V1.4 demo development

## V1.4 Mock Implementation Approach

```python
# Mock factor exposures for demo
MOCK_FACTOR_EXPOSURES = {
    'Market Beta': lambda: random.uniform(0.8, 1.2),
    'Momentum': lambda: random.uniform(-0.5, 0.5),
    'Value': lambda: random.uniform(-0.3, 0.3),
    'Growth': lambda: random.uniform(-0.3, 0.3),
    'Quality': lambda: random.uniform(-0.2, 0.2),
    'Size': lambda: random.uniform(-0.4, 0.4),
    'Low Volatility': lambda: random.uniform(-0.3, 0.3),
    'Short Interest': lambda: 0.0  # Static for V1.4
}

# Static covariance matrix for demo (simplified)
MOCK_COVARIANCE_MATRIX = np.eye(8) * 0.01  # Identity matrix, 1% variance
```

This approach allows the V1.4 demo to proceed with full functionality while deferring complex calculations to future phases.
