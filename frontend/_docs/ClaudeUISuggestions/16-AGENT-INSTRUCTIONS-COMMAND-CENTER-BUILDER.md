# Agent Instructions: Command Center Builder

**Document Version**: 1.0
**Last Updated**: October 31, 2025
**Agent Type**: `general-purpose`
**Purpose**: Build the Command Center page implementation from finalized specifications

---

## Agent Profile

**Name**: Command Center Builder Agent

**Primary Mission**: Implement the Command Center page with professional Bloomberg-style UI, connecting to existing backend APIs through the service layer, following all established frontend patterns.

---

## Core Skills Required

1. **Frontend Architecture**
   - React 18 with hooks
   - Next.js 14 App Router (client-side only, no SSR)
   - Container pattern: Page → Container → Hooks → Services
   - TypeScript with proper interfaces and types

2. **Service Layer Integration**
   - Using existing services without modification
   - Extending services with new methods when needed
   - Never making direct `fetch()` calls
   - Understanding API response types

3. **Custom Hook Development**
   - Data-fetching hooks with proper loading/error states
   - Parallel API calls with Promise.all
   - Graceful error handling and degradation
   - Proper dependency arrays and cleanup

4. **Tailwind CSS Mastery**
   - Professional, information-dense layouts
   - Bloomberg-inspired flat design
   - Consistent spacing system (4/8/16/24px)
   - Dark mode support
   - Responsive breakpoints (mobile/tablet/desktop)

5. **TypeScript Proficiency**
   - Defining interfaces for API responses
   - Type-safe component props
   - Proper error handling with typed catches
   - Using existing types from `src/types/`

6. **Async Data Management**
   - Parallel fetching strategies
   - Handling missing/null data gracefully
   - Loading states and skeleton screens
   - Error boundaries and retry logic

7. **Pattern Recognition**
   - Following existing codebase conventions
   - Matching naming patterns
   - Reusing existing components where possible
   - Consistent file structure

---

## Required Reading (In Order)

**MUST READ BEFORE STARTING:**

1. **`frontend/CLAUDE.md`** (Architecture & Patterns)
   - Frontend architecture overview
   - Service layer usage
   - State management (Zustand + Context)
   - Common pitfalls and solutions

2. **`13-COMMAND-CENTER-FUNCTIONAL-SPEC.md`** (What to Build)
   - Hero metrics specifications
   - Holdings table columns and behavior
   - Risk metrics definitions
   - User interactions

3. **`14-COMMAND-CENTER-VISUAL-SPECS.md`** (How it Looks)
   - Tailwind class reference
   - Component layouts
   - Color palette and typography
   - Responsive breakpoints

4. **`15-COMMAND-CENTER-API-SERVICE-MAPPING.md`** (Where Data Comes From)
   - Complete API → Service mapping
   - TypeScript interfaces
   - Example code for each endpoint
   - Resolved data questions

**Reference Examples:**

5. **Existing Implementations** (Study These)
   - `src/services/portfolioService.ts` - Service layer pattern
   - `src/services/analyticsApi.ts` - API client usage
   - `src/hooks/usePortfolioData.ts` - Hook pattern
   - `src/containers/DashboardContainer.tsx` - Container pattern
   - `src/containers/RiskMetricsContainer.tsx` - Multiple hooks orchestration

---

## Implementation Tasks (Sequential)

### Phase 1: Service Layer Extension

**File**: `src/services/portfolioService.ts`

**Task**: Add `fetchPortfolioSnapshot()` method

```typescript
export interface PortfolioSnapshot {
  snapshot_date: string | null
  target_price_return_eoy: number
  target_price_return_next_year: number
  target_price_coverage_pct: number
  target_price_positions_count: number
  target_price_total_positions: number
  target_price_last_updated: string | null
  beta_calculated_90d: number | null
  beta_provider_1y: number | null
  daily_pnl: number | null
  daily_return: number | null
}

export async function fetchPortfolioSnapshot(portfolioId: string): Promise<PortfolioSnapshot> {
  const token = authManager.getAccessToken()
  if (!token) throw new Error('Authentication token unavailable')

  return await apiClient.get<PortfolioSnapshot>(
    `/api/v1/data/portfolio/${portfolioId}/snapshot`,
    {
      headers: { Authorization: `Bearer ${token}` }
    }
  )
}
```

---

### Phase 2: Custom Hook Development

**File**: `src/hooks/useCommandCenterData.ts`

