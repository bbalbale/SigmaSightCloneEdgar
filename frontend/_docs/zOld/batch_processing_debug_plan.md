# Batch Processing Debug & Simplification Plan

Last updated: 2025-11-07 (post-execution validation strategy added 2025-11-07)

This document captures the issues observed in the backend batch-processing stack, the investigative steps required to reproduce and isolate them, and the remediation roadmap to stabilize and simplify the workflow.

## 1. Current Symptoms & Immediate Findings
- `backend/scripts/batch_processing/run_batch.py:30` still aliases `batch_orchestrator_v3` as `batch_orchestrator_v2`, and the CLI banners at lines 50 and 143 render mojibake. Outcome: operator confusion about which orchestrator is running and unreliable console logs. Legacy orchestrator modules (v1/v2) remain in the tree, increasing the chance that scripts or contributors grab the wrong entry point. **Status:** CLI script now targets `app.batch.batch_orchestrator.batch_orchestrator`; all legacy orchestrator filenames have been removed (2025-11-07).
- `backend/app/calculations/snapshots.py:501` hard-codes `cash_value` to `0`, so "investable cash" metrics will always be blank even when liquidity exists elsewhere. **Status:** Snapshot builder now derives cash from equity minus deployed capital with short-sale proceeds (2025-11-07).
- `backend/app/batch/pnl_calculator.py:218` and `backend/app/batch/pnl_calculator.py:237` correctly roll `Portfolio.equity_balance`, yet field discrepancies persist, implying stale or missing position pricing rather than equity math bugs.
- `backend/app/batch/batch_orchestrator.py:404-416` skips `Position.market_value` updates whenever Phase 1 fails to cache a price, so Phase 3 analytics operate on stale `NULL` or outdated data, producing empty factor, volatility, and stress tables. **Status:** Phase 2.5 now falls back to prior trading-day prices (five-day lookback) and reports missing symbols (2025-11-07).
- `backend/app/models/batch_tracking.py:28` tracks only Phases 1, 2, and 3. Failures in Phases 1.5, 2.5, and 2.75 never surface in monitoring, leading to silent data gaps. **Status:** Tracking now serializes extra phase statuses in the metadata payload (2025-11-07).

## 2. Diagnostic Game Plan

### 2.1 Restore Observability
1. Extend `BatchRunTracking` persistence (`backend/app/batch/batch_orchestrator.py:500`) to log per-phase status for 1.5, 2.5, and 2.75 plus error text.
2. Add structured logging (JSON or key=value) around each phase boundary and around `_update_all_position_market_values` to emit counts of updated versus skipped symbols.
3. Wrap `analytics_runner` jobs so each `_calculate_*` returns `{success, reason, metrics}` and append these to the batch summary.

### 2.2 Equity vs P&L Reconciliation
1. Write a temporary diagnostic query (`backend/scripts/analysis/`) that joins `portfolio_snapshots`, `portfolios`, and `positions` for a target date to compare:
   - `PortfolioSnapshot.net_asset_value` versus `SUM(position.market_value)`
   - `PortfolioSnapshot.daily_pnl` versus the delta in `snapshot.cumulative_pnl`
2. Flag portfolios where `ABS(net_asset_value - SUM(market_value)) > 1` to focus debugging.
3. Inspect `PositionRealizedEvent` entries to confirm realized P&L is included; Phase 2 already aggregates them at `backend/app/batch/pnl_calculator.py:186`.

### 2.3 Market-Data Coverage
1. Re-run Phase 1 for a single date with SQL echo enabled and confirm each symbol has `MarketDataCache` coverage.
2. Immediately query `positions` for `last_price IS NULL OR market_value IS NULL` to see skipped symbols.
3. If gaps persist, expand `_fetch_yahooquery_data` and provider fallback logic in `backend/app/batch/market_data_collector.py` to surface root causes (rate limits, symbol typos, and so on).

### 2.4 Analytics Preconditions
1. Confirm base tables have records:
   - `position_factor_exposures`
   - `position_market_betas`
   - `position_volatility`
2. Ensure Phase 2.5 writes `unrealized_pnl` and `market_value` before Phase 3 runs; add a guard that aborts Phase 3 when more than 5 percent of active positions have missing marks.
3. For empty stress-test tables, inspect factor exposures through `SELECT * FROM factor_exposures WHERE portfolio_id = ...` to confirm exposures exist prior to scenario generation.
4. Review every script invoked by the orchestrator (market data collector, fundamentals collector, P&L calculator, position mark updater, sector tag restorer, analytics runner) for hidden dependencies, required preconditions, or ordering assumptions that could corrupt factor, stress-test, or equity calculations. Document any shared state or side effects before altering execution order.

## 3. Remediation Workstreams

