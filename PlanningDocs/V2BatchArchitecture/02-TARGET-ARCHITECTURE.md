# 02: Target Architecture

## Core Principle

**Symbol Processing**: Time-driven (daily cron)
**Portfolio P&L**: Time-driven (daily, after symbol batch)
**Portfolio Analytics**: Event-driven (on-demand with cache)

---

## New Job Structure

### Job 1: Symbol Daily Batch (Cron 9:00 PM ET)
```
STEP 1: Get all symbols in symbol_universe WHERE is_active = true
STEP 2: Batch fetch today's prices from YFinance
STEP 3: Update market_data_cache table (existing)
STEP 4: For each symbol (parallelized, 10 concurrent):
        a. Calculate Market Beta (OLS vs SPY)
        b. Calculate IR Beta (OLS vs TLT)
        c. Calculate Ridge factors (6 factors)
        d. Calculate Spread factors (4 factors)
        e. UPSERT into symbol_factor_exposures
STEP 5: Update symbol_daily_metrics (denormalized view)

Duration: ~12-15 minutes, FIXED regardless of user count
```

### Job 2: Portfolio Daily Refresh (After Symbol Batch)
```
STEP 1: Get all active portfolios
STEP 2: For each portfolio:
        a. Calculate P&L for today
        b. Create PortfolioSnapshot
        c. Update position market values
STEP 3: Invalidate all portfolio analytics caches

Duration: ~5-10 minutes (scales with portfolios, but no factor calcs)
```

### Job 3: Analytics (On-Demand)
```
On analytics request:
1. Check portfolio_analytics_cache
2. If hit: Return cached data (<10ms)
3. If miss:
   a. Lookup pre-computed symbol betas
   b. Aggregate by position weights
   c. Cache result
   d. Return (~50-100ms)
```

---

## What Changes

| Phase | Current Location | V2 Location |
|-------|------------------|-------------|
| Phase 0: Company Profiles | Daily batch | Symbol batch (before factors) |
| Phase 1: Market Data | Daily batch per watermark | Symbol batch once daily |
| Phase 1.5: Symbol Factors | Daily batch per watermark | Symbol batch once daily |
| Phase 1.75: Symbol Metrics | Daily batch per watermark | Symbol batch once daily |
| Phase 2: Fundamentals | Daily batch | Symbol batch (earnings-triggered) |
| **Phase 3: P&L Snapshots** | Daily batch | **Portfolio refresh job** |
| **Phase 4: Market Values** | Daily batch | **Portfolio refresh job** |
| Phase 5: Sector Tags | Daily batch | Portfolio refresh job |
| Phase 6: Risk Analytics | Daily batch | **On-demand with cache** |

---

## Key Files to Create

```
backend/app/batch/
├── symbol_batch_runner.py       # NEW: Symbol-only daily batch
├── portfolio_refresh_runner.py  # NEW: P&L and market value updates
├── symbol_onboarding_worker.py  # NEW: Async new symbol processing
└── symbol_onboarding_tracker.py # NEW: Concurrent job tracking

backend/app/services/
├── portfolio_cache_service.py   # NEW: Analytics cache operations
└── symbol_price_service.py      # NEW: Price management

backend/app/cache/
└── analytics_cache.py           # NEW: Persistent in-memory cache
```

---

## Key Files to Modify

| File | Change |
|------|--------|
| `batch_orchestrator.py` | Remove symbol processing, keep P&L/analytics structure |
| `scheduler_config.py` | Add symbol batch cron, add portfolio refresh cron |
| `onboarding.py` | Check symbol readiness, skip batch trigger |
| `onboarding_status.py` | Simplified status (ready/pending/error) |

---

## Separation of Concerns

```
Symbol Layer (Global)          Portfolio Layer (Per-User)
─────────────────────          ──────────────────────────
symbol_universe                portfolios
market_data_cache              positions
symbol_factor_exposures        portfolio_snapshots
symbol_daily_metrics           (in-memory analytics cache)
```

**Rule**: Portfolio layer READS from symbol layer, never writes. Symbol layer has no knowledge of portfolios.
