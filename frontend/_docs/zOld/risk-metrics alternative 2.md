# Risk Metrics Overhaul - Planning Summary

**Status:** Approved for execution
**Last Updated:** 2025-10-30

This document captures the key issues we need to resolve before rolling out the refreshed factor and risk analytics stack. The execution plan in `frontend_docs/risk-metrics.md` builds directly on these findings.

---

## 1. Factor Beta Instability

* The 7-factor regression implemented in `calculate_factor_betas_hybrid` is statistically sound but still surfaces high VIF and correlation warnings when the inputs are noisy.【F:backend/app/calculations/factors.py†L298-L340】【F:backend/app/calculations/factors.py†L503-L540】
* Portfolio-level betas are persisted to `factor_exposures`, which means downstream services (risk metrics, stress testing) consume whatever numbers are written there.【F:backend/app/models/market_data.py†L165-L209】
* The current fallback path for missing public positions only returns a "skip" payload, so the API never serves a beta for mixed portfolios with lots of alternatives.【F:backend/app/calculations/factors.py†L365-L408】

**Implication:** We need a deterministic single-factor market beta fallback that works with the existing data structures, instead of bolting on a brand new calculation module.

---

## 2. Risk Metrics API Deferred Status

* The FastAPI endpoint `GET /api/v1/analytics/portfolio/{portfolio_id}/risk-metrics` is still marked `deprecated=True` and warns that the implementation is incomplete.【F:backend/app/api/v1/analytics/portfolio.py†L320-L369】
* `RiskMetricsService` already stitches together volatility, drawdown, and the stored market beta, but it bails out when snapshots are missing and has minimal metadata about data quality.【F:backend/app/services/risk_metrics_service.py†L1-L181】

**Implication:** Before the frontend can rely on this route, we must harden the service, wire up graceful fallbacks, and remove the deprecation banner once validation is in place.

---

## 3. Sector & Concentration Coverage

* We store sector metadata with price records (`MarketDataCache.sector`) but never aggregate it into analytics or expose it through the API.【F:backend/app/models/market_data.py†L10-L55】
* There is no calculation module or service that produces sector weights, Herfindahl-Hirschman Index, or effective position counts—yet the UI roadmap calls for those views on the Risk Metrics page.【F:frontend/app/risk-metrics/page.tsx†L15-L78】

**Implication:** We need a backend calculation pipeline plus an API surface for sector and concentration analytics, then update the React page to consume those results alongside the existing correlation, diversification, and stress testing widgets.

---

## 4. Frontend Integration Gap

* The current page only renders correlation, diversification, and stress test data via existing hooks; market beta, sector exposure, and concentration panels are missing entirely.【F:frontend/app/risk-metrics/page.tsx†L5-L78】
* `analyticsApi.ts` has no helper for risk metrics or sector analytics, so even after the backend is ready the UI cannot call into the endpoint yet.【F:frontend/src/services/analyticsApi.ts†L1-L77】

**Implication:** The execution plan must add the missing API client functions, hooks, and components so the Risk Metrics page reflects the new analytics.

---

## Success Criteria (High Level)

1. **Stable Market Beta:** Frontend displays a market beta sourced from the existing factor pipeline with a reliable single-factor fallback when multivariate regression fails.
2. **Sector & Concentration Analytics:** Backend exposes JSON payloads for sector weights, benchmark comparison, HHI, and top position concentration; frontend renders them with retry handling.
3. **Risk Metrics API Ready:** Endpoint loses the `deprecated` flag and includes validation metadata, making it safe for production consumers.
4. **End-to-End Validation:** Automated scripts (unit tests + analysis utilities) confirm consistent numbers across beta, volatility, drawdown, and sector metrics before the feature flag is removed.

Refer to the execution plan for the step-by-step implementation order.

# Risk Metrics Execution Plan (Updated for Current Codebase)

**Companion Document:** `frontend_docs/RiskMetricsPlanning.md`
**Maintainers:** Risk Analytics squad
**Last Updated:** 2025-10-30

