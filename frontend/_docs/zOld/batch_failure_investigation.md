# Batch Processing Failure Investigation

**Date**: 2025-11-06
**Batch Run Time**: ~30 minutes (21:20 - 21:50 approx)
**Status**: ⚠️ **CRITICAL FAILURE** - Optimizations worked (speed) but calculations failed (correctness)

---

## Symptoms Observed

### ✅ What Worked
1. **Performance**: Batch completed in 30 minutes (vs 6-8 hours expected without optimizations)
2. **Equity Updates**: Portfolio equity_balance fields WERE updated at 2025-11-07 03:16 UTC
3. **No Hangs**: No 6-hour company profile query hangs
4. **Market Data**: Prices exist for Nov 4-6 (58 symbols each day)

### ❌ What Failed
1. **ZERO Snapshots Created**: `portfolio_snapshots` table has 0 rows
2. **No P&L Data**: No daily_pnl, cumulative_pnl values anywhere
3. **No Volatility Analysis**: No volatility metrics calculated
4. **No Stress Tests**: Stress test calculations didn't run
5. **Analytics Missing**: Phase 6 analytics appear to have not executed

---

## Root Cause Hypotheses

### Hypothesis 1: Phase 3 Failed Silently ⭐ **MOST LIKELY**

**Evidence**:
- Equity balances were updated (this happens in Phase 3)
- But snapshots were NOT created (also happens in Phase 3)
- This suggests Phase 3 started but failed during snapshot creation

**Code Location**: `backend/app/batch/pnl_calculator.py:248`
```python
snapshot_result = await create_portfolio_snapshot(
    db=db,
    portfolio_id=portfolio_id,
    calculation_date=calculation_date,
    skip_pnl_calculation=True,
    skip_provider_beta=is_historical,
    skip_sector_analysis=is_historical
)
```

**Possible Causes**:
1. `create_portfolio_snapshot()` returned `success: False`
2. An exception was raised and caught at line 238-242
3. Snapshot object was created but not committed to database
4. Transaction was rolled back before commit

---

### Hypothesis 2: Exception Raised and Caught

**Evidence**:
- We changed line 242 from `logger.warning()` to `raise`
- If an exception occurred, it should have been re-raised
- But batch continued and completed (30 minutes)

**Code Location**: `backend/app/batch/pnl_calculator.py:238-242`
```python
except Exception as e:
    logger.error(f"Error updating equity for {portfolio_id}: {e}", exc_info=True)
    # CRITICAL FIX: Re-raise exception instead of continuing silently
    # Re-raise to stop processing - silent failures are bad!
    raise
```

**Questions**:
- Did the batch script catch this exception higher up?
- Is there error handling in `batch_orchestrator.py` that caught and continued?

---

### Hypothesis 3: Database Transaction Issues

**Evidence**:
- Equity balances persisted (committed)
- Snapshots did NOT persist (rolled back?)

**Possible Causes**:
1. Snapshot creation happens after equity update
2. Exception between equity update and snapshot creation
3. Transaction rolled back only for snapshots, not equity

**Code Flow**:
```
1. Calculate equity (succeeds) ✅
2. Update portfolio.equity_balance (succeeds, committed) ✅
3. Create snapshot (fails?) ❌
4. Commit (only equity persists?) ⚠️
```

---

### Hypothesis 4: Skip Logic Bug

**Evidence**:
- Tested: Nov 6 is NOT treated as historical (is_historical = False)
- All phases should have run fully
- But Phase 6 analytics didn't produce results

**Unlikely**: Skip logic appears correct for Nov 6

---

## Diagnostic Steps Required

### Step 1: Check Batch Command Output ⭐ **CRITICAL**

**Action**: Review the terminal output from the batch run
**Look for**:
- Phase completion messages
- Error messages
- "EQUITY DEBUG" log lines
- Exception tracebacks
- Snapshot creation success/failure messages

