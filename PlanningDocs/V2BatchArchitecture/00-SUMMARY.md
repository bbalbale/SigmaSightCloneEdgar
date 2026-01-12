# Architecture V2: Decoupled Symbol-Portfolio Batch Processing

**Status**: Planning
**Created**: 2026-01-11
**Last Updated**: 2026-01-11

---

## Problem Statement

Current architecture ties symbol-level data maintenance to portfolio-level analytics:
- "Minimum watermark" strategy means ANY behind portfolio drags the entire batch
- New user onboarding triggers full batch (15-30 min wait)
- O(users × symbols × dates) complexity instead of O(symbols)

---

## Solution: Two Daily Cron Jobs + Instant Onboarding

### Cron Job 1: Symbol Batch (9:00 PM ET)
- Fetches closing prices for ALL symbols in universe
- Calculates betas/factors for ALL symbols
- Independent of portfolios
- Duration: ~15 min

### Cron Job 2: Portfolio Refresh (9:30 PM ET)
- Checks symbol batch completion
- Queries: "Which portfolios don't have today's snapshot?"
- Creates snapshots for those portfolios
- Duration: ~5-15 min

### User Onboarding (Instant)
- Creates portfolio + positions
- Creates snapshot using **cached prices** (yesterday's close, or today's if post-cron)
- Snapshot date = price date (not creation time)
- Duration: < 5 seconds

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│              CRON JOB 1: Symbol Batch (9:00 PM ET)              │
│                                                                  │
│   1. Fetch today's closing prices (YFinance)                    │
│   2. Calculate Market Beta, IR Beta (OLS)                       │
│   3. Calculate Ridge factors (6)                                │
│   4. Calculate Spread factors (4)                               │
│   5. Record completion flag                                     │
│                                                                  │
│   Duration: ~15 min | Tables: market_data_cache,              │
│                       symbol_factor_exposures                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Completion flag
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│            CRON JOB 2: Portfolio Refresh (9:30 PM ET)           │
│                                                                  │
│   1. Check symbol batch completion                              │
│   2. Query: Portfolios without today's snapshot                 │
│   3. For each: Create snapshot, update market values            │
│   4. Invalidate analytics caches                                │
│                                                                  │
│   Duration: ~5-15 min | No more watermark calculation!          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  USER ONBOARDING (Anytime)                      │
│                                                                  │
│   1. Create portfolio + positions                               │
│   2. Get latest price date from cache                           │
│   3. Create snapshot using cached prices                        │
│   4. Compute and cache analytics                                │
│                                                                  │
│   Duration: < 5 sec | Snapshot date = price date                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Cron structure | Two separate jobs | Failure isolation, independent scaling |
| Onboarding prices | Use cached (yesterday's close) | Consistency, no live price lookups |
| Snapshot date | Price date, not creation time | Data integrity |
| Historical P&L | Not needed for new portfolios | Simplification |
| Position changes | Affect today forward only | No backfill complexity |

---

## Document Index

| Doc | Description |
|-----|-------------|
| [01-CURRENT-STATE.md](./01-CURRENT-STATE.md) | Current 9-phase architecture analysis |
| [02-TARGET-ARCHITECTURE.md](./02-TARGET-ARCHITECTURE.md) | New decoupled architecture |
| [03-DATABASE-SCHEMA.md](./03-DATABASE-SCHEMA.md) | Schema changes and new tables |
| [04-SYMBOL-BATCH-RUNNER.md](./04-SYMBOL-BATCH-RUNNER.md) | Cron Job 1: Symbol batch |
| [05-PORTFOLIO-REFRESH.md](./05-PORTFOLIO-REFRESH.md) | Cron Job 2: Portfolio refresh |
| [06-PORTFOLIO-CACHE.md](./06-PORTFOLIO-CACHE.md) | Analytics cache service |
| [07-SYMBOL-ONBOARDING.md](./07-SYMBOL-ONBOARDING.md) | New symbol handling (async) |
| [08-USER-ONBOARDING.md](./08-USER-ONBOARDING.md) | User onboarding flow (instant) |
| [09-RAILWAY-CONSTRAINTS.md](./09-RAILWAY-CONSTRAINTS.md) | Railway-specific limits |
| [10-MIGRATION-PLAN.md](./10-MIGRATION-PLAN.md) | Week-by-week migration |
| [11-OPEN-ISSUES.md](./11-OPEN-ISSUES.md) | Gaps to resolve |
| [12-OPERATIONAL-TOGGLES.md](./12-OPERATIONAL-TOGGLES.md) | Master switch and logging strategy |
| [13-FAILURE-HANDLING.md](./13-FAILURE-HANDLING.md) | Retry strategies and admin visibility |
| [14-FRESHNESS-CONTRACTS.md](./14-FRESHNESS-CONTRACTS.md) | Data staleness SLAs and alerting |
| [15-OBSERVABILITY.md](./15-OBSERVABILITY.md) | Logging, admin APIs, and dashboard updates |
| [16-PARALLELISM.md](./16-PARALLELISM.md) | Concurrency, rate limits, idempotency |
| [17-API-CONTRACT-CHANGES.md](./17-API-CONTRACT-CHANGES.md) | Frontend API migration (breaking changes) |
| [18-ANALYTICS-ENDPOINT-STRATEGY.md](./18-ANALYTICS-ENDPOINT-STRATEGY.md) | Cache vs DB for analytics endpoints |
| [19-IMPLEMENTATION-FIXES.md](./19-IMPLEMENTATION-FIXES.md) | Cold start, private positions, race condition fixes |
| [20-CRITICAL-INTEGRATION-GAPS.md](./20-CRITICAL-INTEGRATION-GAPS.md) | **CRITICAL**: Scheduler conflicts, tracker rewrite, P&L complexity |

---

## Critical Integration Points

Before implementation, review `20-CRITICAL-INTEGRATION-GAPS.md` for:

| Gap | Risk | Solution |
|-----|------|----------|
| APScheduler double-runs | Data corruption | Conditional job init based on V2 flag |
| Batch tracker single-run | Concurrent job conflicts | Multi-job tracker rewrite |
| P&L calculation simplification | Wrong valuations | Reuse existing PnLCalculator |
| Analytics services read DB | Broken endpoints | Write to BOTH cache AND DB tables |
| Symbol batch no backfill | Permanent data gaps | Add backfill mode to symbol batch |
| In-memory onboarding queue | Lost jobs on restart | Database-backed queue |
| Onboarding status `not_found` | Jarring UX | Frontend V2 mode detection |

---

## Performance Targets

| Metric | Current | V2 Target |
|--------|---------|-----------|
| Symbol batch (daily) | Variable | ~15 min FIXED |
| Portfolio refresh (daily) | Part of batch | ~5-15 min |
| New user onboarding | 15-30 min | < 5 sec |
| Analytics (cache hit) | N/A | < 10ms |
| Analytics (cache miss) | 3-30 min | < 500ms |

---

## Success Criteria

1. Symbol batch completes in < 15 minutes regardless of portfolio count
2. Portfolio refresh completes in < 15 minutes
3. New user sees analytics in < 5 seconds
4. No regression in calculation accuracy
5. Daily P&L snapshots created for all active portfolios
6. System handles 10,000+ portfolios without degradation
