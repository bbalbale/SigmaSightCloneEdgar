# Multi-Account Aggregation: Planning Overview

**Feature Name:** Multi-Account Portfolio Aggregation
**Created:** 2025-11-01
**Status:** Planning Phase
**Estimated Effort:** 6-8 weeks

---

## Executive Summary

This document captures the planning discussion and approach for implementing multi-account aggregation in SigmaSight. Users will be able to view multiple brokerage accounts (portfolios) in a single unified dashboard, with risk analytics calculated both per-account and in aggregate.

### Use Case

**Primary Goal:** Enable users with multiple brokerage accounts to view consolidated portfolio analytics across all accounts.

**Example User:**
- Has Fidelity taxable account ($500k, 25 positions)
- Has Schwab IRA ($300k, 15 positions)
- Has 401(k) account ($200k, 10 positions)
- Wants to see total household net worth and risk metrics

**Key Insight:** This is NOT a portfolio switching feature - it's an aggregation feature. Users view all accounts simultaneously with optional filtering.

---

## Current Architecture Analysis

### Database Schema (Current State)

**Current Relationship:** One-to-One (Enforced)
```python
# User → Portfolio relationship
User (1) ──unique──> (1) Portfolio

# Enforced by:
user_id: Mapped[UUID] = mapped_column(..., unique=True)
UniqueConstraint('user_id', name='uq_portfolios_user_id')
portfolio: Mapped["Portfolio"] = relationship(..., uselist=False)
```

**What Exists:**
- ✅ Each user has exactly one portfolio
- ✅ Portfolio created during user registration
- ✅ Database constraint prevents multiple portfolios
- ✅ SQLAlchemy ORM enforces one-to-one relationship

**What Needs to Change:**
- ❌ Remove unique constraint on `user_id`
- ❌ Change ORM relationship to one-to-many (`uselist=True`)
- ❌ Add account metadata fields (`account_name`, `account_type`)
- ✅ Keep all existing calculation engines (no changes needed!)

### Backend API Analysis

**Endpoints That Exist:**
- ✅ `GET /api/v1/data/portfolios` - Returns array (future-proofed!)
- ✅ Portfolio ownership validation
- ✅ Default portfolio resolution logic

**Endpoints Missing:**
- ❌ `POST /api/v1/portfolios` - Create new account
- ❌ `PUT /api/v1/portfolios/{id}` - Update account details
- ❌ `DELETE /api/v1/portfolios/{id}` - Remove account

**Endpoints to Modify:**
- 🔧 All analytics endpoints - support optional `portfolio_id` parameter
  - No `portfolio_id` → aggregate across all accounts
  - With `portfolio_id` → single account view

### Frontend Architecture Analysis

**State Management (Current):**
```typescript
interface PortfolioStore {
  portfolioId: string | null        // Single portfolio
  portfolioName: string | null
  setPortfolio: (id: string) => void
}
```

**What Exists:**
- ✅ `portfolioService.getPortfolios()` - Service method for listing
- ✅ `PortfolioSelectionDialog` component (non-functional demo)
- ✅ Service layer infrastructure

**What Needs to Change:**
- ❌ Store multiple portfolios in Zustand
- ❌ Support aggregate view (no filter) vs filtered view
- ❌ Show account breakdown in UI
- ❌ Add account column to positions tables

---

## Technical Approach: Portfolio-as-Asset Aggregation

### Core Concept

**Key Architectural Decision:** Treat each portfolio as a conceptual investment unit for aggregation purposes.

**Two-Tier Analytics:**

**Tier 1: Per-Portfolio Analytics** (Existing Logic)
```python
Portfolio A (Fidelity Taxable):
  - Total Value: $500,000
  - Beta: 1.2
  - Volatility: 20%
  - Sharpe Ratio: 1.4
  - Positions: 25 positions (AAPL, MSFT, NVDA, etc.)

Portfolio B (Schwab IRA):
  - Total Value: $300,000
  - Beta: 0.8
  - Volatility: 15%
  - Sharpe Ratio: 1.2
  - Positions: 15 positions (AAPL, SPY, BND, etc.)

Portfolio C (401k):
  - Total Value: $200,000
  - Beta: 1.0
  - Volatility: 18%
  - Sharpe Ratio: 1.3
  - Positions: 10 positions (Target Date Fund, etc.)
```

