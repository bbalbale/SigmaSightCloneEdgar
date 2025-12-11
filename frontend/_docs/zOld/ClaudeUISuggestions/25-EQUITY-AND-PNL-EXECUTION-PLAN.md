# Phase 1 Execution Plan - Equity Changes & P&L Enhancements
**Owners**: Frontend & Backend teams (SigmaSight)
**Created**: 2025-11-04
**Related Docs**: 21-EQUITY-CHANGES-TRACKING-PLAN.md, 22-EQUITY-AND-PNL-TRACKING-SUMMARY.md, 23-REALIZED-PNL-TRACKING-PLAN.md

---

## 1. Current Status Snapshot
- OK: Realized P&L plumbing (Phase 0) is merged (schemas, service logic, batch rollforward).
- Attention: Inline sell flow has been patched to send `close_quantity`; QA pending.
- Blocker: Equity change features are under development on both backend and frontend.

---

## 2. Objectives
1. Stabilize realized P&L UX so inline and side-panel sells produce correct realized events.
2. Deliver equity change tracking end-to-end (database, API, calculator, Command Center UI).
3. Surface capital flows distinctly from P&L in hero metrics and reporting.
4. Ship regression tests plus documentation covering the new flows.

---

## 3. High-Level Timeline (Target ~2.5 weeks)
| Window | Focus | Primary Deliverables |
|--------|-------|----------------------|
| Days 1-2 | Realized P&L polish | Inline sell fix, side panel QA, smoke tests |
| Days 3-7 | Backend equity changes | Migration, model/service/API, calculator update, unit tests |
| Days 8-11 | Frontend equity management | Equity panel, services, hero metrics wiring |
| Days 12-13 | Integration | Command Center refresh triggers, hook updates, end-to-end testing |
| Day 14 | Wrap-up | Diagnostics, documentation, release notes |

---

## 4. Backend Work Breakdown
| Task | Description | Owner | Status | Notes |
|------|-------------|-------|--------|-------|
| Schema - `equity_changes` | Create table + Alembic migration (UUID PK, `portfolio_id`, `change_type`, `amount`, `change_date`, `notes`, timestamps). | Backend | In Progress | Migration added (62b5c8b1d8a3); indexes and snapshot fields included. |
| Models & Schemas | Add SQLAlchemy model plus Pydantic create/update/response schemas. | Backend | In Progress | `EquityChange` model and Pydantic schemas drafted. |
| Service Layer | Implement CRUD service with validation (auth check, future-date guard, withdrawal <= equity, 7-day edit lock). | Backend | In Progress | `EquityChangeService` implemented; integration tests pending. |
| API Endpoints | REST endpoints under `/api/v1/portfolios/{id}/equity-changes` + summary/export endpoints. | Backend | In Progress | FastAPI router scaffolded; needs QA and auth validation review. |
| Calculator Integration | Extend `pnl_calculator` rollforward to include capital flows; persist snapshot fields. | Backend | In Progress | Calculator now adds capital flow to equity rollforward; requires regression run. |
| Portfolio Equity Sync | Ensure `Portfolio.equity_balance` reflects rollforward (P&L + flows). | Backend | Pending | Post-calculator verification still required. |
| Tests | Unit + integration coverage for service, API, calculator. | Backend | Pending | To be written after API stabilises. |
| Diagnostics | CLI script to audit equity changes and capital flow rollforward. | Backend | Pending | New script still needed post-implementation. |

---

## 5. Frontend Work Breakdown
| Task | Description | Owner | Status | Notes |
|------|-------------|-------|--------|-------|
| Inline Sell Fix | Update `HoldingsTableDesktop.handleSellLot` to call `updatePosition` with `close_quantity`; surface toast feedback. | Frontend | Completed | Quantity/price prompts added; type-check passing. |
| Side Panel QA | Confirm `ManagePositionsSidePanel` sell flow handles lot selection and refresh. | Frontend | Pending | Manual QA still required. |
| Equity Actions UI | Build equity contribution/withdrawal panel (or extend sheet) with recent history. | Frontend | Completed | `ManageEquitySidePanel` created with create/delete/export flows. |
| Service Layer | Add `equityChangeService` for list/create/update/delete. | Frontend | Completed | Service implemented with summary + pagination helpers. |
| Data Hook | Extend `useCommandCenterData` to fetch equity summary and recent changes. | Frontend | Completed | Hook now loads capital flow metrics for hero cards. |
| UI Integration | Update `HeroMetricsRow` / `PerformanceMetricsRow` with capital flow callouts. | Frontend | Completed | Hero metrics include net capital flow card; aggregate view aggregates flows. |
| State Management | Persist equity changes in Zustand store if needed. | Frontend | Pending | Not required yet; will revisit if multiple consumers appear. |
| Tests & Stories | Add unit tests for new hook logic and Storybook stories for equity panel. | Frontend | Pending | To be scheduled after functional QA. |

---

## 6. Integration Tasks
- Finalized equity change API contract (`26-EQUITY-AND-PNL-EXECUTION-PLAN.md`).
- CommandCenter refresh path now re-fetches equity data after mutations.
- Permissions audit and logging/telemetry still pending.
- Snapshot backfill strategy still required post-migration.

---

## 7. Testing Strategy
1. Unit tests: backend service validation, calculator scenarios; frontend hook + form validation.
2. Integration tests: equity change API lifecycle (create/list/edit/delete) and inline sell smoke path.
3. Manual QA: sell via side panel and inline button, record contribution/withdrawal, verify hero metrics and snapshots after batch run.

---

## 8. Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Withdrawal validation bug | Negative equity or broken analytics | Enforce service guard and add integration tests. |
| Capital flow summary latency | Slower Command Center experience | Use paginated history + memoised summary (implemented, monitor). |
| Batch ordering changes required | Incorrect rollforward results | Validate calculator sequencing after integration. |
| Refresh inconsistencies in multi-portfolio mode | Stale metrics | Centralized refresh trigger implemented; regression pending. |

---

## 9. Decisions & Clarifications
1. Backdating is allowed: service and calculator handle historical flows.
2. No edits after 7 days: late adjustments require a new entry.
3. Equity change history must be exportable (CSV endpoint implemented).
4. No additional downstream reporting updates needed for legacy `Portfolio.equity_balance` yet.

---

## 10. Next Immediate Actions
1. Run targeted regression on updated inline sell workflow (manual QA pending).
2. Review/discuss equity change API contract draft (`26-EQUITY-AND-PNL-EXECUTION-PLAN.md`); capture backend feedback.
3. Scaffold Alembic migration plus SQLAlchemy model for `equity_changes`. (Done; smoke test remaining.)
4. Align frontend and backend teams on payload validation and error handling before integration tests.

---

*Maintainer: update this plan after each milestone; sync with summary doc (22) weekly.*
