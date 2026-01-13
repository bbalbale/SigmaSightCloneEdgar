# 21: V2 Batch Architecture - Implementation Status & Summary

## Overview

This document tracks the implementation status of V2 batch architecture and serves as an architectural summary of the changes made.

**Status**: Production Ready (as of 2026-01-13)
**Total Steps**: 12 (11 completed, 1 in progress)

---

## Architecture Summary

### V2 Batch Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     V2 NIGHTLY BATCH (9:00 PM ET)                       │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    SYMBOL BATCH RUNNER                            │   │
│  │                                                                    │   │
│  │  Phase 0: Daily Valuations (PE, beta, 52w range, market cap)     │   │
│  │     └─ Uses yahooquery batch API for efficiency                   │   │
│  │                                                                    │   │
│  │  Phase 1: Market Data Collection (365-day lookback)              │   │
│  │     └─ YFinance primary, Polygon for options, FMP fallback        │   │
│  │                                                                    │   │
│  │  Phase 2: Fundamentals [SKIPPED - needs optimization]            │   │
│  │                                                                    │   │
│  │  Phase 3: Factor Calculations (per symbol)                       │   │
│  │     ├─ Ridge Factors (6): Value, Growth, Momentum, Quality,      │   │
│  │     │                     Size, Low Volatility                    │   │
│  │     ├─ Spread Factors (4): Growth-Value, Momentum, Quality, Size │   │
│  │     └─ OLS Factors (3): Market Beta (90D), IR Beta, Provider Beta│   │
│  │                                                                    │   │
│  │  → Factor Cache Refresh (for Phase 5 and user onboarding)        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                              │                                           │
│                              ▼                                           │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                  PORTFOLIO REFRESH RUNNER                         │   │
│  │                                                                    │   │
│  │  Phase 4: P&L Calculations (uses price cache)                    │   │
│  │     └─ Updates position market values, unrealized P&L             │   │
│  │                                                                    │   │
│  │  Phase 5: Factor Aggregation (symbol → portfolio level)          │   │
│  │     ├─ Ridge betas (equity-weighted average)                      │   │
│  │     ├─ Spread betas (equity-weighted average)                     │   │
│  │     └─ OLS betas: Market Beta, IR Beta, Provider Beta            │   │
│  │                                                                    │   │
│  │  Phase 6: Stress Testing                                         │   │
│  │     └─ Uses IR betas from symbol_factor_exposures (V2)           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Tables (V2 reuses existing tables)

| Table | Purpose |
|-------|---------|
| `symbol_universe` | Track which symbols are in the system |
| `market_data_cache` | Store fetched prices (365 days) |
| `symbol_factor_exposures` | Store calculated factors per symbol |
| `factor_exposures` | Store aggregated factors per portfolio |
| `batch_run_history` | Track batch run completions |

### Symbol Cache Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SYMBOL CACHE SERVICE                        │
│                                                                   │
│  _price_cache: Dict[symbol, Dict[date, float]]                  │
│     └─ Loaded from market_data_cache before Phase 3              │
│     └─ Provides 300x speedup for factor calculations             │
│                                                                   │
│  _factor_cache: Dict[symbol, Dict[factor_name, float]]          │
│     └─ Refreshed AFTER Phase 3 completes                         │
│     └─ Used by Phase 5 aggregation                               │
│     └─ Available for instant user onboarding                     │
│                                                                   │
│  Methods:                                                         │
│     get_latest_price(symbol, date, db) → float (with DB fallback)│
│     get_factors(symbol, date, db) → Dict[str, float]             │
│     refresh_factors(date) → void (called after Phase 3)          │
└─────────────────────────────────────────────────────────────────┘
```

### Private Asset Filtering

V2 filters out private/alternative assets that have no market data:

```python
def is_private_asset_symbol(symbol: str) -> bool:
    # Rule 1: Contains underscore (HOME_EQUITY, FO_PRIVATE_CREDIT, etc.)
    if '_' in symbol:
        return True
    # Rule 2: Internal ID pattern (EQ5D6A2D8F)
    if INTERNAL_ID_PATTERN.match(symbol):
        return True
    return False
