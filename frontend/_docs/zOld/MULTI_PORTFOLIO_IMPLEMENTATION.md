# Multi-Portfolio Feature Implementation

**Date**: November 3, 2025
**Status**: Phases 1-5 Complete (50% Complete)
**Backend**: Complete with demo data seeded
**Frontend**: Core architecture and components built

---

## Overview

This document tracks the implementation of multi-portfolio support in SigmaSight, allowing users to manage multiple investment accounts with aggregate and filtered views.

### Key Features

1. **Aggregate View**: Combined analytics across all portfolios (selectedPortfolioId = null)
2. **Filtered View**: View individual portfolio data
3. **Progressive Disclosure**: Hides multi-portfolio complexity for single-portfolio users
4. **Zustand State Management**: Global portfolio state with localStorage persistence
5. **Demo User**: `demo_familyoffice@sigmasight.com` with 2 portfolios for testing

---

## Backend Implementation (Complete ✅)

### Database Schema

**New Portfolio Fields** (added for multi-portfolio support):
- `account_name` - Short name (e.g., "Public Growth")
- `account_type` - Account type (taxable, ira, roth_ira, 401k, trust, other)
- `is_active` - Boolean flag for active accounts

**Existing Fields**:
- `name` - Full portfolio name
- `equity_balance` - Total portfolio value
- `user_id` - Foreign key to User

### Demo Data Seeded

**User**: `demo_familyoffice@sigmasight.com` / `demo12345`

**Portfolio 1: Public Growth**
- Total Value: $1,250,000
- Positions: 12 (public equities & ETFs)
- Account Type: Taxable
- Categories: Thematic Growth, Quality Compounders, Defensive Yield

**Portfolio 2: Private Opportunities**
- Total Value: $950,000
- Positions: 9 (private & alternative investments)
- Account Type: Taxable
- Categories: Private Credit/PE, Real Assets, Impact & Alternatives

**Total**: ~$2.2M across 21 positions

### Backend Endpoints (Already Implemented)

According to the backend, these 10 endpoints exist:
- `GET /api/v1/portfolios` - List all portfolios
- `POST /api/v1/portfolios` - Create portfolio
- `GET /api/v1/portfolios/{id}` - Get portfolio details
- `PUT /api/v1/portfolios/{id}` - Update portfolio
- `DELETE /api/v1/portfolios/{id}` - Delete portfolio
- `GET /api/v1/portfolios/aggregate/analytics` - Aggregate analytics
- `GET /api/v1/portfolios/aggregate/breakdown` - Portfolio breakdown
- `POST /api/v1/portfolios/{id}/activate` - Activate portfolio
- `POST /api/v1/portfolios/{id}/deactivate` - Deactivate portfolio
- `GET /api/v1/portfolios/{id}/positions` - Get positions by portfolio

---

## Frontend Implementation

### Phase 1: State Management ✅

**File**: `frontend/src/stores/portfolioStore.ts` (223 lines)

**Changes**:
- Migrated from version 2 (single portfolio) to version 3 (multi-portfolio)
- Added `portfolios: PortfolioListItem[]` array
- Added `selectedPortfolioId: string | null` (null = aggregate view)
- Migration logic for existing v2 users

**New State**:
```typescript
interface PortfolioStore {
  portfolios: PortfolioListItem[]           // All user portfolios
  selectedPortfolioId: string | null        // Current selection (null = aggregate)

  setPortfolios: (portfolios) => void
  setSelectedPortfolio: (id) => void
  addPortfolio: (portfolio) => void
  updatePortfolio: (id, updates) => void
  removePortfolio: (id) => void
  clearAll: () => void

  getTotalValue: () => number
  getPortfolioCount: () => number
  getActivePortfolios: () => PortfolioListItem[]
  getSelectedPortfolio: () => PortfolioListItem | null
  isAggregateView: () => boolean
  hasPortfolio: () => boolean
}
```

**Backward Compatibility**:
- Legacy exports (`getPortfolioId`, `usePortfolioId`) still work
- Return selected portfolio ID or first portfolio ID
- Existing code continues to function

---

### Phase 2: API Service ✅

