# Batch Processing Scripts

End-to-end orchestration for nightly portfolio analytics, including market data refresh, fundamentals, P&L roll-forward, and risk analytics. Everything lands in PostgreSQL; the frontend and APIs read directly from the same tables.

---

## Primary Entry Points

| Script | Purpose |
| --- | --- |
| `scripts/run_batch_with_monitoring.py` | **Recommended nightly run.** Executes Phases 1 → 3 for the current trade date with progress indicators and safety checks. |
| `scripts/batch_processing/run_batch.py` | Backfill and ad-hoc runner. Wraps the orchestrator’s backfill logic so you can process missed trading days or scope the run to a single portfolio. |

> Report-generation utilities were retired in October 2025. Consume data through the API or directly from the database.

---

## Daily Workflow

1. Source the backend `.env` (must include `DATABASE_URL`, provider keys, etc.).
2. From the repo root:
   ```bash
   cd backend
   uv run python scripts/run_batch_with_monitoring.py
   ```
   This executes the full production pipeline for *today’s* trade date and prints a per-phase summary (symbols fetched, positions updated, analytics counts, and any errors).
3. To backfill missing trading days or target a subset of portfolios, use `run_batch.py`:
   ```bash
   # Backfill every missing day up to today
   uv run python scripts/batch_processing/run_batch.py

   # Re-run only for a specific portfolio UUID
   uv run python scripts/batch_processing/run_batch.py --portfolio e23ab931-a033-edfe-ed4f-9d02474780b4
   ```
   `run_batch.py` calls `batch_orchestrator.run_daily_batch_with_backfill`, so it automatically processes any historical gaps.

---

## Phase Breakdown (Batch Orchestrator v3)

| Phase | Description | Notes |
| --- | --- | --- |
| **1. Market Data Collection** | Refreshes EOD prices for every active symbol (YFinance first, FMP fallback, Polygon for options). | Populates `market_data_cache`. |
| **1.5. Fundamental Data** | Smart refetch of statements/estimates when post-earnings data ages out. | Gracefully skips when providers return “Data not available”. |
| **2. P&L & Snapshots** | Rolls forward portfolio equity, updates daily/MTD/YTD P&L, writes `portfolio_snapshots`. | Uses cached market values if Phase 1 misses a symbol. |
| **2.5. Position Market Values** | Updates `positions.last_price`, `market_value`, and `unrealized_pnl` to keep exposures consistent. | Required for Phase 3 analytics. |
| **2.75. Sector Tag Restoration** | Re-applies sector tags based on company profiles for Organize/Explorer views. | No-op if tags are current. |
| **3. Risk Analytics** | Calculates market & IR betas, factor exposures (ridge/spread), sector/volatility metrics, correlations, and stress tests. | Results land in `position_market_betas`, `correlation_calculations`, `stress_test_results`, etc. |

If a phase raises an error, later phases still attempt to run. The summary block shows any failures so you can rerun just the impacted portion (e.g., rerun Phase 3 after addressing data issues).

---

## Output Highlights

Key tables and corresponding API endpoints:

| Dataset | Table(s) | Example API |
| --- | --- | --- |
| Portfolio snapshots & exposures | `portfolio_snapshots` | `GET /api/v1/data/portfolio/{id}/snapshot/latest` |
| Position market values | `positions` (`last_price`, `market_value`, `unrealized_pnl`) | `GET /api/v1/positions/{id}` |
| Market / IR betas | `position_market_betas`, `position_interest_rate_betas` | `GET /api/v1/analytics/portfolio/{id}/betas` |
| Factor exposures | `position_factor_exposures`, `portfolio_factor_exposures` | `GET /api/v1/analytics/portfolio/{id}/factors` |
| Correlations | `correlation_calculations`, `pairwise_correlations` | `GET /api/v1/analytics/portfolio/{id}/correlations` |
| Stress tests | `stress_test_results`, `stress_test_scenarios` | `GET /api/v1/analytics/portfolio/{id}/stress-tests` |

Greeks are no longer calculated, so the legacy `/analytics/position-greeks` endpoint is deprecated.

---

## Troubleshooting

- **Missing prices:** Phase 2.5 prints counts for positions updated vs. skipped. If everything is skipped, confirm Phase 1 succeeded or that the symbol has a supported data source. Private positions intentionally skip price updates but still appear in snapshots.
- **Fundamentals warnings:** Provider strings such as “Data not available” are ignored; the collector logs a warning and continues. Check `fundamentals_service.should_fetch_fundamentals` if a symbol never refreshes.
- **Risk analytics rerun:** To re-run just Phase 3 after fixing data, execute:
  ```bash
  uv run python -c "import asyncio; from datetime import date; from app.batch.analytics_runner import analytics_runner; asyncio.run(analytics_runner.run_all_portfolios_analytics(date.today()))"
  ```
- **Backfill:** `run_batch.py` takes care of filling historical gaps automatically. Ensure Postgres is running and `.env` is loaded.

---

## Archived Scripts

- `run_batch_with_reports.py`, `generate_all_reports.py`, `run_batch_calculations.py` — removed when v3 of the orchestrator shipped (October 2025).***