```

**Filtered symbols include:**
- Real estate: `HOME_EQUITY`, `RENTAL_SFH`, `RENTAL_CONDO`
- Family office: `FO_*` (FO_PRIVATE_CREDIT, FO_INFRASTRUCTURE, etc.)
- Private funds: `BX_PRIVATE_EQUITY`, `TWO_SIGMA_FUND`, `A16Z_VC_FUND`
- Cash: `MONEY_MARKET`, `TREASURY_BILLS`
- Alternatives: `ART_COLLECTIBLES`, `CRYPTO_BTC_ETH`, `STARWOOD_REIT`
- Internal IDs: `EQ5D6A2D8F`

---

## Implementation Status

### Phase 1: Foundation (Steps 1-4) ✅ COMPLETE

| Step | Description | Status | Files |
|------|-------------|--------|-------|
| 1 | V2 Feature Flag | ✅ Complete | `config.py` |
| 2 | Multi-Job Batch Tracker | ✅ Complete | `batch_run_tracker.py` |
| 3 | V2 Guards in Schedulers | ✅ Complete | `scheduler_config.py` |
| 4 | Zero New Tables | ✅ Complete | (uses existing tables) |

### Phase 2: Symbol Batch Runner (Steps 5-7) ✅ COMPLETE

| Step | Description | Status | Files |
|------|-------------|--------|-------|
| 5 | Symbol Batch Core | ✅ Complete | `batch/v2/symbol_batch_runner.py` |
| 6 | Market Data Phase | ✅ Complete | (Phase 0, 1, 2) |
| 7 | Factor Phase + DB Writes | ✅ Complete | (Phase 3 + cache refresh) |

**Key Features Implemented:**
- Phase 0: Daily valuations via yahooquery batch API
- Phase 1: Market data collection (365 days, YFinance primary)
- Phase 3: Ridge + Spread + OLS factor calculations
- Factor cache refresh after Phase 3
- Private asset filtering (underscore pattern + internal IDs)
- Backfill support for missed dates

### Phase 3: Portfolio Refresh Runner (Steps 8-9) ✅ COMPLETE

| Step | Description | Status | Files |
|------|-------------|--------|-------|
| 8 | Portfolio Refresh Runner | ✅ Complete | `batch/v2/portfolio_refresh_runner.py` |
| 9 | Symbol Onboarding Queue | ✅ Complete | In-memory queue |

**Key Features Implemented:**
- Phase 4: P&L calculations with price cache
- Phase 5: Factor aggregation (Ridge, Spread, OLS)
- Phase 6: Stress testing with IR betas from V2 tables
- Cache-based factor lookups for aggregation

### Phase 4: Cache & Health (Steps 10-11) ✅ COMPLETE

| Step | Description | Status | Files |
|------|-------------|--------|-------|
| 10 | Symbol Cache + Health | ✅ Complete | `cache/symbol_cache.py` |
| 11 | Frontend V2 Mode | ✅ Complete | Instant onboarding UX |

**Key Features Implemented:**
- In-memory price cache (300x speedup)
- In-memory factor cache with refresh
- DB fallback for cache misses
- Health endpoints (/health/live, /health/ready)

### Phase 5: Testing & Deployment (Step 12) 🔄 IN PROGRESS

| Step | Description | Status |
|------|-------------|--------|
| 12 | Integration Testing & Rollout | 🔄 In Progress |

**Current Status:**
- [x] Local testing complete
- [x] Railway deployment active
- [x] Nightly batch running successfully
- [x] Private asset filtering verified
- [ ] 1-week production monitoring
- [ ] Performance benchmarking

---

## Recent Changes (2026-01-13)

### 1. OLS Factor Aggregation in Phase 5
**Commit:** `120d7bb2`

Added Market Beta (90D), IR Beta, and Provider Beta (1Y) to Phase 5 aggregation:

```python
# backend/app/services/portfolio_factor_service.py
OLS_FACTORS = {
    'Market Beta (90D)': 'ols_market',
    'IR Beta': 'ols_ir',
    'Provider Beta (1Y)': 'provider',
}
```

### 2. Factor Cache Refresh After Phase 3
**Commit:** `adb4ed8c`

Cache is now refreshed after Phase 3 calculations complete:

```python
# backend/app/batch/v2/symbol_batch_runner.py
await symbol_cache.refresh_factors(calc_date)
```

This ensures:
- Phase 5 aggregation uses fresh factors
- User onboarding has immediate access to calculated factors

### 3. Cache-Based Phase 5 Lookups
**Commit:** `0b4171cb`

Phase 5 now uses in-memory cache instead of DB queries:

```python
# backend/app/services/portfolio_factor_service.py
async def load_symbol_betas_from_cache(symbols, calculation_date, factor_names, db):
    for symbol in symbols:
        symbol_factors = await symbol_cache.get_factors(symbol, calculation_date, db)
        # ... aggregate
