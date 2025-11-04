# SigmaSight Equity & P&L Remediation Plan

## 1. Background
- **Option contracts understated**: Phase 2 of the batch run (`app/batch/pnl_calculator.py`) computes position P&L as `price_change * quantity`, omitting the 100× option contract multiplier. Option-heavy portfolios therefore report only 1 % of their true daily P&L, and rolled equity is suppressed by the same factor.
- **Rolled equity not propagated**: The batch updates `PortfolioSnapshot.equity_balance`, but `Portfolio.equity_balance` remains at the user’s initial NAV. Downstream analytics (factor weighting, sector exposure, target price dollar conversions, etc.) mostly read from the `Portfolio` table, so they continue using stale denominators even after P&L rolls forward.
- **Snapshot `total_value` = gross exposure**: Snapshots store `gross_exposure` in the `total_value` column. When the snapshot refresh service re-computes P&L by comparing `current_value` to the previous snapshot’s `total_value`, heavily hedged portfolios can show spurious P&L swings because long/short netting is ignored.
- **Alternative snapshot paths diverge**: Ad‑hoc snapshot creation (e.g., `snapshot_refresh_service`) bypasses Phase 2’s equity rollforward logic, so on-demand recalculations do not benefit from the same fixes applied in the batch.

## 2. Goals
1. Restore accurate daily and cumulative P&L for all asset classes (stocks, options, shorts, privates).
2. Ensure the authoritative equity balance used across analytics reflects the rolled-forward NAV, with `Portfolio.equity_balance` established as the source of truth.
3. Clarify and/or realign snapshot totals so consumers understand true net asset value vs. gross exposure, storing NAV explicitly.
4. Unify snapshot generation paths to reuse the same validated calculation logic.
5. Provide a backfill plan to repair existing snapshots and equity balances without data loss.

### Non-Goals
- Introducing realized P&L, corporate actions, or fee accounting (tracked separately).
- Rewriting the entire batch orchestrator or changing trading-calendar behavior.
- Frontend UI redesign (limited to adapting to corrected backend fields if needed).

## 3. Current Workflow Summary

| Phase | Responsibility | Key Gap |
| --- | --- | --- |
| 1 – Market Data Collector | Populate `market_data_cache` with latest closes | Correct |
| 2 – P&L Calculator | Roll equity forward using mark-to-market P&L | Misses option multiplier |
| 2.5 – Position MV Update | Write `last_price`, `market_value`, `unrealized_pnl` | Correct multiplier here |
| Snapshot creation | Aggregate exposures, store `total_value`, `daily_pnl`, equity | Uses gross exposure for `total_value`; leaves `Portfolio.equity_balance` stale |
| API services | Combine snapshot data with portfolio table fields | Many services still reading the stale `Portfolio.equity_balance` |

## 4. Proposed Solution Strategy

### 4.1 Correct per-position P&L
- Reuse `app.calculations.market_data.calculate_position_market_value` or the canonical `get_position_value` helper inside `_calculate_position_pnl`.
- Explicitly apply the 100× multiplier for option types when deriving `price_change`.
- Add regression tests that load option positions and validate both unrealized and daily P&L.

### 4.2 Propagate rolled equity (Option A)
- After each successful Phase 2 calculation, persist the rolled-forward NAV back to `Portfolio.equity_balance` within the same transaction. This keeps the portfolio table authoritative and avoids downstream service churn.
- Review transactional boundaries so concurrent writers cannot overwrite the persisted NAV unexpectedly.

### 4.3 Align snapshot totals (store NAV explicitly)
- Replace the overloaded `total_value` field with a clearly named `net_asset_value`, and continue keeping gross and net exposure metrics alongside it.
- Update `_calculate_pnl` (non-batch path) to reference NAV/equity rather than gross exposure when computing returns.
- Coordinate with frontend to adopt the new nomenclature while still presenting both NAV and gross/net exposure in the UI.