This playbook aligns the risk-metrics overhaul with the code that currently ships in `backend/app` and the Next.js frontend. Follow the phases in order—each includes concrete file targets, validation commands, and rollback notes.

---

## Pre-Flight Checklist

1. **Repository status**
   - Branch: feature branch off latest `main`
   - Ensure `backend/.env` and `frontend/.env.local` contain valid service URLs
2. **Data prerequisites**
   - PostgreSQL seeded with demo data via `uv run python scripts/seed_database.py`
   - Market prices populated for at least 120 trading days (run `uv run python scripts/batch_processing/run_batch.py --jobs market_data,factors` if necessary)
3. **Quick diagnostics**
   - `uv run python scripts/analysis/debug_multivariate_regression.py --portfolio demo-equities` (confirms factor regression health)
   - `uv run python scripts/analysis/analyze_beta_distributions.py --portfolio demo-equities` (baseline beta distribution)

---

## Phase 0 – Stabilize Factor Inputs

> Goal: Guarantee that factor data feeding beta, stress testing, and upcoming sector analytics is sound before layering new metrics.

### 0.1 Confirm hybrid factor pipeline
- **File:** `backend/app/calculations/factors.py`
- **Actions:**
  1. Review `calculate_factor_betas_hybrid` to verify regression window and context loading logic.【F:backend/app/calculations/factors.py†L298-L408】
  2. Inspect multicollinearity diagnostics emitted by `check_multicollinearity` and ensure warnings reproduce current pain points.【F:backend/app/calculations/factors.py†L503-L540】
- **Validation:**
  ```bash
  uv run python scripts/analysis/debug_multivariate_regression.py --portfolio demo-equities
  ```
  Confirm log output enumerates VIF/condition-number results for problematic positions.

### 0.2 Harden skip-path metadata
- **File:** `backend/app/calculations/factors.py`
- **Actions:** Enrich the skip payload returned when no public positions are available so consumers (RiskMetricsService, market risk) can detect the failure reason without blowing up.【F:backend/app/calculations/factors.py†L365-L408】
- **Validation:** Re-run the regression script against a portfolio that only contains PRIVATE assets to confirm the skip payload contains `skip_reason` and `quality_flag` fields.

---

## Phase 1 – Market Beta Fallback & Service Hardening

> Goal: Deliver a deterministic market beta sourced from the existing factor tables with robust fallback logic.

### 1.1 Add single-factor helper
- **File:** `backend/app/calculations/factors.py`
- **Implementation sketch:**
  - Introduce `async def calculate_market_beta_single_factor(...)` that:
    1. Pulls aligned SPY returns using existing `fetch_factor_returns`
    2. Pulls position returns with `calculate_position_returns`
    3. Runs a univariate OLS (use the same `statsmodels` dependency already imported) with beta capping identical to the multivariate flow
    4. Returns `{beta, r_squared, observations, warnings}`
  - Reuse the shared utilities in `factor_utils` for exposure math and beta caps where possible.【F:backend/app/calculations/factor_utils.py†L161-L232】

### 1.2 Wire helper into market risk
- **File:** `backend/app/calculations/market_risk.py`
- **Actions:**
  1. Update `calculate_portfolio_market_beta` to:
     - Attempt `calculate_factor_betas_hybrid` first (current behaviour)
     - If regression quality is poor (e.g., flagged by `quality_flag` or missing Market factor), call the new single-factor helper and persist results in the response payload
  2. Expose metadata including which path executed.
- **Validation:**
  ```bash
  uv run python scripts/analysis/analyze_beta_distributions.py --portfolio demo-equities --include-single-factor
  ```
  Verify the script prints a comparison between multivariate and fallback betas.
- **Reference:** Existing implementation already aggregates portfolio value and factor betas—keep that logic intact.【F:backend/app/calculations/market_risk.py†L56-L118】

### 1.3 Persist fallback betas
- **Files:**
  - `backend/app/calculations/market_risk.py`
  - `backend/app/models/market_data.py`
