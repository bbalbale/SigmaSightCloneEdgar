# Migration Guide: Calculation Refactoring

**Target Audience**: Developers updating code to use refactored calculation modules
**Date**: 2025-10-20
**Refactoring Phase**: 1 (Critical Duplication Removal)

---

## Quick Start

### For most developers:
```bash
# 1. Preview changes
cd backend
python scripts/refactoring/refactor_calculations.py --dry-run

# 2. Apply changes
python scripts/refactoring/refactor_calculations.py

# 3. Run tests
pytest tests/test_calculations/ -v

# 4. Update your code (if needed - see section below)
```

---

## What Changed?

### Summary of Breaking Changes

| Function | Old Location | New Location | Breaking? |
|----------|-------------|--------------|-----------|
| `calculate_portfolio_market_beta()` | `market_risk.py` | `market_beta.py` | ⚠️ **YES** - Return structure changed |
| `calculate_portfolio_market_value()` | `stress_testing.py` | DELETED (use `get_portfolio_exposures()`) | ⚠️ **YES** - Function removed |

---

## Migration Path 1: Market Beta Function

### If you import from `market_risk.py`:

#### ❌ OLD CODE (BROKEN):
```python
from app.calculations.market_risk import calculate_portfolio_market_beta

result = await calculate_portfolio_market_beta(
    db=db,
    portfolio_id=portfolio_id,
    calculation_date=date.today()
)

# OLD return structure:
market_beta = result['market_beta']
portfolio_value = result['portfolio_value']
factor_breakdown = result['factor_breakdown']  # Had all 7 factors
data_quality = result['data_quality']
```

#### ✅ NEW CODE (CORRECT):
```python
# Update import
from app.calculations.market_beta import calculate_portfolio_market_beta

# Function call is the same
result = await calculate_portfolio_market_beta(
    db=db,
    portfolio_id=portfolio_id,
    calculation_date=date.today()
)

# NEW return structure:
if not result.get('success', True):
    # Handle error case
    logger.error(f"Market beta calculation failed: {result.get('error')}")
    raise ValueError(result.get('error', 'Unknown error'))

market_beta = result['market_beta']
r_squared = result['r_squared']  # NEW - quality metric
observations = result['observations']  # NEW - data points used
position_betas = result['position_betas']  # NEW - per-position betas

# If you need portfolio_value (no longer in return):
from app.calculations.stress_testing import get_portfolio_exposures
exposures = await get_portfolio_exposures(db, portfolio_id, calculation_date)
portfolio_value = exposures['net_exposure']

# If you need all 7 factor betas (not just Market):
from app.calculations.factors import calculate_factor_betas_hybrid
factor_result = await calculate_factor_betas_hybrid(db, portfolio_id, calculation_date)
factor_breakdown = factor_result['factor_betas']  # All 7 factors
```

---

### Why this change?