**Questions for User**:
1. What command did you run? (`uv run python scripts/batch_processing/run_batch.py --start-date ? --end-date ?`)
2. Did you see any error messages?
3. Did you see "EQUITY DEBUG" log lines?
4. Did the batch exit with error code or success?

---

### Step 2: Check Application Logs

**Files to Check**:
```bash
# Most recent logs
tail -1000 logs/sigmasight.log | grep -E "(Phase [1-6]|EQUITY DEBUG|ERROR|Exception|snapshot)"

# Check for Phase 3 completion
tail -1000 logs/sigmasight.log | grep "Phase 3"

# Check for snapshot creation attempts
tail -1000 logs/sigmasight.log | grep -i "snapshot"

# Check for exceptions
tail -1000 logs/sigmasight.log | grep -i "exception\|error" | tail -50
```

---

### Step 3: Check Snapshot Creation Logic

**File**: `backend/app/calculations/snapshots.py`

**Test**:
```python
# Run snapshot creation for one portfolio manually
import asyncio
from datetime import date
from uuid import UUID
from app.database import get_async_session
from app.calculations.snapshots import create_portfolio_snapshot

async def test():
    async with get_async_session() as db:
        result = await create_portfolio_snapshot(
            db=db,
            portfolio_id=UUID('demo-portfolio-id'),
            calculation_date=date(2025, 11, 6),
            skip_pnl_calculation=True,
            skip_provider_beta=False,
            skip_sector_analysis=False
        )
        print(f"Result: {result}")

        if result.get('success'):
            print("✅ Snapshot created successfully")
            snapshot = result.get('snapshot')
            print(f"Snapshot ID: {snapshot.id if snapshot else 'None'}")
        else:
            print(f"❌ Snapshot creation failed: {result.get('error')}")

asyncio.run(test())
```

---

### Step 4: Check Phase 6 (Analytics) Execution

**Evidence Needed**:
- Did Phase 6 start?
- Did it complete?
- Were analytics results calculated?

**Check**:
```python
import asyncio
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.correlations import CorrelationCalculation
from app.models.market_data import PositionFactorExposure

async def check_analytics():
    async with AsyncSessionLocal() as db:
        # Check correlations
        result = await db.execute(select(func.count(CorrelationCalculation.id)))
        corr_count = result.scalar()
        print(f"Correlation calculations: {corr_count}")

        # Check factor exposures
        result = await db.execute(select(func.count(PositionFactorExposure.id)))
        factor_count = result.scalar()
        print(f"Factor exposures: {factor_count}")

asyncio.run(check_analytics())
```

---

## Quick Fixes to Try

### Fix 1: Verify Batch Script Ran Correctly

**Check if script completed or exited early**:
```bash
echo $?  # Check exit code (0 = success, non-zero = error)
```

---

### Fix 2: Re-run with Verbose Logging

**Temporarily increase logging**:
```python
# In backend/app/core/logging.py
logging.basicConfig(level=logging.DEBUG)  # Change from INFO to DEBUG
```

**Then re-run batch** for single day:
```bash
uv run python scripts/batch_processing/run_batch.py \
  --start-date 2025-11-06 \
  --end-date 2025-11-06
```

---

### Fix 3: Test Single Portfolio Manually

