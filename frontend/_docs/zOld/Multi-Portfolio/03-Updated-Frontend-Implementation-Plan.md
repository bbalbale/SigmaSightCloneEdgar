# Updated Frontend Implementation Plan: Multi-Account Aggregation

**Feature:** Multi-Account Portfolio Aggregation
**Created:** 2025-11-03
**Status:** Implementation Starting
**Estimated Effort:** Full release with comprehensive testing

---

## Changes from Original Plan

### Backend Status
- ✅ **Backend Complete** - All 10 endpoints implemented and tested
- ✅ Migration complete (v2 → v3)
- ✅ Aggregation service ready
- ✅ Backward compatible

### Key Changes
1. **Settings Integration**: Account management integrated into `/settings` page (not separate route)
2. **Demo Multi-Portfolio User**: Added `demo_familyoffice@sigmasight.com` with 2 portfolios
3. **Full Release**: All phases implemented at once with comprehensive testing
4. **Backend Seed Data**: New seed script for demo_familyoffice user

---

## Demo Family Office User Specification

**User Details:**
- Email: `demo_familyoffice@sigmasight.com`
- Password: `demo12345`
- Full Name: Demo Family Office Manager
- Strategy: Family office with dedicated public growth and private alternatives mandates

**Portfolio 1: Public Growth** (~$1.25M)
- 12 positions: XLK, SMH, IGV, XLY, COST, AVGO, ASML, LULU, NEE, SCHD, JEPQ, BIL
- Entry dates: March-April 2024
- Mix of thematic ETFs, quality compounders, defensive yield

**Portfolio 2: Private Opportunities** (~$950K)
- 9 private/alternative positions
- Entry dates: September 2023 - February 2024
- Private credit, PE, VC, real assets, infrastructure, art, crypto

**Total: ~$2.2M across 21 positions**

---

## Implementation Phases

### Phase 1: State Management ✅
**File:** `frontend/src/stores/portfolioStore.ts`

**Changes:**
```typescript
// OLD (version 2)
interface PortfolioStore {
  portfolioId: string | null
  portfolioName: string | null
  setPortfolio: (id: string, name?: string | null) => void
  clearPortfolio: () => void
}

// NEW (version 3)
interface PortfolioListItem {
  id: string
  account_name: string
  account_type: string
  total_value: number
  position_count: number
  is_active: boolean
}

interface PortfolioStore {
  portfolios: PortfolioListItem[]
  selectedPortfolioId: string | null  // null = aggregate view

  setPortfolios: (portfolios: PortfolioListItem[]) => void
  setSelectedPortfolio: (id: string | null) => void
  addPortfolio: (portfolio: PortfolioListItem) => void
  updatePortfolio: (id: string, updates: Partial<PortfolioListItem>) => void
  removePortfolio: (id: string) => void
  clearAll: () => void

  // Computed getters
  getTotalValue: () => number
  getPortfolioCount: () => number
  getActivePortfolios: () => PortfolioListItem[]
  getSelectedPortfolio: () => PortfolioListItem | null
  isAggregateView: () => boolean
}
```

**Migration Logic:**
- Migrate existing `portfolioId` to `portfolios[0]`
- Default `selectedPortfolioId` to `null` (aggregate view)
- Storage version: 2 → 3

---

### Phase 2: Service Layer ✅
**File:** `frontend/src/services/portfolioApi.ts` (NEW FILE)

**Methods:**
```typescript
// Portfolio CRUD
createPortfolio(data: CreatePortfolioRequest): Promise<PortfolioResponse>
updatePortfolio(id: string, data: CreatePortfolioRequest): Promise<PortfolioResponse>
deletePortfolio(id: string): Promise<void>
getPortfolios(): Promise<PortfolioListItem[]>

// Aggregate analytics
getAggregateAnalytics(): Promise<AggregateAnalytics>
getPortfolioBreakdown(): Promise<PortfolioBreakdown[]>
```

