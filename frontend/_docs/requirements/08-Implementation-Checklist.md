# Multi-Page Implementation Checklist

**Purpose**: Step-by-step implementation guide with verification steps  
**Audience**: AI coding agents implementing the multi-page architecture  
**Last Updated**: September 29, 2025

---

## Overview

This checklist guides you through implementing the multi-page architecture by following the established pattern: **Hook → Components → Container → Page**

**Total Implementation Time**: ~3-4 weeks  
**Files to Create**: ~25 new files  
**Files to Modify**: ~2 existing files

---

## Phase 1: Core Setup (Week 1, Days 1-3)

### 1.1 Create Auth Provider

**File**: `app/providers.tsx`

- [ ] Create client-side auth context
- [ ] Implement user state management
- [ ] Implement portfolioId state management
- [ ] Add login/logout functions using existing authManager
- [ ] Add checkAuth function using portfolioResolver
- [ ] Add loading states and error handling
- [ ] Export useAuth() hook

**Verification**:
```typescript
// Test in any component
const { user, portfolioId, login, logout } = useAuth()
console.log('User:', user)
console.log('Portfolio:', portfolioId)
```

**Services Used**: authManager, portfolioResolver

---

### 1.2 Update Root Layout

**File**: `app/layout.tsx` (modify existing)

- [ ] Import Providers component
- [ ] Wrap children with Providers
- [ ] Keep existing metadata
- [ ] Maintain min-h-screen wrapper

**Verification**:
```bash
# Run dev server
npm run dev

# Check console for errors
# Navigate to /portfolio - should still work
```

---

### 1.3 Create Navigation Component

**File**: `src/components/navigation/Navigation.tsx`

- [ ] Create navigation items array (6 routes)
- [ ] Use useAuth() for user data
- [ ] Use usePathname() for active route
- [ ] Implement desktop navigation
- [ ] Implement user dropdown menu
- [ ] Add logout functionality
- [ ] Style with existing UI components

**Verification**:
```typescript
// Should see navigation at top of all pages
// Clicking links should highlight active route
// User dropdown should show name and email
```

**Services Used**: None (uses useAuth hook)

---

## Phase 2: Data Hooks (Week 1, Days 4-5)

### 2.1 Create Positions Hook

**File**: `src/hooks/usePositions.ts`

- [ ] Import apiClient and useAuth
- [ ] Create state for positions, loading, error
- [ ] Implement fetchPositions function
- [ ] Filter by investment_class parameter
- [ ] Handle loading and error states
- [ ] Return positions, loading, error, refetch

**Verification**:
```typescript
// Test in component
const { positions, loading, error } = usePositions('PUBLIC')
console.log('Positions:', positions)
console.log('Loading:', loading)
```

**Services Used**: apiClient

---

### 2.2 Create Strategies Hook

**File**: `src/hooks/useStrategies.ts`

- [ ] Import strategiesApi and useAuth
- [ ] Create state for strategies, loading, error
- [ ] Implement fetchStrategies function
- [ ] Use strategiesApi.listByPortfolio
- [ ] Include tags and positions
- [ ] Return strategies, loading, error, refetch

**Verification**:
```typescript
// Test in component
const { strategies, loading } = useStrategies()
console.log('Strategies:', strategies)
```

**Services Used**: strategiesApi

---

### 2.3 Create Tags Hook

**File**: `src/hooks/useTags.ts`

- [ ] Import tagsApi
- [ ] Create state for tags, loading, error
- [ ] Implement fetchTags function
- [ ] Use tagsApi.list (exclude archived)
- [ ] Return tags, loading, error, refetch

**Verification**:
```typescript
// Test in component
const { tags, loading } = useTags()
console.log('Tags:', tags)
```

**Services Used**: tagsApi

---

## Phase 3: Position Pages (Week 2, Days 1-3)

### 3.1 Create Position Components

#### PositionSummary Component

**File**: `src/components/positions/PositionSummary.tsx`

- [ ] Accept positions array prop
- [ ] Calculate total market value
- [ ] Calculate total cost basis
- [ ] Calculate total P&L
- [ ] Calculate return percentage
- [ ] Use Card components for layout
- [ ] Use formatCurrency from lib/formatters
- [ ] Color-code positive/negative values

**Verification**:
```typescript
// Test with sample data
<PositionSummary positions={[{ market_value: 1000, cost_basis: 900, unrealized_pnl: 100 }]} />
// Should show 4 cards with metrics
```

**Services Used**: None (formatters only)

---

#### PositionsTable Component

**File**: `src/components/positions/PositionsTable.tsx`