**Isolate the problem**:
```python
import asyncio
from datetime import date
from uuid import UUID
from app.database import get_async_session
from app.batch.pnl_calculator import PnLCalculator

async def test_single_portfolio():
    async with get_async_session() as db:
        calc = PnLCalculator()

        # Get one portfolio ID
        from sqlalchemy import select
        from app.models.users import Portfolio

        result = await db.execute(select(Portfolio.id).limit(1))
        portfolio_id = result.scalar_one()

        print(f"Testing portfolio: {portfolio_id}")

        # Run P&L calculation
        success = await calc.calculate_portfolio_pnl(
            portfolio_id=portfolio_id,
            calculation_date=date(2025, 11, 6),
            db=db
        )

        print(f"Result: {success}")

        # Check if snapshot was created
        from app.models.snapshots import PortfolioSnapshot
        result = await db.execute(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.portfolio_id == portfolio_id,
                PortfolioSnapshot.snapshot_date == date(2025, 11, 6)
            )
        )
        snapshot = result.scalar_one_or_none()

        if snapshot:
            print(f"✅ Snapshot exists: {snapshot.id}")
            print(f"   Equity: ${snapshot.equity_balance}")
            print(f"   Daily P&L: ${snapshot.daily_pnl}")
        else:
            print("❌ No snapshot found!")

asyncio.run(test_single_portfolio())
```

---

## Code Review Findings

### Potential Issue 1: Exception Re-raising

**Location**: `backend/app/batch/pnl_calculator.py:242`

**Current Code**:
```python
except Exception as e:
    logger.error(f"Error updating equity for {portfolio_id}: {e}", exc_info=True)
    raise  # ⚠️ This stops ALL batch processing!
```

**Problem**: If ONE portfolio fails, the ENTIRE batch stops
**Impact**: If first portfolio had an error, remaining portfolios never processed

**Suggested Fix**:
```python
except Exception as e:
    logger.error(f"Error updating equity for {portfolio_id}: {e}", exc_info=True)
    # Don't raise for individual portfolio failures - continue with next
    return False  # Return failure but keep going
```

---

### Potential Issue 2: Snapshot Commit Timing

**Location**: `backend/app/batch/pnl_calculator.py:280-283`

**Current Code**:
```python
logger.info(f"  [EQUITY DEBUG] About to commit transaction...")
portfolio.equity_balance = new_equity
await db.commit()
logger.info(f"  [EQUITY DEBUG] ✅ TRANSACTION COMMITTED")
```

**Question**: Is snapshot committed BEFORE or AFTER this commit?

**Check**: `create_portfolio_snapshot()` adds snapshot to session but doesn't commit
**Result**: If exception after equity commit but before snapshot commit → equity persists, snapshot lost

---

## Recommended Action Plan

### Immediate (Tonight)

1. ✅ **Share batch command output** - What did you see in terminal?
2. ✅ **Check logs** - Run diagnostic grep commands above
3. ✅ **Test single portfolio** - Run manual test to isolate issue

### Short Term (Tomorrow)

4. ✅ **Fix exception handling** - Don't raise on individual portfolio failures
5. ✅ **Add snapshot validation** - Verify snapshots created before marking success
6. ✅ **Add phase completion logging** - Log "Phase X completed: Y snapshots created"

### Medium Term (This Week)

7. ✅ **Add rollback safety** - If snapshot fails, rollback equity update too
8. ✅ **Add data validation** - Check snapshot count matches portfolio count
9. ✅ **Add health checks** - Post-batch validation that verifies all expected data exists

---

## Questions for User

Please provide the following information:

1. **Batch Command**: What exact command did you run?
2. **Terminal Output**: Did you see any errors or "EQUITY DEBUG" messages?
3. **Date Range**: What --start-date and --end-date did you use?
4. **Exit Status**: Did the script exit successfully or with error?
5. **Log Messages**: Can you share the output of:
   ```bash
   tail -200 logs/sigmasight.log | grep -E "(Phase|EQUITY DEBUG|ERROR|Exception)"
   ```

---

## Success Criteria for Fix

When fixed, we should see:

✅ **Snapshots Created**: `select count(*) from portfolio_snapshots` > 0
✅ **P&L Data Populated**: snapshots have non-null daily_pnl values
✅ **Analytics Completed**: Volatility, stress tests, correlations calculated
✅ **Phase 6 Results**: Factor exposures, betas, sector analysis present
✅ **No Silent Failures**: All errors logged with full tracebacks

---

**Next Step**: Please share the batch command output and we'll pinpoint the exact failure point.
