# App Batch Directory Documentation

This document describes all files in `backend/app/batch/` and its subdirectories.

---

## Overview

The batch directory implements the 3-phase batch processing orchestration framework with 8 calculation engines. Production uses batch_orchestrator (v3), NOT v2.

---

## Root Level: `app/batch/`

### `__init__.py`
Empty module initialization file. Used by Python import system.

### `batch_orchestrator.py`
Main orchestration engine (v3) that coordinates all batch processing phases: Phase 1 (market data), Phase 1.5 (fundamentals), Phase 2 (P&L), Phase 2.5 (position market value updates), Phase 3 (analytics). **CRITICAL**: This is the authoritative batch orchestrator. Imported by admin_batch.py, scheduler_config.py, and all batch processing scripts.

### `batch_run_tracker.py`
Real-time in-memory tracker for batch processing runs with activity logging, phase progress tracking, TTL-based completion status retention, and V2 multi-job support. Used by `batch_orchestrator.py`, `admin_batch.py`, and V2 runners.

### `market_data_collector.py`
Phase 1: Collects market data for 365-day historical lookback using smart incremental/gap-fill fetching with provider priority chain (YFinance → YahooQuery → Polygon → FMP). Called by `batch_orchestrator.py` during Phase 1.

### `pnl_calculator.py`
Phase 2: Calculates mark-to-market P&L and portfolio snapshots with equity rollforward using price cache optimization. Called by `batch_orchestrator.py` during Phase 2.

### `fundamentals_collector.py`
Phase 1.5: Collects fundamental data (income statements, balance sheets, cash flows) with earnings-driven smart fetching. Called by `batch_orchestrator.py` during Phase 1.5.

### `analytics_runner.py`
Phase 6: Runs all risk analytics (market beta, provider beta, IR beta, factor analysis, sector analysis, volatility, correlations, stress testing) using cached market data with NO API calls. Called by `batch_orchestrator.py` during Phase 3.

### `scheduler_config.py`
APScheduler configuration for batch job scheduling configuring V1 mode (all jobs via APScheduler) vs V2 mode (Railway cron for symbol/portfolio jobs). Imported by `app/main.py` to initialize scheduled jobs on startup.

### `admin_metrics_job.py`
Admin dashboard job for aggregating user activity events and AI request metrics to daily_metrics table with 30-day retention policy. Scheduled by `scheduler_config.py` daily at 1 AM UTC.

### `feedback_learning_job.py`
Batch feedback learning job (Phase 3.4 of PRD4) that detects patterns in accumulated user feedback across all users and creates memory rules. Scheduled by `scheduler_config.py` daily at 8:00 PM ET.

---

## V2 Subdirectory (`v2/`)

V2 Batch Architecture for high-performance symbol-centric processing with instant onboarding.

### `__init__.py`
Exports V2 batch components: symbol batch runner, portfolio refresh runner, and symbol onboarding queue. Imported by batch trigger service and API endpoints.

### `symbol_batch_runner.py`
V2 nightly job (9:00 PM ET) that processes ALL symbols in the universe: Phase 0 (daily metrics), Phase 1 (market data collection), Phase 3 (factor calculations). Called by Railway cron job.

### `portfolio_refresh_runner.py`
V2 portfolio refresh job (9:30 PM ET) that runs 30 minutes after symbol batch to leverage cached prices and factors. Called by Railway cron job.

### `symbol_onboarding.py`
V2 instant on-demand symbol onboarding for new positions added to portfolios with in-memory queue. Called by position addition endpoints.

---

## Batch Processing Flow

```
Entry Points:
  ↓
API Endpoints (admin_batch.py):
  - POST /api/v1/admin/batch/run → triggers batch_orchestrator.run_batch_sequence()
  - GET /api/v1/admin/batch/run/current → polls batch_run_tracker.get_current()
  ↓
batch_orchestrator.py (Main Orchestrator):
  Phase 1 → market_data_collector.collect_daily_market_data()
  Phase 1.5 → fundamentals_collector.collect_fundamentals_data()
  Phase 2 → pnl_calculator.calculate_all_portfolios_pnl()
  Phase 2.5 → position market value updates
  Phase 3 → analytics_runner.run_all_portfolios_analytics()
  ↓
batch_run_tracker (Progress Monitoring):
  - Tracks running state
  - Updates activity logs for UI polling
  - Persists logs to database
  - Retains completed status for 2 hours (TTL)
  ↓
Scheduled Jobs:
  APScheduler (scheduler_config.py):
  - Feedback learning batch (daily 8:00 PM ET)
  - Admin metrics aggregation (daily 8:30 PM ET)

  Railway Cron (V2 Architecture):
  - Symbol batch (daily 9:00 PM ET) → symbol_batch_runner.py
  - Portfolio refresh (daily 9:30 PM ET) → portfolio_refresh_runner.py
```

---

## Summary Table

| File | Phase | Purpose | Used By |
|------|-------|---------|---------|
| `batch_orchestrator.py` | All | Main orchestration engine (v3) | admin_batch.py, scheduler, scripts |
| `batch_run_tracker.py` | All | Progress tracking with activity logging | orchestrator, admin endpoints |
| `market_data_collector.py` | 1 | Collect market data (365-day lookback) | batch_orchestrator |
| `fundamentals_collector.py` | 1.5 | Collect fundamental data | batch_orchestrator |
| `pnl_calculator.py` | 2 | P&L and snapshot creation | batch_orchestrator |
| `analytics_runner.py` | 3/6 | Risk analytics (betas, factors, stress) | batch_orchestrator |
| `scheduler_config.py` | - | APScheduler configuration | main.py startup |
| `admin_metrics_job.py` | - | Aggregate admin metrics | scheduler |
| `feedback_learning_job.py` | - | AI feedback learning | scheduler |
| `v2/symbol_batch_runner.py` | 0,1,3 | Nightly symbol processing | Railway cron |
| `v2/portfolio_refresh_runner.py` | 3-6 | Portfolio refresh after symbol batch | Railway cron |
| `v2/symbol_onboarding.py` | Instant | New symbol onboarding | position endpoints |

---

## Key Design Decisions

1. **V3 Orchestrator**: `batch_orchestrator.py` is the current authoritative orchestrator (NOT v2)
2. **YFinance First**: Market data provider priority is YFinance → YahooQuery → Polygon → FMP
3. **Idempotency**: Phase 2.10 insert-first pattern prevents duplicate snapshots
4. **Real-Time Tracking**: `batch_run_tracker` provides in-memory progress tracking with 2-hour TTL
5. **V2 Multi-Job**: Support for concurrent batch jobs with deduplication per job type