**Task**: Create data-fetching hook that:
1. Fetches all required data in parallel
2. Transforms data for display
3. Handles loading and error states
4. Calculates derived metrics

**Data Sources**:
- Portfolio overview (exposures, equity balance)
- Portfolio snapshot (betas, target return, daily P&L)
- Positions details
- Target prices
- Sector exposure
- Concentration metrics
- Correlation matrix

**Return Structure**:
```typescript
{
  // Hero Metrics
  heroMetrics: {
    equityBalance: number
    targetReturnEOY: number
    grossExposure: number
    netExposure: number
    longExposure: number
    shortExposure: number
  }

  // Holdings Table
  holdings: Array<{
    symbol: string
    quantity: number
    todaysPrice: number
    targetPrice: number | null
    marketValue: number
    weight: number
    pnlToday: number | null  // from snapshot.daily_return
    pnlTotal: number
    returnPct: number
    targetReturn: number | null
    beta: number | null
  }>

  // Risk Metrics
  riskMetrics: {
    portfolioBeta90d: number | null
    portfolioBeta1y: number | null
    topSector: { name: string, weight: number, vs_sp: number } | null
    largestPosition: { symbol: string, weight: number } | null
    spCorrelation: number | null
    stressTest: { up: number, down: number } | null
  }

  // State
  loading: boolean
  error: string | null
}
```

---

### Phase 3: Component Development

**File**: `src/components/command-center/HeroMetricsRow.tsx`

**Task**: 6-card metric row (Equity Balance, Target Return, Gross/Net/Long/Short)

**Props**:
```typescript
interface HeroMetricsRowProps {
  metrics: {
    equityBalance: number
    targetReturnEOY: number
    grossExposure: number
    netExposure: number
    longExposure: number
    shortExposure: number
  }
  loading: boolean
}
```

**Layout**: `grid grid-cols-6 gap-4` (equal width cards)

**Styling**: Follow `14-COMMAND-CENTER-VISUAL-SPECS.md` exactly

---

**File**: `src/components/command-center/HoldingsTable.tsx`

**Task**: 11-column sortable table

**Features**:
- Sortable headers (click to sort)
- Color-coded P&L (green/red)
- Weight visualization bars
- Tabular numbers
- Sticky header
- AI button per row (opens modal - future)

**Props**:
```typescript
interface HoldingsTableProps {
  holdings: Array<{...}>  // See Phase 2 structure
  loading: boolean
  onSort?: (column: string) => void
}
```

---

**File**: `src/components/command-center/RiskMetricsRow.tsx`

**Task**: 5-card risk metrics row

**Features**:
- Portfolio Beta card (show both 90d and 1y)
- Top Sector card with S&P comparison
- Largest Position card
- S&P Correlation card
- Stress Test card (±1% market move)

---

### Phase 4: Container & Page

**File**: `src/containers/CommandCenterContainer.tsx`

**Task**: Orchestrate components with data from hook

**Pattern**:
```typescript
'use client'

export function CommandCenterContainer() {
  const { heroMetrics, holdings, riskMetrics, loading, error } = useCommandCenterData()

  if (loading) return <LoadingState />
  if (error) return <ErrorState error={error} />

  return (
    <div>
      <HeroMetricsRow metrics={heroMetrics} loading={loading} />
      <HoldingsTable holdings={holdings} loading={loading} />
      <RiskMetricsRow metrics={riskMetrics} loading={loading} />
    </div>
  )
}
```

---

**File**: `app/command-center/page.tsx`

**Task**: Thin page wrapper (5 lines)

```typescript
'use client'
import { CommandCenterContainer } from '@/containers/CommandCenterContainer'

export default function CommandCenterPage() {
  return <CommandCenterContainer />
}
```

---

### Phase 5: Testing & Validation

**Test Checklist**:
1. ✅ Login works (demo_hnw@sigmasight.com / demo12345)
2. ✅ All 6 hero metrics display with correct values
3. ✅ Holdings table shows all 11 columns
4. ✅ Table is sortable (click headers)
5. ✅ Position betas display correctly
6. ✅ Target prices show when available
7. ✅ Risk metrics all populated
8. ✅ Loading states show during fetch
9. ✅ Error handling works (test with bad portfolio ID)
10. ✅ No console errors
11. ✅ TypeScript compiles without errors
12. ✅ Page accessible via navigation

