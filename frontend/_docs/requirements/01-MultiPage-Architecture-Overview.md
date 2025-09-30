# SigmaSight Multi-Page Architecture Overview

**Purpose**: High-level architecture for converting single-page app to multi-page app  
**Audience**: AI coding agents with limited context windows  
**Last Updated**: September 29, 2025

---

## Core Architecture Pattern

### Hybrid Architecture Approach

We use a **hybrid approach** combining two patterns:

1. **Modular Pattern** (Existing Portfolio Page)
   - Already implemented and working well
   - Page file contains composition logic (~230 lines)
   - Direct use of hooks and components
   - No changes needed

2. **Container Pattern** (All New Pages)
   - Thin route files (5-15 lines)
   - Business logic in containers (150-250 lines)
   - Better for Docker optimization and code splitting
   - Clear separation of concerns

### Client-Side Only Architecture (FastAPI Backend)

```
┌─────────────────────────────────┐
│   Next.js Client Pages          │ ('use client' components)
│   /app/[route]/page.tsx         │ THIN WRAPPERS (5-15 lines)
└────────────┬────────────────────┘
             │ imports
             ▼
┌─────────────────────────────────┐
│   Page Containers               │ (Business logic)
│   /src/containers/              │ (100-300 lines)
└────────────┬────────────────────┘
             │ uses
             ├──────────┬──────────┐
             ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│  Hooks   │ │Components│ │ Services │
│ (Data)   │ │   (UI)   │ │  (API)   │
└──────────┘ └──────────┘ └────┬─────┘
                                │ calls
                                ▼
                    ┌─────────────────────┐
                    │  Next.js API Proxy  │
                    │  /app/api/proxy/    │
                    └──────────┬──────────┘
                               │ forwards
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI Backend   │
                    │  localhost:8000     │
                    └─────────────────────┘
```

---

## Key Principles

### ✅ DO Use
1. **Client Components** - All pages use `'use client'`
2. **Existing Services** - Import from `/src/services/`
3. **Custom Hooks** - Data fetching in `/src/hooks/`
4. **Thin Page Files** - Pages are 5-15 lines, just import containers
5. **Service Layer** - ALL API calls go through services
6. **Proxy Pattern** - Services call `/api/proxy/` which forwards to backend

### ❌ DON'T Use
1. **Server Components** - No RSC, no `'server-only'`
2. **Direct API Calls** - Never `fetch()` backend directly
3. **cookies()** from next/headers - Not available client-side
4. **Server Actions** - Not compatible with FastAPI backend
5. **Direct Backend Calls** - Always use proxy

---

## Directory Structure Changes

### Current Structure (Keep)
```
app/
├── api/proxy/[...path]/route.ts    # ✅ Keep - CORS proxy
├── portfolio/page.tsx              # ✅ Keep - Already thin
├── login/page.tsx                  # ✅ Keep - Already thin
├── landing/page.tsx                # ✅ Keep
├── layout.tsx                      # 📝 Update - Add providers
└── page.tsx                        # ✅ Keep - Root redirect

src/
├── services/                       # ✅ Keep - ALL existing services
│   ├── apiClient.ts               # ✅ Base HTTP client
│   ├── authManager.ts             # ✅ Auth & tokens
│   ├── portfolioService.ts        # ✅ Portfolio data
│   ├── portfolioResolver.ts       # ✅ Portfolio ID resolution
│   ├── analyticsApi.ts            # ✅ Analytics endpoints
│   ├── strategiesApi.ts           # ✅ Strategies API
│   ├── tagsApi.ts                 # ✅ Tags API
│   ├── chatService.ts             # ✅ Chat streaming
│   └── ...
├── components/                     # ✅ Keep - All existing
├── hooks/                          # ✅ Keep & expand
└── lib/                            # ✅ Keep - Utilities
```

### New Additions Needed
```
app/
├── public-positions/               # 🆕 New route
│   └── page.tsx                   # THIN (8 lines)
├── private-positions/              # 🆕 New route
│   └── page.tsx                   # THIN (8 lines)
├── organize/                       # 🆕 New route
│   └── page.tsx                   # THIN (8 lines)
├── ai-chat/                        # 🆕 New route
│   └── page.tsx                   # THIN (8 lines)
├── settings/                       # 🆕 New route
│   └── page.tsx                   # THIN (8 lines)
└── providers.tsx                   # 🆕 Auth context provider

src/
├── containers/                     # 🆕 New folder
│   ├── PublicPositionsContainer.tsx
│   ├── PrivatePositionsContainer.tsx
│   ├── OrganizeContainer.tsx
│   ├── AIChatContainer.tsx
│   └── SettingsContainer.tsx
├── components/
│   ├── navigation/                 # 🆕 New folder
│   │   └── Navigation.tsx
│   ├── positions/                  # 🆕 New folder
│   │   ├── PositionsTable.tsx
│   │   └── PositionSummary.tsx
│   ├── strategies/                 # 🆕 New folder
│   │   └── StrategyList.tsx
│   ├── tags/                       # 🆕 New folder
│   │   └── TagList.tsx
│   └── settings/                   # 🆕 New folder
│       ├── UserSettingsForm.tsx
│       ├── PortfolioSettingsForm.tsx
│       └── ExportForm.tsx
└── hooks/
    ├── usePositions.ts             # 🆕 Hook for position data
    ├── useStrategies.ts            # 🆕 Hook for strategies
    └── useTags.ts                  # 🆕 Hook for tags
```

