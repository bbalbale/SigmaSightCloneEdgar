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

## Next Steps

1. Discuss each open issue and make decisions
2. Update relevant docs with decisions
3. Create implementation tickets
4. Build regression test suite
5. Implement feature flags first