**Tier 2: Aggregate Analytics** (New Logic)
```python
# Treat each portfolio as a single "asset" with its calculated metrics
# Aggregate using weighted averages based on portfolio value

Total Portfolio Value: $1,000,000

Weighted Beta:
  = (1.2 × $500k/$1M) + (0.8 × $300k/$1M) + (1.0 × $200k/$1M)
  = (1.2 × 0.5) + (0.8 × 0.3) + (1.0 × 0.2)
  = 0.6 + 0.24 + 0.2
  = 1.04

Weighted Volatility:
  = (20% × 0.5) + (15% × 0.3) + (18% × 0.2)
  = 10% + 4.5% + 3.6%
  = 18.1%

Weighted Sharpe:
  = (1.4 × 0.5) + (1.2 × 0.3) + (1.3 × 0.2)
  = 1.32
```

### Why This Approach is Better

**Advantages:**
1. ✅ **No changes to existing calculation engines** - All per-portfolio analytics work as-is
2. ✅ **Simpler aggregation logic** - Just weighted averages, not complex position merging
3. ✅ **Better performance** - Calculate once per portfolio, not all positions combined
4. ✅ **Clearer mental model** - "I have 3 accounts with these characteristics"
5. ✅ **Easier to implement** - Reuse existing code, add thin aggregation layer
6. ✅ **More intuitive for users** - See both account-level and total metrics
7. ✅ **Handles duplicate positions naturally** - AAPL in multiple accounts is fine

**Complexity Comparison:**

**Position-Level Aggregation (Rejected):**
```python
# Would need to:
1. Fetch ALL positions across ALL portfolios
2. Merge positions by symbol (AAPL + AAPL + AAPL = 1 position)
3. Recalculate correlations on merged positions
4. Recalculate betas on merged positions
5. Handle sector exposure merging
6. Complex caching strategy
7. Changes to ALL calculation engines
```

**Portfolio-Level Aggregation (Accepted):**
```python
# Much simpler:
1. Fetch portfolio-level analytics (already calculated)
2. Calculate weighted averages
3. Done!
```

---

## Implementation Strategy

### Phase 1: Database Migration (Week 1)
**Goal:** Enable one-to-many User → Portfolio relationship

**Changes:**
1. Remove unique constraint on `portfolios.user_id`
2. Add `account_name` column (e.g., "Fidelity", "Schwab IRA")
3. Add `account_type` column (e.g., "taxable", "ira", "401k", "roth_ira")
4. Change ORM relationship to `uselist=True`
5. Migrate existing portfolios (keep as-is, set account_name from name)

**Risk:** Low - Additive changes only, existing data preserved

### Phase 2: Backend API Extensions (Week 2-3)
**Goal:** Add portfolio CRUD and aggregation endpoints

**New Endpoints:**
```python
POST   /api/v1/portfolios                    # Create account
PUT    /api/v1/portfolios/{id}               # Update account
DELETE /api/v1/portfolios/{id}               # Remove account
GET    /api/v1/analytics/aggregate           # Aggregate analytics (NEW)
```

**Modified Endpoints:**
```python
# All existing analytics endpoints support optional portfolio_id:
GET /api/v1/analytics/overview?portfolio_id={id}  # Single account
GET /api/v1/analytics/overview                     # All accounts (aggregate)
```

**New Service:**
```python
# app/services/portfolio_aggregation_service.py
class PortfolioAggregationService:
    async def get_aggregate_analytics(user_id: UUID) -> AggregateAnalytics:
        """
        Calculate weighted average metrics across all user's portfolios.
        Treats each portfolio as a conceptual asset.
        """
        portfolios = await get_user_portfolios(user_id)

        # Get per-portfolio analytics (existing calculations)
        portfolio_analytics = []
        for portfolio in portfolios:
            analytics = await get_portfolio_analytics(portfolio.id)
            portfolio_analytics.append(analytics)

        # Aggregate using weighted averages
        total_value = sum(p.total_value for p in portfolio_analytics)

        weighted_beta = sum(
            p.beta * (p.total_value / total_value)
            for p in portfolio_analytics
        )

        weighted_volatility = sum(
            p.volatility * (p.total_value / total_value)
            for p in portfolio_analytics
        )

        return AggregateAnalytics(
            total_value=total_value,
            beta=weighted_beta,
            volatility=weighted_volatility,
            portfolios=portfolio_analytics  # Include breakdown
        )
```

**Risk:** Low-Medium - New endpoints are additive, existing endpoints modified carefully