- **Actions:** When the single-factor path executes, store the exposure in `factor_exposures` with the existing "Market Beta" factor id so downstream consumers remain unchanged.【F:backend/app/models/market_data.py†L187-L209】
- **Validation:** Query the database after a batch run:
  ```sql
  SELECT factor_id, exposure_value, calculation_date, source
  FROM factor_exposures
  WHERE portfolio_id = '<portfolio_uuid>'
  ORDER BY calculation_date DESC
  LIMIT 5;
  ```
  Ensure fallback runs set a flag in the metadata you attach (e.g., `source='single_factor'`).

### 1.4 Expand `RiskMetricsService`
- **File:** `backend/app/services/risk_metrics_service.py`
- **Tasks:**
  1. Attach beta provenance (`beta_source`, `observations`, `r_squared`) returned from Phase 1.1 to the metadata payload.【F:backend/app/services/risk_metrics_service.py†L127-L181】
  2. Surface skip reasons from Phase 0 to the caller instead of silently returning `available=False`.
  3. Add logging that mirrors the stress-test latency logging already present.
- **Validation:**
  ```bash
  uv run python -m pytest tests/services/test_risk_metrics_service.py
  uv run python scripts/analysis/analyze_beta_distributions.py --portfolio demo-hedge
  ```
  Confirm the service includes the metadata and gracefully handles missing snapshots.

---

## Phase 2 – Sector & Concentration Analytics

> Goal: Produce backend analytics for sector weights and concentration metrics that the frontend can consume.

### 2.1 Create calculation module
- **File:** `backend/app/calculations/sector_analysis.py` (new)
- **Responsibilities:**
  - Load active positions for a portfolio (reuse the same filters as `calculate_portfolio_market_beta`).
  - Derive market values via `get_position_market_value` and direction via `get_position_signed_exposure` for net/gross math.【F:backend/app/calculations/factor_utils.py†L161-L217】
  - Join sector data from `MarketDataCache` and fall back to `CompanyProfile` when necessary.【F:backend/app/models/market_data.py†L10-L118】
  - Compute:
    * Portfolio sector weights (dict of sector -> weight)
    * Benchmark comparison against an S&P 500 constant map (store in module)
    * Herfindahl-Hirschman Index (HHI) and effective number of positions
    * Top-n concentration (3 and 10) using sorted exposures
  - Return a structured dict with `data_quality` flags (e.g., unclassified positions array).

### 2.2 Service layer & caching
- **File:** `backend/app/services/sector_analysis_service.py` (new)
- **Tasks:** Wrap the calculation with:
  - Async session handling
  - Optional persistence into `portfolio_snapshots` (JSON column)
  - Graceful degradation when sector metadata is missing
- **Migration:**
  - Create Alembic revision `backend/alembic/versions/<timestamp>_add_sector_metrics_to_snapshots.py`
  - Columns:
    * `portfolio_snapshots.sector_exposure` (JSONB, nullable)
    * `portfolio_snapshots.hhi` (Numeric(10,4))
    * `portfolio_snapshots.effective_positions` (Numeric(10,4))
    * `portfolio_snapshots.top_3_concentration` / `top_10_concentration` (Numeric(10,4))
  - Run `uv run alembic upgrade head` after generating the migration.

### 2.3 Validation scripts
- Add `scripts/analysis/check_sector_exposure.py` that:
  - Loads the service and prints weights vs benchmark
  - Calculates HHI manually for regression testing
- Run command:
  ```bash
  uv run python scripts/analysis/check_sector_exposure.py --portfolio demo-equities
  ```
  Compare numbers with manual Excel calculations.

---

## Phase 3 – API Contract & Schema Updates

> Goal: Make the analytics accessible over the existing API routes and remove the deprecated flag once validation passes.

### 3.1 Extend Pydantic schemas
- **File:** `backend/app/schemas/analytics.py`
- **Updates:**
  - Expand `PortfolioRiskMetrics` with fields for `portfolio_beta_details`, `sector_exposure`, `hhi`, `top_concentration`, etc.
  - Ensure optional typing with `Field(None, description="...")` to preserve backwards compatibility.

