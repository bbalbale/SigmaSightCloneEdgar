# Calculation Refactoring Guide - Detailed Code Changes

**Date**: 2025-10-20
**Scope**: Remove calculation duplication across 5 modules
**Status**: Ready for implementation

---

## Overview of Changes

This guide documents **specific line-by-line changes** needed to eliminate calculation duplication.

### Summary
- **Files Modified**: 2 (market_risk.py, stress_testing.py)
- **Files Reviewed**: 3 (market_beta.py, factors.py, factors_ridge.py - no changes needed)
- **Lines Removed**: ~143 lines of duplicate code
- **Lines Added**: ~3 lines (import statements)
- **Net Change**: -140 lines

---

## File 1: `app/calculations/market_risk.py`

### Problem
Contains a duplicate `calculate_portfolio_market_beta()` function that:
- Has the same name as the function in `market_beta.py`
- Does a different thing (calls multi-factor model just to extract Market beta)
- Is inefficient and confusing

### Changes Required

#### **CHANGE 1: Remove duplicate function (lines 56-124)**

**Lines to DELETE** (69 lines):
```python
# DELETE THESE LINES (56-124):

async def calculate_portfolio_market_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date
) -> Dict[str, Any]:
    """
    Calculate portfolio market beta using existing factor betas

    Args:
        db: Database session
        portfolio_id: Portfolio ID to analyze
        calculation_date: Date for the calculation

    Returns:
        Dictionary containing market beta and factor breakdown
    """
    logger.info(f"Calculating portfolio market beta for portfolio {portfolio_id}")

    try:
        # Get active positions for the portfolio
        stmt = select(Position).where(
            and_(
                Position.portfolio_id == portfolio_id,
                Position.exit_date.is_(None)
            )
        )
        result = await db.execute(stmt)
        positions = result.scalars().all()

        if not positions:
            raise ValueError(f"No active positions found for portfolio {portfolio_id}")

        # Get existing factor betas (reuse from Section 1.4.4)
        from app.calculations.factors import calculate_factor_betas_hybrid

        factor_analysis = await calculate_factor_betas_hybrid(
            db=db,
            portfolio_id=portfolio_id,
            calculation_date=calculation_date,
            use_delta_adjusted=False
        )

        portfolio_betas = factor_analysis['factor_betas']

        # Calculate market beta (SPY factor represents broad market exposure)
        market_beta = portfolio_betas.get('Market', 0.0)  # 'Market' from SPY factor

        # Calculate portfolio value for exposure calculations using centralized utility
        portfolio_value = Decimal('0')
        for position in positions:
            value = get_position_market_value(position, recalculate=True)
            portfolio_value += value

        results = {
            'portfolio_id': str(portfolio_id),
            'calculation_date': calculation_date,
            'market_beta': market_beta,
            'portfolio_value': float(portfolio_value),
            'factor_breakdown': portfolio_betas,
            'data_quality': factor_analysis['data_quality'],
            'positions_count': len(positions)
        }

        logger.info(f"Portfolio market beta calculated: {market_beta:.4f}")
        return results

    except Exception as e:
        logger.error(f"Error calculating portfolio market beta: {str(e)}")
        raise
```

**Why delete?**
- This function is LESS EFFICIENT than the one in `market_beta.py`
- Runs 7-factor regression model just to extract one beta
- Doesn't persist results to database
- Has different return structure than `market_beta.py` version

---

#### **CHANGE 2: Update imports (near line 19)**

**FIND this import block** (around line 19):
```python
from app.calculations.factors import fetch_factor_returns, _aggregate_portfolio_betas
```

**REPLACE with**:
```python
# Removed: fetch_factor_returns, _aggregate_portfolio_betas (only used by deleted function)
```

**ADD new import** (after line 20):
```python
from app.calculations.market_beta import calculate_portfolio_market_beta
```

**Final import section should look like**:
```python
from app.models.positions import Position
from app.models.market_data import MarketRiskScenario, PositionInterestRateBeta, FactorDefinition
from app.models.users import Portfolio
from app.calculations.market_beta import calculate_portfolio_market_beta  # ← NEW
from app.calculations.factor_utils import get_position_market_value
from app.constants.factors import (
    FACTOR_ETFS, REGRESSION_WINDOW_DAYS, MIN_REGRESSION_DAYS,
    BETA_CAP_LIMIT, OPTIONS_MULTIPLIER
)
```

---

#### **CHANGE 3: Update function calls (NO CHANGES NEEDED)**

Good news! The function signature is **compatible**, so callers don't need updates.

**Existing caller** (line 152):
```python
market_data = await calculate_portfolio_market_beta(
    db=db,
    portfolio_id=portfolio_id,
    calculation_date=calculation_date
)
```

This will continue to work because `market_beta.py` version has the same signature:
```python
async def calculate_portfolio_market_beta(
    db: AsyncSession,
    portfolio_id: UUID,
    calculation_date: date,
    window_days: int = REGRESSION_WINDOW_DAYS,  # Optional (has default)
    persist: bool = True  # Optional (has default)
)
```

