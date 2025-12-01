# Factor Exposures Fix Plan

**Date**: 2025-11-28
**Issue**: Position-level factor exposures not appearing on Research page

---

## Problem Summary

When clicking on a position in the Research page, the Risk Metrics section shows dashes for:
- 90 Day Beta: —
- Growth Factor: —
- Momentum Factor: —
- Size Factor: —

The 1 Year Beta (from company profile) works fine.

---

## Root Cause Analysis

### Finding 1: API Returns Empty Exposures
```json
GET /api/v1/analytics/portfolio/{id}/positions/factor-exposures
{
  "available": true,
  "positions": [
    {"symbol": "AAPL", "exposures": {}},  // EMPTY!
    {"symbol": "GOOGL", "exposures": {}}, // EMPTY!
    ...
  ]
}
```

### Finding 2: Portfolio-Level Factors Work Fine
```json
GET /api/v1/analytics/portfolio/{id}/factor-exposures
{
  "factors": [
    {"name": "Market Beta (90D)", "beta": 0.49},
    {"name": "Growth", "beta": 0.28},
    {"name": "Momentum", "beta": -0.02},
    ...
  ]
}
```

### Finding 3: Two Separate Factor Systems

| System | Calculation | Table | Status |
|--------|-------------|-------|--------|
| **Portfolio Ridge Factors** | Ridge regression at portfolio level | `FactorExposure` | ✅ Working |
| **Portfolio Betas** | From `PortfolioSnapshot` | `portfolio_snapshots` | ✅ Working |
| **Position OLS Factors** | OLS regression per position | `PositionFactorExposure` | ❌ Empty |

---

## Key Files

### Backend
- `app/calculations/factors.py` - Position-level OLS factor calculation
- `app/calculations/factors_ridge.py` - Portfolio-level Ridge factor calculation
- `app/calculations/factor_utils.py` - Factor name mapping (BROKEN)
- `app/services/factor_exposure_service.py` - API service layer
- `app/db/seed_factors.py` - Database factor definitions
- `app/constants/factors.py` - `FACTOR_ETFS` constant
- `app/batch/batch_orchestrator.py` - Batch processing orchestration

### Frontend (Already Fixed - Commit a5538707)
- `src/services/positionRiskService.ts` - Changed `'Market Beta'` → `'Market Beta (90D)'`
- `src/hooks/useCommandCenterData.ts` - Changed beta lookup
- `src/components/portfolio/FactorExposureCards.tsx` - Changed FACTOR_ORDER
- `src/components/positions/FactorBetaCard.tsx` - Changed factor descriptions

---

## The Factor Name Mismatch

### FACTOR_ETFS (constants/factors.py)
```python
FACTOR_ETFS = {
    "Market": "SPY",
    "Value": "VTV",
    "Growth": "VUG",
    ...
}
```

### FACTOR_NAME_MAPPING (factor_utils.py) - WRONG
```python
FACTOR_NAME_MAPPING = {
    'Market': 'Market Beta',  # WRONG - DB has 'Market Beta (90D)'
    ...
}
```

### Database FactorDefinition (seed_factors.py)
```python
{"name": "Market Beta (90D)", ...},  # Actual DB name
{"name": "Momentum", ...},
{"name": "Value", ...},
...
```

When `store_position_factor_exposures()` runs:
1. It gets factor name `'Market'` from regression
2. Normalizes to `'Market Beta'` via `normalize_factor_name()`
3. Looks up in `factor_name_to_id` dict
4. `'Market Beta'` NOT FOUND (DB has `'Market Beta (90D)'`)
5. **Skips storing** with warning log

---

## Questions to Resolve

### Q1: Is position-level OLS calculation still active?
Check if `batch_orchestrator.py` calls `calculate_factor_betas_hybrid()` from `factors.py`.

### Q2: Should we use Ridge factors for positions too?
The Ridge approach (`factors_ridge.py`) works. Should position-level also use Ridge?

### Q3: What factors should positions have?
- Just Market Beta (90D)?
- All 7 style factors (Value, Growth, Momentum, Quality, Size, Low Vol)?
- Spread factors?

---

## Proposed Fix Options

### Option A: Fix Factor Name Mapping (Quick Fix)
Update `factor_utils.py`:
```python
FACTOR_NAME_MAPPING = {
    'Market': 'Market Beta (90D)',  # Fix mapping
    'Interest Rate': 'IR Beta',
    'Value': 'Value',
    'Growth': 'Growth',
    ...
}
```

**Pros**: Simple, minimal change
**Cons**: Only works if position OLS calculation is still running

### Option B: Add Position-Level Factors from Ridge Results
Derive position factors from portfolio-level Ridge results + position weights.

**Pros**: Consistent with portfolio factors
**Cons**: More complex, may not accurately reflect position-specific factor exposure

### Option C: Calculate Position Betas via Simple OLS
For each position, run simple OLS regression vs SPY (for beta) and vs factor ETFs.

**Pros**: Position-specific, accurate
**Cons**: Computationally expensive, may already exist but broken

---

## Recommended Next Steps

1. **Check batch_orchestrator.py** - Verify if `calculate_factor_betas_hybrid()` is called
2. **Check Railway logs** - Look for factor calculation logs during batch runs
3. **Decide on approach** - Fix mapping vs redesign position factors
4. **Implement fix**
5. **Test on Railway** - Run batch, verify data populated
6. **Verify frontend** - Check Research page shows factors

---

## Frontend Fix Status

Already committed (a5538707) but NOT YET deployed to Railway:
- Changed factor name lookups from `'Market Beta'` to `'Market Beta (90D)'`
- Frontend will work once backend populates `PositionFactorExposure` table

---

## Related Commits

- `a5538707` - Frontend factor name fixes (not deployed)
- `cb483d06` - Backend signed weights fix for portfolio beta

---

## Commands for Investigation

```bash
# Check if position factor exposures exist in Railway DB
# (Need Railway CLI or direct DB access)

# Check batch orchestrator for factor calculation calls
grep -n "calculate_factor_betas" backend/app/batch/batch_orchestrator.py

# Check Railway logs for factor calculation
# Look for: "Storing position factor exposures"
```
