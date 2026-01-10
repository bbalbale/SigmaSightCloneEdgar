# Testscotty Batch Processing Fix - Progress Tracker

**Started**: January 8, 2026
**Goal**: Fix batch processing bugs identified during Testscotty onboarding
**Working Branch**: main
**Remote Push**: ✅ Pushed to origin/main (January 8, 2026)

---

# 🤖 AGENT HANDOFF APPENDIX

> **For AI Coding Agents**: Start here. This section summarizes current state, how to verify, and what's left to do. Read this before diving into the detailed sections below.

**Last Updated**: January 9, 2026, 11:00 PM UTC
**Handoff From**: Claude Opus 4.5 session

---

## A1. Related Documentation (Cross-Links)

| Document | Purpose | Location |
|----------|---------|----------|
| **This File** | Progress tracker, phase details, timeline | `backend/_docs/TESTSCOTTY_PROGRESS.md` |
| **Session Summary** | Jan 8 investigation findings | `backend/_docs/SESSION_SUMMARY_BATCH_INVESTIGATION_JAN8.md` |
| **Batch Status UI Design** | Frontend UX spec for status display | `backend/_docs/TESTSCOTTY_BATCH_STATUS_UI.md` |
| **Issue #8 Code Review** | Factor exposure fix details | `backend/_docs/CODE_REVIEW_REQUEST_ISSUE8_FACTOR_EXPOSURE.md` |
| **Backend CLAUDE.md** | Overall backend reference | `backend/CLAUDE.md` |
| **Frontend CLAUDE.md** | Overall frontend reference | `frontend/CLAUDE.md` |

---

## A2. Current System State (as of 2026-01-09 23:00 UTC)

### Deployed to Railway (Production)

| Commit | Description | Deployed | Verified |
|--------|-------------|----------|----------|
| `4db1ad63` | Issue #8 fix: Add total_symbols key | ✅ Yes | ⏳ Pending |
| `fe1f2632` | Issue #8 fix: Signature mismatch + logging | ✅ Yes | ⏳ Pending |
| `4fd51be8` | AI agent verification instructions | ✅ Yes | N/A (docs) |
| `bbd87c79` | Batch status UI design doc | ✅ Yes | N/A (docs) |
| Phase 5 commits | Unified batch function | ✅ Yes | ✅ Verified (testscotty4) |
| Phase 6 commits | Error handling hardening | ✅ Yes | ✅ Verified (testscotty4) |

### Verification Still Needed

| Item | What to Check | Status |
|------|---------------|--------|
| **Issue #8 Factor Storage** | Re-run batch for testscotty5, verify 12+ factors stored | ⏳ **PENDING** |
| Stress testing | After Issue #8 fix, verify non-zero style factor impacts | ⏳ **PENDING** |
| Phase 7 frontend | Frontend integration for status UI | ❌ **NOT STARTED** |

### Known Good Reference Points

| Test | Portfolio | Date | Result |
|------|-----------|------|--------|
| testscotty4 batch | Scott Y 5M | 2026-01-08 | ✅ 254/254 dates, 27 symbols, 894s |
| testscotty5 batch | (verify ID) | 2026-01-09 | ✅ Snapshots OK, ❌ Factors need re-run |

---

## A3. Test Accounts Reference

| User | Email | Portfolio Name | Portfolio ID | Purpose | Current State |
|------|-------|----------------|--------------|---------|---------------|
| testscotty (original) | elliott.ng+testscotty@gmail.com | Yaphe 5M | `98518c7d-ea23-593b-aaed-9c0be7f3a66f` | Original test | Legacy |
| testscotty2 | elliott.ng+testscotty2@gmail.com | Yaphe 5M | `2ecdbdaf-468d-5484-98a1-26943635c829` | Phase 1 test | Blocked by stuck tracker |
| testscotty3 | (check DB) | (check DB) | (check DB) | Import path debug | Used for debugging |
| testscotty4 | (check DB) | Scott Y 5M | (check DB) | Phase 5/6 verification | ✅ **BASELINE** - use for regression |
| testscotty5 | (check DB) | (check DB) | (check DB) | Issue #8 verification | ⏳ Needs force rerun |

**To find portfolio IDs**:
```sql
SELECT u.email, p.id, p.name, p.created_at
FROM users u
JOIN portfolios p ON p.user_id = u.id
WHERE u.email ILIKE '%scotty%' OR p.name ILIKE '%yaphe%' OR p.name ILIKE '%scott%'
ORDER BY p.created_at DESC;
```

---

## A4. Outstanding Work Items (Prioritized)

### Priority 1 - Immediate Verification
| Task | Description | Blocked By |
|------|-------------|------------|
| **Verify Issue #8** | Re-run batch for testscotty5, check factors stored | Nothing - ready now |
| Check Railway logs | Look for "Stored X Ridge factors" messages | Issue #8 deployment |

### Priority 2 - Frontend Work
| Task | Description | Design Doc |
|------|-------------|------------|
| Phase 7 Frontend | Real-time status UI during onboarding | `TESTSCOTTY_BATCH_STATUS_UI.md` |
| Log download button | Download full activity log as txt | `TESTSCOTTY_BATCH_STATUS_UI.md` |

### Priority 3 - Deferred/Nice-to-Have
| Task | Description | Why Deferred |
|------|-------------|--------------|
| Phase 3 fire-and-forget | Await db writes properly | Superseded by Phase 6; only causes log warnings |
| Automated tests | Add tests for batch processing | Time constraints |

---

## A5. Environment & Credentials Runbook

### Railway Access

**Service Name**: `sigmasight-be-production`

**View Logs**:
```bash
# Tail live logs
railway logs -f

# Last 100 lines
railway logs -n 100

# Filter for batch processing
railway logs -n 500 | grep -i "batch\|phase\|factor"
```

**Run Python Script on Railway**:
```bash
railway run python -c "print('hello')"
```

### Trigger Batch Processing

**Option 1 - Admin API** (requires admin JWT):
```bash
# Single portfolio, force rerun
curl -X POST "https://sigmasight-be-production.up.railway.app/api/v1/admin/batch/run" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"portfolio_id": "<PORTFOLIO_ID>", "force_rerun": true}'
```

**Option 2 - Railway CLI**:
```bash
railway run python -c "
import asyncio
from app.batch.batch_orchestrator import batch_orchestrator

async def main():
    result = await batch_orchestrator.run_daily_batch_with_backfill(
        portfolio_id='<PORTFOLIO_ID>',
        source='manual',
        force_rerun=True
    )
    print(result)

asyncio.run(main())
"
```

**Option 3 - Local Development**:
```bash
cd backend
uv run python -c "
import asyncio
from app.batch.batch_orchestrator import batch_orchestrator

async def main():
    result = await batch_orchestrator.run_daily_batch_with_backfill(
        portfolio_id='<PORTFOLIO_ID>',
        source='manual',
        force_rerun=True
    )
    print(result)

asyncio.run(main())
"
```

### Database Queries for Verification

**Check factor exposures**:
```sql
SELECT factor_name, beta_value, calculation_date
FROM factor_exposures
WHERE portfolio_id = '<PORTFOLIO_ID>'
ORDER BY calculation_date DESC, factor_name
LIMIT 30;
```

**Count distinct factors** (should be 12+, not 3):
```sql
SELECT COUNT(DISTINCT factor_name) as factor_count
FROM factor_exposures
WHERE portfolio_id = '<PORTFOLIO_ID>';
```

**Check snapshots**:
```sql
SELECT snapshot_date, total_value
FROM portfolio_snapshots
WHERE portfolio_id = '<PORTFOLIO_ID>'
ORDER BY snapshot_date DESC
LIMIT 10;
```

**Check batch history**:
```sql
SELECT id, source, status, started_at, completed_at
FROM batch_run_history
ORDER BY started_at DESC
LIMIT 10;
```

---

## A6. Force Rerun / Recovery Runbook

### Symptom: Portfolio missing factor exposures

**Diagnosis**:
```sql
SELECT COUNT(DISTINCT factor_name) FROM factor_exposures WHERE portfolio_id = '<ID>';
-- If < 12, factors are missing
```

**Recovery**:
```bash
# Via Admin API
curl -X POST "https://sigmasight-be-production.up.railway.app/api/v1/admin/batch/run" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"portfolio_id": "<ID>", "force_rerun": true}'
```

**Verification**:
1. Check Railway logs for: `Stored X Ridge factors for portfolio <id>`
2. NO more: `"message":"Skipped: no_public_positions"`
3. Re-run factor count query - should be 12+

### Symptom: Batch stuck in "running" state

**Diagnosis**:
```sql
SELECT * FROM batch_run_history WHERE status = 'running' ORDER BY started_at DESC;
```

**Recovery**:
- Wait 30 minutes - system auto-expires stuck batches
- Or restart Railway service to clear in-memory tracker

### Symptom: Stress testing shows $0 for style factors

**Root Cause**: Issue #8 - factor exposures not stored

**Recovery**: Force rerun batch (see above), then re-test stress endpoint

---