- [ ] Accept positions array prop
- [ ] Implement sortable columns
- [ ] Use Table components from UI
- [ ] Format currency and numbers
- [ ] Show position type badges
- [ ] Color-code P&L
- [ ] Handle empty state

**Verification**:
```typescript
// Test with sample data
<PositionsTable positions={positions} />
// Should show sortable table
// Click headers to sort
```

**Services Used**: None (formatters only)

---

### 3.2 Create Public Positions Container

**File**: `src/containers/PublicPositionsContainer.tsx`

- [ ] Use usePositions('PUBLIC') hook
- [ ] Handle loading state with Skeleton
- [ ] Handle error state
- [ ] Render PositionSummary component
- [ ] Render PositionsTable component
- [ ] Add page title and count

**Verification**:
```typescript
// Test container
<PublicPositionsContainer />
// Should show loading → summary + table
```

**Services Used**: Indirect via usePositions hook

---

### 3.3 Create Public Positions Page

**File**: `app/public-positions/page.tsx`

- [ ] Mark as 'use client'
- [ ] Import PublicPositionsContainer
- [ ] Render container (5-8 lines total)

**Verification**:
```bash
# Navigate to /public-positions
# Should see public positions page
# Check only PUBLIC positions show
```

---

### 3.4 Create Private Positions Container

**File**: `src/containers/PrivatePositionsContainer.tsx`

- [ ] Copy from PublicPositionsContainer
- [ ] Change hook to usePositions('PRIVATE')
- [ ] Change title to "Private Positions"
- [ ] Everything else same

**Verification**:
```bash
# Navigate to /private-positions
# Should see private positions page
# Check only PRIVATE positions show
```

---

### 3.5 Create Private Positions Page

**File**: `app/private-positions/page.tsx`

- [ ] Mark as 'use client'
- [ ] Import PrivatePositionsContainer
- [ ] Render container (5-8 lines total)

**Verification**:
```bash
# Navigate to /private-positions
# Should see private positions
# Compare with /public-positions
```

---

## Phase 4: Organize Page (Week 2, Days 4-5)

### 4.1 Create Strategy List Component

**File**: `src/components/strategies/StrategyList.tsx`

- [ ] Accept strategies, tags, onUpdate props
- [ ] Display strategy cards
- [ ] Show positions count and net exposure
- [ ] Show assigned tags with colors
- [ ] Implement delete with strategiesApi.delete
- [ ] Add create button (placeholder)
- [ ] Handle empty state

**Verification**:
```typescript
// Test with sample strategies
<StrategyList strategies={strategies} tags={tags} onUpdate={() => {}} />
// Should show strategy cards
// Delete should work
```

**Services Used**: strategiesApi

---

### 4.2 Create Tag List Component

**File**: `src/components/tags/TagList.tsx`

- [ ] Accept tags and onUpdate props
- [ ] Display tag list with colors
- [ ] Show usage count
- [ ] Implement inline create form
- [ ] Use tagsApi.create for creation
- [ ] Use tagsApi.delete for archiving
- [ ] Handle empty state

**Verification**:
```typescript
// Test tag creation and deletion
<TagList tags={tags} onUpdate={() => {}} />
// Create tag should work
// Delete/archive should work
```

**Services Used**: tagsApi

---

### 4.3 Create Organize Container

**File**: `src/containers/OrganizeContainer.tsx`

- [ ] Use useStrategies() hook
- [ ] Use useTags() hook
- [ ] Handle loading state
- [ ] Create shared update handler
- [ ] Use two-column grid layout
- [ ] Render StrategyList component
- [ ] Render TagList component

**Verification**:
```typescript
// Test container
<OrganizeContainer />
// Should show two-column layout
// Updates should refresh both sides
```

**Services Used**: Indirect via hooks

---

### 4.4 Create Organize Page

**File**: `app/organize/page.tsx`

- [ ] Mark as 'use client'
- [ ] Import OrganizeContainer
- [ ] Render container (5-8 lines total)

**Verification**:
```bash
# Navigate to /organize
# Should see strategies and tags
# Create/delete should work
```

---

## Phase 5: AI Chat Page (Week 3, Days 1-2)

### 5.1 Create AI Chat Container

**File**: `src/containers/AIChatContainer.tsx`

- [ ] Use useAuth() for portfolioId and user
- [ ] Add page title and description
- [ ] Show portfolio ID reference
- [ ] Render existing ChatInterface component
- [ ] Pass portfolioId and userId props

**Verification**:
```typescript
// Test container
<AIChatContainer />
// Should show chat interface
// Portfolio ID should display
```

