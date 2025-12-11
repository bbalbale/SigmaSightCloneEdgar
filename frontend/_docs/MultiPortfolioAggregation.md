# Multi-Portfolio Aggregation Plan

**Created**: 2025-12-11
**Status**: Planning
**Author**: Claude Code

---

## Executive Summary

This document outlines the plan for implementing true multi-portfolio aggregation across SigmaSight. The goal is to consolidate positions with the same symbol across multiple portfolios and calculate aggregate risk metrics as if all holdings were in a single portfolio.

---

## Current State Analysis (Verified via Playwright Testing)

### How It Works Today

| Page | Aggregate View Behavior | Symbol Consolidation | Risk Metrics |
|------|------------------------|---------------------|--------------|
| **Command Center** | Shows combined metrics, lists all positions separately | No | Weighted average across portfolios |
| **Risk Metrics** | Shows each portfolio SEPARATELY (not aggregated) | No | Per-portfolio only |
| **Research & Analyze** | Consolidates positions by symbol | Yes | Per-position only |

### What the Risk Metrics "All Accounts" View Actually Shows

When selecting "All Accounts" in the Risk Metrics dropdown (verified on Railway production):

1. **Header**: "All Accounts - Combined risk analytics across 2 portfolios"
2. **Info Banner**: "Viewing risk metrics for 2 portfolios. Public portfolios (1) show full analytics. Private portfolios (1) have limited market data."
3. **Public Portfolio Section** ("Demo Family Office Public Growth"):
   - Full Factor Exposures (Ridge + Long-Short Spread factors)
   - Stress Test Scenarios (19 scenarios)
   - Correlation Matrix (12x12 for that portfolio's symbols only)
   - Volatility Analysis
   - Sector Exposure vs S&P 500
   - Beta comparison table
4. **Private Portfolio Section** ("Demo Family Office Private Opportunities"):
   - "Limited Analytics Available" warning
   - No risk metrics (private holdings lack market data)

**KEY INSIGHT: This is NOT aggregation - it's showing each portfolio's metrics separately, stacked vertically.**

### The Current Architecture

The Risk Metrics page (RiskMetricsContainer.tsx) in aggregate view:
- Separates portfolios into public vs private
- Shows FULL metrics for the first public portfolio
- Shows "Limited Analytics" warning for private portfolios
- Does NOT combine positions across portfolios
- Does NOT calculate aggregate risk metrics

### Backend Aggregate Endpoints (Exist but Limited)

The backend has aggregate endpoints at `/api/v1/analytics/aggregate/*`:

| Endpoint | What It Does | Current Usage |
|----------|--------------|---------------|
| `/aggregate/overview` | Total value, portfolio breakdown | Used by Command Center |
| `/aggregate/beta` | Weighted average of portfolio betas | Available but not ideal |
| `/aggregate/volatility` | Weighted average of portfolio vols | Available but not ideal |
| `/aggregate/factor-exposures` | Weighted average factor exposures | Available but not ideal |

**Limitation**: These endpoints calculate weighted averages of PORTFOLIO-LEVEL metrics, not true aggregation from consolidated positions.

### What Command Center Does

`useCommandCenterData.ts` (lines 416-720):
1. Fetches ALL portfolios (line 417)
2. Builds section for each portfolio in parallel (lines 435-448)
3. Combines holdings from all portfolios (lines 459-465)
4. Calculates weighted averages for beta, volatility (lines 550-621)
5. Uses `portfolioService.getAggregateAnalytics()` (line 431)

**Key Point**: Command Center shows all positions separately (not consolidated by symbol).

### What Research & Analyze Does Right

`ResearchAndAnalyzeContainer.tsx` (lines 391-482) DOES consolidate by symbol:
- Groups positions by ticker across all portfolios
- Sums quantities and market values
- Weight-averages entry prices
- Merges tags from all lots

**This is the pattern we should follow for true aggregation.**

---

## True Aggregation Requirements

### What "True Aggregation" Means

If a user has:
- **Portfolio A**: 100 shares of META @ $500
- **Portfolio B**: 50 shares of META @ $520

True aggregation should show:
- **Consolidated**: 150 shares of META @ $506.67 (weighted avg)
- **Risk metrics**: Calculated as if 150 shares in single portfolio

### Mathematical Considerations

#### Simple Aggregations (Current Approach)
These can be done with weighted averages:
- **Beta**: `Σ(Beta_i × Weight_i)` - approximation
- **Volatility**: `Σ(Vol_i × Weight_i)` - approximation (ignores correlations)
- **Factor Exposures**: `Σ(Exposure_i × Weight_i)`

#### True Portfolio Calculations (Requires Position-Level Data)
These need position-level recalculation:
- **Portfolio Volatility**: Needs covariance matrix of all positions
- **Correlation Matrix**: Must include all unique symbols
- **Concentration (HHI)**: Must be calculated on consolidated holdings
- **Sector Exposure**: Must sum by sector across all positions

### The Shadow Portfolio Question

**Question: Do we need a "shadow portfolio" with aggregated holdings?**

**Answer: Yes, for the backend calculation engines to work properly.**

The batch calculation engines (factor exposures, correlations, stress tests, volatility) are designed to operate on a single portfolio's positions. To get TRUE aggregate metrics, we have two approaches:

#### Option A: Virtual Aggregation at API Time
- When aggregate view requested, fetch all positions from all portfolios
- Consolidate by symbol in memory
- Run calculation engines on consolidated position set
- Return results

**Pros:**
- No schema changes
- Always reflects current positions
- No sync issues

**Cons:**
- Expensive calculations on every request
- May have performance issues for large portfolios
- Duplicates calculation logic

#### Option B: Materialized Aggregate Portfolio (Recommended)
- Create a special "aggregate" portfolio per user (marked as `is_aggregate = true`)
- Batch process syncs positions: consolidates all user's positions into this portfolio
- Run standard batch calculations on aggregate portfolio
- Frontend reads from aggregate portfolio in "All Accounts" view

**Pros:**
- Uses existing batch calculation infrastructure
- Pre-computed, fast reads
- Consistent with single-portfolio architecture

**Cons:**
- Requires schema addition (`is_aggregate` flag on portfolios)
- Sync job needed to keep aggregate portfolio in sync
- Slight delay in reflecting position changes (until next sync)

#### Option C: Hybrid Approach
- Virtual aggregation for simple metrics (total value, position list)
- Materialized aggregate portfolio for expensive calculations (correlations, stress tests)

**Recommendation: Option B (Materialized Aggregate Portfolio)** - This approach reuses existing infrastructure and provides the best user experience with pre-computed metrics.

---

## Implementation Plan

### Phase 1: Default to Aggregate View (Quick Win)

**Goal**: Change default from "first portfolio" to "All Accounts"

**Changes:**

1. **portfolioStore.ts** - Change initialization:
```typescript
// Current: selectedPortfolioId defaults based on first portfolio
// New: selectedPortfolioId defaults to null (aggregate view)
selectedPortfolioId: null, // Already the case, but ensure setPortfolios doesn't override
```

2. **AccountFilter.tsx** - Ensure "All Accounts" is default selection

**Effort**: Small (1-2 hours)

---

### Phase 2: Risk Metrics Aggregate View (Medium)

**Goal**: Show true aggregate risk metrics when "All Accounts" selected

**Changes:**

1. **Create `useAggregateRiskMetrics.ts` hook**:
```typescript
export function useAggregateRiskMetrics() {
  const isAggregateView = useIsAggregateView()

  // Only fetch when in aggregate view
  if (!isAggregateView) return { data: null }

  // Call backend aggregate endpoints
  const [beta, volatility, factors, sectorExposure] = await Promise.all([
    analyticsApi.getAggregateBeta(),
    analyticsApi.getAggregateVolatility(),
    analyticsApi.getAggregateFactorExposures(),
    analyticsApi.getAggregateSectorExposure() // NEW endpoint needed
  ])

  return { beta, volatility, factors, sectorExposure }
}
```

2. **Update `RiskMetricsContainer.tsx`**:
```typescript
// In aggregate view, use aggregate hooks instead of single-portfolio hooks
if (isAggregateView && isMultiPortfolio) {
  const aggregateMetrics = useAggregateRiskMetrics()
  // Render aggregate data instead of first portfolio
}
```

3. **Add frontend service methods in `analyticsApi.ts`**:
```typescript
async getAggregateBeta(): Promise<AggregateBetaResponse>
async getAggregateVolatility(): Promise<AggregateVolatilityResponse>
async getAggregateFactorExposures(): Promise<AggregateFactorExposuresResponse>
```

**Backend Changes Needed:**
- Add `/api/v1/analytics/aggregate/sector-exposure` endpoint
- Add `/api/v1/analytics/aggregate/concentration` endpoint
- Consider `/api/v1/analytics/aggregate/correlation-matrix` (complex)

**Effort**: Medium (2-3 days)

---

### Phase 3: Position Consolidation - Command Center (Medium)

**Goal**: Consolidate duplicate symbols in Command Center holdings table

**Changes:**

1. **Update `useCommandCenterData.ts`** - Add consolidation logic:
```typescript
// After line 465, add consolidation
const consolidatedHoldings = consolidateBySymbol(aggregateHoldingsRaw)

function consolidateBySymbol(holdings: HoldingRow[]): ConsolidatedHolding[] {
  const bySymbol = new Map<string, HoldingRow[]>()

  holdings.forEach(h => {
    const existing = bySymbol.get(h.symbol) || []
    bySymbol.set(h.symbol, [...existing, h])
  })

  return Array.from(bySymbol.entries()).map(([symbol, lots]) => ({
    symbol,
    quantity: lots.reduce((sum, l) => sum + l.quantity, 0),
    marketValue: lots.reduce((sum, l) => sum + l.marketValue, 0),
    entryPrice: weightedAverage(lots, 'entryPrice', 'quantity'),
    // ... other consolidated fields
    lots, // Keep original lots for drill-down
    portfolios: [...new Set(lots.map(l => l.account_name))]
  }))
}
```

2. **Update Holdings Table UI**:
- Show consolidated row by default
- Add expand/collapse to see per-portfolio breakdown
- Show "Held in: Portfolio A, Portfolio B" indicator

**Effort**: Medium (2-3 days)

---

### Phase 4: True Aggregate Calculations - Backend (Large)

**Goal**: Calculate risk metrics on consolidated position set

**New Backend Endpoint**: `POST /api/v1/analytics/aggregate/calculate`

```python
@router.post("/calculate")
async def calculate_aggregate_analytics(
    portfolio_ids: Optional[List[UUID]] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate risk analytics on virtually aggregated portfolio.

    1. Fetch all positions from specified portfolios
    2. Consolidate by symbol (sum quantities, weight-avg prices)
    3. Run calculation engines on consolidated position set
    4. Return aggregate metrics
    """
    service = AggregateCalculationService(db)

    # Get all positions
    positions = await service.get_all_positions(
        user_id=current_user.id,
        portfolio_ids=portfolio_ids
    )

    # Consolidate by symbol
    consolidated = service.consolidate_positions(positions)

    # Calculate metrics on consolidated set
    return {
        "sector_exposure": calculate_sector_exposure(consolidated),
        "concentration_hhi": calculate_hhi(consolidated),
        "factor_exposures": calculate_factor_exposures(consolidated),
        "correlation_matrix": calculate_correlation_matrix(consolidated),
        "volatility": calculate_portfolio_volatility(consolidated),
        "beta": calculate_portfolio_beta(consolidated)
    }
```

**Calculation Engine Updates:**
- `calculate_sector_exposure()` - Sum market values by sector
- `calculate_hhi()` - Herfindahl-Hirschman Index on consolidated weights
- `calculate_portfolio_volatility()` - Use covariance matrix (complex)
- `calculate_correlation_matrix()` - Build for all unique symbols

**Effort**: Large (3-5 days)

---

### Phase 5: Correlation Matrix for Aggregate View (Large)

**Challenge**: Current correlation matrix is pre-calculated per portfolio during batch processing.

**Options:**

1. **On-Demand Calculation**: Calculate correlation matrix when aggregate view requested
   - Pros: Always accurate
   - Cons: Slow (needs historical price data for all symbols)

2. **Union of Existing Matrices**: Combine correlation matrices from individual portfolios
   - Pros: Fast
   - Cons: Missing cross-portfolio correlations for symbols only in one portfolio

3. **Expanded Batch Processing**: Calculate correlation for all user's symbols during batch
   - Pros: Pre-computed, fast reads
   - Cons: More batch processing time, storage

**Recommendation**: Option 2 for MVP, then Option 3 for accuracy.

**Effort**: Large (3-5 days)

---

## Summary: Implementation Phases

| Phase | Description | Effort | Priority |
|-------|-------------|--------|----------|
| 1 | Default to aggregate view | Small | High |
| 2 | Risk Metrics aggregate view | Medium | High |
| 3 | Position consolidation (Command Center) | Medium | Medium |
| 4 | True aggregate calculations (Backend) | Large | Medium |
| 5 | Aggregate correlation matrix | Large | Low |

**Total Estimated Effort**: 2-3 weeks

---

## Design Decisions Required

### 1. Default View Behavior

**Question**: Should we default to "All Accounts" for all users?

**Options**:
- A: Always default to aggregate view
- B: Default to aggregate only if multiple portfolios
- C: Remember user's last selection (persisted)

**Recommendation**: Option B - Default to aggregate if multiple portfolios, otherwise show single portfolio.

### 2. Position Consolidation Display

**Question**: How to show consolidated vs. individual positions?

**Options**:
- A: Always consolidated, expand to see per-portfolio breakdown
- B: Toggle between "Consolidated" and "By Account" view
- C: Show consolidated with inline portfolio indicators

**Recommendation**: Option A - Consistent with Research & Analyze pattern.

### 3. Mathematical Accuracy vs. Performance

**Question**: How accurate should aggregate calculations be?

**Options**:
- A: Simple weighted averages (fast, approximate)
- B: True portfolio calculations (slower, accurate)
- C: Hybrid - simple for quick views, accurate for detailed analysis

**Recommendation**: Option C - Start with weighted averages, add accurate calculations for key metrics.

### 4. Correlation Matrix Handling

**Question**: How to handle aggregate correlation matrix?

**Options**:
- A: Don't show in aggregate view (simplest)
- B: Show union of portfolio matrices (fast, incomplete)
- C: Calculate on-demand (slow, accurate)
- D: Pre-calculate during batch (accurate, more processing)

**Recommendation**: Option A for MVP, then Option D.

---

## Technical Notes

### Store Architecture Consideration

The current `portfolioStore` design where `portfolioId` always points to a real portfolio creates the issue. Consider:

```typescript
// Current
portfolioId: string | null  // Always set to first portfolio in aggregate view

// Alternative approach
portfolioId: string | null  // null when in aggregate view
effectivePortfolioId: string | null  // For hooks that need a real ID
```

This would require updating all hooks to handle `portfolioId = null` for aggregate view.

### API Design for Aggregate Endpoints

Current aggregate endpoints use query params for portfolio filtering:
```
GET /api/v1/analytics/aggregate/beta?portfolio_ids=uuid1&portfolio_ids=uuid2
```

Consider adding a simpler pattern:
```
GET /api/v1/analytics/aggregate/beta  // All user's portfolios by default
```

### Caching Strategy

For expensive aggregate calculations:
1. Cache key: `aggregate:{user_id}:{sorted_portfolio_ids_hash}`
2. TTL: 5 minutes (matches position cache)
3. Invalidate on: position changes, new batch calculations

---

## Open Questions

1. Should aggregate view include private portfolios in metrics?
2. How to handle options positions in consolidation (same underlying, different strikes)?
3. Should we show "contribution to aggregate" metrics per portfolio?
4. Performance targets for aggregate calculation endpoints?

---

## Related Documentation

- `frontend/src/stores/portfolioStore.ts` - Multi-portfolio state management
- `frontend/src/hooks/useCommandCenterData.ts` - Current aggregate implementation
- `frontend/src/containers/RiskMetricsContainer.tsx` - Risk metrics display
- `backend/app/api/v1/analytics/aggregate.py` - Backend aggregate endpoints
- `backend/app/services/portfolio_aggregation_service.py` - Aggregation service