**File**: `frontend/src/services/portfolioApi.ts` (423 lines, v4)

**Added Methods**:
```typescript
// CRUD Operations
createPortfolio(data: CreatePortfolioRequest): Promise<PortfolioResponse>
updatePortfolio(id: string, data: UpdatePortfolioRequest): Promise<PortfolioResponse>
deletePortfolio(id: string): Promise<void>

// Aggregate Analytics
getAggregateAnalytics(): Promise<AggregateAnalytics>
getPortfolioBreakdown(): Promise<PortfolioBreakdown>
```

**New TypeScript Interfaces**:
- `CreatePortfolioRequest` - Create new portfolio
- `UpdatePortfolioRequest` - Update existing portfolio
- `PortfolioResponse` - Backend response structure
- `AggregateAnalytics` - Combined analytics with risk metrics, top holdings, sector allocation
- `PortfolioBreakdown` - Individual portfolio contributions to total

**All existing methods remain unchanged** - full backward compatibility maintained.

---

### Phase 3: Custom Hooks ✅

**File**: `frontend/src/hooks/useMultiPortfolio.ts` (342 lines)

**Hooks Created**:

1. **`usePortfolios()`**
   - Fetches list of all user portfolios
   - Auto-updates Zustand store
   - Returns: `{ portfolios, loading, error, refetch }`

2. **`useAggregateAnalytics()`**
   - Fetches combined analytics across all portfolios
   - Returns: `{ analytics, loading, error, refetch }`
   - Includes: total value, positions, P&L, risk metrics, top holdings, sectors

3. **`usePortfolioBreakdown()`**
   - Fetches each portfolio's contribution to total
   - Returns: `{ breakdown, loading, error, refetch }`

4. **`usePortfolioMutations()`**
   - CRUD operations with loading states
   - Functions: `createPortfolio`, `updatePortfolio`, `deletePortfolio`
   - Auto-syncs with Zustand store
   - Returns: `{ createPortfolio, updatePortfolio, deletePortfolio, creating, updating, deleting, error }`

5. **`useSelectedPortfolio()`**
   - Helper hook for current selection
   - Returns: `{ selectedPortfolio, isAggregateView, portfolioCount }`

**Pattern**: Consistent with existing codebase (useState/useEffect, not React Query)

---

### Phase 4: Account Summary Card ✅

**File**: `frontend/src/components/portfolio/AccountSummaryCard.tsx` (176 lines)

**Features**:
- **Progressive Disclosure**: Hides complexity for single-portfolio users
- **Core Metrics**: Total value, positions, unrealized P&L, overall return
- **Risk Metrics** (multi-portfolio only): Portfolio beta, Sharpe ratio, volatility, max drawdown
- **Top 3 Holdings** (multi-portfolio only): Symbol, value, percentage of total
- **Visual Indicators**: Trend icons (up/down/neutral) with color coding
- **Responsive Grid**: 2-column mobile, 4-column desktop
- **Loading & Error States**: Spinner and error messages

**Props**:
```typescript
interface AccountSummaryCardProps {
  showFullAnalytics?: boolean  // Override progressive disclosure (default: false)
}
```

**Logic**:
```typescript
const shouldShowMultiPortfolio = portfolioCount > 1 || showFullAnalytics
```

---

### Phase 5: Account Filter ✅

**File**: `frontend/src/components/portfolio/AccountFilter.tsx` (114 lines)

**Features**:
- **Progressive Disclosure**: Hidden for single-portfolio users
- **Dropdown Select**: Switch between "All Accounts" (aggregate) and individual portfolios
- **Displays**: Account name, type (Taxable, IRA, etc.), position count
- **Updates**: Zustand store on selection change
- **Uses**: Radix UI Select component for accessibility

**Props**:
```typescript
interface AccountFilterProps {
  showForSinglePortfolio?: boolean  // Override progressive disclosure (default: false)
  className?: string                // Optional styling
}
```

**Behavior**:
- Selecting "All Accounts" sets `selectedPortfolioId = null` (aggregate view)
- Selecting individual portfolio sets `selectedPortfolioId = portfolio.id`
- Only shows active portfolios (`is_active = true`)