**Services Used**: None (ChatInterface uses services internally)

---

### 5.2 Create AI Chat Page

**File**: `app/ai-chat/page.tsx`

- [ ] Mark as 'use client'
- [ ] Import AIChatContainer
- [ ] Render container (5-8 lines total)

**Verification**:
```bash
# Navigate to /ai-chat
# Should see chat interface
# Send message - should stream
# Check portfolio context works
```

---

## Phase 6: Settings Page (Week 3, Days 3-5)

### 6.1 Create User Settings Form

**File**: `src/components/settings/UserSettingsForm.tsx`

- [ ] Accept user prop
- [ ] Create profile update form (full_name)
- [ ] Create password change form
- [ ] Use apiClient.patch for profile update
- [ ] Use apiClient.post for password change
- [ ] Add validation for password match
- [ ] Handle success/error messages
- [ ] Use useAuth().refreshSession after update

**Verification**:
```typescript
// Test form
<UserSettingsForm user={user} />
// Update name - should save
// Change password - should work
```

**Services Used**: apiClient

---

### 6.2 Create Portfolio Settings Form

**File**: `src/components/settings/PortfolioSettingsForm.tsx`

- [ ] Accept portfolioId prop
- [ ] Fetch portfolio details on mount
- [ ] Create settings form (name, description, currency)
- [ ] Use apiClient.get to fetch portfolio
- [ ] Use apiClient.patch to update
- [ ] Add currency dropdown
- [ ] Handle success/error messages

**Verification**:
```typescript
// Test form
<PortfolioSettingsForm portfolioId={portfolioId} />
// Update settings - should save
```

**Services Used**: apiClient

---

### 6.3 Create Export Form

**File**: `src/components/settings/ExportForm.tsx`

- [ ] Accept portfolioId prop
- [ ] Add format selector (CSV/JSON)
- [ ] Fetch positions using apiClient
- [ ] Implement exportAsCSV function
- [ ] Implement exportAsJSON function
- [ ] Implement downloadFile function
- [ ] Handle success/error messages

**Verification**:
```typescript
// Test export
<ExportForm portfolioId={portfolioId} />
// Export CSV - should download
// Export JSON - should download
```

**Services Used**: apiClient

---

### 6.4 Create Settings Container

**File**: `src/containers/SettingsContainer.tsx`

- [ ] Use useAuth() for user and portfolioId
- [ ] Create tabs (User, Portfolio, Export)
- [ ] Render UserSettingsForm in user tab
- [ ] Render PortfolioSettingsForm in portfolio tab
- [ ] Render ExportForm in export tab
- [ ] Handle missing portfolioId

**Verification**:
```typescript
// Test container
<SettingsContainer />
// Should show three tabs
// All forms should work
```

**Services Used**: Indirect via components

---

### 6.5 Create Settings Page

**File**: `app/settings/page.tsx`

- [ ] Mark as 'use client'
- [ ] Import SettingsContainer
- [ ] Render container (5-8 lines total)

**Verification**:
```bash
# Navigate to /settings
# Should see settings tabs
# All forms should function
```

---

## Phase 7: Testing & Polish (Week 4)

### 7.1 Navigation Testing

- [ ] Test all navigation links work
- [ ] Verify active route highlighting
- [ ] Check mobile responsive navigation
- [ ] Test user dropdown menu
- [ ] Test logout functionality
- [ ] Verify navigation shows on all pages

---

### 7.2 Data Flow Testing

- [ ] Test position filtering (PUBLIC/PRIVATE)
- [ ] Verify strategy creation and deletion
- [ ] Test tag creation and assignment
- [ ] Check chat streaming works
- [ ] Test settings updates persist
- [ ] Verify data exports work

---

### 7.3 Error Handling

- [ ] Test with backend offline
- [ ] Test with invalid portfolio ID
- [ ] Test with network errors
- [ ] Test with authentication failures
- [ ] Verify error messages display
- [ ] Check loading states show correctly

---

### 7.4 Authentication Flow

- [ ] Test login flow
- [ ] Verify portfolio ID resolution
- [ ] Test logout clears state
- [ ] Check protected routes redirect to login
- [ ] Verify public routes accessible
- [ ] Test session persistence

---

### 7.5 Performance Testing

- [ ] Check page load times
- [ ] Verify data caching works
- [ ] Test with large datasets
- [ ] Check memory usage
- [ ] Optimize slow components
- [ ] Test on slow connections

---

## File Summary

### New Files to Create (25 total)

**Core Setup** (2 files):
- app/providers.tsx
- src/components/navigation/Navigation.tsx