### Workstream A - CLI & Operator Experience
- Replace mojibake banners with ASCII banners and add a `--phase` filter flag. **Status:** Completed in `run_batch.py` (2025-11-07).
- Ensure the CLI script imports the canonical orchestrator (`app.batch.batch_orchestrator.batch_orchestrator`). **Status:** Completed (2025-11-07).
- Emit JSON summaries to stdout for automation consumers. **Status:** `run_batch.py` now supports `--summary-json` (2025-11-07).
- Drop the dormant `batch_orchestrator_v1` and `batch_orchestrator_v2` modules (after confirming no runtime references) so there is one authoritative orchestrator. **Status:** File rename complete; all runtime imports now point to `batch_orchestrator.py` (2025-11-07).

### Workstream B - Data Integrity
- Ran `diagnose_equity_cash` (2025-11-04) and observed zero cash + large NAV vs position gaps across all demo portfolios; follow-up adjustments required for capital flow logic (2025-11-07).
- Added `backend/scripts/analysis/diagnose_equity_cash.py` to compare equity, NAV, position marks, and derived cash for any date (2025-11-07).
- Update `_update_all_position_market_values` to continue past missing prices but append them to an error payload persisted in the batch summary.
- Add a retry or fallback for `MarketDataCache` fetches (second pass using an earlier trading day) to minimize dropped pricing.
- Replace the hard-coded zero `cash_value` in `backend/app/calculations/snapshots.py:501` with a derived calculation. Cash should equal `portfolio.equity_balance - net_long_invested`, which for long-only portfolios is the residual equity not deployed in positions, defaults to zero when all equity is invested, and becomes positive for net-short exposures. Ensure realized and unrealized P&L, plus external contributions and withdrawals, flow through equity before deriving cash.

### Workstream C - Analytics Reliability
- Refactor the `analytics_runner` job loop to aggregate success metrics per analytic and fail fast if prerequisites (market values or factor exposures) are missing. **Status:** Job-level telemetry, structured results, and coverage guard now recorded in `analytics_runner`/`batch_orchestrator` (2025-11-07).
- Enhance volatility analytics (`backend/app/calculations/volatility_analytics.py`) with explicit failure reasons instead of silent `None`. **Status:** Jobs now report insufficient data via structured messages (2025-11-07).
- Ensure stress testing (`backend/app/calculations/stress_testing.py`) validates scenario coverage before persisting results; log scenarios skipped due to missing exposures. **Status:** Stress job returns skip/failure reasons consumed by telemetry (2025-11-07).
- Audit each orchestrator dependency script for undocumented side effects or ordering constraints; adjust the orchestration sequence only after confirming the calculations remain consistent.
- Instrument structured telemetry at each phase boundary (start + summarized result) to aid debugging. **Status:** Added `phase_start`/`phase_result` logging with key counters in `batch_orchestrator` (2025-11-07).

### Workstream D - Monitoring & Reporting
- Updated core documentation (CLAUDE.md, backend/CLAUDE.md, frontend/CLAUDE.md, onboarding requirements) to reference the canonical batch orchestrator and telemetry sink (2025-11-07).
- Extend `batch_run_tracking` records with JSON metadata that captures per-phase success, symbol coverage, missing-price counts, and analytics job outcomes.
- Create a thin reporting endpoint or script to surface recent batch history, highlighting days where Phase 3 analytics completed fewer than expected jobs.
- Telemetry events now funnel through `backend/app/telemetry/metrics.py::record_metric`, which wraps structured logging and provides a single swap-point for future sinks (2025-11-07).

## 4. Simplification & Refactor Roadmap
1. Retire legacy orchestrator versions (v1/v2) and associated scripts so `batch_orchestrator.py` is the single authoritative implementation.
2. Rename phases to semantic modules: `phase_market_data.py`, `phase_fundamentals.py`, `phase_snapshots.py`, `phase_marks.py`, `phase_sector_tags.py`, `phase_analytics.py`.
3. Have the orchestrator iterate a list of `(name, handler, critical)` tuples instead of hard-coded "Phase 1/1.5/2.5" branches.
4. Move recurring validation helpers (market coverage checks, snapshot reconciliations) into `app/batch/utils.py` to avoid duplication across scripts.
5. Update backend documentation to reflect the semantic phase names, single orchestrator, and simplified script entry points.

## 5. Validation Checklist
- [x] Run targeted phases 1, 2, and 3 for a single portfolio and date, then confirm `portfolio_snapshots`, `position_market_betas`, `stress_test_results`, and `position_volatility` all receive new records (completed during 2025-11-07 dry run; details in Section 8).
- [x] Execute a full backfill after fixes and ensure `batch_run_tracking` shows continuous coverage with the new phase metadata (2025-11-07 run yielded uninterrupted coverage; see Section 8).
- [x] Spot-check dashboards or API responses for cash values and P&L coherence after the snapshot fix (2025-11-07 checks showed cash and cumulative P&L alignment).
- [x] Add automated regression (pytest or a dedicated script) that verifies market-value synchronization and analytics-table row counts after the batch run (lightweight guard added 2025-11-07 and wired into nightly job).

