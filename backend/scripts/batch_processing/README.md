# Batch Processing Scripts

End-to-end orchestration for nightly portfolio analytics, including market data refresh, fundamentals, P&L roll-forward, and risk analytics. Everything lands in PostgreSQL; the frontend and APIs read directly from the same tables.

---

## Primary Entry Points

| Script | Purpose |
| --- | --- |
| `scripts/batch_processing/run_batch.py` | **Primary batch runner.** Executes all 7 phases (0-6) with automatic backfill detection. Supports date ranges and portfolio filtering. |
| `scripts/automation/railway_daily_batch.py` | **Railway cron job.** Thin wrapper that calls the batch orchestrator directly. Handles trading day detection and logging. |

> Report-generation utilities were retired in October 2025. Consume data through the API or directly from the database.

---

## Daily Workflow

1. Source the backend `.env` (must include `DATABASE_URL`, provider keys, etc.).
2. From the repo root:
   ```bash
   cd backend
   uv run python scripts/batch_processing/run_batch.py
   ```
   This executes the full production pipeline with automatic backfill detection and prints a per-phase summary (symbols fetched, positions updated, analytics counts, and any errors).

3. To backfill specific date ranges or target a subset of portfolios:
   ```bash
   # Backfill specific date range
   uv run python scripts/batch_processing/run_batch.py --start-date 2025-07-01 --end-date 2025-11-07

   # Re-run only for a specific portfolio UUID
   uv run python scripts/batch_processing/run_batch.py --portfolio e23ab931-a033-edfe-ed4f-9d02474780b4
   ```
   `run_batch.py` calls `batch_orchestrator.run_daily_batch_with_backfill()`, which automatically detects and processes any historical gaps.

---

## Phase Breakdown (Batch Orchestrator - Updated 2025-11-09)

The batch orchestrator executes 7 phases in sequence. Each phase is isolated - failures don't cascade to later phases.

| Phase | Description | Key Features |
| --- | --- | --- |
| **Phase 0: Company Profile Sync** | Syncs company profiles (beta values, sector, industry) from FMP. | Runs ONLY on final date (not every backfill date). Provides fresh beta values for analytics. |
| **Phase 1: Market Data Collection** | Fetches EOD prices for all active symbols with 1-year lookback. | YFinance primary, FMP fallback, Polygon for options. Populates `market_data_cache`. |
| **Phase 2: Fundamental Data Collection** | Smart refetch of financial statements and estimates. | Fetches 3+ days after earnings. Gracefully handles "Data not available" from providers. |
| **Phase 3: P&L Calculation & Snapshots** | Rolls forward portfolio equity, calculates daily/MTD/YTD P&L. | Uses cached market values if Phase 1 misses a symbol. Creates `portfolio_snapshots` for trading days only. |
| **Phase 4: Position Market Value Updates** | Updates `positions.last_price`, `market_value`, and `unrealized_pnl`. | Critical for accurate analytics. Keeps exposure calculations current. |
| **Phase 5: Sector Tag Restoration** | Auto-applies sector tags from company profiles. | Enables sector-based filtering in Organize/Explorer views. No-op if tags are current. |
| **Phase 6: Risk Analytics** | Calculates betas, factor exposures, volatility, correlations, stress tests. | Market betas, IR betas, 5 factor exposures (ridge regression), HAR volatility forecasting, correlation matrices. |

### Key Features:
- **Automatic Backfill**: Detects last successful run and fills missing trading days
- **Trading Day Detection**: Automatically adjusts to previous trading day if run before market close (4:30 PM ET) or on non-trading days
- **Phase Isolation**: Failures in one phase don't prevent later phases from running
- **Smart Optimization**: Company profiles and fundamentals only fetch on final date (not every backfill date)
- **Graceful Degradation**: Missing data doesn't stop the batch - calculations proceed with available data

---

## Output Highlights

Key tables and corresponding API endpoints:

| Dataset | Table(s) | Example API |
| --- | --- | --- |
| Portfolio snapshots & exposures | `portfolio_snapshots` | `GET /api/v1/data/portfolio/{id}/complete` |
| Position market values | `positions` (`last_price`, `market_value`, `unrealized_pnl`) | `GET /api/v1/data/positions/details` |
| Company profiles | `company_profiles` | `GET /api/v1/data/company-profile/{symbol}` |
| Market betas | `position_market_betas` | `GET /api/v1/analytics/portfolio/{id}/overview` |
| Interest rate betas | `position_interest_rate_betas` | `GET /api/v1/analytics/portfolio/{id}/factor-exposures` |
| Factor exposures | `position_factor_exposures`, `portfolio_factor_exposures` | `GET /api/v1/analytics/portfolio/{id}/positions/factor-exposures` |
| Correlations | `correlation_calculations` | `GET /api/v1/analytics/portfolio/{id}/correlation-matrix` |
| Sector exposure | Computed from `company_profiles` + `positions` | `GET /api/v1/analytics/portfolio/{id}/sector-exposure` |
| Volatility | Computed with HAR forecasting | `GET /api/v1/analytics/portfolio/{id}/volatility` |
| Stress tests | `stress_test_scenarios`, `stress_test_results` | `GET /api/v1/analytics/portfolio/{id}/stress-test` |

---

## Troubleshooting

### Missing Prices
Phase 1 prints counts for symbols fetched vs. failed. If many failures occur:
- Check YFinance/FMP API status
- Verify API keys in `.env`
- Check symbol validity (some symbols may have been delisted)
- Private positions intentionally skip price updates

### Fundamentals Warnings
Provider strings like "Data not available" are normal and logged as warnings. The batch continues. Check `fundamentals_service.should_fetch_fundamentals()` if a symbol never refreshes (it may not meet the 3+ day post-earnings criteria).

### Risk Analytics Issues
To re-run just Phase 6 after fixing data:
```bash
uv run python -c "
import asyncio
from datetime import date
from app.batch.analytics_runner import analytics_runner
asyncio.run(analytics_runner.run_all_portfolios_analytics(date.today()))
"
```

### Backfill Gaps
The orchestrator automatically detects and fills gaps. To force a specific range:
```bash
uv run python scripts/batch_processing/run_batch.py --start-date 2025-07-01 --end-date 2025-11-07
```

### Trading Day Detection
The orchestrator uses `app.utils.trading_calendar` for NYSE trading days:
- Non-trading days: Automatically adjusts to previous trading day
- Before 4:30 PM ET: Uses previous trading day (market hasn't closed)
- After 4:30 PM ET: Uses current day if it's a trading day

---

## Railway Deployment

The Railway cron job (`scripts/automation/railway_daily_batch.py`) is a thin wrapper that:
1. Fixes Railway's DATABASE_URL format (adds `asyncpg` driver)
2. Calls `batch_orchestrator.run_daily_batch_with_backfill()` directly
3. Logs results and exits with appropriate status code

**No duplicate logic** - Railway uses the exact same batch orchestrator code path as local development.

---

## Archived Scripts

- `run_batch_with_monitoring.py` - Deprecated (use `run_batch.py` instead)
- `run_batch_with_reports.py` - Removed when v3 shipped (October 2025)
- `generate_all_reports.py` - Removed when v3 shipped (October 2025)
- `run_batch_calculations.py` - Removed when v3 shipped (October 2025)