**Hooks** (3 files):
- src/hooks/usePositions.ts
- src/hooks/useStrategies.ts
- src/hooks/useTags.ts

**Position Components** (2 files):
- src/components/positions/PositionSummary.tsx
- src/components/positions/PositionsTable.tsx

**Containers** (5 files):
- src/containers/PublicPositionsContainer.tsx
- src/containers/PrivatePositionsContainer.tsx
- src/containers/OrganizeContainer.tsx
- src/containers/AIChatContainer.tsx
- src/containers/SettingsContainer.tsx

**Strategy & Tag Components** (2 files):
- src/components/strategies/StrategyList.tsx
- src/components/tags/TagList.tsx

**Settings Components** (3 files):
- src/components/settings/UserSettingsForm.tsx
- src/components/settings/PortfolioSettingsForm.tsx
- src/components/settings/ExportForm.tsx

**Pages** (5 files):
- app/public-positions/page.tsx
- app/private-positions/page.tsx
- app/organize/page.tsx
- app/ai-chat/page.tsx
- app/settings/page.tsx

**Modified Files** (2 files):
- app/layout.tsx (add Providers wrapper)
- (Navigation shows automatically via providers)

---

## Services Usage Summary

### Services Used Per Feature

**Public/Private Positions**:
- apiClient (via usePositions hook)

**Organize Page**:
- strategiesApi (direct + via hook)
- tagsApi (direct + via hook)

**AI Chat Page**:
- chatService (via ChatInterface)
- chatAuthService (via ChatInterface)

**Settings Page**:
- apiClient (direct in components)

**Auth/Navigation**:
- authManager (via providers)
- portfolioResolver (via providers)

---

## Common Pitfalls

### ❌ Mistakes to Avoid

1. **Forgetting 'use client' directive**
   - All pages and containers need this

2. **Direct fetch() calls**
   - Always use services

3. **Hardcoding portfolio IDs**
   - Use portfolioResolver

4. **Skipping error handling**
   - Always handle loading and error states

5. **Not testing incrementally**
   - Test each phase before moving on

6. **Recreating existing services**
   - Check if service exists first

7. **Fat page files**
   - Keep pages thin (5-15 lines)

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Auth provider works
- [ ] Navigation shows on all pages
- [ ] Login/logout works

### Phase 2 Complete When:
- [ ] All hooks fetch data correctly
- [ ] Loading and error states work
- [ ] Refetch functions work

### Phase 3 Complete When:
- [ ] Public positions page works
- [ ] Private positions page works
- [ ] Filtering by investment class works

### Phase 4 Complete When:
- [ ] Strategies display and delete
- [ ] Tags create and delete
- [ ] Two-column layout responsive

### Phase 5 Complete When:
- [ ] Chat interface loads
- [ ] Messages stream correctly
- [ ] Portfolio context works

### Phase 6 Complete When:
- [ ] User settings save
- [ ] Portfolio settings save
- [ ] Export downloads files

### Phase 7 Complete When:
- [ ] All pages tested
- [ ] No console errors
- [ ] Performance acceptable
- [ ] Ready for production

---

## Quick Reference

### File Sizes
- Page files: 5-15 lines
- Containers: 30-50 lines
- Components: 50-150 lines
- Hooks: 30-80 lines

### Import Pattern
```typescript
// Services
import { apiClient } from '@/services/apiClient'
import strategiesApi from '@/services/strategiesApi'

// Hooks
import { useAuth } from '@/app/providers'
import { usePositions } from '@/hooks/usePositions'

// Components
import { Button } from '@/components/ui/button'
import { PositionsTable } from '@/components/positions/PositionsTable'
```

### Service Check
Before writing API code:
1. Check if service exists
2. Use service instead of direct fetch
3. Use portfolioResolver for IDs
4. Handle errors properly

---

## Final Checklist

- [ ] All 25 files created
- [ ] All pages accessible via navigation
- [ ] All services used correctly
- [ ] No direct fetch() calls
- [ ] No hardcoded portfolio IDs
- [ ] All error states handled
- [ ] All loading states shown
- [ ] Authentication works
- [ ] Data filtering works
- [ ] Exports work
- [ ] Chat streams work
- [ ] Tests pass
- [ ] No console errors
- [ ] Performance acceptable
- [ ] Ready for deployment

---

## Summary

**Total Files**: 27 (25 new + 2 modified)  
**Implementation Time**: 3-4 weeks  
**Pattern**: Hook → Components → Container → Page  
**Key Principle**: Always use existing services, never recreate