### Phase 3: Frontend State Management (Week 3-4)
**Goal:** Support multiple portfolios in Zustand store

**Store Refactor:**
```typescript
interface PortfolioStore {
  // Multiple portfolios
  portfolios: PortfolioListItem[]

  // Filter state (null = show all accounts)
  selectedPortfolioId: string | null

  // Actions
  setPortfolios: (portfolios: PortfolioListItem[]) => void
  setFilter: (id: string | null) => void

  // Computed
  getTotalValue: () => number
  getActivePortfolios: () => PortfolioListItem[]  // Filtered or all
}
```

**Data Flow:**
```
1. Login → Load all user portfolios
2. Set selectedPortfolioId = null (aggregate view)
3. Fetch aggregate analytics
4. Display all accounts with breakdown
5. User can optionally filter to single account
```

**Risk:** Low - State management is straightforward

### Phase 4: Frontend UI Components (Week 4-5)
**Goal:** Build aggregation UI

**New Components:**
1. `AccountSummaryCard` - Shows total value and breakdown by account
2. `AccountFilter` - Dropdown to filter by account (optional)
3. `AccountManagementPage` - CRUD for accounts
4. Updated `PositionsTable` - Add "Account" column

**Example UI:**
```typescript
<Dashboard>
  {/* Total across all accounts */}
  <AccountSummaryCard>
    <div className="total">
      <h2>Total Portfolio Value</h2>
      <div className="value">$1,000,000</div>
      <div className="pnl">+$12,500 (+1.25%)</div>
    </div>

    {/* Breakdown by account */}
    <div className="breakdown">
      <h3>Account Breakdown</h3>
      {portfolios.map(p => (
        <AccountRow key={p.id}>
          <span>{p.account_name}</span>
          <span>{formatCurrency(p.total_value)}</span>
          <span>{(p.total_value / totalValue * 100).toFixed(1)}%</span>
        </AccountRow>
      ))}
    </div>
  </AccountSummaryCard>

  {/* Aggregate risk metrics */}
  <RiskMetricsCard>
    <Metric label="Portfolio Beta" value={aggregateMetrics.beta} />
    <Metric label="Volatility" value={aggregateMetrics.volatility} />
    <Metric label="Sharpe Ratio" value={aggregateMetrics.sharpe} />
  </RiskMetricsCard>
</Dashboard>
```

**Risk:** Low - UI components are straightforward

### Phase 5: Testing & Rollout (Week 5-6)
**Goal:** Comprehensive testing with multiple accounts

**Test Scenarios:**
1. User with 1 account (backward compatibility)
2. User with 3 accounts (typical case)
3. User with 10 accounts (stress test)
4. Create/update/delete accounts
5. Filter to single account
6. Aggregate analytics accuracy
7. Performance with multiple accounts

**Migration Strategy:**
1. Deploy database migration (non-breaking)
2. Deploy backend API (backward compatible)
3. Deploy frontend (progressive enhancement)
4. Enable feature for beta users
5. Monitor performance and accuracy
6. Full rollout

**Risk:** Low - Gradual rollout with rollback plan

---

## Key Architectural Decisions

### 1. Default View: Aggregate (All Accounts)

**Decision:** Default to showing all accounts aggregated.

**Rationale:**
- ✅ Matches primary use case (household net worth view)
- ✅ Reduces cognitive load (one number to focus on)
- ✅ User can filter to single account if needed

**Implementation:**
```typescript
// On login, set filter to null (all accounts)
useEffect(() => {
  setFilter(null)  // Show aggregate view
}, [])
```

### 2. Portfolio-as-Asset Aggregation

**Decision:** Calculate risk metrics per portfolio, then aggregate using weighted averages.

**Rationale:**
- ✅ Reuses existing calculation engines (no changes!)
- ✅ Simpler math (weighted averages)
- ✅ Better performance
- ✅ Clearer mental model

**Implementation:**
```python
# Per-portfolio (existing):
portfolio_analytics = await calculate_portfolio_analytics(portfolio_id)

# Aggregate (new):
aggregate_analytics = await calculate_aggregate_analytics(user_id)
# → Weighted average of portfolio_analytics
```

### 3. Position Display: Show Account Column

**Decision:** Display positions with account name, do NOT merge duplicate symbols.

**Rationale:**
- ✅ Users want to see which account holds which positions
- ✅ Important for tax planning (taxable vs IRA)
- ✅ Clearer than merged view