---

## Remaining Work (Phases 6-10)

### Phase 6: Update PositionsTable ⏳

**Goal**: Add conditional "Account" column when in aggregate view

**File**: `frontend/src/components/portfolio/PortfolioPositions.tsx` (or similar)

**Changes Needed**:
```typescript
const { isAggregateView } = useSelectedPortfolio()

// Add column conditionally
{isAggregateView && (
  <TableColumn header="Account">
    {position.portfolio_name || 'Unknown'}
  </TableColumn>
)}
```

---

### Phase 7: Settings Page Integration ⏳

**Goal**: Add portfolio management UI to Settings page

**File**: `frontend/app/settings/page.tsx`

**Features to Add**:
1. List all portfolios with edit/delete actions
2. Create new portfolio form
3. Activate/deactivate portfolios
4. Uses `usePortfolios()` and `usePortfolioMutations()` hooks

---

### Phase 8: LoginForm Update ⏳

**Goal**: Add demo_familyoffice user to login dropdown

**File**: `frontend/src/components/auth/LoginForm.tsx` (or similar)

**Changes**:
```typescript
const DEMO_USERS = [
  { email: 'demo_individual@sigmasight.com', label: 'Demo Individual' },
  { email: 'demo_hnw@sigmasight.com', label: 'Demo High Net Worth' },
  { email: 'demo_hedgefundstyle@sigmasight.com', label: 'Demo Hedge Fund' },
  { email: 'demo_familyoffice@sigmasight.com', label: 'Demo Family Office (Multi-Portfolio)' },  // NEW
]
```

---

### Phase 9: Dashboard Update ⏳

**Goal**: Integrate AccountFilter and AccountSummaryCard into main dashboard

**File**: `frontend/app/portfolio/page.tsx`

**Changes**:
```typescript
import { AccountFilter } from '@/components/portfolio/AccountFilter'
import { AccountSummaryCard } from '@/components/portfolio/AccountSummaryCard'

export default function PortfolioPage() {
  return (
    <div>
      {/* Add filter at top */}
      <AccountFilter className="mb-4" />

      {/* Add summary card */}
      <AccountSummaryCard />

      {/* Existing components */}
      <PortfolioMetrics />
      <PortfolioPositions />
    </div>
  )
}
```

---

### Phase 10: Testing & Validation ⏳

**Test Cases**:

1. **Single Portfolio User**:
   - [ ] AccountFilter is hidden
   - [ ] AccountSummaryCard shows simplified view
   - [ ] No "Account" column in positions table
   - [ ] All existing functionality works

2. **Multi-Portfolio User** (demo_familyoffice):
   - [ ] AccountFilter shows all portfolios
   - [ ] Can switch between aggregate and individual portfolios
   - [ ] AccountSummaryCard shows full analytics
   - [ ] Positions table shows "Account" column in aggregate view
   - [ ] Settings page allows portfolio CRUD

3. **Data Persistence**:
   - [ ] Selected portfolio persists across page reloads
   - [ ] Migration from v2 to v3 works correctly
   - [ ] Logout clears portfolio state

4. **Backend Integration**:
   - [ ] Login as demo_familyoffice user
   - [ ] Verify 2 portfolios loaded
   - [ ] Verify aggregate analytics calculated correctly
   - [ ] Create/update/delete portfolio operations work

---

## Technical Decisions

### Why Progressive Disclosure?

**Problem**: Multi-portfolio features add complexity that 95% of users (single portfolio) don't need.

**Solution**: Hide multi-portfolio UI for single-portfolio users by default.

**Benefits**:
- Simpler UX for majority of users
- Easier onboarding
- No UI clutter
- Can still enable with `showFullAnalytics={true}` prop

### Why Zustand for Portfolio State?

**Alternatives Considered**:
1. URL parameters (`?portfolio=abc-123`)
2. React Context only
3. Server-side session

**Chosen**: Zustand with localStorage persistence

**Reasons**:
- Cleaner URLs (no ID pollution)
- Persists across page reloads
- Single source of truth
- Better security (no portfolio ID exposure in URL)
- Easier to manage for thousands of users

### Why null = Aggregate View?

