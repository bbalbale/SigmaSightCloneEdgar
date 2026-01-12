# 11: Open Issues

## Status: Active Discussion Required

This document tracks issues identified during planning that need resolution before implementation.

---

## Issue 1: Railway Cron Sizing & Telemetry

**Status**: 🟢 Resolved

**Resolution**: See `09-RAILWAY-CONSTRAINTS.md`.

**Key Decisions**:
- Symbol batch: 15 min target, 20 min warning, 25 min abort
- Portfolio refresh: 10 min target, 15 min warning, 20 min abort
- Peak memory: ~200 MB
- Windows asyncio fix: Use `WindowsSelectorEventLoopPolicy` locally, `uvloop` on Railway
- Concurrency: 5 for price fetching, 10 for factor calc

---

## Issue 2: Post-Split Daily Job Matrix

**Status**: 🟢 Resolved

**Resolution**: Created `05-PORTFOLIO-REFRESH.md` defining:
- Job 1: Symbol Daily Batch (9:00 PM ET)
- Job 2: Portfolio Daily Refresh (after symbol batch)
- P&L snapshots and market values run in Portfolio Refresh job

---

## Issue 3: Freshness Contracts

**Status**: 🟢 Resolved

**Resolution**: See `14-FRESHNESS-CONTRACTS.md`.