```

### 4. Private Asset Filtering
**Commit:** `95a73249`

Filters private/alternative assets BEFORE factor calculations:

```python
# backend/app/batch/v2/symbol_batch_runner.py
public_symbols, private_symbols = filter_private_assets(symbol_list)
```

This prevents:
- Wasted time calculating factors for symbols without market data
- Batch timeouts from processing 20+ private assets
- Cache miss warnings flooding logs

### 5. Stress Test Import Fix
**Commit:** `95a73249`

Fixed `FactorDefinition` import in stress testing:

```python
# Before (broken):
from app.models.factors import FactorDefinition

# After (fixed):
from app.models.market_data import FactorDefinition
```

---

## Key Files Reference

### Core V2 Batch Files

| File | Purpose |
|------|---------|
| `app/batch/v2/symbol_batch_runner.py` | Nightly symbol batch (Phases 0-3) |
| `app/batch/v2/portfolio_refresh_runner.py` | Portfolio refresh (Phases 4-6) |
| `app/cache/symbol_cache.py` | In-memory price + factor cache |
| `app/services/portfolio_factor_service.py` | Factor aggregation service |
| `app/calculations/symbol_factors.py` | Symbol-level factor calculations |

### Maintenance Scripts

| Script | Purpose |
|--------|---------|
| `scripts/maintenance/clear_calcs_for_date.py` | Clear V2 calculations for a date |
| `scripts/maintenance/run_phase3_only.py` | Run Phase 3+ manually |
| `scripts/railway/audit_railway_data.py` | Audit Railway deployment |

---

## Rollback Plan

If V2 causes issues in production:

1. Set `BATCH_V2_ENABLED=false` in Railway dashboard
2. Redeploy (automatic on env change)
3. V1 batch resumes on next scheduled run
4. Investigate and fix V2 issues
5. Re-enable when fixed

**Rollback time**: ~3 minutes

---

## Next Steps

1. **Performance Benchmarking** - Measure Phase 3 execution time improvements
2. **Monitoring Dashboard** - Add V2 batch metrics to admin panel
3. **Phase 2 Fundamentals** - Re-enable after optimization
4. **Remove V1 Code** - Once V2 stable for 2+ weeks

---

## Changelog

| Date | Change | Commit |
|------|--------|--------|
| 2026-01-13 | Private asset filtering | `95a73249` |
| 2026-01-13 | Cache-based Phase 5 lookups | `0b4171cb` |
| 2026-01-13 | Factor cache refresh after Phase 3 | `adb4ed8c` |
| 2026-01-13 | OLS factors in Phase 5 aggregation | `120d7bb2` |
| 2026-01-12 | IR Beta V2 architecture fix | `1db7ff0e` |