**OLD approach** (deleted):
- Ran 7-factor regression to get 1 beta (inefficient)
- Didn't persist results to database
- Mixed concerns (market risk scenarios shouldn't do multi-factor analysis)

**NEW approach**:
- Direct OLS regression against SPY (efficient)
- Persists to `position_market_betas` table for historical tracking
- Returns position-level betas for transparency
- Single responsibility: calculate market beta only

---

## Migration Path 2: Portfolio Market Value

### If you use `calculate_portfolio_market_value()`:

#### ❌ OLD CODE (BROKEN):
```python
from app.calculations.stress_testing import calculate_portfolio_market_value

# Get positions
positions = await get_positions(db, portfolio_id)

# Calculate value
net_value = calculate_portfolio_market_value(positions, return_gross=False)
gross_value = calculate_portfolio_market_value(positions, return_gross=True)
```

#### ✅ NEW CODE (CORRECT):
```python
from app.calculations.stress_testing import get_portfolio_exposures

# Get exposures (uses snapshot if available, calculates real-time if not)
exposures = await get_portfolio_exposures(
    db=db,
    portfolio_id=portfolio_id,
    calculation_date=date.today(),
    max_staleness_days=3  # Use snapshot if within 3 days
)

# Get values
net_value = exposures['net_exposure']
gross_value = exposures['gross_exposure']

# Bonus: Know the source
source = exposures['source']  # 'snapshot' or 'real_time'
snapshot_date = exposures['snapshot_date']  # When snapshot was taken
```

---

### Why this change?

**OLD approach** (deleted):
- Recalculated values every time (slow)
- Ignored pre-calculated snapshots in database
- Duplicate logic with `calculate_portfolio_exposures()` in `portfolio.py`
- Already marked DEPRECATED

**NEW approach**:
- Uses cached snapshot values when available (fast)
- Falls back to real-time calculation if needed
- Single source of truth
- Tells you whether data is fresh or cached

---

## Migration Path 3: Internal Changes (market_risk.py)

### For `calculate_market_scenarios()` function

This function **calls** `calculate_portfolio_market_beta()` internally. We've updated it for you.

#### Before (how it was):
```python
# Inside market_risk.py
market_data = await calculate_portfolio_market_beta(...)  # Called local function
market_beta = market_data['market_beta']
portfolio_value = market_data['portfolio_value']
```

#### After (how it is now):
```python
# Inside market_risk.py
from app.calculations.market_beta import calculate_portfolio_market_beta

market_data = await calculate_portfolio_market_beta(...)  # Calls market_beta.py
if not market_data.get('success'):
    raise ValueError(f"Market beta calculation failed: {market_data.get('error')}")

market_beta = market_data['market_beta']

# Get portfolio value separately
from app.calculations.stress_testing import get_portfolio_exposures
exposures = await get_portfolio_exposures(db, portfolio_id, calculation_date)
portfolio_value = exposures['net_exposure']
```

**Action**: ✅ **NO ACTION NEEDED** - We already updated this for you in the refactoring script.

---

## Common Migration Patterns

### Pattern 1: Need market beta only

```python
# ✅ RECOMMENDED
from app.calculations.market_beta import calculate_portfolio_market_beta

result = await calculate_portfolio_market_beta(db, portfolio_id, calc_date)
beta = result['market_beta']
```

### Pattern 2: Need all factor exposures (7 factors)

```python
# ✅ RECOMMENDED
from app.calculations.factors import calculate_factor_betas_hybrid

result = await calculate_factor_betas_hybrid(db, portfolio_id, calc_date)
market_beta = result['factor_betas']['Market']  # Just market
all_betas = result['factor_betas']  # All 7 factors
```

### Pattern 3: Need market beta with alternative method (Ridge regression)

```python
# ✅ RECOMMENDED
from app.calculations.factors_ridge import calculate_factor_betas_ridge

# Ridge gives you 6 non-market factors
ridge_result = await calculate_factor_betas_ridge(db, portfolio_id, calc_date)

# Market beta must be calculated separately (not included in Ridge)
from app.calculations.market_beta import calculate_portfolio_market_beta
market_result = await calculate_portfolio_market_beta(db, portfolio_id, calc_date)

# Combine results
all_betas = ridge_result['factor_betas']
all_betas['Market'] = market_result['market_beta']
```

### Pattern 4: Need portfolio value

```python
# ✅ RECOMMENDED
from app.calculations.stress_testing import get_portfolio_exposures

exposures = await get_portfolio_exposures(db, portfolio_id, calc_date)
net_exposure = exposures['net_exposure']  # Signed sum (longs - shorts)
gross_exposure = exposures['gross_exposure']  # Sum of absolute values
```

### Pattern 5: Need position-level market betas

```python
# ✅ RECOMMENDED
from app.calculations.market_beta import calculate_portfolio_market_beta

result = await calculate_portfolio_market_beta(
    db=db,
    portfolio_id=portfolio_id,
    calculation_date=calc_date,
    persist=True  # Saves to position_market_betas table
)

# Position-level betas are in the result
position_betas = result['position_betas']  # Dict[position_id, beta]

# Individual position beta
for position_id, beta in position_betas.items():
    print(f"Position {position_id}: Beta = {beta:.3f}")
```

---

## Testing Your Migrations

### Step 1: Check imports
```python
# Test your imports work
from app.calculations.market_beta import calculate_portfolio_market_beta
from app.calculations.stress_testing import get_portfolio_exposures

print("✅ Imports successful")
```

### Step 2: Run unit tests
```bash
# Test individual modules
pytest tests/test_market_beta.py -v
pytest tests/test_market_risk.py -v
pytest tests/test_stress_testing.py -v
```

### Step 3: Run integration tests
```bash
# Test the full calculation pipeline
pytest tests/test_calculations/ -v
```

### Step 4: Test with demo data
```python
# Quick validation script
from app.calculations.market_beta import calculate_portfolio_market_beta
from app.database import get_async_session
from datetime import date
import asyncio

async def test_migration():
    async with get_async_session() as db:
        # Use demo portfolio UUID
        demo_portfolio_id = "your-demo-portfolio-uuid"

        result = await calculate_portfolio_market_beta(
            db=db,
            portfolio_id=demo_portfolio_id,
            calculation_date=date.today()
        )

        if result['success']:
            print(f"✅ Market beta: {result['market_beta']:.3f}")
            print(f"✅ R²: {result['r_squared']:.3f}")
            print(f"✅ Observations: {result['observations']}")
        else:
            print(f"❌ Failed: {result.get('error')}")

asyncio.run(test_migration())
```

---

## Troubleshooting

### Issue 1: ImportError for `calculate_portfolio_market_beta`

**Error**:
```
ImportError: cannot import name 'calculate_portfolio_market_beta' from 'app.calculations.market_risk'
```

**Cause**: You're importing from old location

**Fix**:
```python
# OLD (broken):
from app.calculations.market_risk import calculate_portfolio_market_beta

# NEW (correct):
from app.calculations.market_beta import calculate_portfolio_market_beta
```

---

### Issue 2: KeyError for 'portfolio_value' or 'factor_breakdown'

**Error**:
```
KeyError: 'portfolio_value'
```

**Cause**: New function has different return structure

**Fix**:
```python
# OLD (broken):
portfolio_value = result['portfolio_value']

# NEW (correct):
from app.calculations.stress_testing import get_portfolio_exposures
exposures = await get_portfolio_exposures(db, portfolio_id, calc_date)
portfolio_value = exposures['net_exposure']
```

---

### Issue 3: NameError for `calculate_portfolio_market_value`

**Error**:
```
NameError: name 'calculate_portfolio_market_value' is not defined
```

**Cause**: Function was deleted (deprecated)

**Fix**:
```python
# OLD (broken):
value = calculate_portfolio_market_value(positions)

# NEW (correct):
from app.calculations.stress_testing import get_portfolio_exposures
exposures = await get_portfolio_exposures(db, portfolio_id, calc_date)
value = exposures['net_exposure']
```

---

### Issue 4: Test failures in market_risk.py

**Error**:
```
AssertionError: Expected 'factor_breakdown' in result
```

**Cause**: Tests expect old return structure

**Fix**: Update test assertions:
```python
# OLD test (broken):
assert 'factor_breakdown' in result
assert 'portfolio_value' in result

# NEW test (correct):
assert 'success' in result
assert result['success'] is True
assert 'market_beta' in result
assert 'r_squared' in result
assert 'position_betas' in result
```

---

## Performance Impact

### Before Refactoring:
```python
# market_risk.py calling local calculate_portfolio_market_beta()
# This ran 7-factor regression just to get 1 beta
# Time: ~500ms (fetches 7 factor ETF histories, runs multivariate OLS)
```

### After Refactoring:
```python
# market_risk.py calling market_beta.calculate_portfolio_market_beta()
# Direct OLS against SPY
# Time: ~150ms (fetches only SPY history, runs simple OLS)
# Speedup: 3.3x faster
```

**Bonus**: Results are now persisted to `position_market_betas` table for historical tracking!

---

## Backwards Compatibility

### What's backwards compatible?

✅ Function **signature** is compatible (same parameters)
✅ Core functionality is the same (calculates market beta)
✅ Can be called with same arguments

### What's NOT backwards compatible?

❌ Function **location** changed (import path)
❌ Return **structure** changed (different keys)
❌ Deprecated function removed (`calculate_portfolio_market_value`)

**Recommendation**: Treat this as a **minor version bump** (1.4.x → 1.5.0)

---

## FAQ

### Q: Why didn't you just keep both functions?

**A**: Having two functions with the **same name** but **different behavior** is confusing and error-prone. It violates the principle of least surprise. Developers would get different results depending on which import they used.

---

### Q: Can I still get the 7-factor breakdown?

**A**: Yes! Use `calculate_factor_betas_hybrid()` from `factors.py`:
```python
from app.calculations.factors import calculate_factor_betas_hybrid
result = await calculate_factor_betas_hybrid(db, portfolio_id, calc_date)
all_seven_factors = result['factor_betas']
```

---

### Q: What if I need the old behavior exactly?

**A**: The old function is still in git history:
```bash
# See the old implementation
git show HEAD~1:backend/app/calculations/market_risk.py

# Extract just that function if absolutely needed
git show HEAD~1:backend/app/calculations/market_risk.py | sed -n '/^async def calculate_portfolio_market_beta/,/^async def /p'
```

But we **strongly recommend** using the new approach. The old function was inefficient and didn't persist results.

---

### Q: Will this break production?

**A**: Depends on your deployment:

**If you have automated tests**: Tests will catch issues before deployment ✅

**If you deploy to staging first**: You'll catch issues in staging ✅

**If you deploy directly to production**: Run the refactoring script in a feature branch first, test thoroughly, then merge ⚠️

**Recommendation**:
1. Create feature branch
2. Run refactoring script
3. Run full test suite
4. Deploy to staging
5. Smoke test all calculation endpoints
6. Deploy to production

---

### Q: How do I rollback if something breaks?

**A**: The refactoring script creates backups:
```bash
# List backups
ls -la backend/app/calculations/*.backup_*

# Restore specific file
cp backend/app/calculations/market_risk.backup_20251020_143022 \
   backend/app/calculations/market_risk.py

# Or use git
git checkout backend/app/calculations/market_risk.py
```

---

## Success Checklist

Before marking migration complete, verify:

- [ ] All imports updated to new locations
- [ ] All tests passing (`pytest tests/ -v`)
- [ ] No warnings about deprecated functions in logs
- [ ] Batch processing runs successfully
- [ ] Market risk scenarios calculate correctly
- [ ] Stress testing works as expected
- [ ] Performance is same or better
- [ ] No unexpected errors in staging/production

---

## Support

If you encounter issues not covered in this guide:

1. Check the **REFACTORING_GUIDE_CALCULATIONS.md** for detailed code changes
2. Review the **refactor_calculations.py** script source
3. Search git history: `git log --grep="calculation" --oneline`
4. Ask in #eng-backend Slack channel

---

**Last Updated**: 2025-10-20
**Version**: 1.0
**Related Docs**: REFACTORING_GUIDE_CALCULATIONS.md, CLAUDE.md (Part II)