**HOWEVER**, the return structure is different:

**OLD return** (from deleted function):
```python
{
    'portfolio_id': str,
    'calculation_date': date,
    'market_beta': float,
    'portfolio_value': float,
    'factor_breakdown': dict,
    'data_quality': dict,
    'positions_count': int
}
```

**NEW return** (from market_beta.py):
```python
{
    'portfolio_id': UUID,
    'market_beta': float,
    'r_squared': float,
    'observations': int,
    'positions_count': int,
    'calculation_date': date,
    'position_betas': dict,
    'success': bool
}
```

**Action**: Update line 158 in `calculate_market_scenarios()`:
```python
# OLD:
market_beta = market_data['market_beta']
portfolio_value = market_data['portfolio_value']

# NEW:
if not market_data.get('success', True):
    raise ValueError(f"Market beta calculation failed: {market_data.get('error', 'Unknown error')}")

market_beta = market_data['market_beta']

# Need to get portfolio_value separately
from app.calculations.stress_testing import get_portfolio_exposures
exposures = await get_portfolio_exposures(db, portfolio_id, calculation_date)
portfolio_value = exposures['net_exposure']
```

---

### After Changes - market_risk.py

**Before**: 545 lines
**After**: ~479 lines (-66 lines from function, -3 lines from imports, +3 lines for new logic)

**Functions remaining**:
- ✅ `calculate_market_scenarios()` - uses imported market beta function
- ✅ `calculate_position_interest_rate_betas()` - unique functionality
- ✅ `calculate_interest_rate_scenarios()` - unique functionality
- ✅ `_is_options_position()` - helper function
- ✅ `_calculate_mock_interest_rate_betas()` - helper function

---

## File 2: `app/calculations/stress_testing.py`

### Problem
Contains a deprecated `calculate_portfolio_market_value()` function that:
- Is marked DEPRECATED in its own docstring
- Has been replaced by `get_portfolio_exposures()`
- Still exists in codebase (technical debt)

### Changes Required

#### **CHANGE 1: Remove deprecated function (lines 35-108)**

**Lines to DELETE** (74 lines):
```python
# DELETE THESE LINES (35-108):

def calculate_portfolio_market_value(positions, return_gross: bool = False) -> float:
    """
    DEPRECATED: Use get_portfolio_exposures() instead.

    This function duplicates logic that already exists in:
    - app.calculations.portfolio.calculate_portfolio_exposures()
    - app.models.snapshots.PortfolioSnapshot (gross_exposure, net_exposure columns)

    Kept for backward compatibility only. Will be removed in future version.

    Calculate portfolio market value correctly handling options and short positions.

    ISSUE #1 FIX: Returns NET exposure by default (signed values)
    Factor betas already encode net sensitivity, so stress P&L should be calculated
    as: net_exposure × beta × shock (not gross_exposure × beta × shock)

    Args:
        positions: List of Position objects
        return_gross: If True, return gross exposure (absolute value)
                     If False (default), return net exposure (signed sum)

    Returns:
        Net portfolio exposure (signed) by default for accurate stress testing
        OR gross exposure (absolute) if return_gross=True for transparency metrics

    Note:
        - Uses Position.market_value if available
        - Applies options contract multiplier (100)
        - Handles SHORT positions correctly (negative values)
        - Net exposure = long positions - short positions (signed sum)
        - Gross exposure = sum of absolute values (total capital at risk)
    """
    logger.warning(
        "calculate_portfolio_market_value() is deprecated. "
        "Use get_portfolio_exposures() instead to avoid recalculating stored values."
    )

    net_total = 0.0
    gross_total = 0.0

    for pos in positions:
        # Use pre-calculated market value if available
        if pos.market_value is not None:
            signed_value = float(pos.market_value)
            net_total += signed_value
            gross_total += abs(signed_value)
        elif pos.last_price is not None:
            # Calculate market value based on position type
            quantity = float(pos.quantity)
            price = float(pos.last_price)

            # Apply options contract multiplier
            if pos.position_type.name in ['LC', 'LP', 'SC', 'SP']:
                multiplier = OPTIONS_CONTRACT_MULTIPLIER
            else:
                multiplier = 1

            # Apply sign for short positions
            # Note: SHORT stock and short options (SC, SP) are negative
            if pos.position_type.name in ['SHORT', 'SC', 'SP']:
                sign = -1
            else:
                sign = 1

            market_value = sign * quantity * price * multiplier
            net_total += market_value
            gross_total += abs(market_value)

    # ISSUE #1 FIX: Return NET exposure by default
    # Factor exposures are calculated using signed position values
    # Beta already encodes directional sensitivity, so we need net exposure
    # For hedged portfolios: net = $1.4M, gross = $5.6M (4x difference!)
    # CRITICAL: Gross = sum(abs values), NOT abs(sum values)
    return gross_total if return_gross else net_total
```

**Why delete?**
- Function is already marked DEPRECATED
- Replacement function (`get_portfolio_exposures()`) exists immediately after it
- No callers should be using this anymore