## A7. Design Decisions & Tradeoffs

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| **Fix writer not reader** (Issue #8) | `total_symbols` semantically belongs in `data_quality` dict, single point of change | CODE_REVIEW_REQUEST_ISSUE8 |
| **In-memory status logs** | Only relevant during processing, fast reads, no DB overhead | Phase 7 design |
| **30-min batch timeout** | Longest normal batch ~15-20 min, gives buffer | Phase 4 |
| **Polling not SSE** | Simpler, proven pattern, 2s interval acceptable | Phase 7.1 |
| **Scoped symbol processing** | 44x fewer symbols for single-portfolio batches | Phase 5 |
| **MIN of MAX watermark** | Find most lagging portfolio, not just check if any is current | Phase 2 |
| **Deferred Phase 3** | Phase 6 ensures completion call made; fire-and-forget only causes log warnings | Phase 3 section |
| **force_rerun requires explicit flag** | Prevent accidental reprocessing, date params ignored without flag | `e0bea800` |

---

## A8. Quick Start for New Agent

### If asked to verify Issue #8:
1. Read "AI Agent Verification Instructions" section below
2. Trigger force rerun for testscotty5
3. Check logs for "Stored X Ridge factors"
4. Query factor_exposures table for 12+ factors

### If asked to implement Phase 7 frontend:
1. Read `TESTSCOTTY_BATCH_STATUS_UI.md`
2. Existing backend endpoint: `GET /api/v1/onboarding/status/{portfolio_id}`
3. New endpoint needed: `GET /api/v1/onboarding/status/{portfolio_id}/logs`
4. Follow component list in design doc

### If asked about batch processing issues:
1. Check batch_run_history table for status
2. Check Railway logs for errors
3. Use force_rerun to recover
4. See Runbook section above

---

## A9. The "Why" of the 9-Phase Architecture

### Phase Ordering & Data Dependencies

The batch processing phases **MUST** execute in order. Each phase depends on data produced by earlier phases.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BATCH PHASE DEPENDENCY GRAPH                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1: Market Data Collection                                            │
│      │                                                                      │
│      │ ─── produces: symbol_daily_prices, historical_prices                 │
│      ▼                                                                      │
│  Phase 1.5: Symbol Factors (Ridge/Spread Regression)                        │
│      │                                                                      │
│      │ ─── requires: historical_prices (from Phase 1)                       │
│      │ ─── produces: symbol_factor_exposures                                │
│      ▼                                                                      │
│  Phase 1.75: Symbol Metrics                                                 │
│      │                                                                      │
│      │ ─── requires: historical_prices (from Phase 1)                       │
│      │ ─── produces: symbol_returns, volatility_metrics                     │
│      ▼                                                                      │
│  Phase 2: Portfolio Snapshots                                               │
│      │                                                                      │
│      │ ─── requires: symbol_daily_prices (from Phase 1)                     │
│      │ ─── produces: portfolio_snapshots (daily NAV, P&L)                   │
│      ▼                                                                      │
│  Phase 2.5: Position Market Values                                          │
│      │                                                                      │
│      │ ─── requires: latest prices (from Phase 1)                           │
│      │ ─── produces: updated position.market_value                          │
│      ▼                                                                      │
│  Phase 3: Position Betas                                                    │
│      │                                                                      │
│      │ ─── requires: position.market_value (from Phase 2.5)                 │
│      │ ─── requires: historical_prices (from Phase 1)                       │
│      │ ─── produces: position_betas (market, IR)                            │
│      ▼                                                                      │
│  Phase 4: Factor Exposures                                                  │
│      │                                                                      │
│      │ ─── requires: symbol_factor_exposures (from Phase 1.5)               │
│      │ ─── requires: position weights (from Phase 2.5)                      │
│      │ ─── produces: portfolio_factor_exposures                             │
│      ▼                                                                      │
│  Phase 5: Volatility Analysis                                               │
│      │                                                                      │
│      │ ─── requires: symbol_returns (from Phase 1.75)                       │
│      │ ─── requires: portfolio_snapshots (from Phase 2)                     │
│      │ ─── produces: volatility_forecasts (HAR model)                       │
│      ▼                                                                      │
│  Phase 6: Correlations                                                      │
│                                                                             │
│      ─── requires: historical_prices (from Phase 1)                         │
│      ─── requires: position weights (from Phase 2.5)                        │
│      ─── produces: correlation_matrices (position & factor)                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why Parallelization Would Break Things

**Scenario: Run Phase 4 before Phase 1.5**
- Phase 4 aggregates `symbol_factor_exposures` to portfolio level
- If Phase 1.5 hasn't run, `symbol_factor_exposures` table is empty
- Result: Portfolio shows 0 factor exposure (wrong)

**Scenario: Run Phase 3 before Phase 2.5**
- Phase 3 calculates position betas using position weights
- Position weights = `market_value / portfolio_equity`
- If Phase 2.5 hasn't run, `market_value` is stale
- Result: Betas calculated with wrong weights (wrong)

**Scenario: Run Phase 2 before Phase 1**
- Phase 2 creates snapshots using daily prices
- If Phase 1 hasn't fetched prices, uses stale/missing data
- Result: Snapshots show incorrect portfolio values (wrong)

### Sub-Phase Naming Explained

| Phase | Why This Number? |
|-------|------------------|
| 1.5 | Runs after Phase 1 (prices), before Phase 2 (snapshots) |
| 1.75 | Runs after 1.5 (factors), before Phase 2 (needs returns) |
| 2.5 | Runs after Phase 2 (snapshots), before Phase 3 (needs updated values) |

The decimal naming indicates insertion points in the original 6-phase design when we discovered intermediate calculations were needed.

---

## A10. In-Memory vs. Persistent State Boundaries

### State Storage Locations

| State | Storage | Purpose | Lifetime |
|-------|---------|---------|----------|
| `batch_run_tracker` | In-memory (Python singleton) | Prevent concurrent batches, track progress | Until server restart |
| `batch_run_history` | Database (`batch_run_history` table) | Audit trail, historical batch records | Permanent |
| `status_messages` | In-memory (attached to tracker) | Real-time progress for frontend | Until batch completes |
| `activity_log` | In-memory (attached to tracker) | Debug/activity feed for frontend | Until batch completes |

### When State Moves from Memory to Database

```
┌─────────────────────────────────────────────────────────────────┐
│                      BATCH LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. batch_run_tracker.start()                                   │
│     └── In-memory: _running = True, _started_at = now()         │
│     └── Database: INSERT batch_run_history (status='running')   │
│                                                                 │
│  2. During processing (per date/phase)                          │
│     └── In-memory: status_messages.append(), activity_log.append()
│     └── Database: (nothing - too slow for tight loops)          │
│                                                                 │
│  3. batch_run_tracker.complete() or error handler               │
│     └── In-memory: _running = False, clear messages             │
│     └── Database: UPDATE batch_run_history (status='completed') │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### What Happens on Server Restart Mid-Batch

| Scenario | In-Memory State | Database State | Result |
|----------|-----------------|----------------|--------|
| Normal completion | Cleared by `complete()` | `status='completed'` | ✅ Correct |
| Server restart mid-batch | **LOST** (singleton reset) | `status='running'` (stuck) | ⚠️ Stale DB record |
| Startup cleanup runs | N/A | `status='failed'` (auto-fixed) | ✅ Self-healed |

**Key insight**: The in-memory tracker resets on restart, but the database record remains stuck. This is why we have:
1. **Startup cleanup** - Marks stale `running` records as `failed`
2. **30-minute timeout** - In-memory tracker auto-expires if running too long

### Frontend Polling Implications

The frontend polls `GET /api/v1/onboarding/status/{portfolio_id}` which reads from **in-memory tracker**.

**If server restarts during batch**:
- Tracker resets → endpoint returns `status: "not_found"`
- Frontend should handle this gracefully (show "Unknown state" or retry)
- User can manually re-trigger batch via force_rerun

**Design decision**: We accept losing progress bars on restart because:
1. Restarts are rare (deploys, OOM, crashes)
2. Adding DB writes for every status update would kill performance
3. The batch itself is idempotent - rerunning is safe

---

## A11. Scoped Mode Implementation Details

### How Symbol Scoping Works

When `portfolio_id` is provided, the batch fetches **only symbols in that portfolio** + factor ETFs, not the entire 1,193-symbol universe.

**Code location**: `batch_orchestrator.py` → `_get_symbols_for_batch()`

```python
async def _get_symbols_for_batch(
    self,
    db: AsyncSession,
    portfolio_id: Optional[str] = None,
    scoped_only: bool = False
) -> List[str]:
    """
    Get symbols to process.

    If scoped_only=True and portfolio_id provided:
        → Only portfolio's symbols + FACTOR_ETFS (~30 total)
    Else:
        → Entire symbol_universe table (~1,193 symbols)
    """
    if scoped_only and portfolio_id:
        # Get symbols from this portfolio's positions only
        position_symbols = await db.execute(
            select(distinct(Position.symbol))
            .where(Position.portfolio_id == portfolio_id)
            .where(Position.exit_date.is_(None))
        )
        symbols = [row[0] for row in position_symbols.fetchall()]

        # Add factor ETFs (needed for factor calculations)
        symbols.extend(FACTOR_ETFS)  # ~17 ETFs
        return list(set(symbols))
    else:
        # Full universe mode (cron job)
        universe = await db.execute(select(SymbolUniverse.symbol))
        return [row[0] for row in universe.fetchall()]
```

### When Scoped Mode is Used

| Entry Point | `portfolio_id` | `scoped_only` | Symbols Fetched |
|-------------|----------------|---------------|-----------------|
| Cron job (daily) | `None` | `False` | ~1,193 (full universe) |
| Onboarding | `"uuid"` | `True` | ~30 (portfolio + ETFs) |
| Admin force rerun | `"uuid"` | `True` | ~30 (portfolio + ETFs) |
| Admin full refresh | `None` | `False` | ~1,193 (full universe) |

### Adding a New Data Source (e.g., Crypto)

If you add a new data source, you **MUST** respect scoped mode:

```python
# ❌ WRONG - Ignores scoping, fetches everything
async def fetch_crypto_data():
    all_cryptos = await get_all_crypto_symbols()  # 10,000+ symbols
    for symbol in all_cryptos:
        await fetch_price(symbol)  # Re-introduces the "fetch everything" bug!

# ✅ CORRECT - Respects scoping
async def fetch_crypto_data(symbols: List[str]):
    # Only fetch for symbols passed from _get_symbols_for_batch()
    crypto_symbols = [s for s in symbols if is_crypto(s)]
    for symbol in crypto_symbols:
        await fetch_price(symbol)
```

**Rule**: Any new data collector must accept a `symbols` parameter and only process those symbols.

### Log Evidence of Scoped Mode

When scoped mode is active, you'll see:
```
INFO: Scoped mode: skipping cached universe (single-portfolio optimization)
INFO: Symbol universe for portfolio: 27 symbols
```

When full universe mode is active:
```
INFO: Loading full symbol universe: 1193 symbols
```

---

## A12. Operational Reset Procedures

### Clearing a Stuck BatchRunTracker (In-Memory)

**Symptom**: New batches fail with 409 Conflict, logs show "Batch already running"

**Option 1 - Wait for auto-expire** (preferred):
- Tracker auto-expires after 30 minutes
- Just wait and retry

**Option 2 - Restart Railway service**:
```bash
# Via Railway CLI
railway service restart

# Or via Railway dashboard: click "Restart" on service
```

**Option 3 - Force complete via admin endpoint** (if available):
```bash
curl -X POST "https://sigmasight-be-production.up.railway.app/api/v1/admin/batch/force-complete" \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

### Clearing Stuck Database Records

**Symptom**: `batch_run_history` shows stale `status='running'` records

**Option 1 - Server restart** (triggers startup cleanup):
- Startup hook marks stale records as `failed`

**Option 2 - Manual SQL update**:
```sql
-- Mark stuck batches as failed
UPDATE batch_run_history
SET status = 'failed',
    completed_at = NOW(),
    error_summary = '{"reason": "Manually cleared - stuck record"}'
WHERE status = 'running'
AND started_at < NOW() - INTERVAL '30 minutes';
```

### Wiping Portfolio Data for Clean Test Run

**Symptom**: Need to re-test onboarding from scratch

**Step 1 - Delete portfolio data** (keeps user):
```sql
-- Get portfolio ID first
SELECT id FROM portfolios WHERE name = 'Test Portfolio';

-- Delete in dependency order
DELETE FROM portfolio_snapshots WHERE portfolio_id = '<ID>';
DELETE FROM factor_exposures WHERE portfolio_id = '<ID>';
DELETE FROM correlation_calculations WHERE portfolio_id = '<ID>';
DELETE FROM position_factor_exposures WHERE position_id IN (
    SELECT id FROM positions WHERE portfolio_id = '<ID>'
);
DELETE FROM position_greeks WHERE position_id IN (
    SELECT id FROM positions WHERE portfolio_id = '<ID>'
);
DELETE FROM position_tags WHERE position_id IN (
    SELECT id FROM positions WHERE portfolio_id = '<ID>'
);
DELETE FROM target_prices WHERE position_id IN (
    SELECT id FROM positions WHERE portfolio_id = '<ID>'
);
DELETE FROM positions WHERE portfolio_id = '<ID>';
DELETE FROM portfolios WHERE id = '<ID>';
```

**Step 2 - Re-create via onboarding**:
- Log out and log back in as test user
- Upload CSV again to trigger onboarding flow

### Full Environment Reset (Nuclear Option)

**⚠️ WARNING: Destroys ALL data**

```bash
# Local development only
cd backend
python scripts/database/reset_and_seed.py reset

# This will:
# 1. Drop all tables
# 2. Re-run migrations
# 3. Seed demo data (3 portfolios, 63 positions)
```

**For Railway**: Do NOT run this. Instead:
1. Create new test user via sign-up
2. Delete individual test portfolios as needed
3. Use force_rerun to re-process

### Quick Reference: Common Reset Scenarios

| Scenario | Action |
|----------|--------|
| Batch stuck, need to run new batch | Wait 30 min OR restart Railway service |
| Portfolio missing factors | Force rerun with `force_rerun=true` |
| Need fresh test portfolio | Delete via SQL, re-upload CSV |
| Stuck `running` DB record | Restart service OR manual SQL update |
| Complete local reset | `reset_and_seed.py reset` |

---

*End of Agent Handoff Appendix. Detailed progress tracking continues below.*

---

## Executive Summary (For Non-Engineers)

### What Happened
When Scott tested the new portfolio onboarding flow ("Testscotty"), we discovered several bugs in the batch processing system that prevented portfolios from getting their analytics calculated properly. Some portfolios were stuck days behind, onboarding was taking 4+ hours instead of minutes, and the system couldn't recover from crashes without manual intervention.

### What We Fixed

| Problem | Impact | Solution | Result |
|---------|--------|----------|--------|
| **Onboarding processed ALL 1,193 symbols** instead of just the portfolio's ~30 symbols | 4+ hour processing time, API rate limits hit | Scoped processing to only portfolio symbols | **~15 minutes** (16x faster) |
| **11 portfolios stuck 2 days behind** | Cron job saw one current portfolio and skipped the rest | Changed to find the "most behind" portfolio and catch everyone up | All portfolios now stay current |
| **Crashes left system stuck** | No new batches could run until manual server restart | Added automatic timeout and cleanup | System self-heals within 30 minutes |
| **No visibility into processing** | Users saw fake progress animation | Planned: Real status updates with debug mode | Not yet implemented |

### Business Impact

- **User Experience**: New portfolios now fully process in ~15 minutes instead of 4+ hours
- **Reliability**: System automatically recovers from crashes - no manual restarts needed
- **Data Accuracy**: All portfolios stay current, not just the most recently updated one
- **Operational**: Admin can force-reprocess any date range to fix partial runs

### What's Still To Do

1. **Phase 7**: Real-time status updates during onboarding with debug mode (nice to have)

### Deferred (Low Priority)

1. **Phase 3**: Fix "fire-and-forget" database writes - superseded by Phase 6, only causes log warnings

### Key Commits Deployed

All changes are live on Railway:
- `98f97246` - Phase 2: Global watermark bug fix (hybrid approach)
- `058ed9f5` - Force rerun mode for repairing partial batches
- `f20202ba` - Critical fix: pass force_rerun to _execute_batch_phases
- `686f4ac2` - Admin batch tracker cleanup and single-date default
- `e0bea800` - Reject date params without force_rerun (prevent silent ignore)

### Verification

Tested with "testscotty4" (Scott Y 5M) portfolio:
- ✅ 254 trading days processed successfully
- ✅ Only 27 symbols fetched (not 1,193)
- ✅ Completed in 894 seconds (~15 minutes)
- ✅ All analytics calculated correctly

---

## Current Status

| Phase | Description | Status | Verified on Railway |
|-------|-------------|--------|---------------------|
| 1 | Fix Phase 1.5 Skipping | ✅ IMPLEMENTED | Pending |
| 2 | Fix Global Watermark Bug (Hybrid) | ✅ IMPLEMENTED | Pending |
| 3 | Fix Fire-and-Forget Tasks | ⏸️ DEFERRED | - |
| 4 | Add batch_run_tracker Timeout & Cleanup | ✅ DONE (earlier) | - |
| 5 | Unify Batch Functions (REFACTOR) | ✅ IMPLEMENTED | ✅ VERIFIED |
| 6 | Harden batch_run_history Error Handling | ✅ IMPLEMENTED | ✅ VERIFIED |
| 7 | Real-Time Onboarding Status Updates | ✅ BACKEND DONE | Frontend pending |
| 7.1 | Onboarding Status API Endpoint | ✅ IMPLEMENTED | ✅ Pushed to origin |
| 7.2 | Onboarding Flow: Invite Code Gate | ✅ IMPLEMENTED | Pending push |
| 8 | Fix Factor Exposure Storage Bug | ✅ IMPLEMENTED | Pending verification |

---

### Issue #8: Factor Exposure Storage Bug (January 9, 2026)

**Status**: ✅ **BOTH BUGS FIXED** - Pending Railway verification

**Code Reviews Received**:
- **Gemini**: Verified & Approved (recommended logging enhancement, naming consistency check)
- **Codex**: Identified second bug (signature mismatch) that initial fix missed

**Discovery**: Found during investigation of stress testing warnings showing "No exposure found for shocked factor" for Value, Growth, Momentum, Size, Quality, and Low Volatility factors.

**Symptoms**:
- Stress testing shows: `No exposure found for shocked factor: Value (mapped to Value)`
- Only 3 factors available instead of 12+ expected
- Logs show: `[FALLBACK] No complete snapshot found, trying any available factors`
- Logs show: `[COMPLETE] Total factors after adding snapshot betas: 3`
- Railway telemetry shows: `"name":"Ridge Factors","success":true,"message":"Skipped: no_public_positions"`

**Root Cause #1**: Key name mismatch between `analytics_runner.py` and `portfolio_factor_service.py`

**The Bug**:

`analytics_runner.py` (line 572) looks for `total_symbols` in `data_quality`:
```python
# _calculate_ridge_factors() and _calculate_spread_factors()
data_quality = symbol_result.get('data_quality', {})
total_symbols = data_quality.get('total_symbols', 0)  # ← Looks for 'total_symbols'

# Handle PRIVATE-only portfolios (no public positions)
if total_symbols == 0:  # ← Always TRUE because key doesn't exist!
    return {
        'success': True,
        'message': 'Skipped: no_public_positions'  # ← This is what Railway logs show
    }
```

But `portfolio_factor_service.py` (lines 254-264) puts symbol count in `metadata`, not `data_quality`:
```python
# get_portfolio_factor_exposures() returns:
results = {
    'metadata': {
        'unique_symbols': len(symbols),  # ← Symbol count is HERE
    },
    'data_quality': {
        'symbols_with_ridge': 0,
        'symbols_with_spread': 0,
        'symbols_missing': 0
        # ← 'total_symbols' DOES NOT EXIST HERE!
    }
}
```

**What happens**:
1. `get_portfolio_factor_exposures()` returns symbol count in `metadata.unique_symbols`
2. `analytics_runner.py` looks for `data_quality.total_symbols` which doesn't exist
3. `data_quality.get('total_symbols', 0)` returns default value `0`
4. `if total_symbols == 0:` evaluates to TRUE even when portfolio has 13 PUBLIC positions
5. Returns `"Skipped: no_public_positions"` and exits early
6. `store_portfolio_factor_exposures()` is never called
7. Ridge/Spread factors never stored to `FactorExposure` table
8. Stress testing finds no factor exposures

**Root Cause #2**: Incorrect call signature when persisting factor exposures

Even when the code reaches the storage step, `analytics_runner._calculate_ridge_factors()` and `_calculate_spread_factors()` call `store_portfolio_factor_exposures()` with keyword arguments that do not exist (`ridge_betas`, `spread_betas`) and omit the required `portfolio_betas` + `portfolio_equity` parameters:

```python
await store_portfolio_factor_exposures(
    db=db,
    portfolio_id=portfolio_id,
    calculation_date=calculation_date,
    ridge_betas=ridge_betas,
    spread_betas={}
)
```

The actual signature (portfolio_factor_service.py lines 312-317) expects:

```python
async def store_portfolio_factor_exposures(
    db: AsyncSession,
    portfolio_id: UUID,
    portfolio_betas: Dict[str, float],
    calculation_date: date,
    portfolio_equity: float
)
```

Python raises `TypeError: got an unexpected keyword argument 'ridge_betas'`, which is swallowed by the surrounding `except Exception`. Result: ridge/spread rows are never persisted even when symbol coverage is fine. Market/IR beta still appear because they use separate helper functions.

**Fix Plan**:
1. Fix the data-quality contract: either populate `data_quality['total_symbols'] = len(symbols)` or update `analytics_runner` to read `metadata['unique_symbols']`.
2. Refactor the storage call to pass a combined `portfolio_betas` dict and the `portfolio_equity` value returned by `get_portfolio_factor_exposures()`.

**Evidence from Railway Logs** (testscotty5 batch - January 9, 2026):
```
telemetry {"name":"Ridge Factors","success":true,"message":"Skipped: no_public_positions"}
telemetry {"name":"Spread Factors","success":true,"message":"Skipped: no_public_positions"}
```
This repeats for every calculation date - factors are never stored.

**Why Market Beta and IR Beta work**: They use separate code paths (`run_provider_beta_job` and `run_interest_rate_beta_job`) that don't rely on `data_quality.total_symbols`.

**Impact**:
- Ridge factors (Value, Growth, Momentum, Quality, Size, Low Volatility) never stored
- Spread factors (Growth-Value, Momentum, Size, Quality spreads) never stored
- Stress test scenarios show $0 impact for style factors
- Affects ALL portfolios, not just new ones

**Files Modified**:
| File | Line | Change Made |
|------|------|-------------|
| `app/services/portfolio_factor_service.py` | 261, 466 | ✅ Added `'total_symbols': len(symbols)` to `data_quality` dict |
| `app/batch/analytics_runner.py` | 595-600 | ✅ Fixed Ridge factors call: `portfolio_betas=ridge_betas`, added `portfolio_equity` |
| `app/batch/analytics_runner.py` | 674-679 | ✅ Fixed Spread factors call: `portfolio_betas=spread_betas`, added `portfolio_equity` |
| `app/batch/analytics_runner.py` | 603, 681 | ✅ Changed logger.debug to logger.info for operational visibility |

**Fix** (Option 1 - Add missing key):
```python
# portfolio_factor_service.py line 260-264
'data_quality': {
    'total_symbols': len(symbols),  # ← ADD THIS LINE
    'symbols_with_ridge': 0,
    'symbols_with_spread': 0,
    'symbols_missing': 0
}
```

**Fix** (Option 2 - Read from correct location in analytics_runner.py):
```python
# analytics_runner.py line 571-572
metadata = symbol_result.get('metadata', {})
total_symbols = metadata.get('unique_symbols', 0)  # ← Change to read from metadata
```

**Recommended**: Option 1 (add the missing key) is cleaner - the key name `total_symbols` in `data_quality` is semantically correct.

**Verification Steps After Fix**:
1. Deploy fix to Railway
2. Re-run batch for testscotty5 portfolio
3. Check Railway logs for:
   - NO more `"Skipped: no_public_positions"` for Ridge/Spread Factors
   - Telemetry showing `"success":true` with actual factor storage
4. Query `FactorExposure` table to confirm 12+ factors stored (not just 3)
5. Verify stress testing shows non-zero impacts for style factors

**Verification** (testscotty5 - January 9, 2026):
- ✅ Snapshots current (2026-01-09, 254 trading days)
- ✅ Batch completed successfully (686s)
- ❌ Only 3 factors available (should be 12+)
- ❌ Ridge/Spread factors skipped with "no_public_positions" (false positive)
- ❌ Stress testing missing factor impacts

---

## 🤖 AI Agent Verification Instructions (Issue #8)

**Status**: Fix deployed to Railway, awaiting verification
**Commits**: `4db1ad63`, `fe1f2632`
**Date**: January 9, 2026

### What Was Fixed

Two bugs were preventing Ridge/Spread factor storage:
1. **Bug #1**: Missing `total_symbols` key in `data_quality` dict caused false "no_public_positions" skip
2. **Bug #2**: Function signature mismatch - `store_portfolio_factor_exposures()` was called with wrong kwargs

### Step-by-Step Verification

#### Step 1: Trigger Batch Re-run for testscotty5

Option A - Via Railway CLI:
```bash
railway run python -c "
import asyncio
from app.batch.batch_orchestrator import batch_orchestrator

async def main():
    result = await batch_orchestrator.run_daily_batch_with_backfill(
        portfolio_id='<TESTSCOTTY5_PORTFOLIO_ID>',
        source='manual',
        force_rerun=True
    )
    print(result)

asyncio.run(main())
"
```

Option B - Via Admin API (if available):
```bash
curl -X POST "https://sigmasight-be-production.up.railway.app/api/v1/admin/batch/run" \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"portfolio_id": "<TESTSCOTTY5_PORTFOLIO_ID>", "force_rerun": true}'
```

#### Step 2: Check Railway Logs

**SUCCESS indicators** (what you SHOULD see):
```
Stored 6 Ridge factors for portfolio <id> (X/Y symbols)
Stored 4 Spread factors for portfolio <id> (X/Y symbols)
```

**FAILURE indicators** (what you should NOT see anymore):
```
"message":"Skipped: no_public_positions"
```

#### Step 3: Query Database for Factor Count

Run this query to verify factors are stored:
```sql
SELECT
    factor_name,
    beta_value,
    calculation_date
FROM factor_exposures
WHERE portfolio_id = '<TESTSCOTTY5_PORTFOLIO_ID>'
ORDER BY calculation_date DESC, factor_name
LIMIT 20;
```

**Expected**: 12+ distinct factor names including:
- Value, Growth, Momentum, Quality, Size, Low_Volatility (Ridge factors)
- Growth_Value_Spread, Momentum_Spread, Size_Spread, Quality_Spread (Spread factors)
- Market_Beta, IR_Beta (these already worked)

**Previous (broken)**: Only 3 factors (Market_Beta, IR_Beta, one other)

#### Step 4: Test Stress Testing Endpoint

```bash
curl "https://sigmasight-be-production.up.railway.app/api/v1/analytics/portfolio/<TESTSCOTTY5_PORTFOLIO_ID>/stress-test" \
  -H "Authorization: Bearer <TOKEN>"
```

**Expected**: Non-zero `impact` values for style factors like Value, Growth, Momentum

**Previous (broken)**: `"No exposure found for shocked factor: Value"`

### Success Criteria Checklist

- [ ] Batch completes without "Skipped: no_public_positions" for Ridge/Spread
- [ ] Railway logs show "Stored X Ridge factors" and "Stored X Spread factors"
- [ ] Database query returns 12+ distinct factor names (not just 3)
- [ ] Stress test endpoint returns non-zero impacts for style factors

### If Verification Fails

1. Check Railway logs for any new error messages
2. Look for TypeError or other exceptions in the except blocks
3. Report findings back with specific error messages

### Portfolio IDs for Reference

To find testscotty5 portfolio ID:
```sql
SELECT id, name, created_at
FROM portfolios
WHERE name ILIKE '%scotty%' OR name ILIKE '%yaphe%'
ORDER BY created_at DESC;
```

---

### Phase 5 Details (January 8, 2026)

**Commits (pushed to origin/main)**:
- `337e7d39` - docs: Add Phase 5 detailed implementation plan
- `3ae56503` - feat: Implement Phase 5 unified batch function with symbol scoping
- `ffb68fa1` - docs: Add code review request for Phase 5
- `a020f1ca` - fix: Address code review findings (tracker cleanup, history timing, source default)

**Key Changes**:
- Unified `run_daily_batch_with_backfill()` with `portfolio_id` and `source` params
- Added `scoped_only` mode for single-portfolio batches (~40x faster)
- `run_portfolio_onboarding_backfill()` now wraps unified function with try/finally
- Fixed: batch_run_tracker.complete() always called (prevents stuck UI)
- Fixed: record_batch_start() only after confirming work exists
- Fixed: source param defaults to None (preserves manual detection)

**Railway Verification (January 8, 2026 - testscotty4 "Scott Y 5M")**:
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Symbols processed | 1,193 | 27 | **44x fewer** |
| Runtime | 4+ hours | 894s (~15 min) | **~16x faster** |
| Dates processed | N/A | 254/254 | **100% success** |

**Key Log Evidence**:
- `Scoped mode: skipping cached universe (single-portfolio optimization)`
- `Symbol universe for portfolio: 27 symbols`
- `Backfill complete: 254/254 dates in 894s`

### Phase 6 Details (January 8, 2026)

**Commits (pushed to origin/main)**:
- `be0c7052` - docs: Add Phase 6 for batch_run_history error handling hardening
- `9963c9af` - feat: Implement Phase 6 try/except/finally implementation
- `f82496d7` - fix: Catch asyncio.CancelledError for deployment/restart handling
- `5749f64a` - fix: Track actual progress for accurate crash reporting
- `1357bd7b` - fix: Update progress tracker only after commit succeeds

**Problem Solved**:
The `batch_run_history` database table could have rows stuck in "running" status forever if:
- Server crashes (OOM, timeout, unhandled exception)
- Process killed during batch execution
- Any uncaught exception between `record_batch_start()` and `record_batch_complete()`

This is separate from the in-memory `batch_run_tracker` (fixed in Phase 5) - this is about the **persistent database record**.

**Solution**:
Wrapped all batch processing in `run_daily_batch_with_backfill()` with try/except:
1. Extracted processing logic into new `_execute_batch_phases()` method
2. On success: `record_batch_complete()` called with status="completed"
3. On exception: `record_batch_complete()` called with status="failed" before re-raising
4. Catches both `Exception` AND `asyncio.CancelledError` (inherits from BaseException)
5. Progress tracker accurately reports completed/failed dates even on crash

**Key Code** (batch_orchestrator.py lines 254-297):
```python
# Progress tracker: Mutable dict updated by _execute_batch_phases()
progress = {"completed": 0, "failed": 0}

try:
    return await self._execute_batch_phases(
        missing_dates=missing_dates,
        progress=progress,
        ...
    )
except (Exception, asyncio.CancelledError) as e:
    logger.error(f"Batch failed with exception: {e}")
    completed = progress["completed"]
    failed = len(missing_dates) - completed
    record_batch_complete(
        batch_run_id=batch_run_id,
        status="failed",
        completed_jobs=completed,
        failed_jobs=failed,
        error_summary={"exception": str(e), "type": type(e).__name__, "crashed_after_dates": completed},
    )
    raise  # Re-raise so caller knows batch failed
```

**Code Review Improvements**:
1. `asyncio.CancelledError` handling for SIGTERM/deployment restarts
2. Accurate progress tracking (not hardcoded to 0/total)
3. Progress updated AFTER `db.commit()` succeeds (not before)

**Impact**:
- Admin dashboard will never show phantom "running" batches
- Crashed batches now properly marked as "failed" with error details
- Better debugging: can distinguish running vs crashed batches
- Accurate crash reporting shows how many dates completed before failure

**Railway Verification (January 8, 2026)**:
- Batch completed successfully: 254/254 dates
- No stuck "running" status observed
- Phase 6 analytics executed for all dates

### Phase 7: Real-Time Onboarding Status Updates (January 8, 2026)

**Problem Statement**:
The current onboarding progress screen shows a fake animation through conceptual steps that don't reflect actual batch processing. With batch processing now taking ~15 minutes (down from 4+ hours after Phase 5), users still see a misleading progress UI. We want transparent, real-time status updates showing what's actually happening.

**Goals**:
1. Replace fake animation with real batch processing status
2. Two display modes: **User Mode** (friendly) and **Debug Mode** (technical)
3. Show actual phases and sub-phases as they execute
4. Per-symbol granularity for detailed progress tracking

**Scope**: Onboarding flow only (not admin batch triggers or cron jobs)

---

#### Design Decisions

**State Storage**: Extend `batch_run_tracker` (in-memory)
- Already tracks batch running state
- No database changes needed
- Fast reads/writes
- Status only relevant during processing (lost on restart is fine)

**Transport**: Polling (simplest)
- Frontend polls new endpoint periodically
- Already proven pattern with `/admin/batch/run/current`

**Endpoint**: New dedicated endpoint
- `GET /api/v1/onboarding/status/{portfolio_id}?debug=false`
- Tailored for onboarding UX (not mixed with admin concerns)
- RESTful (status is per-portfolio)

---

#### Two Display Modes

**User Mode** (default: `?debug=false`):
- Current phase name + friendly description
- Progress bar/percentage (e.g., "45% complete")
- Dates processed count (e.g., "120/254 dates")
- Elapsed time (e.g., "Running for 3m 42s")
- Estimated time remaining (based on current rate)
- All phases/steps printed and staying on screen (not just current)
- Technical details + timing per phase (e.g., "Phase 1: 45s")
- Error summaries if any occur

**Debug Mode** (`?debug=true`):
- Everything from User Mode, plus:
- Scrollable log window for verbose output
- Filtered log lines (remove Clerk auth, duplicates, noise)
- Per-symbol processing details
- Timing breakdowns per sub-phase
- Warning/error details that User Mode hides

**Mode Toggle**: Frontend button to switch between modes

---

#### Status Message Structure

```python
# In batch_run_tracker.py
@dataclass
class StatusMessage:
    timestamp: datetime
    phase: str              # "phase_1", "phase_1.5", "phase_2", etc.
    phase_name: str         # "Market Data Collection"
    message: str            # User-friendly: "Fetching historical prices..."
    detail: Optional[str]   # Debug: "AAPL: 254 days fetched in 0.3s"
    level: str              # "info", "warning", "error"
    progress: Optional[dict] # {"current": 15, "total": 27, "unit": "symbols"}

# Example status messages during processing:
{"phase": "phase_1", "phase_name": "Market Data Collection",
 "message": "Fetching historical prices...",
 "detail": "Processing AAPL (1/27)",
 "progress": {"current": 1, "total": 27, "unit": "symbols"}}

{"phase": "phase_1.5", "phase_name": "Symbol Factors",
 "message": "Calculating factor exposures...",
 "detail": "Ridge regression for 27 symbols",
 "progress": {"current": 0, "total": 27, "unit": "symbols"}}

{"phase": "phase_2", "phase_name": "Portfolio Snapshots",
 "message": "Creating daily snapshots...",
 "detail": "Processing 2025-03-15 (120/254)",
 "progress": {"current": 120, "total": 254, "unit": "dates"}}
```

---

#### API Response Schema

```python
# GET /api/v1/onboarding/status/{portfolio_id}?debug=false
{
    "portfolio_id": "uuid",
    "status": "running" | "completed" | "failed" | "not_found",
    "started_at": "2026-01-08T12:00:00Z",
    "elapsed_seconds": 223,
    "estimated_remaining_seconds": 450,  # null if can't estimate

    # Overall progress
    "overall_progress": {
        "current_phase": "phase_2",
        "current_phase_name": "Portfolio Snapshots",
        "phases_completed": 2,
        "phases_total": 6,
        "percent_complete": 45
    },

    # Current phase detail
    "current_phase_progress": {
        "current": 120,
        "total": 254,
        "unit": "dates",
        "message": "Creating daily snapshots..."
    },

    # All status messages (User Mode: condensed, Debug Mode: full)
    "messages": [
        {
            "timestamp": "2026-01-08T12:00:05Z",
            "phase": "phase_1",
            "phase_name": "Market Data Collection",
            "message": "Fetching historical prices...",
            "detail": "Completed in 45s (27 symbols)",  # Only in debug mode
            "level": "info"
        },
        ...
    ],

    # Only in debug mode
    "debug_logs": [
        "2026-01-08 12:00:05 - Fetching AAPL: 254 days",
        "2026-01-08 12:00:05 - Fetching MSFT: 254 days",
        ...
    ]
}
```

---

#### Implementation Plan

**Backend Changes**:

1. **Extend `batch_run_tracker.py`**:
   - Add `status_messages: List[StatusMessage]` to tracker
   - Add `add_status(phase, message, detail, progress)` method
   - Add `get_status_for_portfolio(portfolio_id)` method
   - Cap messages at ~200 to prevent memory growth

2. **Add status calls to `batch_orchestrator.py`**:
   - Add status updates at start/end of each phase
   - Add per-symbol/per-date progress updates
   - Track timing per phase for estimates

3. **New endpoint `app/api/v1/onboarding_status.py`**:
   - `GET /api/v1/onboarding/status/{portfolio_id}`
   - Query param `?debug=true|false` (default: false)
   - Returns filtered messages based on mode
   - Include progress calculations and time estimates

**Frontend Changes**:

1. **Update onboarding progress component**:
   - Replace fake animation with polling-based real status
   - Poll every 2-3 seconds during processing
   - Show phase list with checkmarks for completed phases
   - Progress bar for current phase

2. **Add debug mode toggle**:
   - Button/switch in UI to toggle debug mode
   - Debug mode: scrollable log window with filtered output
   - Persist preference in localStorage

3. **Handle edge cases**:
   - Status not found (batch not started yet)
   - Batch completed (show success state)
   - Batch failed (show error details)

---

#### Batch Processing Phases to Report

| Phase | Name | User Message | Progress Unit |
|-------|------|--------------|---------------|
| phase_1 | Market Data Collection | "Fetching historical prices..." | symbols |
| phase_1.5 | Symbol Factors | "Calculating factor exposures..." | symbols |
| phase_1.75 | Symbol Metrics | "Computing symbol metrics..." | symbols |
| phase_2 | Portfolio Snapshots | "Creating daily snapshots..." | dates |
| phase_2.5 | Position Market Values | "Updating position values..." | positions |
| phase_3 | Betas | "Calculating position betas..." | positions |
| phase_4 | Factor Exposures | "Computing factor exposures..." | positions |
| phase_5 | Volatility | "Analyzing volatility..." | positions |
| phase_6 | Correlations | "Building correlation matrix..." | N/A |

---

#### Files to Modify

| File | Changes |
|------|---------|
| `backend/app/batch/batch_run_tracker.py` | Add StatusMessage dataclass, status_messages list, helper methods |
| `backend/app/batch/batch_orchestrator.py` | Add status update calls throughout processing |
| `backend/app/api/v1/onboarding_status.py` | NEW: Status endpoint for onboarding |
| `backend/app/api/v1/router.py` | Register new endpoint |
| `frontend/src/components/onboarding/...` | Update progress UI (TBD) |

---

#### Debug Mode Log Filtering

**Include** (in debug mode):
- Phase start/complete messages
- Per-symbol/date processing
- Timing information
- Warnings and errors
- API call summaries

**Exclude** (filter out):
- Clerk authentication logs
- Duplicate consecutive messages
- Low-level database session logs
- Health check logs
- Routine HTTP request logs

---

#### Success Criteria

- [ ] User sees real phase names during onboarding
- [ ] Progress bar reflects actual completion percentage
- [ ] Per-symbol updates visible in debug mode
- [ ] Elapsed time and estimate displayed
- [ ] Debug mode shows filtered technical logs
- [ ] Status endpoint returns accurate data
- [ ] Frontend polls and updates smoothly (no flicker)
- [ ] Completed state shows success with summary

---

### Phase 7.1: Onboarding Wait Experience UX Design (REVISED)

**Added**: January 9, 2026
**Revised**: January 9, 2026 - Simplified to show real-time activity logs
**Implemented**: January 9, 2026 - Backend complete, frontend integration pending
**Context**: Users wait ~15 minutes for batch processing. Show actual progress with streaming log activity.

---

#### Problem Discovered (2026-01-09)

During Universe Test Alpha batch processing, the frontend showed **"authorization failed"** when trying to check status. Investigation revealed:

1. **Root cause**: Frontend was polling admin-only endpoint `/api/v1/admin/batch/run/current`
2. **Why it failed**: Regular users don't have admin credentials
3. **Secondary issue**: JWT token likely expired during 1.5+ hour batch run

**Solution implemented**: New endpoint `GET /api/v1/onboarding/status/{portfolio_id}` that:
- Uses regular Clerk JWT (NOT admin-only)
- Verifies user owns the portfolio
- Returns real-time activity log and phase progress

---

#### Core Design Principle

**Show the work as it happens.** Instead of separate "user mode" and "debug mode", display a filtered stream of useful log entries in real-time. Users see phases progress AND the actual activity happening within each phase.

---

#### Onboarding Status Screen Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   🚀 Setting Up Your Portfolio                                  │
│                                                                 │
│   Analyzing 254 trading days for 20 positions.                  │
│   This typically takes 15-20 minutes.                           │
│                                                                 │
│   ════════════════════════════════════════════════════════════  │
│                                                                 │
│   ✅ Phase 1: Market Data Collection                    45s     │
│   ✅ Phase 2: Factor Analysis                           12s     │
│   🔄 Phase 3: Portfolio Snapshots                    3m 24s     │
│      ████████████████░░░░░░░░░░░░░░  142/254 dates              │
│   ⏳ Phase 4: Position Betas                                    │
│   ⏳ Phase 5: Correlations                                      │
│   ⏳ Phase 6: Final Calculations                                │
│                                                                 │
│   ════════════════════════════════════════════════════════════  │
│                                                                 │
│   📋 Activity                                                   │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │ Fetched AAPL: 254 days of history                       │   │
│   │ Fetched MSFT: 254 days of history                       │   │
│   │ ⚠️ HZNP: Symbol unavailable (delisted)                  │   │
│   │ ⚠️ SGEN: Symbol unavailable (delisted)                  │   │
│   │ Phase 1 complete: 18/20 symbols (90% coverage)          │   │
│   │ Calculating factor exposures for 18 symbols...          │   │
│   │ Phase 2 complete: Factor analysis done                  │   │
│   │ Creating snapshot for 2024-01-02... (1/254)             │   │
│   │ Creating snapshot for 2024-01-03... (2/254)             │   │
│   │ Creating snapshot for 2024-01-04... (3/254)             │   │
│   │ ... ← auto-scrolls, shows last ~10 entries              │   │
│   │ Creating snapshot for 2024-06-15... (142/254)           │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   ⏱️  Elapsed: 4m 21s    📊 Overall: 45% complete               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Key differences from original design:**
- Activity log is **always visible** (no toggle needed)
- Log entries stream in real-time as processing happens
- Auto-scrolls to show latest activity
- Shows last ~10 entries (older entries scroll away)
- Warnings (⚠️) displayed inline with activity

---

#### Phase Display States

| State | Icon | Color | Description |
|-------|------|-------|-------------|
| Pending | ⏳ | Gray | Not started yet |
| Running | 🔄 | Blue | Currently executing (with spinner) |
| Completed | ✅ | Green | Finished successfully |
| Warning | ⚠️ | Yellow | Completed with issues (shown in activity log) |
| Failed | ❌ | Red | Phase failed (rare - system continues anyway) |

---

#### Activity Log Entry Types

**Include (filter IN):**
| Entry Type | Example | When Shown |
|------------|---------|------------|
| Symbol fetch success | "Fetched AAPL: 254 days of history" | Phase 1 |
| Symbol unavailable | "⚠️ HZNP: Symbol unavailable (delisted)" | Phase 1 |
| Phase complete | "Phase 1 complete: 18/20 symbols (90%)" | End of each phase |
| Date processing | "Creating snapshot for 2024-01-02... (1/254)" | Phase 2 (every 5th date) |
| Calculation milestone | "Calculating betas for 18 positions..." | Phases 3-6 |

**Exclude (filter OUT):**
| Entry Type | Reason |
|------------|--------|
| Individual date processing (1-4 of 5) | Too noisy - show every 5th |
| HTTP request logs | Technical noise |
| Database session logs | Internal detail |
| Auth/token logs | Security, irrelevant |
| Duplicate consecutive messages | Redundant |

**Sampling Strategy for Phase 2:**
- Phase 2 processes 254 dates, showing each would flood the log
- Show every 5th date: 1, 5, 10, 15... (plus milestones: 50, 100, 150, 200, 250)
- Always show first and last date

---

#### User-Friendly Phase Names

| Internal Phase | User-Facing Name | Completed Summary |
|----------------|------------------|-------------------|
| phase_1 | Market Data Collection | "{n}/{total} symbols (x% coverage)" |
| phase_1.5 | Factor Analysis | "Factor analysis done" |
| phase_1.75 | Symbol Metrics | "Metrics computed" |
| phase_2 | Portfolio Snapshots | "{n} trading days processed" |
| phase_2.5 | Position Values | "Values updated" |
| phase_3 | Position Betas | "Betas calculated" |
| phase_4 | Factor Exposures | "Exposures computed" |
| phase_5 | Volatility Analysis | "Volatility analyzed" |
| phase_6 | Correlations | "Correlations complete" |

---

#### Error Handling UX

**Inline Warning (common - symbols unavailable)**
- Shows as activity log entry: "⚠️ HZNP: Symbol unavailable (delisted)"
- Processing continues without interruption
- Final phase summary shows: "18/20 symbols (90% coverage)"

**Extended Wait (>20 min)**
- Add message below elapsed time: "Taking longer than usual..."
- No error shown - just informational

**Batch Failure (rare)**
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   ⚠️ Setup Interrupted                                          │
│                                                                 │
│   We encountered an issue while setting up your portfolio.      │
│   Some data may be incomplete.                                  │
│                                                                 │
│   Completed: Phases 1-3 (Market Data, Factors, Snapshots)       │
│   Failed at: Phase 4 (Position Betas)                           │
│                                                                 │
│   Your portfolio is available with partial analytics.           │
│                                                                 │
│            [ View Portfolio ]    [ Retry Setup ]                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

#### Completion Screen

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   ✅ Portfolio Setup Complete!                                  │
│                                                                 │
│   Your portfolio "Universe Test Alpha" is ready.                │
│                                                                 │
│   📊 Summary:                                                   │
│   • 18 positions analyzed (2 unavailable symbols)               │
│   • 254 trading days of history                                 │
│   • Risk metrics, factor exposures, and correlations ready      │
│                                                                 │
│   ⏱️  Total time: 14m 32s                                       │
│                                                                 │
│                [ View Portfolio Dashboard → ]                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

#### API Response Schema (Simplified)

```python
# GET /api/v1/onboarding/status/{portfolio_id}
{
    "portfolio_id": "uuid",
    "status": "running" | "completed" | "failed" | "not_found",
    "started_at": "2026-01-08T12:00:00Z",
    "elapsed_seconds": 223,

    # Overall progress
    "overall_progress": {
        "current_phase": "phase_2",
        "current_phase_name": "Portfolio Snapshots",
        "phases_completed": 2,
        "phases_total": 6,
        "percent_complete": 45
    },

    # Current phase detail
    "current_phase_progress": {
        "current": 120,
        "total": 254,
        "unit": "dates"
    },

    # Activity log entries (last 50, frontend shows ~10)
    "activity_log": [
        {
            "timestamp": "2026-01-08T12:00:05Z",
            "message": "Fetched AAPL: 254 days of history",
            "level": "info"  # "info" | "warning" | "error"
        },
        {
            "timestamp": "2026-01-08T12:00:06Z",
            "message": "⚠️ HZNP: Symbol unavailable (delisted)",
            "level": "warning"
        },
        ...
    ]
}
```

---

#### Polling Strategy

```typescript
// Simple fixed polling
const POLL_INTERVAL_MS = 2000;        // Poll every 2 seconds
const POLL_TIMEOUT_MS = 30 * 60000;   // Give up after 30 minutes
```

---

#### Implementation Priority (Simplified)

| Item | Priority | Effort | Impact |
|------|----------|--------|--------|
| Backend status endpoint with activity log | P0 | Medium | Required for everything |
| Phase list UI with progress | P0 | Low | Core UX |
| Activity log display (auto-scroll) | P0 | Low | Real-time feedback |
| Completion/error screens | P1 | Low | Polish |

---

#### Files to Create/Modify

**Backend**:
| File | Change |
|------|--------|
| `app/batch/batch_run_tracker.py` | Add `activity_log: List[dict]` with `add_activity(message, level)` |
| `app/batch/batch_orchestrator.py` | Call `add_activity()` at key points (symbol fetch, phase complete, date milestones) |
| `app/api/v1/onboarding_status.py` | NEW: Simple status endpoint returning above schema |
| `app/api/v1/router.py` | Register new endpoint |

**Frontend**:
| File | Change |
|------|--------|
| `src/components/onboarding/OnboardingProgress.tsx` | NEW or replace fake animation |
| `src/hooks/useOnboardingStatus.ts` | NEW: Simple polling hook |

---

#### Implementation Simplifications

1. **Single view mode** - No toggle between user/debug mode. Just show the activity log always.

2. **Fixed polling** - No adaptive intervals. 2-second polling is fine for all phases.

3. **Backend filtering** - Filter log entries server-side before sending. Frontend just renders what it gets.

4. **Capped activity log** - Keep last 50 entries in memory. Frontend shows last ~10 with auto-scroll.

5. **No time estimates** - Just show elapsed time. Avoid "estimated remaining" since it's unreliable.

6. **Inline warnings** - No separate warning state for phases. Warnings appear in activity log.

7. **Minimal state machine** - Just: `not_found` → `running` → `completed|failed`

---

### Phase 7.2: Onboarding Flow - Invite Code Gate (January 9, 2026)

**Status**: ✅ IMPLEMENTED (Frontend only - not pushed yet)

**Problem Solved**:
After Clerk account creation, users were redirected directly to portfolio upload. However, we require invite code validation during the beta period. The invite code entry was buried in the Settings page, which users might not find.

**Solution**: Added a dedicated `/onboarding/invite` page that gates access to the upload page.

**New Onboarding Flow**:
1. User creates account via Clerk → `/sign-up`
2. Clerk redirects to → `/onboarding/invite` (NEW)
3. User enters valid invite code
4. On success, redirect to → `/onboarding/upload`
5. User uploads portfolio CSV
6. Batch processing begins

**Files Changed**:

| File | Change |
|------|--------|
| `frontend/app/onboarding/invite/page.tsx` | **NEW** - Invite code gate page |
| `frontend/app/sign-up/[[...sign-up]]/page.tsx` | Changed `fallbackRedirectUrl` from `/settings` to `/onboarding/invite` |
| `frontend/.env.local` | Updated comments documenting the flow |

**Key Code** (`app/onboarding/invite/page.tsx`):
```typescript
'use client'

import { useRouter } from 'next/navigation'
import { InviteCodeForm } from '@/components/onboarding/InviteCodeForm'

export default function OnboardingInvitePage() {
  const router = useRouter()

  const handleInviteSuccess = () => {
    // After successful invite validation, proceed to portfolio upload
    router.push('/onboarding/upload')
  }

  return <InviteCodeForm onSuccess={handleInviteSuccess} />
}
```

**Clerk Configuration Fix**:
Also resolved a Clerk authentication issue where browser showed "Unable to authenticate this browser for your development instance".
- **Root cause**: Stale browser cookies for Clerk development instance
- **Fix**: User cleared cookies for `included-chimp-71.clerk.accounts.dev`
- **Code fix**: Removed legacy `NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL` env var that conflicted with `fallbackRedirectUrl` prop

**Future Removal**:
To remove the invite code requirement in the future, simply change:
```typescript
// In app/sign-up/[[...sign-up]]/page.tsx
fallbackRedirectUrl="/onboarding/upload"  // Skip invite page
```

**Verification**:
- ✅ New user account creation works
- ✅ Redirects to invite code page after sign-up
- ✅ Invite code validation triggers redirect to upload
- ✅ CSV upload works and triggers batch processing

---

## Manual Catch-Up: DEFERRED

**Decision**: Deferred until after Phase 1 and Phase 2 are deployed.

**Why**: Phase 2 fix will automatically backfill all 11 behind portfolios on the next cron run. No manual intervention needed.

**Script Status**: `scripts/manual_catchup_batch.py` was deployed (commit `6de057b2`) but encountered Railway SSH environment issues. Script remains available if needed later.

---

## Phase 1: Fix Phase 1.5 Skipping

### Objective
Ensure all batch entry points (admin, onboarding, cron) run Phase 1.5 (Symbol Factors) and Phase 1.75 (Symbol Metrics), AND ensure new portfolios get full historical snapshots for complete analytics.

### Pre-Fix State (Railway Production)
- Testscotty has 13 positions
- 8 symbols missing from `symbol_universe`: GGIPX, GINDX, GOVT, IAU, IEFA, MUB, NEAIX, VO
- 0 `position_factor_exposures` for all 13 positions
- Batch triggered by "admin" via `run_daily_batch_sequence()` which skips Phase 1.5
- New portfolios only get single-date snapshots (no historical data for P&L trends)

### Implementation - Part A (batch_orchestrator.py)

**File**: `backend/app/batch/batch_orchestrator.py`

**Status**: ✅ IMPLEMENTED (January 8, 2026)

**Changes Made**:
- [x] Updated docstring from "7-phase" to "9-phase" with full phase listing
- [x] Added `'phase_1_5': {}` and `'phase_1_75': {}` to result dict
- [x] Added Phase 1.5 (Symbol Factors) block after Phase 1, before Phase 2
  - Calls `calculate_universe_factors()` from `app.calculations.symbol_factors`
  - Ensures symbols in `symbol_universe` table
  - Calculates factor exposures (Ridge and Spread)
  - Non-blocking: continues to Phase 1.75 even on error
- [x] Added Phase 1.75 (Symbol Metrics) block after Phase 1.5
  - Calls `calculate_symbol_metrics()` from `app.services.symbol_metrics_service`
  - Pre-calculates returns for all symbols
  - Non-blocking: continues to Phase 2 even on error
- [x] Verified imports work correctly

**Key Code Locations**:
- Result dict: lines 559-572
- Phase 1.5: lines 625-661
- Phase 1.75: lines 663-697

### Implementation - Part B (portfolios.py + new orchestrator method)

**Files**:
- `backend/app/batch/batch_orchestrator.py` - New `run_portfolio_onboarding_backfill()` method
- `backend/app/api/v1/portfolios.py` - Updated to use new method

**Status**: ✅ IMPLEMENTED (January 8, 2026) - REVISED after code review

**Code Review Finding (Critical)**:
The initial implementation using `run_daily_batch_with_backfill()` had two issues:
1. **Global watermark short-circuit**: If cron already ran today, returns "already up to date" without processing the new portfolio
2. **Global start date**: Uses MAX snapshot across ALL portfolios, not per-portfolio earliest position

**Solution**: Created new dedicated method `run_portfolio_onboarding_backfill(portfolio_id)` that:
1. Queries earliest position `entry_date` for THIS portfolio specifically
2. Calculates all trading days from that date to today
3. Runs full batch (Phase 1 → 1.5 → 1.75 → 2-6) for all dates
4. Bypasses global watermark entirely

**Changes Made**:
- [x] Created `run_portfolio_onboarding_backfill(portfolio_id, end_date)` in batch_orchestrator.py (lines 442-671)
- [x] Changed portfolios.py to call `run_portfolio_onboarding_backfill()` instead of `run_daily_batch_with_backfill()`
- [x] Added detailed comments explaining why per-portfolio backfill is needed
- [x] Verified imports work correctly

**Key Code Locations**:
- New method: `batch_orchestrator.py` lines 442-671
- Trigger: `portfolios.py` lines 590-601

### Verification Queries

```sql
-- Check symbols in universe after fix
SELECT symbol FROM symbol_universe
WHERE symbol IN ('GGIPX', 'GINDX', 'GOVT', 'IAU', 'IEFA', 'MUB', 'NEAIX', 'VO');
-- Expected: 8 rows

-- Check symbol factor exposures after fix
SELECT symbol, COUNT(*) as factor_count
FROM symbol_factor_exposures
WHERE symbol IN ('GGIPX', 'GINDX', 'GOVT', 'IAU', 'IEFA', 'MUB', 'NEAIX', 'VO')
GROUP BY symbol;
-- Expected: 8 rows with factor_count > 0

-- Check position factor exposures for Testscotty
SELECT p.symbol, COUNT(pfe.id) as exposure_count
FROM positions p
LEFT JOIN position_factor_exposures pfe ON p.id = pfe.position_id
WHERE p.portfolio_id = '98518c7d-ea23-593b-aaed-9c0be7f3a66f'
GROUP BY p.symbol;
-- Expected: 13 rows with exposure_count > 0
```

### Post-Fix Verification
- [ ] Deployed to Railway
- [ ] Re-ran batch for Testscotty portfolio
- [ ] Verified 8 missing symbols now in `symbol_universe`
- [ ] Verified all 13 positions have `symbol_factor_exposures`
- [ ] Verified all 13 positions have `position_factor_exposures`

### Notes
- **Design Decision (Part A)**: Phase 1.5 and 1.75 are non-blocking - they continue to subsequent phases even if they fail. This is consistent with the pattern used in `run_daily_batch_with_backfill()`.
- **Design Decision (Part B - Revised v2)**: After code review v1, switched from `run_daily_batch_with_backfill()` to new dedicated `run_portfolio_onboarding_backfill()` method because:
  1. Global backfill short-circuits when cron already ran (returns "already up to date")
  2. Global backfill uses system-wide watermark, not per-portfolio dates
  3. New method guarantees processing regardless of global system state
- **Design Decision (Part B - Revised v3)**: After code review v2:
  1. Added try/finally to ensure `batch_run_tracker.complete()` always called (prevents 409 errors)
  2. **REMOVED** universe-wide `calculate_universe_factors()` call - was corrupting global analytics
  3. **REMOVED** universe-wide `calculate_symbol_metrics()` call - same issue
  4. Now only calls `ensure_symbols_in_universe()` for portfolio's specific symbols
  5. Daily cron will calculate factors with complete price cache
- **Trade-off Accepted**: New portfolios won't have factor exposures immediately. Daily cron calculates them with full data. This is acceptable because data integrity is preserved for all portfolios.
- **Key Benefit**: Now ALL batch entry points run Phase 1.5 and 1.75, and onboarding specifically gets full per-portfolio backfill from earliest position date.
- **Testing Note**: Imports verified locally. Ready for Railway deployment and verification.

---

## Testscotty2 Verification Test (January 8, 2026)

### Test Setup
- **User**: Testscotty2 (elliott.ng+testscotty2@gmail.com)
- **Portfolio**: Yaphe 5M
- **Portfolio ID**: `2ecdbdaf-468d-5484-98a1-26943635c829`
- **Created**: 2026-01-08 19:15:38 UTC
- **Positions**: 13 (same symbols as original Testscotty)

### Test Results

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| User created in DB | ✅ | ✅ Created 19:14:43 UTC | ✅ PASS |
| Portfolio created | ✅ | ✅ Created 19:15:38 UTC | ✅ PASS |
| Positions imported | 13 | 13 | ✅ PASS |
| Symbols in `symbol_universe` | 8 new | 8 found | ✅ PASS |
| Portfolio snapshots | >0 | **0** | ❌ FAIL |
| Position factor exposures | >0 | **0** | ❌ FAIL |
| Batch triggered on onboarding | Yes | **No batch record** | ❌ FAIL |

### Root Cause Analysis

**Finding: Stuck batch blocking onboarding**

The `batch_run_tracker` is an **in-memory singleton** that prevents concurrent batch runs:

1. When a batch starts → calls `batch_run_tracker.start()` → sets "running" flag
2. If another batch tries to start while flag is set → **blocked** (409 conflict)
3. When batch completes → should call `batch_run_tracker.complete()` → clears flag

**The problem**: A previous batch crashed/hung WITHOUT calling `complete()`, leaving the flag stuck. This blocked the onboarding batch from starting.

**Evidence from Railway DB**:
```
=== Batch Run History (since Jan 7) ===
2026-01-09 01:21:47 | manual | running | completed: None  ← STUCK
2026-01-07 20:56:52 | admin  | completed | completed: 2026-01-07 21:01:11
```

**Timeline**:
| Time (UTC) | Event |
|------------|-------|
| 2026-01-07 21:01:11 | Last successful batch completed (original Testscotty) |
| 2026-01-08 19:15:38 | Yaphe 5M portfolio created |
| 2026-01-08 19:15:38 | Onboarding batch should have triggered → **BLOCKED or FAILED** |
| 2026-01-09 01:21:47 | Manual batch triggered → now **STUCK** |

**Why symbols are in universe**: The `ensure_symbols_in_universe()` call may have succeeded before the batch crashed, or there's a separate code path that adds symbols.

### Implications

1. **Phase 1 fix is correct** - the try/finally ensures `batch_run_tracker.complete()` is always called
2. **But old code was running** - the deployment happened AFTER the portfolio was created, so the old (unfixed) code ran
3. **Need to clear stuck batch** - before testing again, need to:
   - Restart Railway service (clears in-memory tracker), OR
   - Wait for the stuck batch to timeout (if there's a timeout)

### Next Steps

1. [ ] Restart Railway service to clear stuck `batch_run_tracker`
2. [ ] Manually trigger batch for Yaphe 5M portfolio
3. [ ] Verify snapshots and factor exposures are created
4. [ ] Test with a NEW account created AFTER the deployment

---

## Phase 2: Fix Global Watermark Bug

### Objective
Ensure cron job processes ALL portfolios that are behind, not just check global MAX snapshot date.

### Pre-Fix State (Railway Production)
- 11 portfolios stuck at Jan 5 snapshots
- 1 portfolio (Tech Growth) at Jan 6
- 1 portfolio (Testscotty) at Jan 7
- Global MAX = Jan 7, so cron thinks "all caught up"

### Design Decision (January 8, 2026)

**Chosen Approach**: Hybrid (MIN of MAX + per-date portfolio filtering)

**Options Considered**:
| Option | Description | Verdict |
|--------|-------------|---------|
| Option 1 | MIN of per-portfolio MAX dates | Simple but reprocesses already-current portfolios |
| Option 2 | Process each portfolio independently | Efficient but complex, loses batch efficiency |
| Option 3 | Global MAX + per-date filtering | Efficient but unclear start date |
| **Hybrid** | MIN of MAX + per-date filtering | **CHOSEN** - Best of both |

**Rationale**:
- MIN of MAX gives clear, simple date range calculation
- Per-date filtering avoids reprocessing already-current portfolios
- Processing time is already a concern (~15 min per onboarding) - efficiency matters

### Implementation

**File**: `backend/app/batch/batch_orchestrator.py`

**Status**: ✅ IMPLEMENTED (January 8, 2026)

**Changes Made**:
- [x] Modify `_get_last_batch_run_date()` to use MIN of per-portfolio MAX dates
- [x] Add `_get_portfolios_with_snapshot(db, date)` helper method
- [x] Add `_get_all_active_portfolio_ids(db)` helper method
- [x] Add per-date portfolio filtering in `_execute_batch_phases()`

**Code Review**: See `CODE_REVIEW_REQUEST_PHASE2_GLOBAL_WATERMARK.md`

**Key Code Changes**:

1. **`_get_last_batch_run_date()`** - MIN of MAX watermark:
```python
# Subquery: Get MAX snapshot date for each portfolio
subquery = (
    select(
        PortfolioSnapshot.portfolio_id,
        func.max(PortfolioSnapshot.snapshot_date).label('max_date')
    )
    .group_by(PortfolioSnapshot.portfolio_id)
    .subquery()
)
# Main query: Get the MIN of those max dates
query = select(func.min(subquery.c.max_date))
```

2. **Per-date filtering** in processing loop:
```python
for calc_date in missing_dates:
    portfolios_with_snapshot = await self._get_portfolios_with_snapshot(db, calc_date)
    portfolios_to_process = [p for p in all_portfolios if p not in portfolios_with_snapshot]
    if not portfolios_to_process:
        logger.debug(f"Skipping {calc_date}: all portfolios already have snapshots")
        continue
    # Process only portfolios_to_process for this date
```

### Verification Queries

```sql
-- Check snapshot dates per portfolio after fix
SELECT p.name, MAX(ps.snapshot_date) as last_snapshot
FROM portfolios p
LEFT JOIN portfolio_snapshots ps ON p.id = ps.portfolio_id
WHERE p.deleted_at IS NULL
GROUP BY p.id, p.name
ORDER BY last_snapshot;
-- Expected: All portfolios should have same date (or within 1 day)
```

### Post-Fix Verification
- [ ] Deployed to Railway
- [ ] Ran `run_daily_batch_with_backfill()`
- [ ] Verified all portfolios have snapshots for current date
- [ ] Verified no portfolios are more than 1 day behind
- [ ] Verified logs show "System watermark (most lagging portfolio): YYYY-MM-DD"
- [ ] Verified logs show "Skipping {date}: all portfolios already have snapshots" for caught-up dates

### Notes
- Full implementation plan in `TESTSCOTTY_BATCH_PROCESSING_DEBUG_AND_FIX_PLAN.md` Phase 2 section
- This fix applies to cron job path only (onboarding uses scoped mode from Phase 5)

---

## Phase 3: Fix Fire-and-Forget Tasks

### Status: ⏸️ DEFERRED (January 8, 2026)

**Decision**: Deferred indefinitely - low priority, superseded by Phase 6.

### Original Objective
Ensure batch history records are properly persisted and no "Task was destroyed" warnings in logs.

### Why Deferred

Phase 6 already ensures `record_batch_complete()` is **called** in a finally block. Phase 3 was about how that call **executes internally** (fire-and-forget vs awaited).

**Impact analysis**:
| Scenario | What Happens | Severity |
|----------|--------------|----------|
| Normal batch completion | Works fine - task usually finishes | ✅ OK |
| Server restart during write | Status might stay "running" in DB | Low - rare edge case |
| Railway redeploy during batch | Might miss final status update | Low - Phase 6 covers this |
| Log noise | "Task was destroyed" warnings | Cosmetic only |

**Conclusion**: The system works correctly now. Only downside is occasional log warnings and a tiny edge case during deploys (milliseconds window). Not worth the engineering effort.

### Original Pre-Fix State (For Reference)
- Multiple cron batches show `status="running"` forever
- "Task was destroyed but it is pending" warnings in logs
- `batch_history_service.py` uses `asyncio.create_task()` without awaiting

---

## Phase 4: Add batch_run_tracker Timeout & Cleanup

### Objective
Make the batch system self-healing when batches crash or hang, eliminating the need for manual Railway restarts.

### Problem Statement
The `batch_run_tracker` is an in-memory singleton that prevents concurrent batch runs. If a batch crashes without calling `complete()`, the flag stays stuck until server restart, blocking ALL subsequent batches.

**Discovered during**: Testscotty2 verification test (Jan 8, 2026)

### Pre-Fix State
- `batch_run_tracker` has no timeout mechanism
- Crashed batches leave tracker stuck indefinitely
- Only fix is manual Railway restart
- No automatic cleanup on server startup

### Implementation

**Files to Modify**:
- `backend/app/batch/batch_run_tracker.py` - Add timeout logic
- `backend/app/main.py` - Add startup cleanup

**Status**: NOT STARTED

**Changes Required**:

#### Part A: Add Timeout to In-Memory Tracker

```python
# batch_run_tracker.py
class BatchRunTracker:
    def __init__(self, timeout_minutes=30):
        self._running = False
        self._started_at = None
        self._timeout = timedelta(minutes=timeout_minutes)

    def is_running(self) -> bool:
        if self._running and self._started_at:
            # Auto-expire if running too long
            if datetime.utcnow() - self._started_at > self._timeout:
                logger.warning(f"Batch auto-expired after {self._timeout}")
                self._running = False
                return False
        return self._running

    def start(self):
        if self.is_running():  # Uses timeout check
            raise BatchAlreadyRunningError()
        self._running = True
        self._started_at = datetime.utcnow()

    def complete(self):
        self._running = False
        self._started_at = None
```

#### Part B: Add Startup Cleanup for Database Records

```python
# In app startup (main.py or lifespan)
async def cleanup_stale_batches():
    """Mark any batch 'running' for >30 min as 'failed'"""
    async with get_async_session() as db:
        await db.execute(text("""
            UPDATE batch_run_history
            SET status = 'failed',
                completed_at = NOW(),
                notes = 'Auto-failed: exceeded 30 minute timeout'
            WHERE status = 'running'
            AND started_at < NOW() - INTERVAL '30 minutes'
        """))
        await db.commit()
```

### Design Decisions

1. **Timeout value**: 30 minutes
   - Longest normal batch run is ~15-20 minutes
   - 30 minutes gives buffer for slow runs
   - Can be made configurable via environment variable

2. **Dual approach**:
   - In-memory timeout: Self-heals during runtime
   - Startup cleanup: Handles restart scenarios and keeps DB accurate

3. **Logging**: Log when auto-expiring so we can track crash frequency

### Verification Steps

1. [ ] Unit test: Verify tracker auto-expires after timeout
2. [ ] Integration test: Start batch, kill process, verify new batch can start after timeout
3. [ ] Startup test: Create stale "running" record, restart server, verify it's marked "failed"

### Post-Fix Verification
- [ ] Deployed to Railway
- [ ] Simulated stuck batch (or waited for natural occurrence)
- [ ] Verified system auto-recovered without restart
- [ ] Verified stale DB records cleaned up on startup

### Notes
- This is a **preventive fix** - makes the system resilient to future crashes
- Combined with Phase 1's try/finally, crashes should be rare
- But when they do happen, system will self-heal

---

## Phase 5: Unify Batch Functions (REFACTOR)

### Objective
Consolidate `run_portfolio_onboarding_backfill()` and `run_daily_batch_with_backfill()` into a single unified function with parameters for different entry points.

### Problem Discovered (January 8, 2026)

During Testscotty3 debugging, we found the batch was processing **ALL 1,193 symbols** in the symbol universe when it only needed **~30 symbols** (13 positions + 17 factor ETFs). This caused:
- Excessive runtime (~4+ hours estimated vs ~10 minutes expected)
- Polygon API rate limiting (429 errors)
- Unnecessary database writes

### Root Cause

When we created `run_portfolio_onboarding_backfill()` as a separate function from `run_daily_batch_with_backfill()`, we:
1. Created code duplication (two similar functions to maintain)
2. Did NOT scope the symbol collection to just the portfolio's symbols
3. Made debugging harder (bugs can exist in one path but not the other)

### Proposed Solution

Create ONE unified `run_batch()` function with parameters:

```python
async def run_batch(
    portfolio_id: Optional[str] = None,  # If None, process all portfolios
    source: str = "cron",                # "cron" | "onboarding" | "settings" | "admin"
    backfill_mode: bool = True,          # True = historical, False = today only
    symbols_scope: str = "auto"          # "auto" | "portfolio" | "universe"
) -> Dict[str, Any]:
```

**Key behavior**:
- When `portfolio_id` is provided → only fetch portfolio's symbols + factor ETFs (~30 symbols)
- When `portfolio_id` is None → fetch entire universe (cron job behavior)

### Implementation Status

**Status**: NOT STARTED - **NEXT PRIORITY**

**Files to Modify**:
- [ ] `backend/app/batch/batch_orchestrator.py` - Unify functions
- [ ] `backend/app/api/v1/portfolios.py` - Update to use unified function
- [ ] `backend/app/api/v1/endpoints/admin_batch.py` - Update to use unified function
- [ ] `backend/app/batch/scheduler_config.py` - Update cron to use unified function

### Expected Benefits
1. Single code path = easier debugging
2. **~40x faster** for single-portfolio batches (30 vs 1,193 symbols)
3. Consistent behavior across all entry points
4. Reduced API rate limiting issues

### Import Fix (January 8, 2026)

While debugging, we also fixed a blocking bug:
- **Bug**: `ImportError: cannot import name 'get_most_recent_trading_day' from 'app.utils.trading_calendar'`
- **Fix**: Changed import to `from app.core.trading_calendar import get_most_recent_trading_day`
- **Commit**: `7d8b0e2a` - "fix: Correct import path for get_most_recent_trading_day"

This fix allows the batch to START, but it still runs inefficiently until Phase 5 is implemented.

---

## Timeline

| Date | Action | Result |
|------|--------|--------|
| 2026-01-08 | Initial analysis and plan created | 3 bugs identified |
| 2026-01-08 | Phase 1 Part A implemented | Added Phase 1.5 and 1.75 to `_run_sequence_with_session()` |
| 2026-01-08 | Phase 1 Part B implemented (v1) | Changed onboarding to use `run_daily_batch_with_backfill()` |
| 2026-01-08 | Code review identified issues | Global watermark problems with Part B v1 |
| 2026-01-08 | Phase 1 Part B revised (v2) | Created `run_portfolio_onboarding_backfill()` method |
| 2026-01-08 | Code review v2 identified issues | batch_run_tracker cleanup, Phase 1.5 corruption |
| 2026-01-08 | Phase 1 Part B revised (v3) | Added try/finally, scoped symbol processing |
| 2026-01-08 | Code review request v3 written | `CODE_REVIEW_REQUEST_BATCH.md` |
| 2026-01-08 | Pushed to origin/main | Railway deployment triggered |
| 2026-01-08 | Testscotty2 verification test | Onboarding batch blocked by stuck batch_run_tracker |
| 2026-01-08 | Phase 4 added to plan | batch_run_tracker timeout & cleanup |
| 2026-01-08 | Testscotty3 debugging session | Found ImportError blocking batch start |
| 2026-01-08 | Import fix deployed | `7d8b0e2a` - Fixed `get_most_recent_trading_day` import path |
| 2026-01-08 | Batch now runs but inefficient | Processing 1,193 symbols instead of ~30 |
| 2026-01-08 | Phase 5 added to plan | Unify batch functions for efficiency |
| 2026-01-08 | Phase 5 & 6 implemented | Unified batch function + error handling hardening |
| 2026-01-08 | Code review iterations (3 rounds) | asyncio.CancelledError, progress tracking, commit ordering |
| 2026-01-08 | Pushed 9 commits to origin/main | Railway auto-deployed |
| 2026-01-08 | Railway verification (testscotty4) | ✅ 254/254 dates in 894s (~15 min), 27 symbols |
| 2026-01-08 | Phase 7 planned | Real-time onboarding status updates with User/Debug modes |
| 2026-01-08 | Phase 2 implemented | Hybrid approach: MIN of MAX + per-date filtering |
| 2026-01-09 | Phase 7.1 implemented | Backend onboarding status endpoint pushed to origin |
| 2026-01-09 | Phase 7.2 implemented | Frontend invite code gate (local only) |
| 2026-01-09 | Issue #8 discovered | Factor exposure storage bug - key name mismatch |
| 2026-01-09 | testscotty5 verified | Snapshots current, batch 254/254 in 686s, but only 3 factors |
| 2026-01-09 | Issue #8 partial fix | Added `total_symbols` key to `data_quality` dict |
| 2026-01-09 | Code reviews received | Gemini: approved; Codex: found second bug (signature mismatch) |
| 2026-01-09 | Issue #8 complete fix | Fixed signature mismatch in analytics_runner.py, added logging |
| | | |

---

## Code Review Checklist

Before pushing to remote:
- [x] Phase 1 changes reviewed by AI agent (Claude Opus 4.5)
- [ ] Phase 2 changes reviewed by AI agent
- [ ] Phase 3 changes reviewed by AI agent
- [ ] Phase 4 changes reviewed by AI agent
- [x] Phase 5 changes reviewed by AI agent (3 iterations)
- [x] Phase 6 changes reviewed by AI agent (3 iterations)
- [x] Phase 5 & 6 verified on Railway (testscotty4)
- [ ] All verification queries pass on Railway
- [ ] No regressions in existing functionality

---

## Rollback Plan

If issues arise after deployment:

**Phase 1 Rollback**:
```bash
git revert <phase1-commit-hash>
git push origin main
```

**Phase 2 Rollback**:
```bash
git revert <phase2-commit-hash>
git push origin main
```

**Phase 3 Rollback**:
```bash
git revert <phase3-commit-hash>
git push origin main
```

**Phase 4 Rollback**:
```bash
git revert <phase4-commit-hash>
git push origin main
```

**Phase 5 Rollback**:
```bash
# Revert all Phase 5 commits in reverse order
git revert a020f1ca  # fix: Address code review findings
git revert ffb68fa1  # docs: Add code review request
git revert 3ae56503  # feat: Implement Phase 5 unified batch
git revert 337e7d39  # docs: Add Phase 5 plan
git push origin main
```

**Phase 6 Rollback**:
```bash
# Revert all Phase 6 commits in reverse order
git revert 1357bd7b  # fix: Update progress tracker only after commit
git revert 5749f64a  # fix: Track actual progress for crash reporting
git revert f82496d7  # fix: Catch asyncio.CancelledError
git revert 9963c9af  # feat: Implement Phase 6 try/except/finally
git revert be0c7052  # docs: Add Phase 6 plan
git push origin main
```
