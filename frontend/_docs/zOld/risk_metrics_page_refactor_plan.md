# Risk Metrics Page Refactor Plan

## Goals
- Rebuild the risk metrics page hierarchy so users see high‑signal portfolio factor tilts first, mirroring the Command Center hero pattern.
- Group related analytics (spreads, stress scenarios, correlations, volatility, S&P allocations) into a logical north‑to‑south narrative.
- Preserve existing data hooks/services where possible while tightening loading/error UX and adding data provenance callouts.

## Current State Snapshot
- `src/containers/RiskMetricsContainer.tsx` presently renders seven analytics blocks in sequence: volatility, market beta comparison, sector exposure, concentration metrics, diversification score, correlation matrix, stress tests.
- Factor exposures and spread factor analytics live elsewhere (dashboard + Command Center) and are not surfaced, so users miss systematic tilt context on this page.
- Layout spacing is consistent but long; no quick summary at the top; some cards still use legacy styling (`SectorExposure` etc.) rather than the newer hero row visual language.

## Proposed UX Layout (top → bottom)
- **Factor & Spread Hero Cards** – Command Center–style row highlighting the core factor betas (Market, Momentum, Value, Growth, Quality, Size, Low Vol) alongside key spread tilts (Growth-Value, Momentum vs SPY, Size vs SPY, Quality vs SPY). Each hero card shows the beta or spread value only—no dollar exposure, no z-scores.
- **Spread Factor Stack** – Reuse `SpreadFactorCards` just below the hero row for richer context (trend copy, tooltips) while keeping the hero cards concise.
- **Stress Test Scenarios** – Promote the existing `StressTest` component, optionally adding a quick scenario selector/expand all affordance.
- **Correlation Matrix** – Keep `CorrelationMatrix` but collapse default view to top holdings with toggle for full matrix to reduce scroll.
- **Volatility Analysis** – Keep `VolatilityMetrics`; augment with timeframe toggle if data is available (30/90/252d) and highlight portfolio vs benchmark.
- **S&P Sector Allocations** – Reuse `SectorExposure` charts/table, ensuring the copy makes it explicit that benchmark is the S&P 500 and adds gap callouts for top +/- differentials.

## Implementation Plan

### 1. Factor Hero Cards
- Create `FactorExposureHeroRow` (or extend `HeroMetricsRow` via props) that maps `FactorExposure` responses to hero cards.
  - Data source: call `analyticsApi.getPortfolioFactorExposures`, likely via a new `useFactorExposures` hook for parity with other risk hooks.
  - Card layout: reuse `MetricCard` pattern with beta/spread rounded to 2 decimal places and color coding for >0 (overweight) vs <0 (underweight). No dollar exposure lines.
  - Include data quality badge using `data.metadata` if provided (staleness timestamp, calculation batch).

### 2. Page Composition Updates
- Update `RiskMetricsContainer.tsx`:
  - Inject the new hook and render hero row as the first section.
  - Move/insert `SpreadFactorCards` directly under hero row (requires importing and invoking `useSpreadFactors`).
  - Reorder existing sections to match desired stack.
- Push `MarketBetaComparison` to the bottom of the page pending redesign.
  - Audit spacing to avoid repeated `px-4 py-8`; consider shared section shell helper for consistency.
- Review each component for command-center palette alignment (backgrounds, borders) and adjust classes where needed to match the newer themed styles.

### 3. UX Polish & Observability
- Add loading skeletons/spinners consistent with hero cards and spread cards.
- Surface API source endpoints in dev mode (console debug) to aid troubleshooting.
- Ensure retry buttons remain on the heavy-calculation cards (`StressTest`, `CorrelationMatrix`, `VolatilityMetrics`, `SectorExposure`).
- Include at least one inline helper tooltip/description per section clarifying how to interpret the metric (e.g., “Spread > 0 ⇒ long first leg”).

### 4. QA & Validation
- Cross-check interactions using seeded demo portfolios (balanced, HNW, hedge fund) to make sure all calculations populate.
- Validate responsiveness at breakpoints: hero cards wrap cleanly on mobile, tables remain horizontally scrollable.
- Run `npm run lint` / `npm run type-check` and targeted jest tests if they exist for hooks.

## Risk Metric Calculation Enhancements (Roadmap Ideas)
- **Factor Depth & Stability** – Add rolling time-series for factor betas (e.g., 60d trailing) and compute z-score vs 1-year mean to highlight drift. Requires backend to persist historical factor_exposures.
- **Spread Attribution** – Extend spread endpoints to include contribution to portfolio return/variance so cards can display impact, not just level.
- **Volatility Decomposition** – Calculate ex-ante factor model variance (systematic vs idiosyncratic) and show contribution pie.
- **Scenario Library Expansion** – Introduce macro scenarios (rate shocks, credit widening) and allow user-saved stress templates.
- **Correlation Context** – Attach statistical significance/confidence and highlight pairs with correlation regime shifts (large delta vs 90d average).
- **S&P Benchmark Customization** – Allow alternative benchmarks (sector ETF, MSCI World) and compute relative sector gaps automatically.
- **Alerting** – Flag metrics breaching guardrails (e.g., net exposure > 150%, beta > 1.3, spread > ±1σ) and surface notifications in hero row.

## Dependencies & Risks
- Factor exposures endpoint must remain performant; we may need to gate hero cards until analytics batch completes to avoid blank top sections.
- Spread factors currently rely on batch job output; ensure backend returns metadata (as-of timestamp) for clarity.
- Reordering sections could break deep links or tests; audit any e2e/visual tests referencing DOM sequence.

## Questions / Follow-Ups
- Should hero cards show beta only, or include both beta and dollar exposure with mini sparklines?
- Do we want to keep `MarketBetaComparison` anywhere, or fold its insights into the hero section tooltips?
- Are there specific stress scenarios or spreads we should prioritize for hedge-fund users beyond the current four standard factors?