**Design**: `selectedPortfolioId = null` means "show all portfolios"

**Reasons**:
- Explicit distinction between "no selection" and "specific portfolio"
- Easier to check: `if (selectedPortfolioId === null) { /* aggregate */ }`
- Matches backend convention
- More intuitive than magic string like "aggregate" or "all"

---

## Files Changed

### Backend
1. `backend/app/db/seed_demo_familyoffice.py` - Demo data seeding (278 lines)
2. `backend/scripts/verify_demo_familyoffice.py` - Verification script

### Frontend
1. `frontend/src/stores/portfolioStore.ts` - v2→v3 migration (223 lines)
2. `frontend/src/services/portfolioApi.ts` - v4 with CRUD (423 lines)
3. `frontend/src/hooks/useMultiPortfolio.ts` - Custom hooks (342 lines)
4. `frontend/src/components/portfolio/AccountSummaryCard.tsx` - Summary card (176 lines)
5. `frontend/src/components/portfolio/AccountFilter.tsx` - Filter dropdown (114 lines)

**Total**: ~1,556 lines of new/updated code

---

## Next Steps

1. **Complete Phase 6**: Update PositionsTable with conditional account column
2. **Complete Phase 7**: Build Settings page portfolio management UI
3. **Complete Phase 8**: Add demo_familyoffice to LoginForm
4. **Complete Phase 9**: Integrate components into Dashboard
5. **Complete Phase 10**: Comprehensive testing with both user types

**Estimated Remaining Time**: 3-4 hours

---

## Usage Examples

### For Developers

**Using the hooks**:
```typescript
import { usePortfolios, useAggregateAnalytics } from '@/hooks/useMultiPortfolio'

function MyComponent() {
  const { portfolios, loading } = usePortfolios()
  const { analytics } = useAggregateAnalytics()

  return (
    <div>
      <p>Total Value: ${analytics?.total_value}</p>
      <p>Portfolios: {portfolios.length}</p>
    </div>
  )
}
```

**Using the components**:
```typescript
import { AccountFilter } from '@/components/portfolio/AccountFilter'
import { AccountSummaryCard } from '@/components/portfolio/AccountSummaryCard'

export default function Dashboard() {
  return (
    <div>
      <AccountFilter />
      <AccountSummaryCard />
    </div>
  )
}
```

**Accessing state**:
```typescript
import { usePortfolioStore } from '@/stores/portfolioStore'

const selectedPortfolioId = usePortfolioStore(state => state.selectedPortfolioId)
const setSelectedPortfolio = usePortfolioStore(state => state.setSelectedPortfolio)

// Switch to aggregate view
setSelectedPortfolio(null)

// Switch to specific portfolio
setSelectedPortfolio('portfolio-uuid-here')
```

---

## Migration Notes

### For Existing Users (v2 → v3)

**What Happens**:
1. localStorage key `portfolio-storage` version bumps from 2 to 3
2. Old `portfolioId` is cleared
3. `portfolios` array starts empty
4. `selectedPortfolioId` starts as null (aggregate view)
5. On next login, portfolios array populated from backend

**User Experience**:
- Must login again after upgrade
- Portfolio selection persists from that point forward
- No data loss (backend unchanged)

### For New Users (v3)

**What Happens**:
1. Login fetches all portfolios
2. Portfolios stored in Zustand state
3. Default to aggregate view (selectedPortfolioId = null)
4. User can switch to individual portfolio via AccountFilter
5. Selection persists in localStorage

---

## Known Issues & Future Enhancements

### Known Issues
- None currently

### Future Enhancements
1. **Portfolio Reordering**: Drag-and-drop to reorder portfolios in filter
2. **Portfolio Groups**: Group portfolios by type (taxable, retirement, trust)
3. **Portfolio Comparison**: Side-by-side comparison of 2+ portfolios
4. **Portfolio Transfer**: Move positions between portfolios
5. **Portfolio Archiving**: Soft-delete instead of hard-delete
6. **Portfolio Dashboard**: Dedicated page showing all portfolios in grid layout
7. **Portfolio Sharing**: Share read-only view with others (advisors, family)

---

**End of Document**