**Implementation:**
```typescript
// Positions table
<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Symbol</TableHead>
      <TableHead>Account</TableHead>  {/* NEW */}
      <TableHead>Quantity</TableHead>
      <TableHead>Value</TableHead>
      <TableHead>Weight (Account)</TableHead>
      <TableHead>Weight (Total)</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {positions.map(p => (
      <TableRow key={p.id}>
        <TableCell>{p.symbol}</TableCell>
        <TableCell>{p.portfolio.account_name}</TableCell>
        <TableCell>{p.quantity}</TableCell>
        <TableCell>{formatCurrency(p.value)}</TableCell>
        <TableCell>{p.weight_in_portfolio}%</TableCell>
        <TableCell>{p.weight_in_total}%</TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

### 4. Account Types for Future Tax Features

**Decision:** Add `account_type` field now for future tax-aware analytics.

**Types:**
- `taxable` - Regular brokerage account
- `ira` - Traditional IRA
- `roth_ira` - Roth IRA
- `401k` - 401(k) or 403(b)
- `sep_ira` - SEP IRA
- `simple_ira` - SIMPLE IRA
- `hsa` - Health Savings Account
- `529` - 529 Education Savings

**Future Features:**
- Pre-tax vs post-tax values
- Tax implications of rebalancing
- RMD calculations
- Asset location optimization

### 5. Account Limits

**Decision:** Limit to 20 accounts per user initially.

**Rationale:**
- ✅ Covers 99% of use cases (most users have 2-5 accounts)
- ✅ Prevents performance issues
- ✅ Can increase limit later if needed

**Implementation:**
```python
# Validation in create endpoint
if len(user.portfolios) >= 20:
    raise HTTPException(
        status_code=400,
        detail="Maximum of 20 accounts per user"
    )
```

### 6. Progressive Disclosure for Single-Portfolio Users

**Decision:** Hide multi-portfolio features when user has only 1 portfolio.

**Rationale:**
- ✅ **Backward compatible** - Existing users (all have 1 portfolio) see clean, familiar UI
- ✅ **No confusing UI** - No "100%" breakdowns or redundant account filters
- ✅ **Progressive enhancement** - Features appear when user creates 2nd portfolio
- ✅ **Simplified onboarding** - New users start with simple UI
- ✅ **Adaptive** - UI complexity scales with user's portfolio count

**What Changes for Single-Portfolio Users:**

**Hidden Elements:**
- Account filter dropdown (only 1 account to select)
- Account breakdown section (100% is redundant)
- Account column in positions table (all positions in same account)
- "Across N accounts" messaging

**Simplified Elements:**
- "Total Portfolio Value" → "Portfolio Value"
- Show account name as subtitle, not in breakdown
- Prominent "Add Another Account" button for discovery

**Implementation:**
```typescript
// Conditional rendering based on portfolio count
const portfolios = usePortfolioStore(state => state.portfolios)
const isSinglePortfolio = portfolios.length === 1

if (isSinglePortfolio) {
  // Simplified single-portfolio view
  return <SimplifiedPortfolioCard />
} else {
  // Full multi-portfolio view with aggregation
  return <AggregatePortfolioCard />
}
```

**User Experience Scenarios:**

**Scenario 1: Existing User (1 Portfolio) After Migration**
```
✅ Portfolio Value: $500,000 (Fidelity)
✅ Same metrics as before (no change!)
✅ Simple, clean UI (no clutter)
✅ "Add Another Account" button (discovery)
✅ No confusing 100% breakdown
✅ No redundant account filter
```

**Scenario 2: User Creates 2nd Portfolio**
```
1. User clicks "Add Another Account"
2. Creates "Schwab IRA" portfolio
3. UI automatically expands to show:
   ✅ Account breakdown (Fidelity 60%, Schwab 40%)
   ✅ Account filter dropdown
   ✅ Account column in positions table
   ✅ Aggregate metrics
```

**Scenario 3: User Deletes Down to 1 Portfolio**
```
1. User has 3 portfolios, deletes 2
2. UI automatically simplifies:
   ✅ Hide account filter
   ✅ Hide account breakdown
   ✅ Remove account column
   ✅ Show simple "Portfolio Value"
```

**Mathematical Correctness:**
```python
# Weighted averages work perfectly with n=1
Portfolio A: Value=$500k, Beta=1.2

Weight A = $500k / $500k = 1.0