### 3.2 Update FastAPI endpoints
- **File:** `backend/app/api/v1/analytics/portfolio.py`
- **Actions:**
  1. Remove `deprecated=True` once Phase 1 & 2 validations succeed.【F:backend/app/api/v1/analytics/portfolio.py†L320-L369】
  2. Inject the sector service results into the response payload alongside the existing volatility/drawdown numbers.
  3. Preserve latency logging style and structured error handling already present for stress testing.【F:backend/app/api/v1/analytics/portfolio.py†L300-L369】

### 3.3 Automated coverage
- **Tests:**
  - Add unit tests under `backend/tests/api/v1/analytics/test_risk_metrics_endpoint.py`
  - Mock the services to simulate:
    * Full data availability
    * Missing snapshots (returns `available=False`)
    * Partial data (beta fallback triggered)
- **Command:** `uv run pytest tests/api/v1/analytics/test_risk_metrics_endpoint.py`

---

## Phase 4 – Frontend Integration

> Goal: Surface the new analytics on the Risk Metrics page with the established service + hook pattern.

### 4.1 API client additions
- **File:** `frontend/src/services/analyticsApi.ts`
- **Changes:**
  - Add `getRiskMetrics(portfolioId: string)` returning `{ data, url }` just like existing helpers.【F:frontend/src/services/analyticsApi.ts†L1-L77】
  - Add `getSectorAnalytics(portfolioId: string)` if sector data is served on a dedicated endpoint.
  - Ensure both attach auth headers via `getAuthHeader()`.

### 4.2 Hook & state management
- **File:** `frontend/src/hooks/useRiskMetrics.ts` (new)
- **Implementation:**
  - Use `usePortfolioData` to fetch the active `portfolioId`
  - Call `analyticsApi.getRiskMetrics`
  - Expose `{ data, loading, error, refetch }` shape consistent with other hooks (`useStressTest`, etc.)

### 4.3 Components
- **Directory:** `frontend/src/components/risk`
- **New components:**
  - `MarketBetaCard.tsx` – displays beta, R², observation count, fallback badges
  - `SectorExposure.tsx` – stacked bar comparing portfolio vs benchmark, list unclassified tickers
  - `ConcentrationSummary.tsx` – HHI, effective positions, top-3/top-10 percentages
- **Styling:** Match Tailwind design tokens already used in `DiversificationScore` and `CorrelationMatrix` components.

### 4.4 Page assembly
- **File:** `frontend/app/risk-metrics/page.tsx`
- **Updates:**
  - Import the new hook + components and render them above the existing sections.【F:frontend/app/risk-metrics/page.tsx†L5-L78】
  - Preserve dark-mode handling via `useTheme`.
  - Add skeleton/loading states for the new cards consistent with other risk widgets.

### 4.5 Frontend validation
- **Commands:**
  ```bash
  cd frontend
  npm run lint
  npm run test -- --runInBand src/hooks/useRiskMetrics.test.tsx
  npm run dev
  ```
  Manually QA the Risk Metrics page at `http://localhost:3005/risk-metrics`.

---

## Phase 5 – End-to-End Verification

1. **Batch run:** `uv run python scripts/batch_processing/run_batch.py --jobs factors,market_risk,sector_analysis`
2. **API smoke:** `uv run python scripts/test_api_endpoints.py --include risk-metrics`
3. **Frontend smoke:** Cypress/Playwright scenario hitting the Risk Metrics page (add to `frontend/tests` suite).
4. **Monitoring hooks:** Add structured logging for fallback activations so observability dashboards highlight when single-factor beta is in play.

---

## Rollout Notes

* Keep the endpoint behind a feature flag until regression and sector analytics have at least 30 consecutive days of data.
* Update `backend/_docs/generated/Calculation_Engine_White_Paper.md` with a short section on the single-factor fallback once deployed.
* Coordinate with the agent team so the OpenAI tool descriptions reference the new analytics payload.

---

Following this plan ensures we reuse the mature factor infrastructure already in place, harden the risk metrics API, and deliver the sector/concentration insights the frontend expects—all without inventing new pipelines that bypass existing tables.