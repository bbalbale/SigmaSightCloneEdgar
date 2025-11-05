# Phase 1 Execution Plan – Equity Changes & P&L Enhancements  
**Owners**: Frontend & Backend teams (SigmaSight)  
**Created**: 2025-11-04  
**Related Docs**: 21-EQUITY-CHANGES-TRACKING-PLAN.md, 22-EQUITY-AND-PNL-TRACKING-SUMMARY.md, 23-REALIZED-PNL-TRACKING-PLAN.md

---

## 1. Current Status Snapshot
- ✅ **Realized P&L plumbing (Phase 0) is largely implemented**:
  - `UpdatePositionRequest` supports `exit_price`, `exit_date`, `close_quantity`.
  - `PositionService.update_position` records realized events and persists `position_realized_events`.
  - `pnl_calculator` now aggregates daily realized P&L into snapshots.
- ⚠️ **UX gaps remain**:
  - Inline sell action in `HoldingsTableDesktop` does not pass `close_quantity`, so partial sells fail server-side.
  - `ManagePositionsSidePanel` fetches existing lots but equity add/remove flows are not wired.
- ⛔ **Equity change tracking (Phase 1) still planning-only**: no database table, endpoints, or UI yet.

---

## 2. Objectives
1. Fix outstanding realized P&L UX issues so position sells (inline + side panel) drive correct backend updates.
2. Deliver the equity change tracking feature end-to-end (database → API → calculations → Command Center UI).
3. Update analytics/hero metrics so capital flows and P&L are clearly differentiated.
4. Ship regression tests and documentation updates covering the new flows.

---

## 3. High-Level Timeline (Target = 2.5 weeks)
| Window | Focus | Primary Deliverables |
|--------|-------|----------------------|
| **Days 1-2** | Stabilise realized P&L UX | Inline sell fix, side panel QA, smoke tests |
| **Days 3-7** | Backend equity changes | Alembic migration, service + API layer, calculator integration, unit tests |
| **Days 8-11** | Frontend equity management | Equity side panel, hero metrics wiring, portfolio store updates |
| **Days 12-13** | Systems integration | Command Center refresh triggers, aggregator updates, end-to-end testing |
| **Day 14** | Polish & Documentation | Diagnostics dashboard entries, doc updates, release notes |

---

## 4. Backend Work Breakdown
| Task | Description | Owner | Status | Notes |
|------|-------------|-------|--------|-------|
| Schema – `equity_changes` | Create table + Alembic migration (UUID PK, `portfolio_id`, `change_type`, `amount`, `change_date`, `notes`, timestamps) | Backend | Pending | Mirror style of `position_realized_events`; include indices on `(portfolio_id, change_date)` |
| Models & Schemas | Add SQLAlchemy model, Pydantic request/response (`EquityChangeCreateRequest`, `EquityChangeResponse`) | Backend | Pending | Keep enum values `CONTRIBUTION` / `WITHDRAWAL` |
| Service Layer | Implement CRUD service with validation (no future dates, withdrawals ≤ equity, soft delete with window) | Backend | Pending | Reuse logging/permission patterns from `PositionService` |
| API Endpoints | `POST/GET/LIST/PUT/DELETE /api/v1/portfolios/{id}/equity-changes` + summary endpoint for Command Center | Backend | Pending | Follow routing conventions in `app/api/v1/portfolios.py` (or new router if cleaner) |
| Calculator Integration | Extend `pnl_calculator` rollforward: add net capital flows to equity; persist `daily_capital_flows` on snapshots | Backend | Pending | Update `PortfolioSnapshot` model & migration (new fields) |
| Portfolio Equity Sync | Ensure `Portfolio.equity_balance` reflects rollforward (P&L + flows). Add helper to recompute if stale. | Backend | Pending | Update analytics endpoints relying on equity |
| Tests | Unit + integration coverage for service, API, calculator. Include withdrawal > balance edge case. | Backend | Pending | Add snapshot regression test verifying rollforward formula |
| Diagnostics | CLI script to list latest equity changes, validate rollforward totals, feed into Observability docs. | Backend | Pending | Similar to `scripts/verification/verify_demo_portfolios.py` |

---