Aggregate Beta = 1.2 × 1.0 = 1.2  ✅ Identical to portfolio beta!
```

**Backend Impact:** None - Backend aggregation service handles n=1 automatically (weighted average with single item = that item)

**Frontend Effort:** ~2-3 hours additional work in Phase 4

---

## Data Model Changes

### Before (Current)
```python
class User(Base):
    id: UUID
    portfolio: Mapped["Portfolio"] = relationship(..., uselist=False)
    # ONE portfolio per user

class Portfolio(Base):
    id: UUID
    user_id: UUID = mapped_column(..., unique=True)  # UNIQUE constraint
    name: str
    total_value: Decimal
```

### After (Multi-Account)
```python
class User(Base):
    id: UUID
    portfolios: Mapped[List["Portfolio"]] = relationship(..., uselist=True)
    # MANY portfolios per user

class Portfolio(Base):
    id: UUID
    user_id: UUID = mapped_column(..., unique=False)  # UNIQUE removed
    name: str  # Keep for backward compatibility
    account_name: str  # NEW: "Fidelity", "Schwab IRA"
    account_type: str  # NEW: "taxable", "ira", "401k"
    total_value: Decimal
    is_active: bool  # NEW: Can hide accounts
```

---

## API Changes Summary

### New Endpoints
```python
POST   /api/v1/portfolios
PUT    /api/v1/portfolios/{id}
DELETE /api/v1/portfolios/{id}
GET    /api/v1/analytics/aggregate  # Aggregate analytics
```

### Modified Endpoints
```python
# All analytics endpoints support optional portfolio_id parameter:

# Before (current):
GET /api/v1/analytics/overview
→ Returns analytics for user's single portfolio

# After (multi-account):
GET /api/v1/analytics/overview
→ Returns AGGREGATE analytics across all accounts

GET /api/v1/analytics/overview?portfolio_id={id}
→ Returns analytics for single account
```

### Unchanged Endpoints
```python
# These already return lists, no changes needed:
GET /api/v1/data/portfolios
GET /api/v1/data/positions
```

---

## User Experience Flow

### Login and Initial View
```
1. User logs in
2. Backend loads all portfolios for user
3. Frontend sets filter to null (aggregate view)
4. Dashboard shows:
   - Total value across all accounts: $1,000,000
   - Account breakdown: Fidelity $500k, Schwab $300k, 401k $200k
   - Aggregate risk metrics: Beta 1.04, Volatility 18.1%
```

### Viewing Single Account
```
1. User selects "Fidelity" from account filter
2. Frontend sets filter to Fidelity portfolio_id
3. Dashboard shows:
   - Fidelity account value: $500,000
   - Fidelity risk metrics: Beta 1.2, Volatility 20%
   - Positions in Fidelity account only
```

### Creating New Account
```
1. User clicks "Add Account" button
2. Modal opens with form:
   - Account Name: [Vanguard IRA]
   - Account Type: [IRA ▼]
3. User submits
4. Backend creates new portfolio
5. Frontend refreshes portfolio list
6. New account appears in account breakdown
```

### Managing Accounts
```
1. User navigates to /account-management page
2. Sees list of all accounts:
   - Fidelity Taxable ($500k) [Edit] [Delete]
   - Schwab IRA ($300k) [Edit] [Delete]
   - 401k ($200k) [Edit] [Delete]