**Testing Commands**:
```bash
cd frontend
npm run type-check  # Verify TypeScript
npm run lint        # Check code quality
docker-compose up -d  # Start frontend
# Navigate to http://localhost:3005/command-center
```

---

## Critical Constraints

### ✅ MUST DO

1. **Use Existing Services Only**
   - Import from `@/services/portfolioService`, `@/services/analyticsApi`, etc.
   - Never write `fetch('http://localhost:8000/...')`
   - Follow service layer patterns exactly

2. **Client-Side Only**
   - Add `'use client'` directive to all components
   - No Server Components, no SSR

3. **State Management**
   - Portfolio ID from Zustand: `usePortfolioStore()`
   - No URL parameters

4. **TypeScript**
   - Define interfaces for all data structures
   - Use existing types from `src/types/` when available
   - Proper error typing: `catch (err: any)`

5. **Styling**
   - Match Tailwind classes from visual specs EXACTLY
   - Dark mode support: `theme === 'dark' ? ... : ...`
   - Responsive: `md:`, `lg:` breakpoints

6. **Error Handling**
   - Try/catch around all async operations
   - Display user-friendly error messages
   - Graceful degradation (show what data you have)

### ❌ MUST NOT DO

1. **Don't Create New Services**
   - Use existing `portfolioService`, `analyticsApi`, `targetPriceService`
   - Only ADD methods to existing services

2. **Don't Use Server Components**
   - No `'use server'`
   - No async page components
   - All data fetching in hooks

3. **Don't Hardcode Values**
   - No `const portfolioId = 'abc-123'`
   - Always use Zustand store

4. **Don't Make Direct API Calls**
   - No `fetch()` anywhere
   - No `axios.get()`

5. **Don't Improvise UI**
   - Follow visual specs exactly
   - Don't add features not in spec
   - Don't change layout structure

6. **Don't Skip TypeScript**
   - All functions must have types
   - All components must have typed props
   - No `any` without justification

---

## Success Criteria

**The implementation is complete when:**

1. ✅ Page loads at `/command-center` route
2. ✅ All 6 hero metrics display correctly
3. ✅ Holdings table shows 11 columns with demo data
4. ✅ All 5 risk metrics display correctly
5. ✅ Table sorting works (click column headers)
6. ✅ Loading states display during data fetch
7. ✅ Error states display if data fetch fails
8. ✅ No TypeScript errors (`npm run type-check`)
9. ✅ No ESLint errors (`npm run lint`)
10. ✅ No console errors in browser
11. ✅ Responsive design works (test 1024px+ desktop)
12. ✅ Dark mode styling matches specs

---

## Agent Reporting Format

**When complete, report:**

1. **Files Created** (list all new files with line counts)
2. **Files Modified** (list all changed files with what changed)
3. **Testing Results** (checklist above with ✅/❌)
4. **Screenshots** (if possible, show the rendered page)
5. **Known Issues** (anything not working as expected)
6. **Next Steps** (what remains to be done)

---

## Example Output Format

```markdown
## Implementation Complete ✅

### Files Created (5 total, ~800 lines)
- `src/hooks/useCommandCenterData.ts` (180 lines) - Data fetching hook
- `src/components/command-center/HeroMetricsRow.tsx` (120 lines) - Hero metrics
- `src/components/command-center/HoldingsTable.tsx` (280 lines) - Holdings table
- `src/components/command-center/RiskMetricsRow.tsx` (150 lines) - Risk metrics
- `src/containers/CommandCenterContainer.tsx` (80 lines) - Main container
- `app/command-center/page.tsx` (8 lines) - Page wrapper

### Files Modified (1 total)
- `src/services/portfolioService.ts` - Added `fetchPortfolioSnapshot()` method

### Testing Results
✅ All 12 success criteria met
✅ TypeScript compiles cleanly
✅ No console errors
✅ Tested with demo_hnw@sigmasight.com

### Known Issues
None - implementation complete

### Screenshots
[Attach screenshot of rendered Command Center page]

### Next Steps
Ready for user review and feedback
```

---

## Notes for Agent

- **Read all 5 required documents before starting**
- **Study existing code patterns** (DashboardContainer, RiskMetricsContainer)
- **Test incrementally** (service → hook → component → container → page)
- **Follow the visual specs exactly** - no creative liberties
- **Ask questions if unclear** - don't guess at implementation details
- **Report progress** - let orchestrator know when each phase is complete

---

**End of Agent Instructions**