---

#### **CHANGE 2: Verify no callers exist**

**Search the codebase for**:
```bash
grep -r "calculate_portfolio_market_value" backend/app/
```

**Expected result**: Should only find the definition (which we're deleting)

If any callers are found, they must be updated to use:
```python
# OLD:
portfolio_value = calculate_portfolio_market_value(positions, return_gross=False)

# NEW:
exposures = await get_portfolio_exposures(db, portfolio_id, calculation_date)
portfolio_value = exposures['net_exposure']  # or exposures['gross_exposure']
```

---

### After Changes - stress_testing.py

**Before**: 1147 lines
**After**: ~1073 lines (-74 lines)

**Functions remaining**:
- ✅ `get_portfolio_exposures()` - CORRECT replacement function
- ✅ `calculate_factor_correlation_matrix()` - unique functionality
- ✅ `load_stress_scenarios()` - unique functionality
- ✅ `calculate_direct_stress_impact()` - unique functionality
- ✅ `calculate_correlated_stress_impact()` - unique functionality
- ✅ `run_comprehensive_stress_test()` - unique functionality
- ✅ `save_stress_test_results()` - unique functionality

---

## File 3: `app/calculations/market_beta.py`

### Changes Required

**NO CHANGES NEEDED** ✅

This file contains the **correct, canonical implementation** of market beta calculations.

**Keep as-is**:
- ✅ `fetch_returns_for_beta()` - helper function
- ✅ `calculate_position_market_beta()` - position-level beta
- ✅ `persist_position_beta()` - database persistence
- ✅ `calculate_portfolio_market_beta()` - **CANONICAL VERSION**
- ✅ `calculate_portfolio_provider_beta()` - alternative method

---

## File 4: `app/calculations/factors.py`

### Changes Required

**NO CHANGES NEEDED** ✅

This file correctly implements multi-factor analysis and is properly reused.

**Keep as-is**:
- ✅ `fetch_factor_returns()` - properly centralized, used by 4 modules
- ✅ `calculate_position_returns()` - properly centralized, used by 3 modules
- ✅ `calculate_factor_betas_hybrid()` - 7-factor model
- ✅ `_aggregate_portfolio_betas()` - equity-weighted aggregation
- ✅ `store_position_factor_exposures()` - database persistence
- ✅ `aggregate_portfolio_factor_exposures()` - portfolio-level aggregation

---

## File 5: `app/calculations/factors_ridge.py`

### Changes Required

**NO CHANGES NEEDED** ✅

This file correctly implements Ridge regression for 6 non-market factors.

**Keep as-is**:
- ✅ `calculate_factor_betas_ridge()` - Ridge regression implementation
- ✅ `tune_ridge_alpha()` - hyperparameter tuning
- ✅ Properly reuses `fetch_factor_returns()` and `calculate_position_returns()`

---

## Testing Changes

After applying refactoring, run these tests:

### 1. Import Tests
```bash
cd backend
uv run python -c "
from app.calculations.market_risk import calculate_market_scenarios
from app.calculations.stress_testing import get_portfolio_exposures
print('✅ Imports working')
"
```

### 2. Function Signature Tests
```bash
uv run python -c "
import inspect
from app.calculations.market_beta import calculate_portfolio_market_beta

sig = inspect.signature(calculate_portfolio_market_beta)
print('Function signature:', sig)
print('✅ Function accessible')
"
```

### 3. Integration Tests
```bash
# Run full test suite
uv run pytest tests/test_calculations/ -v

# Run specific market risk tests
uv run pytest tests/test_market_risk.py -v
```

### 4. Batch Processing Test
```bash
# Test batch processing still works
uv run python scripts/batch_processing/run_batch.py --portfolio-id <demo-portfolio-uuid>
```

---

## Rollback Plan

If issues occur after refactoring:

### Option 1: Restore from backups
```bash
# Script creates timestamped backups automatically
cd backend/app/calculations
cp market_risk.backup_20251020_HHMMSS market_risk.py
cp stress_testing.backup_20251020_HHMMSS stress_testing.py
```

### Option 2: Git revert
```bash
git diff app/calculations/market_risk.py
git diff app/calculations/stress_testing.py

# If changes look wrong:
git checkout app/calculations/market_risk.py
git checkout app/calculations/stress_testing.py
```

---

## Success Criteria

✅ All tests pass
✅ No import errors
✅ Batch processing runs successfully
✅ Market risk scenarios calculate correctly
✅ Stress testing works as expected
✅ No deprecated function warnings in logs
✅ Code is ~140 lines shorter
✅ No duplicate function names

---

## Next Steps After Refactoring

1. **Update documentation** in `CLAUDE.md` Part II
2. **Add linter rules** to prevent duplicate function names
3. **Consider Phase 2** refactoring:
   - Standardize portfolio aggregation weighting method
   - Extract shared utilities to `factor_utils.py`
   - Create calculation module hierarchy diagram

---

**Questions or issues?** Refer to the migration guide or contact the development team.
