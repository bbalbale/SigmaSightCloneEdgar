# SigmaSight Equity & P&L Remediation Plan

_Last reviewed: 2025-11-04_

## 1. Current Implementation Snapshot
- **Position P&L fallback visibility** – `_calculate_position_pnl` now calls `get_previous_trading_day_price` with a configurable lookback (`backend/app/batch/pnl_calculator.py:360-377`). When the immediate prior close is missing, the calculator walks back up to ten calendar days and logs when a fallback price is used.
- **Market data helper** – `get_previous_trading_day_price` returns both price and price date, enabling diagnostics and reuse (`backend/app/calculations/market_data.py:258-323`). `calculate_daily_pnl` applies the broader lookback and reports daily returns aligned with P&L sign for both long and short positions (`backend/app/calculations/market_data.py:301-359`).
- **Shared valuation function** – `get_position_valuation` centralises multiplier, cost-basis, and unrealised P&L calculations (`backend/app/calculations/market_data.py:105-204`). `get_position_value` delegates to it whenever recalculation is required (`backend/app/calculations/market_data.py:206-229`).
- **Service layer alignment** – `PortfolioAnalyticsService`, `PortfolioDataService`, and `CorrelationService` now rely on the shared valuation helper for all market value and exposure maths (see `backend/app/services/portfolio_analytics_service.py:118-226`, `backend/app/services/portfolio_data_service.py:90-162`, `backend/app/services/correlation_service.py:226-232`, `384-414`, `742-780`, `1058-1124`, `1217-1225`, `1397-1403`). 
- **Regression coverage** – `backend/tests/unit/test_market_data_valuation.py` validates option multipliers, fallback behaviour, short-position daily returns, and analytics aggregation.

## 2. Verified Outcomes
- Position and portfolio P&L no longer collapse to zero when the prior trading day price is absent, provided the price exists elsewhere within the ten-day lookback window.
- Option contracts and short exposures flow correctly through analytics, top-position listings, and correlation weights thanks to the shared valuation helper.
- Unit tests covering the new helper, fallback logic, short-position returns, and analytics aggregation pass under `pytest tests/unit/test_market_data_valuation.py`.

## 3. Remaining Gaps
1. Frontend dashboards have not yet been regression-tested against the corrected APIs; verify charts, leverage cards, and top-position widgets.
2. Historical equity/P&L backfill has not been scheduled. Existing snapshots still reflect the old calculations on days where data gaps suppressed P&L.

## 4. Implementation Status & Next Actions

| Step | Owner | Description | Status |
| --- | --- | --- | --- |
| A | Backend | Harden prior-price lookup for Phase 2 and live market updates | ✅ Completed (`get_previous_trading_day_price`) |
| B | Backend | Provide shared valuation helper with option multiplier support | ✅ Completed (`get_position_valuation`) |
| C | Backend | Refactor analytics/data services to consume the helper | ✅ Completed (analytics/data/correlation services updated) |
| D | Backend | Add regression tests covering options/short scenarios | ✅ Completed (`tests/unit/test_market_data_valuation.py`) |
| E | Frontend | Smoke-test dashboards and analytics cards against updated fields | ⏳ Pending |
| F | Data/QA | Backfill historic snapshots / reconcile NAV trajectories | ⏳ Pending |

## 5. Testing & Verification
- **Unit** – New tests ensure valuation multipliers, fallback prices, short-position daily returns, and analytics aggregation behave correctly (`tests/unit/test_market_data_valuation.py`). 
- **Integration** – Recommended next steps: hit `/api/v1/analytics/overview`, `/api/v1/data/portfolios`, `/api/v1/data/portfolio/{id}/complete`, and correlation endpoints with seeded option-heavy portfolios to confirm consistent outputs.
- **Data reconciliation** – After running the batch with the new logic, compare recalculated snapshots to historical market moves to quantify corrections before executing any backfill.
- **Frontend** – Validate dashboards (exposures, leverage, top positions, correlation summaries) once backend endpoints redeploy.

## 6. Risks & Mitigations
- **Residual data gaps** – Prices outside the ten-day lookback still yield zero P&L. Monitor batch logs and run market data backfills when gaps appear.
- **Service drift** – When introducing new analytics endpoints, ensure they call `get_position_valuation`; run repository-wide audits (`rg "quantity *"`).
- **Historical recalculation cost** – Backfilling multi-year histories can be expensive; execute during maintenance windows and in portfolio batches.

## 7. Immediate Next Steps
1. Coordinate frontend QA to verify UI elements against corrected API responses (Step E).
2. Plan and execute a controlled historical backfill leveraging the enhanced pricing logic (Step F).
3. Prepare a reconciliation plan ahead of the backfill to quantify and communicate equity adjustments.