---

## Service Layer Architecture

### Existing Services (Use These!)

| Service | Purpose | Endpoints Used |
|---------|---------|----------------|
| **apiClient.ts** | Base HTTP client with retry | All endpoints |
| **authManager.ts** | JWT token management | `/auth/login`, `/auth/me` |
| **portfolioService.ts** | Portfolio data | `/analytics/portfolio/{id}/overview`<br>`/data/positions/details` |
| **portfolioResolver.ts** | Dynamic portfolio ID | `/data/portfolios` |
| **analyticsApi.ts** | Analytics calculations | `/analytics/portfolio/{id}/*` |
| **strategiesApi.ts** | Strategy management | `/strategies/*` |
| **tagsApi.ts** | Tag management | `/tags/*` |
| **chatService.ts** | Chat streaming | `/chat/*` |

### Service Usage Pattern

```typescript
// ✅ CORRECT: Use existing services
import { apiClient } from '@/services/apiClient'
import { portfolioResolver } from '@/services/portfolioResolver'
import { analyticsApi } from '@/services/analyticsApi'

// In a custom hook
const portfolioId = await portfolioResolver.getUserPortfolioId()
const { data } = await analyticsApi.getOverview(portfolioId)

// ❌ WRONG: Don't make direct API calls
const response = await fetch('http://localhost:8000/api/v1/data/positions')
```

---

## State Management Architecture

### Portfolio ID Management (Zustand Store)

```typescript
// src/stores/portfolioStore.ts
interface PortfolioStore {
  portfolioId: string | null
  setPortfolioId: (id: string) => void
  clearPortfolioId: () => void
}

// Key Features:
- Persists across ALL page navigations
- No URL parameters (cleaner, more secure)
- Single source of truth for portfolio ID
- Cleared only on logout
- Supports thousands of users without URL pollution
```

### Portfolio Switching Policy
- **No in-app portfolio switching**
- Users must logout to switch portfolios
- Simplifies state management
- Better security and session isolation
- Each login = one portfolio session

## Authentication Flow

### Client-Side Auth Context

```typescript
// app/providers.tsx
'use client'

export function Providers({ children }) {
  const [user, setUser] = useState(null)
  const [portfolioId, setPortfolioId] = useState(null)
  
  // Use existing authManager service
  const checkAuth = async () => {
    const token = localStorage.getItem('access_token')
    const isValid = await authManager.validateToken(token)
    // ...
  }
  
  // Use existing portfolioResolver service
  const loadPortfolioId = async () => {
    const id = await portfolioResolver.getUserPortfolioId()
    setPortfolioId(id)
  }
  
  return (
    <AuthContext.Provider value={{ user, portfolioId, ... }}>
      {children}
    </AuthContext.Provider>
  )
}
```

---

## Page Creation Pattern

### Step-by-Step for Each New Page

1. **Create Custom Hook** (`/src/hooks/`)
   - Uses existing services
   - Manages data fetching & state
   - Returns loading, error, data, refetch

2. **Create Container Component** (`/src/containers/`)
   - Uses custom hook
   - Composes UI components
   - Handles page-level logic
   - 100-300 lines

3. **Create UI Components** (`/src/components/[category]/`)
   - Reusable, focused components
   - Display only, minimal logic
   - < 100 lines each

4. **Create Thin Page Route** (`/app/[route]/page.tsx`)
   - Just imports and renders container
   - 5-15 lines total

### Example: Public Positions Page

```typescript
// 1. Hook: src/hooks/usePositions.ts
export function usePositions(investmentClass) {
  const { portfolioId } = useAuth()
  const [positions, setPositions] = useState([])
  
  useEffect(() => {
    // Use existing apiClient service
    const endpoint = `/api/v1/data/positions/details?portfolio_id=${portfolioId}`
    const response = await apiClient.get(endpoint)
    setPositions(response.positions.filter(p => p.investment_class === investmentClass))
  }, [portfolioId, investmentClass])
  
  return { positions, loading, error }
}

// 2. Container: src/containers/PublicPositionsContainer.tsx
export function PublicPositionsContainer() {
  const { positions, loading, error } = usePositions('PUBLIC')
  
  return (
    <div>
      <h1>Public Positions</h1>
      <PositionSummary positions={positions} />
      <PositionsTable positions={positions} />
    </div>
  )
}

// 3. Page: app/public-positions/page.tsx (THIN!)
'use client'
import { PublicPositionsContainer } from '@/containers/PublicPositionsContainer'

export default function PublicPositionsPage() {
  return <PublicPositionsContainer />
}
```

---

## Navigation Structure

### Dropdown Navigation Menu