## 5. Frontend Work Breakdown
| Task | Description | Owner | Status | Notes |
|------|-------------|-------|--------|-------|
| Inline Sell Fix | Update `HoldingsTableDesktop.handleSellLot` to send `close_quantity` & remaining quantity; add toast feedback. | Frontend | Pending | Use `positionManagementService.updatePosition` directly |
| Side Panel QA | Confirm `ManagePositionsSidePanel` sell flow handles lot selection & refresh. Add validation messaging for backend errors. | Frontend | Pending | Ensure `onComplete` triggers `useCommandCenterData` refresh |
| Equity Actions UI | Build `ManageEquitySidePanel` (or extend existing panel) with contribution/withdrawal form + recent history. | Frontend | Pending | Reuse Sheet component, follow doc 21 specs |
| Service Layer | Add `equityChangeService` for new endpoints (list, create, edit, delete). | Frontend | Pending | Mirror `positionManagementService` style |
| Data Hook | Extend `useCommandCenterData` to fetch equity summary (net flows, realized P&L, contributions list). | Frontend | Pending | Introduce memoised selectors for hero metrics |
| UI Integration | Update `HeroMetricsRow` / `PerformanceMetricsRow` to show capital flows vs. P&L. Add equity history widget if time. | Frontend | Pending | Ensure null-safe defaults for aggregate view |
| State Management | Persist equity changes in Zustand store if needed for cross-component access. | Frontend | Pending | Evaluate necessity after hook update |
| Tests & Stories | Add unit tests for new hook logic + Storybook stories for equity side panel. | Frontend | Pending | Focus on error handling + loading states |

---

## 6. Integration Tasks
- **API Contract Finalisation**: confirm request/response payloads for equity changes before front-end wiring.
- **Permissions Audit**: ensure only portfolio owners can mutate equity (align with existing auth guard).
- **Refresh Strategy**: extend `handleRefresh` in `CommandCenterContainer` to also refetch equity changes and metrics after contributions/withdrawals.
- **Snapshot Backfill**: optional job to populate new capital flow fields for historical data (coordinate after migration).
- **Telemetry & Logging**: add structured logs for equity change creation/deletion; surface in monitoring dashboards.

---

## 7. Testing Strategy
1. **Unit Tests**  
   - Backend: service validation, calculator rollforward (contribution + withdrawal scenarios).  
   - Frontend: hook responds to mocked API, form validation for negative amounts, etc.
2. **Integration Tests**  
   - API lifecycle: create → list → edit → delete equity changes.  
   - End-to-end sell flow from UI using Playwright smoke path (optional).
3. **Manual QA Checklist**  
   - Sell a lot via side panel (partial + full) → verify realized P&L updates.  
   - Use inline Sell button → confirm equity + snapshots update after batch run.  
   - Record contribution/withdrawal → hero metrics reflect new equity rollforward.  
   - Cross-day snapshot run to ensure daily realized/net flows show correctly.

---

## 8. Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Incorrect withdrawal validation allowing negative equity | Equity analytics corrupted | Enforce guard in service + add integration test |
| Performance regression when loading equity history | Slower Command Center load | Paginate server-side (limit recent 10) and lazy-load details |
| Batch job ordering issues with new flow fields | Inaccurate rollforward | Update orchestrator docs; ensure Phase 2.5 respects new fields |
| Frontend refresh inconsistencies (multi-portfolio view) | Stale metrics | Use centralized refresh trigger & optimistic updates |

---

## 9. Open Questions
1. Do we need support for backdating contributions/withdrawals prior to existing snapshots-  
2. Should equity changes be editable beyond 7-day window, or is hard delete acceptable-  
3. Do we expose equity change history via analytics API for exports-  
4. Any downstream reporting that relies on legacy `Portfolio.equity_balance` needing adjustment-

Collect answers before mid-sprint to avoid rework.

---

## 10. Next Immediate Actions
1. Fix inline sell flow (`HoldingsTableDesktop`) and add smoke test.
2. Draft API schema for equity changes; circulate for sign-off.
3. Scaffold Alembic migration + SQLAlchemy model.
4. Align frontend/back-end on payload example (JSON contract in doc 21 Appendix).

Once the above are complete, transition to full implementation per work breakdown.

---

*Maintainer: Execution plan to be updated after each milestone. Sync with summary doc (22) weekly.*