**Existing Services Updated:**
- `analyticsApi.ts` - Add optional `portfolio_id` parameter to all methods
- When `portfolio_id` is null → aggregate view
- When `portfolio_id` is provided → single portfolio view

---

### Phase 3: React Query Hooks ✅
**File:** `frontend/src/hooks/usePortfolioData.ts` (UPDATE EXISTING)

**New Hooks:**
```typescript
usePortfolios() // Load all portfolios on mount
useAggregateAnalytics() // Aggregate analytics (enabled when aggregate view)
usePortfolioBreakdown() // Portfolio breakdown
useCreatePortfolio() // Create portfolio mutation
useUpdatePortfolio() // Update portfolio mutation
useDeletePortfolio() // Delete portfolio mutation
```

**Updated Hooks:**
```typescript
usePortfolioAnalytics() // Now uses selectedPortfolioId from store
```

---

### Phase 4: UI Components ✅

#### 4.1 AccountSummaryCard
**File:** `frontend/src/components/portfolio/AccountSummaryCard.tsx` (NEW)

**Features:**
- Progressive disclosure (1 portfolio = simple view, 2+ = breakdown)
- Shows total value across all accounts
- Account breakdown with percentages
- "Add Another Account" button for discovery

#### 4.2 AccountFilter
**File:** `frontend/src/components/portfolio/AccountFilter.tsx` (NEW)

**Features:**
- Dropdown with "All Accounts" + individual portfolios
- Shows account values in dropdown
- Hides when only 1 portfolio (progressive disclosure)
- Invalidates caches on filter change

#### 4.3 PositionsTable Update
**File:** `frontend/src/components/portfolio/PositionsTable.tsx` (UPDATE)

**Changes:**
- Add conditional "Account" column (only shows in aggregate view)
- Show `weight_in_total` vs `weight_in_portfolio` based on view
- Hide account column when viewing single portfolio

---

### Phase 5: Settings Integration ✅
**File:** `frontend/src/containers/SettingsContainer.tsx` (UPDATE)

**New Section: Account Management**
- List all portfolios with edit/delete actions
- Create new portfolio button
- Account type selector (taxable, ira, roth_ira, 401k, etc.)
- Inline editing (no separate page)
- Prevent deleting last portfolio

**UI Layout:**
```
Settings Page
├── User Profile (existing)
├── Account Management (NEW)
│   ├── Account List
│   │   ├── Portfolio 1 [Edit] [Delete]
│   │   ├── Portfolio 2 [Edit] [Delete]
│   │   └── [+ Add Account] button
│   └── Create/Edit Form (inline)
└── Preferences (existing)
```

---

### Phase 6: Login Screen Update ✅
**File:** `frontend/src/components/auth/LoginForm.tsx` (UPDATE)

**Changes:**
- Add 4th demo account: "Family Office" (demo_familyoffice@sigmasight.com)
- Icon: `Building` or `Briefcase`
- Description: "Multi-account portfolio ($2.2M across 2 portfolios)"

---

### Phase 7: Dashboard Update ✅
**File:** `frontend/app/portfolio/page.tsx` (UPDATE)

**Changes:**
- Add `<AccountFilter />` to header
- Add `<AccountSummaryCard />` above metrics
- Call `usePortfolios()` on mount to load portfolios
- Existing components work with both aggregate and single portfolio views

---

### Phase 8: Backend Seed Script ✅
**File:** `backend/scripts/database/seed_demo_familyoffice.py` (NEW)

**Tasks:**
1. Create demo_familyoffice user
2. Create 2 portfolios
3. Create 21 positions (12 public + 9 private)
4. Apply tags to all positions
5. Run batch calculations to populate analytics

**Entry Date:** March 15, 2024 (earliest position)

---

## Progressive Disclosure Logic

### Single Portfolio (n=1)
```typescript
- AccountSummaryCard: Simple "Portfolio Value" (no breakdown)
- AccountFilter: Hidden (shows account name as text)
- PositionsTable: No account column
- Settings: Show "Add Account" prominently
```

