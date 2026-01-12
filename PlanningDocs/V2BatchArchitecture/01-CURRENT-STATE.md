# 01: Current State Analysis

## Current 9-Phase Batch Architecture

```
Phase 0:   Company Profile Sync (beta, sector, industry)
Phase 1:   Market Data Collection (1-year lookback)
Phase 1.5: Symbol Factor Calculation (ridge + spread)
Phase 1.75: Symbol Metrics Calculation (returns, valuations)
Phase 2:   Fundamental Data Collection
Phase 3:   P&L Calculation & Snapshots
Phase 4:   Position Market Value Updates
Phase 5:   Sector Tag Restoration
Phase 6:   Risk Analytics (portfolio aggregation)
```

---

## Current Factor Calculations

### OLS Regressions (2)
| Factor | Window | ETF/Index | Location |
|--------|--------|-----------|----------|
| Market Beta | 90 days | SPY | `market_beta.py` |
| IR Beta | 90 days | TLT | `interest_rate_beta.py` |

### Ridge Regression Factors (6)
| Factor | ETF | Window |
|--------|-----|--------|
| Value | VTV | 90 days |
| Growth | VUG | 90 days |
| Momentum | MTUM | 90 days |
| Quality | QUAL | 90 days |
| Size | IWM | 90 days |
| Low Volatility | USMV | 90 days |

### Spread Factors (4)
| Factor | Long ETF | Short ETF | Window |
|--------|----------|-----------|--------|
| Growth-Value Spread | VUG | VTV | 180 days |
| Momentum Spread | MTUM | SPY | 180 days |
| Size Spread | IWM | SPY | 180 days |
| Quality Spread | QUAL | SPY | 180 days |

---

## Root Cause of Performance Issue

**Current watermark calculation** (in `_get_last_batch_run_date`):
```python
# MIN of per-portfolio MAX snapshot dates
subquery = select(
    PortfolioSnapshot.portfolio_id,
    func.max(PortfolioSnapshot.snapshot_date).label('max_date')
).group_by(PortfolioSnapshot.portfolio_id).subquery()
query = select(func.min(subquery.c.max_date))
```

**Problem**: If ANY portfolio is behind (e.g., new user from Dec 15), the ENTIRE batch processes from that date, even for symbols already computed.

---

## Existing Symbol-Level Tables

Already implemented:
- `symbol_universe` - Master symbol list
- `symbol_factor_exposures` - Per-symbol factor betas (ridge + spread)
- `symbol_daily_metrics` - Denormalized dashboard data

**Key Insight**: Phase 1.5 (`symbol_factors.py`) already calculates at symbol level. The problem is WHEN it runs - it's triggered by portfolio watermarks, not independently.

---

## Current Entry Points

| Entry Point | File | Calls |
|-------------|------|-------|
| Daily cron | `scheduler_config.py` | `batch_orchestrator.run_daily_batch_with_backfill()` |
| CLI script | `run_batch.py` | `batch_orchestrator.run_daily_batch_with_backfill()` |
| Admin trigger | `admin_batch.py` | `batch_orchestrator.run_daily_batch_with_backfill()` |
| Onboarding | `batch_trigger_service.py` | `batch_orchestrator.run_daily_batch_with_backfill(portfolio_id=X)` |

---

## Current Batch Tracking (Phase 7.x)

Implemented in `batch_run_tracker.py`:
- `CurrentBatchRun` - Tracks one batch at a time
- `PhaseProgress` - Per-phase progress (current/total/unit)
- `ActivityLogEntry` - Real-time activity log (max 50 entries)
- `CompletedRunStatus` - 60-second TTL for completed status

**Limitation**: Tracks ONE batch at a time. V2 needs to support concurrent symbol onboarding jobs.