```typescript
// src/components/navigation/NavigationDropdown.tsx
const navigationItems = [
  { href: '/portfolio', label: 'Dashboard', icon: Home },
  { href: '/public-positions', label: 'Public Positions', icon: Building2 },
  { href: '/private-positions', label: 'Private Positions', icon: Shield },
  { href: '/organize', label: 'Organize', icon: PieChart },
  { href: '/ai-chat', label: 'AI Chat', icon: Bot },
  { href: '/settings', label: 'Settings', icon: Settings },
]

// Features:
- Dropdown menu (not horizontal nav bar)
- Current page indicator
- User logout option in dropdown
- No portfolio switcher (logout to switch)
- Clean, minimal interface
```

---

## Investment Classes

### Position Types
- **PUBLIC**: Regular equities, ETFs (position_type: LONG, SHORT)
- **OPTIONS**: Options contracts (position_type: LC, LP, SC, SP)
- **PRIVATE**: Private/alternative investments

### API Response Structure
```typescript
// /data/positions/details response
{
  positions: [
    {
      id: string
      symbol: string
      investment_class: 'PUBLIC' | 'OPTIONS' | 'PRIVATE'
      position_type: 'LONG' | 'SHORT' | 'LC' | 'LP' | 'SC' | 'SP'
      quantity: number
      current_price: number
      market_value: number
      cost_basis: number
      unrealized_pnl: number
      // Options-specific fields (when investment_class = 'OPTIONS')
      strike_price?: number
      expiration_date?: string
      underlying_symbol?: string
    }
  ]
}
```

---

## Critical Reminders

### For AI Agents

1. **Always use services** - Never make direct fetch() calls
2. **Check existing services** - Don't recreate what exists
3. **Thin page files** - Pages should be < 15 lines
4. **Use portfolioResolver** - Never hardcode portfolio IDs
5. **Client components only** - Always use `'use client'`
6. **Follow the pattern** - Hook → Container → Page
7. **Proxy all calls** - API calls go through `/api/proxy/`

### Common Mistakes to Avoid

```typescript
// ❌ WRONG: Direct backend call
fetch('http://localhost:8000/api/v1/data/positions')

// ✅ CORRECT: Use service
import { apiClient } from '@/services/apiClient'
await apiClient.get('/api/v1/data/positions/details')

// ❌ WRONG: Hardcoded portfolio ID
const portfolioId = '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe'

// ✅ CORRECT: Use resolver
import { portfolioResolver } from '@/services/portfolioResolver'
const portfolioId = await portfolioResolver.getUserPortfolioId()

// ❌ WRONG: Fat page file with business logic
export default function Page() {
  const [data, setData] = useState([])
  useEffect(() => { /* 100 lines of logic */ }, [])
  return <div>{/* 200 lines of JSX */}</div>
}

// ✅ CORRECT: Thin page, container has logic
export default function Page() {
  return <PageContainer />
}
```

---

## Implementation Phases (Hybrid Approach)

### Phase 1: Core Setup & State Management (Days 1-2)
- Create `src/stores/portfolioStore.ts` (Zustand)
- Create `app/providers.tsx` with auth context
- Create `src/components/navigation/NavigationDropdown.tsx`
- Update `app/layout.tsx` to use providers & navigation
- **Keep portfolio page as-is** (already working)

### Phase 2: Data Hooks (Day 3)
- Create `src/hooks/usePositions.ts` (uses portfolioStore)
- Create `src/hooks/useStrategies.ts` (uses portfolioStore)
- Create `src/hooks/useTags.ts` (uses portfolioStore)

### Phase 3: Position Pages with Containers (Days 4-5)
- Create containers: PublicPositionsContainer, PrivatePositionsContainer
- Create thin pages: public-positions, private-positions (8 lines each)
- Reuse existing position components

### Phase 4: Organize & Chat Pages (Days 6-7)
- Create OrganizeContainer, AIChatContainer
- Create thin pages: organize, ai-chat
- Reuse existing ChatInterface

### Phase 5: Settings & Testing (Days 8-11)
- Create SettingsContainer
- Create settings page
- Test portfolio ID persistence
- Test navigation dropdown
- Verify auth flow across pages

---

## Next Steps

1. Review individual page implementation guides:
   - `02-PublicPositions-Implementation.md`
   - `03-PrivatePositions-Implementation.md`
   - `04-Organize-Implementation.md`
   - `05-AIChat-Implementation.md`
   - `06-Settings-Implementation.md`

2. Check service reference:
   - `07-Services-Reference.md`

3. Follow implementation checklist:
   - `08-Implementation-Checklist.md`

---

## Summary

**Architecture**: Hybrid approach - existing modular + new container pattern
**State Management**: Zustand for portfolio ID (no URL params)
**Navigation**: Dropdown menu with 6 pages
**Portfolio Switching**: Logout required (no in-app switching)
**Backend**: FastAPI via proxy
**Services**: Use existing 11 services, never recreate
**Existing Page**: Keep portfolio page as-is (already optimized)
**New Pages**: Use container pattern for better Docker optimization
**Result**: Pragmatic, maintainable, scalable multi-page app