### Multiple Portfolios (n>1)
```typescript
- AccountSummaryCard: "Total Across All Accounts" with breakdown
- AccountFilter: Dropdown visible
- PositionsTable: Account column visible in aggregate view
- Settings: Full account management
```

---

## Cache Invalidation Strategy

```typescript
// On filter change
queryClient.invalidateQueries({ queryKey: ['analytics'] })
queryClient.invalidateQueries({ queryKey: ['positions'] })
queryClient.invalidateQueries({ queryKey: ['risk-metrics'] })

// On portfolio CRUD
queryClient.invalidateQueries({ queryKey: ['portfolios'] })
queryClient.invalidateQueries({ queryKey: ['analytics'] })
queryClient.invalidateQueries({ queryKey: ['positions'] })
```

---

## Testing Checklist

### Phase 1: State Management
- [ ] Store migration works (v2 → v3)
- [ ] Persists to localStorage correctly
- [ ] Computed getters return correct values
- [ ] Single portfolio → portfolios array conversion

### Phase 2: Service Layer
- [ ] Portfolio CRUD endpoints work
- [ ] Aggregate analytics returns correct data
- [ ] Portfolio breakdown calculates percentages
- [ ] Optional portfolio_id parameter works

### Phase 3: React Query
- [ ] usePortfolios loads on mount
- [ ] Cache invalidation works on mutations
- [ ] Optimistic updates for CRUD operations
- [ ] Error handling for failed requests

### Phase 4: UI Components
- [ ] AccountSummaryCard shows breakdown correctly
- [ ] AccountFilter changes trigger re-fetch
- [ ] PositionsTable shows/hides account column
- [ ] Progressive disclosure works (1→2→1 portfolios)

### Phase 5: Settings Integration
- [ ] Can create new portfolio
- [ ] Can update portfolio name/type
- [ ] Can delete portfolio (prevents last)
- [ ] Inline editing works smoothly

### Phase 6: Login Screen
- [ ] Demo family office button appears
- [ ] Credentials fill correctly
- [ ] Login succeeds and loads 2 portfolios

### Phase 7: Dashboard
- [ ] AccountFilter appears in header
- [ ] Aggregate view shows all positions
- [ ] Single portfolio filter works
- [ ] Metrics update on filter change

### Phase 8: Backend Seed
- [ ] User created successfully
- [ ] 2 portfolios created
- [ ] 21 positions created with correct data
- [ ] Tags applied
- [ ] Batch calculations complete

### Integration Testing
- [ ] Login as demo_familyoffice
- [ ] See aggregate view by default
- [ ] Filter to Public Growth portfolio
- [ ] Filter to Private Opportunities portfolio
- [ ] Switch back to aggregate view
- [ ] Create new portfolio via Settings
- [ ] Edit portfolio name
- [ ] Delete portfolio (not last one)
- [ ] Logout and login again (persistence test)

---

## Implementation Order

1. **Backend First** - Create seed script for demo_familyoffice
2. **Phase 1** - Update portfolioStore
3. **Phase 2** - Create portfolioApi service
4. **Phase 3** - Create React Query hooks
5. **Phase 4** - Build UI components
6. **Phase 5** - Integrate into Settings
7. **Phase 6** - Update LoginForm
8. **Phase 7** - Update Dashboard
9. **Phase 8** - Comprehensive testing

---

## Success Criteria

- ✅ Demo family office user can login
- ✅ See aggregate view of 2 portfolios (~$2.2M total)
- ✅ Filter to individual portfolios
- ✅ Create/edit/delete portfolios via Settings
- ✅ Existing single-portfolio users see no changes
- ✅ Progressive disclosure works smoothly
- ✅ All tests passing
- ✅ No breaking changes to existing functionality

---

**Ready to implement?** All phases will be completed in sequence with testing at each stage.