### 4.4 Consolidate snapshot generation
- Refactor `snapshot_refresh_service` (and other ad-hoc callers) to invoke `PnLCalculator.calculate_portfolio_pnl` rather than duplicating logic.
- Provide an asynchronous task wrapper that safely executes the batch calculator for a single portfolio/date, reusing Phase 2 validations.

### 4.5 Data repair & validation
- Design a backfill script that:
  1. Recomputes daily P&L for a configurable date range.
  2. Updates `PortfolioSnapshot` equity and P&L fields.
  3. Synchronizes `Portfolio.equity_balance` with the latest snapshot per portfolio.
- Produce before/after metrics (max delta, portfolio-level totals) to confirm accuracy.
- Provide a runnable utility (see `backend/scripts/analysis/backfill_net_asset_value.py`) with dry-run support, portfolio filters, and date-range controls so data teams can safely rerun Phase 2 for historical gaps.

## 5. Implementation Plan

| Step | Owner | Description | Dependencies |
| --- | --- | --- | --- |
| A | Backend | Patch `_calculate_position_pnl` to use canonical valuation and multiplier | None |
| B | Backend | Add regression tests for stock/option/short P&L in `tests/batch` | Step A |
| C | Backend | Update Phase 2 to persist rolled equity back to `Portfolio` (or create equity accessor service) | Step A |
| D | Backend | Rename snapshot `total_value` → `net_asset_value`, adjust calculations, update consumers | Step C |
| E | Backend | Refactor snapshot refresh flow to call Phase 2 logic; add rate limiting guardrails | Steps A–D |
| F | Backend | Write migration/backfill script; dry-run in staging; capture metrics | Steps A–E |
| G | Frontend | Audit usages of `equity_balance`/`total_value`; update to `net_asset_value` while still surfacing gross/net exposure | Steps C–D |
| H | QA/Data | Execute validation suite (unit + integration + data reconciliation) | Steps A–F |

## 6. Testing & Verification
- **Unit tests**: Expand `tests/batch/test_batch_reality_check.py` with option and hedged-portfolio fixtures; assert proper multiplier usage.
- **Integration tests**: Simulate Phase 1–3 run on sample portfolios; compare expected vs. actual equity trajectories.
- **Data reconciliation**: Generate portfolio-level P&L and equity deltas before/after the fix; ensure deviations match the previously missing 100× multiplier or correct netting.
- **Frontend checks**: Regression test dashboards and analytics cards to confirm updated equity numbers do not break formatting, leverage calculations, or charts.

## 7. Deployment & Backfill
1. Ship backend fixes behind feature flag or maintenance window.
2. Run backfill script in staging; verify snapshot counts, equity totals, and option P&L corrections.
3. Repeat in production during low-traffic window; monitor logs for missed price data or batch failures.
4. Notify stakeholders once reconciliation reports show parity with expected NAV history.

## 8. Risks & Mitigations
- **Historical data gaps**: Backfill relies on `market_data_cache`; ensure missing dates are fetched prior to recompute.
- **Concurrent batch runs**: Updating `Portfolio.equity_balance` must be transactional to avoid race conditions with other writers.
- **Frontend assumptions**: UI components may expect `total_value` to equal “portfolio value”; coordinate messaging and potential visual updates before deployment.
- **Performance**: Recomputing multiple years of snapshots can be expensive; run in batches and monitor DB load.

## 9. Open Questions & Current Decisions
1. **Client data surfaces**: We will expose both NAV (`net_asset_value`) and gross/net exposure to clients; frontend updates are required but aligned with current UX goals.
2. **API compatibility**: Renaming to `net_asset_value` constitutes a breaking change; ensure versioned responses or coordinated frontend updates before rollout.
3. **Realized P&L**: A separate initiative will address realized-vs-unrealized splits; implement the fixes here first, then re-evaluate realized P&L requirements.
4. **User communication**: Environment is still in development—no production customer messaging required yet, but document changes for future release notes.

---

**Next Actions**  
Start with Step A (option multiplier fix) and Step C (equity propagation), as they unlock downstream verification and limit further data drift. Once merged, execute the backfill plan and coordinate frontend adjustments.