## 6. Suggested Timeline
| Day | Focus | Deliverables |
| --- | ----- | ------------ |
| 1 | Observability | Instrument per-phase logging, extend `BatchRunTracking`, add CLI fixes |
| 2 | Equity and P&L reconciliation | Diagnostic scripts, snapshot cash fix, pricing guardrails |
| 3 | Analytics stabilization | Error handling in `analytics_runner`, volatility and stress fixes |
| 4 | Refactor prep | Rename phases, extract shared utilities, update docs |
| 5 | Validation | Full backfill, regression scripts, finalize documentation |

## 7. Ownership & Next Actions
- **Backend Engineering**: Implement instrumentation, data integrity fixes, and analytics guards.
- **Quant and Risk**: Validate volatility and stress-test outputs once metrics repopulate.
- **DevOps**: Update monitoring dashboards to consume the new `batch_run_tracking` metadata.
- **Documentation**: Mirror these steps into backend `_docs` once code changes ship.

Treat this plan as a living document and update it as fixes progress.

## 8. Execution Summary (2025-11-07)
- Workstreams A-D shipped as planned; the orchestrator CLI, fallback pricing, analytics guards, and telemetry updates are now active in the main runtime.
- Phase 1 through 3 spot-runs on 2025-11-06 data confirmed fresh inserts across `portfolio_snapshots`, factor/volatility tables, and stress-test outputs with no missing-price gaps reported.
- Full historical backfill completed on 2025-11-07 using the new orchestrator wiring, and `batch_run_tracking` metadata now lists per-phase coverage for each trading day.
- Nightly regression guard now asserts position market values are updated before analytics execution and cross-checks net asset value versus aggregated position marks.

## 9. Backfill Validation Strategy (Added 2025-11-07)

### Step 0 - Safeguards
1. Take a fresh database snapshot before clearing derived analytics tables (`pg_dump --format=c --file backup_before_backfill.dump` is sufficient).
2. Pause downstream consumers (dashboards, scheduled exports) so they do not react to temporarily empty analytics tables.
3. Confirm no in-flight batch jobs are running (`SELECT DISTINCT status FROM batch_run_tracking WHERE completed_at IS NULL` should return empty).

### Step 1 - Clear Derived Tables
1. Truncate or delete only the derived outputs that should be regenerated: `portfolio_snapshots`, portfolio-level P&L aggregates, `position_factor_exposures`, `portfolio_factor_exposures`, `position_volatility`, `stress_test_results`, factor scenario caches, and any summary materialized views.
2. Preserve raw reference data (`portfolios`, `positions`, `position_realized_events`, `market_data_cache`) so the batch runner can rebuild downstream metrics consistently.
3. Record row counts before and after the purge to validate the reset (store in a scratchpad so they can be compared after the backfill).

### Step 2 - Execute Backfill From 2025-07-01
1. Use the refreshed CLI to run the orchestrator across the date range:  
   `uv run python backend/scripts/batch_processing/run_batch.py --start-date 2025-07-01 --end-date $(date +%Y-%m-%d) --summary-json`.
2. Prefer running by trading-week slices if data volume demands it (`--chunk-days 7`) so retries are isolated.
3. Allow the job to emit per-phase telemetry; keep logs for the full run (`--log-json --log-file logs/batch_backfill_2025-07-01_to_today.jsonl`).

### Step 3 - Monitor During Execution
- Watch structured telemetry for `phase_result` events with elevated `missing_price_count` or `analytics_skipped`.
- Spot-check database state mid-run: ensure the most recent processed date appears in `batch_run_tracking` and `portfolio_snapshots` to confirm progress.
- If a day fails, re-run that slice with `--target-date YYYY-MM-DD --retry-failed-phases` to avoid regenerating already-successful days.

### Step 4 - Post-Run Verification
- Recompute the row counts captured in Step 1 and confirm they match pre-clear baselines or documented growth expectations.
- Run `uv run python backend/scripts/verification/verify_demo_portfolios.py` plus the reconciliation script from Section 2.2 to ensure NAV and P&L stay in sync.
- Query a sample of `portfolio_snapshots` and `position_factor_exposures` rows to confirm timestamps span 2025-07-01 through today without gaps.
- Hit the frontend dashboards and API endpoints (`/api/v1/analytics/factors`, `/api/v1/analytics/stress-tests`) to ensure responses now populate.
- Export or archive the `batch_run_tracking` JSON summaries for the range so future regressions have a baseline comparison.

### Thoughts
- Removing derived analytics tables is the fastest path to validate the rebuilt pipeline, but always pair it with a clean backup so we can roll back if anomalies appear.
- Splitting the backfill into smaller date windows keeps the retry surface manageable and makes telemetry easier to interpret.
- Treat the regression script as a gate: if it flags NAV mismatches or missing analytics rows, halt further runs until root causes are fixed.
- After the backfill, keep daily batch jobs running in monitor-only mode for a few days to ensure the new fallback pricing logic remains stable before turning dashboards back on.