3. Can rename accounts
4. Can change account types
5. Can delete accounts (soft delete, preserves history)
```

---

## Performance Considerations

### Query Optimization
```python
# Efficient loading of portfolios with analytics
async def get_user_portfolios_with_analytics(user_id: UUID):
    # Single query with join
    stmt = (
        select(Portfolio)
        .options(
            selectinload(Portfolio.positions),
            selectinload(Portfolio.analytics)
        )
        .where(Portfolio.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalars().all()
```

### Caching Strategy
```python
# Cache per-portfolio analytics (existing)
cache_key = f"portfolio:{portfolio_id}:analytics"
ttl = 300  # 5 minutes

# Cache aggregate analytics (new)
cache_key = f"user:{user_id}:aggregate_analytics"
ttl = 300  # 5 minutes

# Invalidate on:
# - Position changes
# - Market data updates
# - Portfolio creation/deletion
```

### Scalability Estimate
```
User with 5 accounts, 20 positions each = 100 total positions
- Per-portfolio analytics: 5 queries (existing)
- Aggregate calculation: O(5) weighted average
- Total query time: ~100ms
- Acceptable performance
```

---

## Risk Assessment

### Technical Risks

**Database Migration** - Medium Risk
- **Risk:** Removing unique constraint requires migration
- **Mitigation:** Test migration thoroughly in dev, stage
- **Rollback:** Keep migration reversible

**Analytics Accuracy** - Low Risk
- **Risk:** Weighted average calculations could be wrong
- **Mitigation:** Comprehensive unit tests, validation with known data
- **Rollback:** Easy to fix (just math)

**Frontend State Complexity** - Low Risk
- **Risk:** State synchronization issues
- **Mitigation:** Clear data flow, use existing patterns
- **Rollback:** Feature flag to disable

### User Experience Risks

**Confusion About Aggregation** - Low Risk
- **Risk:** Users don't understand what "aggregate" means
- **Mitigation:** Clear UI labels, account breakdown visible
- **Rollback:** Add onboarding tooltip

**Performance with Many Accounts** - Low Risk
- **Risk:** Slow with 10+ accounts
- **Mitigation:** Caching, query optimization, 20 account limit
- **Rollback:** Reduce limit if needed

---

## Success Metrics

### Adoption Metrics
- % of users who create 2+ accounts
- Average accounts per user
- % of users viewing aggregate vs filtered view

### Performance Metrics
- API response time for aggregate analytics
- Page load time for dashboard with multiple accounts
- Cache hit rate for portfolio analytics

### Engagement Metrics
- Time spent on aggregate view vs filtered view
- Account switching frequency
- Position viewing patterns (across accounts vs per-account)

---

## Future Enhancements

### Phase 2 Features (Post-Launch)
1. **Cross-Account Position Aggregation**
   - Show "You own AAPL in 3 accounts" summary
   - Aggregate P&L for same symbol across accounts

2. **Tax-Aware Analytics**
   - Pre-tax vs post-tax values
   - Tax loss harvesting opportunities
   - Asset location optimization

3. **Account Comparison View**
   - Side-by-side comparison of accounts
   - Performance attribution by account
   - Rebalancing recommendations across accounts

4. **Bulk Position Import**
   - Import CSV for entire account
   - Sync with brokerage (future integration)

5. **Account-Level Benchmarking**
   - Compare IRA vs taxable performance
   - Track account-specific goals

---

## Questions and Open Issues

### Resolved
- ✅ How to aggregate risk metrics? → Portfolio-as-asset weighted averages
- ✅ Default view? → Aggregate (all accounts)
- ✅ Position merging? → No merging, show account column
- ✅ Account limits? → 20 accounts per user

### To Be Decided
- ❓ Should we allow setting a "primary" account for single-account workflows?
- ❓ Do we need account-level goals/targets?
- ❓ Should we support account groups (e.g., "Retirement Accounts" group)?
- ❓ How to handle closing an account with positions? (Soft delete? Archive?)

---

## Timeline

| Week | Phase | Deliverables |
|------|-------|-------------|
| 1 | Database Migration | Schema changes, ORM updates, test migration |
| 2-3 | Backend APIs | Portfolio CRUD, aggregation service, endpoint updates |
| 3-4 | Frontend State | Zustand refactor, service layer updates |
| 4-5 | Frontend UI | Account summary, filter, management page, table updates |
| 5-6 | Testing & Rollout | E2E tests, beta rollout, monitoring |

**Total Estimated Effort:** 6-8 weeks

---

## Implementation Sequencing Recommendation

### **Recommended Order: Multi-Portfolio FIRST, Fundamental Data SECOND**

**Critical Decision:** Implement multi-portfolio before fundamental data to minimize issues and reduce total effort.

**Rationale:**

**1. Foundation Before Features**
- Multi-portfolio changes the **core data model** (database schema)
- Fundamental data is **additive only** (no database changes, API-only)
- Better to establish foundation, then build features on stable ground

**2. Avoid Double Testing**
- If fundamental data first:
  - Test 9 new fundamental endpoints ✅
  - Do multi-portfolio migration 🔧
  - **Re-test all 9 fundamental endpoints** with multi-portfolio ❌ (wasted effort)
  - **Re-test all 59 existing endpoints** ❌

- If multi-portfolio first:
  - Do migration and test all 59 endpoints ✅
  - Add fundamental data ✅
  - Test 9 new endpoints (once) ✅
  - Done! ✅

**3. Risk Isolation**
- **Multi-portfolio**: HIGH risk (database migration, breaking changes, affects all endpoints)
- **Fundamental data**: LOW risk (new endpoints only, no migration)
- Do the risky thing first when you have a clean slate

**4. Migration Complexity**
- Multi-portfolio requires **database downtime** for schema changes
- Fundamental data requires **zero downtime** (just code deployment)
- Better to have one migration window, not complicate it with new features

**5. Aggregation Patterns**
- Multi-portfolio establishes the **weighted average aggregation pattern**
- Fundamental data will **reuse the same pattern** (`PortfolioAggregationService`)
- Build the reusable service first, then use it for fundamental data

**Staged Timeline:**

```
Stage 1: Multi-Portfolio (6-8 weeks)
├── Week 1:    Database migration
├── Week 2-3:  Backend APIs
├── Week 3-4:  Frontend state
├── Week 4-5:  Frontend UI
├── Week 5-6:  Testing & rollout
└── Week 7-8:  Stabilization & monitoring
    ✅ CHECKPOINT: Multi-portfolio stable in production

Stage 2: Fundamental Data (8 weeks, AFTER Stage 1 stable)
├── Backend (4 weeks): 9 endpoints, data transformation, caching
└── Frontend (4 weeks): FINANCIALS tab, 4 display sections
    ✅ CHECKPOINT: Fundamental data with multi-portfolio aggregation
```

**Total Timeline:** ~16 weeks for both features, done right

**Effort Saved:** ~2 weeks of re-testing and rework avoided

**Risk Reduced:** Isolate risky database migration, don't complicate it

---

## Conclusion

The multi-account aggregation feature is a valuable addition to SigmaSight that aligns well with the current architecture. By treating portfolios as conceptual assets for aggregation, we can:

1. ✅ Reuse all existing calculation engines (no changes!)
2. ✅ Implement simple weighted average aggregation
3. ✅ Provide clear, intuitive user experience
4. ✅ Maintain good performance
5. ✅ Enable future tax-aware features
6. ✅ Support single-portfolio users gracefully (progressive disclosure)

The implementation is straightforward, with low-to-medium risk and clear rollout path.

**Next Steps:**
1. Review and approve this plan
2. Approve sequencing (multi-portfolio first, fundamental data second)
3. Create detailed technical specs for backend and frontend
4. Begin Stage 1, Phase 1 (Database Migration)

---

## Appendix: Calculation Examples

### Example: Weighted Beta Calculation
```python
Portfolio A: Value=$500k, Beta=1.2
Portfolio B: Value=$300k, Beta=0.8
Portfolio C: Value=$200k, Beta=1.0

Total Value = $1,000k

Weight A = $500k / $1,000k = 0.50
Weight B = $300k / $1,000k = 0.30
Weight C = $200k / $1,000k = 0.20

Aggregate Beta = (1.2 × 0.50) + (0.8 × 0.30) + (1.0 × 0.20)
              = 0.60 + 0.24 + 0.20
              = 1.04
```

### Example: Weighted Volatility Calculation
```python
Portfolio A: Value=$500k, Volatility=20%
Portfolio B: Value=$300k, Volatility=15%
Portfolio C: Value=$200k, Volatility=18%

Total Value = $1,000k

Weight A = 0.50
Weight B = 0.30
Weight C = 0.20

Aggregate Volatility = (20% × 0.50) + (15% × 0.30) + (18% × 0.20)
                     = 10% + 4.5% + 3.6%
                     = 18.1%
```

### Example: Account Breakdown Display
```
Total Portfolio Value: $1,000,000
Daily P&L: +$12,500 (+1.25%)

Account Breakdown:
┌─────────────────────┬──────────────┬────────┬───────────┐
│ Account             │ Value        │ %      │ Daily P&L │
├─────────────────────┼──────────────┼────────┼───────────┤
│ Fidelity Taxable    │ $500,000     │ 50.0%  │ +$7,500   │
│ Schwab IRA          │ $300,000     │ 30.0%  │ +$3,000   │
│ 401(k)              │ $200,000     │ 20.0%  │ +$2,000   │
└─────────────────────┴──────────────┴────────┴───────────┘

Aggregate Risk Metrics:
- Portfolio Beta: 1.04
- Volatility (Annualized): 18.1%
- Sharpe Ratio: 1.32
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-01
**Authors:** SigmaSight Team
