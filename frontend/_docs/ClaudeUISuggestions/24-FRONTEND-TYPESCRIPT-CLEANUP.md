# Frontend TypeScript Cleanup Plan

**Created**: November 4, 2025  
**Status**: In Progress  
**Owner**: Frontend maintainers (Codex support)

---

## Objective
Resolve the outstanding `npm run type-check` failures introduced over time so the frontend regains a clean TypeScript baseline. This plan captures the current errors, groups them by functional area, and outlines the remediation sequence so we can chip away safely within future context windows.

---

## Current Signal
- Command: `npm run type-check`
- Latest run: `tsc-errors.log` (captured November 4, 2025)
- Result: **FAIL** (`ts --noEmit`)

---

## Error Inventory (tsc-errors.log)
| Area | File(s) | Summary |
| --- | --- | --- |
| Onboarding upload state | `app/onboarding/upload/page.tsx` | `uploadState` union narrowed incorrectly (missing `'uploading' | 'processing'`) |
| Portfolio position cards | `src/components/positions/OrganizePositionCard.tsx`, `src/components/portfolio/PortfolioPositions.tsx` | Local `Position` shape drifted from service types (missing `company_name`, optional quantities) |
| Research & analyze tables | `src/components/research-and-analyze/ResearchTableViewDesktop.tsx`, `ResearchTableMobile.tsx` | `EnhancedPosition` interface missing fields (`avg_cost`, `current_market_value`, `unrealized_pnl_percent`, `beta`) |
| Tag components | `src/components/research-and-analyze/StickyTagBar.tsx`, `StickyTagBarMobile.tsx`, `CompactTagBar.tsx` | Tag shape mismatch between store types and `TagBadge` props; `TagBadge` lacks `size` support |
| Command Center data | `src/hooks/useCommandCenterData.ts` | API response interfaces missing fields (`account_name`, `equity_balance`, `ytd_pnl`, etc.) |
| Correlation matrix | `src/hooks/useCorrelationMatrix.ts`, `src/containers/ResearchAndAnalyzeContainer.tsx` | Response interface missing fields (`position_symbols`, `correlation_matrix`, `data_quality`, `min_overlap`) |
| Fundamentals hook | `src/hooks/useFundamentals.ts` | Nullability handling incomplete (multiple `Object is possibly 'null'`) |
| Chat containers/tests | `src/containers/AIChatContainer.tsx`, `tests/chat-auth.test.ts`, `tests/chat-integration.spec.ts` | Store API changes (`portfolioName` removal) and Playwright typings |
| Misc analytics | `src/containers/ResearchAndAnalyzeContainer.tsx` | Diff between documented return types and current API responses |

> See `tsc-errors.log` for the full compiler output.

---

## Plan & Sequencing

### Phase 1: UI Type Corrections (High-confidence fixes)
- [ ] Align onboarding upload state comparisons with `UploadState` union.
- [ ] Refine `TagBadge` props (`size`, drag handlers) and update callers (`CompactTagBar`, `StickyTagBar*`, private position cards).
- [ ] Introduce shared `Position`/`OptionPosition`/`PrivatePosition` view types for portfolio components and ensure services supply matching fields.
- [ ] Extend `EnhancedPosition` DTO in `positionResearchService.ts` with missing analytics fields (`avg_cost`, `current_market_value`, `unrealized_pnl_percent`, `beta`). Adjust table components to use new fields safely.

### Phase 2: Data Contract Updates
- [ ] Update Command Center response types (`PortfolioListItem`, `PortfolioOverviewResponse`, factor exposure responses) to match backend payloads and adjust helper logic.
- [ ] Normalize correlation matrix types (structure for `position_symbols`, `correlation_matrix`, `data_quality`, `min_overlap`) and tighten container rendering.
- [ ] Audit fundamentals hook for nullable responses and add guards or type refinements.

### Phase 3: Test & Store Cleanup
- [ ] Update AI chat containers to the current store API (remove `portfolioName`, use canonical selectors).
- [ ] Ensure Vitest and Playwright typings are correctly declared (`vitest/globals` only; rely on Playwright’s own config for E2E tests).
- [ ] Harden Playwright tests (`chat-auth`, `chat-integration`) by adding explicit typing for route handlers and pruning unused diagnostics.

---

## Tracking Checklist
- [ ] Phase 1 merged, `PortfolioPositions`/`Research*` components compile.
- [ ] Phase 2 merged, Command Center & correlation hooks compile.
- [ ] Phase 3 merged, Vitest/Playwright suites compile without extra type defs.
- [ ] `npm run type-check` passes locally.
- [ ] `npm run lint` executed (once lint config is clarified).

---

## Testing Strategy
1. Incremental `npm run type-check` after each phase.
2. Targeted `npm run test` / `npm run test -- --runInBand` for impacted areas (chat, research analytics, onboarding).
3. Smoke run of key pages (`npm run dev` spot checks) once TypeScript is clean.

---

## Notes & References
- Type-check log: `tsc-errors.log`
- Current tasks executed on November 4, 2025 (see git history / `npm run type-check` output)
- Keep this document update-to-date as errors are resolved or new ones surface.