**Key Decisions**:
- Staleness calculated in trading days only (weekends/holidays don't count)
- User visibility: None (admin-only)
- Alerts: Warning at 1 trading day stale, Critical at 2+ days
- Onboarding: Confirmation screen shows "Valued using [date] closing prices"

---

## Issue 4: Cache Lifecycle & Invalidation

**Status**: 🟢 Resolved

**Resolution**: See updated `06-PORTFOLIO-CACHE.md`.

**Key Decisions**:
- In-memory cache for all symbol data (~65 MB for 5,000 symbols)
- No invalidation needed - just refresh daily and add new symbols
- Portfolio analytics computed on-demand from cached symbol data
- Cache loaded on app startup, refreshed by nightly batch, symbols added during onboarding

---

## Issue 5: Failure Handling & Graceful Degradation

**Status**: 🟢 Resolved

**Resolution**: See `13-FAILURE-HANDLING.md`.

**Key Decisions**:
- Symbol prices: Cascading fallback (yfinance → yahooquery → FMP → polygon)
- Portfolio refresh: Retry once, skip private portfolios (always fail)
- Admin page: Shows failed symbols, failed portfolios, and cache staleness date
- Unknown symbols: Show "Data unavailable" badge, user can edit/remove on command center

---

## Issue 6: Observability Metrics

**Status**: 🟢 Resolved

**Resolution**: See `15-OBSERVABILITY.md`.

**Key Decisions**:
- Structured logging only (no external services for now)
- Admin dashboard displays batch status, cache status, queue status, freshness
- 5 new admin API endpoints needed
- Frontend admin page updates with status cards, batch panels, history table

---

## Issue 7: Parallelism & Idempotency

**Status**: 🟢 Resolved

**Resolution**: See `16-PARALLELISM.md`.

**Key Decisions**:
- Portfolio refresh: Skip if snapshot already exists (idempotent)
- Symbol onboarding: Dedupe at queue time
- API rate limits: YFinance primary (30/min), FMP (1/min), Polygon (4/min)
- Queue backpressure: Max 50 pending symbols

---

## Issue 8: Validation Regression Suite

**Status**: 🟢 Resolved

**Resolution**: Manual testing sufficient for launch.

**Key Decisions**:
- No formal regression test suite needed for V2 launch
- Manual smoke testing: batch runs, onboarding works, data looks sane
- Can add automated tests later if needed

---

## Issue 9: Operational Toggles

**Status**: 🟢 Resolved

**Resolution**: Single master switch with comprehensive logging. See `12-OPERATIONAL-TOGGLES.md`.

**Key Decisions**:
- One environment variable: `BATCH_V2_ENABLED` (true/false)
- Structured logging for all V2 steps (`V2_BATCH_STEP`, `V2_ONBOARDING`)
- No automatic fallback to legacy (prevents duplicate processing)
- Rollback time: ~3 minutes (redeploy with flag=false)

---

## Issue 10: SLA Alignment & Backpressure

**Status**: 🟢 Resolved

**Resolution**: Timing thresholds in `09-RAILWAY-CONSTRAINTS.md` are sufficient.

**Key Decisions**:
- No formal SLA documentation needed
- Timing thresholds already defined (15 min target, 20 min warning, 25 min abort)
- Backpressure covered in `16-PARALLELISM.md` (queue max 50)

---

## Priority Matrix

| Issue | Priority | Blocker? |
|-------|----------|----------|
| Issue 2: Job Matrix | P0 | 🟢 Resolved |
| Issue 9: Operational Toggles | P0 | 🟢 Resolved |
| Issue 5: Failure Handling | P1 | 🟢 Resolved |
| Issue 3: Freshness Contracts | P1 | 🟢 Resolved |
| Issue 4: Cache Lifecycle | P1 | 🟢 Resolved |
| Issue 6: Observability | P1 | 🟢 Resolved |
| Issue 1: Railway Sizing | P2 | 🟢 Resolved |
| Issue 7: Parallelism | P2 | 🟢 Resolved |
| Issue 8: Regression Tests | P2 | 🟢 Resolved |
| Issue 10: SLA/Backpressure | P2 | 🟢 Resolved |

---

## Additional Issues Resolved (January 2026)

### Issue 11: Cold Start & Cache Health

**Status**: 🟢 Resolved

**Resolution**: See `19-IMPLEMENTATION-FIXES.md` Section 1.

**Key Decisions**:
- Two-tier health endpoints: `/health/live` and `/health/ready`
- Background cache initialization (non-blocking)
- DB fallback for all analytics until cache ready
- Readiness probe gates traffic for max 30 seconds

---

### Issue 12: Private Position Handling

**Status**: 🟢 Resolved

**Resolution**: See `19-IMPLEMENTATION-FIXES.md` Section 2.

**Key Decisions**:
- PRIVATE positions skipped in symbol batch (no market prices)
- Portfolio refresh uses manual `market_value` field for PRIVATE
- Analytics: PRIVATE contributes to value, NOT to factor exposures
- Response includes `private_allocation_pct` for transparency

---

### Issue 13: Options Symbol Handling

**Status**: 🟢 Resolved

**Resolution**: See `19-IMPLEMENTATION-FIXES.md` Section 3.

**Key Decisions**:
- Options symbols detected by format (15+ chars with date pattern)
- Equity prices from YFinance, options prices from Polygon
- Options do NOT get factor exposures (only equity symbols do)
- Greeks NOT tracked (confirmed out of scope)

---

### Issue 14: Symbol Onboarding Race Condition

**Status**: 🟢 Resolved

**Resolution**: See `19-IMPLEMENTATION-FIXES.md` Section 4 and `05-PORTFOLIO-REFRESH.md`.

**Key Decisions**:
- Portfolio refresh waits up to 2 min for pending onboarding jobs
- Before creating snapshot, checks for symbols missing factors
- Missing factors calculated inline (fills gaps from race condition)
- Ensures complete data even if symbol onboarded mid-day

---

### Issue 15: Dual Database Confirmation

**Status**: 🟢 Resolved

**Resolution**: See `19-IMPLEMENTATION-FIXES.md` Section 5.

**Key Decisions**:
- All V2 batch tables are in Core database (gondola)
- AI database (metro) NOT accessed by batch processing
- Use `get_async_session()` for all V2 queries

---

## Critical Integration Issues (January 2026 - Round 2)

> **See `20-CRITICAL-INTEGRATION-GAPS.md` for full implementation details.**

### Issue 16: APScheduler + Railway Cron Double-Runs

**Status**: 🟢 Resolved

**Resolution**: See `20-CRITICAL-INTEGRATION-GAPS.md` Issue 2.

**Key Decisions**:
- APScheduler conditionally initializes based on `BATCH_V2_ENABLED`
- V2 mode: Only non-conflicting jobs (feedback_learning, admin_metrics)
- Railway cron uses wrapper script to route V1/V2
- Old `railway_daily_batch.py` guards against V2 mode

---

### Issue 17: Batch Tracker Single-Run Limitation

**Status**: 🟢 Resolved

**Resolution**: See `20-CRITICAL-INTEGRATION-GAPS.md` Issue 6.

**Key Decisions**:
- Multi-job tracker supports concurrent jobs by type
- One job per type (no duplicate symbol batches)
- V1 compatibility via wrapper methods
- `check_batch_running()` accepts optional job_type filter

---

### Issue 18: Symbol Batch Must Support Backfill

**Status**: 🟢 Resolved

**Resolution**: See `20-CRITICAL-INTEGRATION-GAPS.md` Issue 3.

**Key Decisions**:
- Symbol batch has `backfill=True` mode (default)
- Finds last successful symbol batch date from `BatchRunTracking`
- Processes all missed trading days in sequence
- Records completion per date for granular tracking

---

### Issue 19: Analytics Services Read from DB Tables

**Status**: 🟢 Resolved

**Resolution**: See `20-CRITICAL-INTEGRATION-GAPS.md` Issue 4.

**Key Decisions**:
- **Hybrid approach**: Symbol batch writes to BOTH cache AND DB tables
- Analytics services (FactorExposureService, etc.) unchanged
- Cache provides fast reads; DB provides service compatibility
- No rewrite of existing analytics code

---

### Issue 20: P&L Calculation Complexity

**Status**: 🟢 Resolved

**Resolution**: See `20-CRITICAL-INTEGRATION-GAPS.md` Issue 5.

**Key Decisions**:
- Reuse existing `PnLCalculator` class
- Pass V2 price cache via existing `price_cache` parameter
- Maintains: equity rollforward, options multipliers, exit date handling
- Maintains: snapshot slot locking for idempotency

---

### Issue 21: In-Memory Onboarding Queue

**Status**: 🟢 Resolved

**Resolution**: See `20-CRITICAL-INTEGRATION-GAPS.md` Issue 7.

**Key Decisions**:
- Database-backed queue (`symbol_onboarding_jobs` table)
- Survives Railway restarts/scaling
- `resume_on_startup()` called from lifespan handler
- Status tracking: pending → processing → completed/failed

---

### Issue 22: Factor Definitions Seeding

**Status**: 🟢 Resolved

**Resolution**: See `20-CRITICAL-INTEGRATION-GAPS.md` Issue 8.

**Key Decisions**:
- V2 symbol batch calls `ensure_factor_definitions()` before factor phase
- Same pattern as existing `railway_daily_batch.py`
- Idempotent - safe to run multiple times

---

### Issue 23: Fundamentals & Company Profile Migration

**Status**: 🟢 Resolved

**Resolution**: See `20-CRITICAL-INTEGRATION-GAPS.md` Issue 10.

**Key Decisions**:
- Symbol batch includes company profile sync (Phase 0)
- Symbol batch includes fundamentals collection (Phase 2)
- Phase order matches V1 for compatibility
- Uses existing `fundamentals_collector` module

---

### Issue 24: Onboarding Status UX

**Status**: 🟢 Resolved

**Resolution**: See `20-CRITICAL-INTEGRATION-GAPS.md` Issue 1.

**Key Decisions**:
- **Option A (Recommended)**: Skip progress page entirely in V2
- Upload page redirects directly to `/portfolio` on success
- Backend returns `mode: "v2_instant"` for frontend detection
- Frontend `useOnboardingStatus` detects V2 mode from first response

---

## Next Steps

1. ~~Discuss each open issue and make decisions~~
2. ~~Update relevant docs with decisions~~
3. Create implementation tickets
4. Build regression test suite
5. Implement feature flags first
6. **CRITICAL**: Start with multi-job tracker (blocks everything else)
7. **CRITICAL**: Add V2 guards to existing schedulers before any V2 code
