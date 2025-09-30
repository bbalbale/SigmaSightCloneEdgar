# SigmaSight Authentication & State Management Process

**Document Version**: 1.0
**Date**: September 30, 2025
**Purpose**: Comprehensive documentation of the authentication flow from login through portfolio loading and how state is managed across the application.

---

## Table of Contents

1. [Authentication Architecture Overview](#authentication-architecture-overview)
2. [Login Flow (Step-by-Step)](#login-flow-step-by-step)
3. [State Management](#state-management)
4. [Portfolio ID Resolution](#portfolio-id-resolution)
5. [Portfolio Data Loading](#portfolio-data-loading)
6. [Logout Flow](#logout-flow)
7. [Authentication Services](#authentication-services)
8. [Data Persistence](#data-persistence)
9. [Code References](#code-references)

---

## Authentication Architecture Overview

SigmaSight uses a **hybrid authentication system** with multiple layers:

### Core Components

1. **Dual Authentication Services**
   - `authManager.ts` - JWT token management (localStorage)
   - `chatAuthService.ts` - Cookie-based auth for streaming (HttpOnly cookies)

2. **State Management**
   - React Context (`providers.tsx`) - User authentication state
   - Zustand Store (`portfolioStore.ts`) - Portfolio ID with persistence

3. **Backend Integration**
   - All API calls proxy through `/api/proxy/`
   - FastAPI backend at `http://localhost:8000`
   - JWT tokens in Authorization headers
   - HttpOnly cookies for SSE streaming

### Authentication Flow Diagram

```
┌─────────────┐
│ Login Page  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│ chatAuthService.login()         │
│ - POST /api/v1/auth/login       │
│ - Returns JWT + user data       │
│ - Sets HttpOnly cookie          │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ authManager.setSession()        │
│ - Store JWT in localStorage     │
│ - Store user email              │
│ - Cache user data               │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ portfolioResolver.getUserPortfolioId() │
│ - Fetch user's portfolios       │
│ - Resolve portfolio ID          │
│ - Cache in memory               │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ usePortfolioStore.setPortfolio()│
│ - Store ID in Zustand           │
│ - Persist to localStorage       │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Navigate to /portfolio          │
└─────────────────────────────────┘
```

---

## Login Flow (Step-by-Step)

### 1. User Submits Login Form

**Location**: `frontend/src/components/auth/LoginForm.tsx:44-57`

```typescript
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault()
  setError(null)
  setIsLoading(true)

  try {
    await login(email, password) // Calls useAuth().login
  } catch (err: any) {
    console.error('Login error:', err)
    setError(err?.message || 'Failed to login. Please try again.')
  } finally {
    setIsLoading(false)
  }
}
```

### 2. Auth Context Login Function

**Location**: `frontend/app/providers.tsx:114-119`

```typescript
const login = useCallback(async (email: string, password: string) => {
  const response = await chatAuthService.login(email, password)
  setUser(mapUser(response.user || null))
  await initializePortfolio()
  router.push('/portfolio')
}, [initializePortfolio, mapUser, router])
```

### 3. Chat Auth Service Processes Login

**Location**: `frontend/src/services/chatAuthService.ts:44-138`

#### Step 3.1: Send Login Request

```typescript
const response = await fetch(`${this.baseUrl}/api/v1/auth/login`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include', // Important: sets HttpOnly cookie
  body: JSON.stringify({ email, password }),
});

const data: LoginResponse = await response.json();
// Returns: { access_token, token_type, expires_in, portfolio_id, user }
```

#### Step 3.2: Clear Previous User Data (if different user)

```typescript
if (isDifferentUser) {
  console.log('[Auth] Different user detected, clearing all user-specific data');
  // Clear localStorage except cache_version
  // Clear sessionStorage
  // Clear chat storage
  clearPortfolioState();
}
```

#### Step 3.3: Store Session Data

```typescript
authManager.setSession({
  token: data.access_token,
  email,
  tokenType: data.token_type,
  expiresIn: data.expires_in,
  portfolioId: data.portfolio_id ?? null,
  user: data.user ?? null,
});
```

#### Step 3.4: Resolve Portfolio ID

```typescript
let resolvedPortfolioId = data.portfolio_id ?? null;
try {
  const discoveredId = await portfolioResolver.getUserPortfolioId(true);
  if (discoveredId) {
    resolvedPortfolioId = discoveredId;
  }
} catch (error) {
  console.warn('Could not discover portfolio ID after login:', error);
}

if (resolvedPortfolioId) {
  authManager.setPortfolioId(resolvedPortfolioId);
  setPortfolioState(resolvedPortfolioId);
}
```

#### Step 3.5: Initialize Conversation

```typescript
try {
  const conversationId = await this.initializeConversation();
  console.log('[Auth] Initialized new conversation:', conversationId);
} catch (error) {
  console.warn('[Auth] Could not initialize conversation on login:', error);
}
```

### 4. Auth Manager Stores Session

**Location**: `frontend/src/services/authManager.ts:38-69`

```typescript
setSession(payload: SessionPayload): void {
  const expiresInMs = (payload.expiresIn ?? this.DEFAULT_TOKEN_LIFETIME / 1000) * 1000
  const expiresAt = Date.now() + Math.max(expiresInMs - this.TOKEN_EXPIRY_BUFFER, this.DEFAULT_TOKEN_LIFETIME / 2)

  // Store in memory
  this.session = {
    token: payload.token,
    email: payload.email,
    expiresAt,
    portfolioId: payload.portfolioId ?? null,
    user: payload.user ?? null
  }

  // Store in localStorage
  localStorage.setItem('access_token', payload.token)
  localStorage.setItem('user_email', payload.email)
  localStorage.setItem('token_expires_at', `${expiresAt}`)

  if (payload.portfolioId) {
    localStorage.setItem('portfolio_id', payload.portfolioId)
  }

  if (payload.user) {
    sessionStorage.setItem('auth_user', JSON.stringify(payload.user))
  }
}
```

### 5. Portfolio Resolver Discovers Portfolio ID

**Location**: `frontend/src/services/portfolioResolver.ts:38-133`

#### Step 5.1: Check Cache

```typescript
async getUserPortfolioId(forceRefresh = false): Promise<string | null> {
  const token = authManager.getAccessToken()
  if (!token) return null

  const email = authManager.getCachedUser()?.email || localStorage.getItem('user_email')
  const cacheKey = this.buildCacheKey(token, email || undefined)

  // Check cache first (5-minute TTL)
  if (!forceRefresh && this.portfolioCache.has(cacheKey)) {
    const expiry = this.cacheExpiry.get(cacheKey) || 0
    if (Date.now() < expiry) {
      return this.portfolioCache.get(cacheKey)?.id ?? null
    }
  }
```

#### Step 5.2: Fetch from Backend

```typescript
  const response = await requestManager.authenticatedFetch(
    '/api/proxy/api/v1/data/portfolios',
    token,
    {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      maxRetries: 1,
      timeout: 5000,
      dedupe: true
    }
  )

  if (response.ok) {
    const portfolios = await response.json()

    if (Array.isArray(portfolios) && portfolios.length > 0) {
      const portfolio = portfolios[0]

      // Cache the portfolio info
      this.portfolioCache.set(cacheKey, {
        id: portfolio.id,
        name: portfolio.name,
        totalValue: portfolio.total_value || 0,
        positionCount: portfolio.position_count || 0
      })

      authManager.setPortfolioId(portfolio.id)
      return portfolio.id
    }
  }
```

#### Step 5.3: Fallback Mapping (Development)

```typescript
  // Fallback for development if backend unavailable
  const portfolioMap: Record<string, string> = {
    'demo_individual@sigmasight.com': '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe',
    'demo_hnw@sigmasight.com': 'e23ab931-a033-edfe-ed4f-9d02474780b4',
    'demo_hedgefundstyle@sigmasight.com': 'fcd71196-e93e-f000-5a74-31a9eead3118'
  }

  const mappedId = portfolioMap[email]
  if (mappedId) {
    authManager.setPortfolioId(mappedId)
    return mappedId
  }
}
```

### 6. Portfolio Store Persists ID

**Location**: `frontend/src/stores/portfolioStore.ts:31-36`

```typescript
setPortfolio: (id, name) => {
  set({
    portfolioId: id,
    portfolioName: name ?? null
  })
  // Zustand persist middleware automatically saves to localStorage
}
```

**Storage**: `localStorage.getItem('portfolio-storage')`

```json
{
  "state": {
    "portfolioId": "e23ab931-a033-edfe-ed4f-9d02474780b4"
  },
  "version": 2
}
```

### 7. Navigation to Portfolio Page

After successful login:
- User is redirected to `/portfolio`
- Auth context provides authenticated user
- Portfolio ID is available in Zustand store
- Data fetching begins automatically

---

## State Management

### Authentication State (React Context)

**Location**: `frontend/app/providers.tsx:25-33`

```typescript
interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshAuth: () => Promise<void>
}
```

**User Object Structure**:
```typescript
interface User {
  id: string
  email: string
  fullName: string
  isAdmin: boolean
}
```

**Access Pattern**:
```typescript
import { useAuth } from '../app/providers'

function MyComponent() {
  const { user, loading, login, logout } = useAuth()
  // ...
}
```

### Portfolio State (Zustand Store)

**Location**: `frontend/src/stores/portfolioStore.ts:10-21`

```typescript
interface PortfolioStore {
  // State
  portfolioId: string | null
  portfolioName: string | null

  // Actions
  setPortfolio: (id: string, name?: string | null) => void
  clearPortfolio: () => void

  // Computed
  hasPortfolio: () => boolean
}
```

**Access Patterns**:

```typescript
// In React components
import { usePortfolioStore } from '@/stores/portfolioStore'

function MyComponent() {
  const { portfolioId, portfolioName } = usePortfolioStore()
  // or use selectors
  const portfolioId = usePortfolioStore(state => state.portfolioId)
}

// Outside React (services, utilities)
import { getPortfolioId } from '@/stores/portfolioStore'

const portfolioId = getPortfolioId()
```

**Persistence Configuration**:
- **Storage Key**: `portfolio-storage`
- **Version**: 2
- **Persisted Fields**: Only `portfolioId` (name fetched fresh)
- **Storage Type**: localStorage

### Session Data (Auth Manager)

**Location**: `frontend/src/services/authManager.ts:13-19`

```typescript
interface AuthSession {
  token: string
  email: string
  expiresAt: number
  portfolioId: string | null
  user: AuthUser | null
}
```

**Storage Locations**:
- **In-Memory**: `this.session` object
- **localStorage**:
  - `access_token` - JWT token
  - `user_email` - User email
  - `token_expires_at` - Expiration timestamp
  - `portfolio_id` - Portfolio UUID
- **sessionStorage**:
  - `auth_user` - JSON user object

---

## Portfolio ID Resolution

### Resolution Strategy

The application uses a **three-tier resolution strategy**:

1. **Primary**: Fetch from backend API
2. **Secondary**: Check localStorage cache
3. **Fallback**: Development hardcoded mapping

### Resolution Flow

```typescript
// 1. On login - portfolioResolver.getUserPortfolioId(forceRefresh: true)
const portfolioId = await portfolioResolver.getUserPortfolioId(true)
authManager.setPortfolioId(portfolioId)
setPortfolioState(portfolioId) // Zustand

// 2. On app load - portfolioResolver.getUserPortfolioId(forceRefresh: false)
const portfolioId = await portfolioResolver.getUserPortfolioId(false)
// Uses cache if available and not expired (5 min TTL)

// 3. In components - usePortfolioStore()
const { portfolioId } = usePortfolioStore()
// Reads from Zustand (which reads from localStorage on hydration)
```

### Cache Management

**Memory Cache** (portfolioResolver):
- **Duration**: 5 minutes
- **Key Format**: `portfolio_${email}` or `portfolio_${token.substring(0,10)}`
- **Stored Data**: `{ id, name, totalValue, positionCount }`

**localStorage Cache** (Zustand):
- **Duration**: Indefinite (cleared only on logout)
- **Key**: `portfolio-storage`
- **Stored Data**: `{ portfolioId }`

**Invalidation**:
- Logout: Clears all caches
- Different user login: Clears previous user caches
- Force refresh: Bypasses memory cache, fetches fresh

---

## Portfolio Data Loading

### Data Loading Hook

**Location**: `frontend/src/hooks/usePortfolioData.ts:52-133`

The `usePortfolioData` hook orchestrates all portfolio data fetching:

```typescript
export function usePortfolioData(): UsePortfolioDataReturn {
  const portfolioId = usePortfolioStore(state => state.portfolioId)

  useEffect(() => {
    const loadData = async () => {
      const data = await loadPortfolioData(abortController.signal, {
        portfolioId,
        forceRefresh: retryCount > 0
      })

      // Process and set state...
    }

    loadData()
  }, [portfolioId, retryCount])
}
```

### Portfolio Service Data Fetching

**Location**: `frontend/src/services/portfolioService.ts:38-74`

```typescript
export async function loadPortfolioData(
  abortSignal?: AbortSignal,
  options: LoadOptions = {}
) {
  const token = authManager.getAccessToken()
  if (!token) throw new Error('Authentication token unavailable')

  // Resolve portfolio ID
  let portfolioId = options.portfolioId ?? authManager.getPortfolioId()

  if (!portfolioId || options.forceRefresh) {
    portfolioId = await portfolioResolver.getUserPortfolioId(options.forceRefresh)
  }

  if (!portfolioId) throw new Error('Could not resolve portfolio ID')

  authManager.setPortfolioId(portfolioId)

  // Fetch data from multiple APIs in parallel
  const results = await fetchPortfolioDataFromApis(portfolioId, token, abortSignal)

  return {
    ...results,
    portfolioId
  }
}
```

### Parallel API Fetching

**Location**: `frontend/src/services/portfolioService.ts:79-152`

```typescript
async function fetchPortfolioDataFromApis(
  portfolioId: string,
  token: string,
  abortSignal?: AbortSignal
) {
  // Fetch 3 APIs in parallel using Promise.allSettled
  const [overviewResult, positionsResult, factorExposuresResult] =
    await Promise.allSettled([
      // 1. Overview API - portfolio metrics
      analyticsApi.getOverview(portfolioId),

      // 2. Positions API - position details
      apiClient.get(`/api/v1/data/positions/details?portfolio_id=${portfolioId}`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: abortSignal
      }),

      // 3. Factor Exposures API - factor data
      apiClient.get(`/api/v1/analytics/portfolio/${portfolioId}/factor-exposures`, {
        headers: { Authorization: `Bearer ${token}` },
        signal: abortSignal
      })
    ])

  // Process results and handle partial failures
  return {
    exposures: calculateExposuresFromOverview(overviewResponse),
    positions: transformPositionDetails(positionData.positions),
    factorExposures: factorExposuresResult.value?.data?.factors || null,
    portfolioInfo: { name: 'Portfolio' },
    errors: {
      overview: overviewResult.status === 'rejected' ? overviewResult.reason : null,
      positions: positionsResult.status === 'rejected' ? positionsResult.reason : null,
      factorExposures: factorExposuresResult.status === 'rejected' ? factorExposuresResult.reason : null
    }
  }
}
```

### Data Flow in Portfolio Page

**Location**: `frontend/app/portfolio/page.tsx:17-103`

```typescript
function PortfolioPageContent() {
  const {
    loading,
    error,
    portfolioName,
    portfolioSummaryMetrics,
    positions,
    shortPositions,
    publicPositions,
    optionsPositions,
    privatePositions,
    factorExposures,
    dataLoaded,
    handleRetry
  } = usePortfolioData()

  // Render components with fetched data
  return (
    <div>
      <PortfolioHeader portfolioName={portfolioName} />
      <PortfolioMetrics metrics={portfolioSummaryMetrics} />
      <FactorExposureCards factors={factorExposures} />
      <PortfolioPositions
        longPositions={positions}
        publicPositions={publicPositions}
        optionsPositions={optionsPositions}
        privatePositions={privatePositions}
      />
    </div>
  )
}
```

---

## Logout Flow

### Logout Sequence

**Location**: `frontend/app/providers.tsx:121-131`

```typescript
const logout = useCallback(async () => {
  try {
    // 1. Call backend logout endpoint (clears HttpOnly cookie)
    await chatAuthService.logout()
  } finally {
    // 2. Clear authManager session
    authManager.clearSession()

    // 3. Clear user state
    setUser(null)

    // 4. Clear portfolio state
    clearPortfolioState()

    // 5. Clear portfolio resolver cache
    portfolioResolver.clearCache()

    // 6. Redirect to login
    router.push('/login')
  }
}, [router])
```

### Chat Auth Service Logout

**Location**: `frontend/src/services/chatAuthService.ts:196-220`

```typescript
async logout(): Promise<void> {
  try {
    // Clear backend session (removes HttpOnly cookie)
    await fetch(`${this.baseUrl}/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
  } catch (error) {
    console.error('Logout error:', error);
  } finally {
    // Clear local state regardless of backend call
    this.isAuthenticated = false;
    this.currentUser = null;
    authManager.clearSession();
    clearPortfolioState();

    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('auth_user');
      localStorage.removeItem('conversationId');
      localStorage.removeItem('chatHistory');
      localStorage.removeItem('currentConversationId');
      sessionStorage.removeItem('conversationId');
      sessionStorage.removeItem('chatHistory');
    }
  }
}
```

### Auth Manager Session Clearing

**Location**: `frontend/src/services/authManager.ts:74-85`

```typescript
clearSession(): void {
  this.session = null
  if (typeof window === 'undefined') return

  localStorage.removeItem('access_token')
  localStorage.removeItem('user_email')
  localStorage.removeItem('token_expires_at')
  localStorage.removeItem('portfolio_id')
  sessionStorage.removeItem('auth_user')
}
```

### What Gets Cleared on Logout

**localStorage**:
- `access_token`
- `user_email`
- `token_expires_at`
- `portfolio_id`
- `portfolio-storage` (Zustand)
- `conversationId`
- `chatHistory`
- `currentConversationId`

**sessionStorage**:
- `auth_user`
- `conversationId`
- `chatHistory`

**In-Memory**:
- Auth context user state
- AuthManager session object
- PortfolioResolver cache maps
- Portfolio Zustand store state

---

## Authentication Services

### 1. authManager (JWT Token Management)

**File**: `frontend/src/services/authManager.ts`

**Purpose**: Centralized JWT token and session management

**Key Methods**:

```typescript
// Session Management
setSession(payload: SessionPayload): void
clearSession(): void

// Token Management
getAccessToken(): string | null
validateToken(token?: string): Promise<boolean>

// Portfolio ID Management
setPortfolioId(portfolioId: string | null): void
getPortfolioId(): string | null

// User Management
setCachedUser(user: AuthUser | null): void
getCachedUser(): AuthUser | null
getCurrentUser(): Promise<AuthUser | null>
```

**Storage Strategy**:
- **In-Memory**: Fast access, lost on refresh
- **localStorage**: JWT, email, expiry, portfolio ID
- **sessionStorage**: User object (for faster hydration)

### 2. chatAuthService (Cookie-Based Auth)

**File**: `frontend/src/services/chatAuthService.ts`

**Purpose**: Authentication for SSE streaming with HttpOnly cookies

**Key Methods**:

```typescript
// Authentication
login(email: string, password: string): Promise<LoginResponse>
logout(): Promise<void>
checkAuth(): Promise<AuthUser | null>
refreshIfNeeded(): Promise<boolean>

// Conversation Management
initializeConversation(): Promise<string | null>

// Streaming
sendChatMessage(
  message: string,
  conversationId: string,
  onChunk: (chunk: string) => void,
  onError: (error: any) => void,
  onDone: () => void
): Promise<AbortController>

// Authenticated Requests
authenticatedFetch(url: string, options?: RequestInit): Promise<Response>
```

**Why Dual Authentication?**:
- **JWT (localStorage)**: Portfolio API calls, RESTful endpoints
- **Cookies (HttpOnly)**: SSE streaming (can't set headers on EventSource)

### 3. portfolioResolver (Portfolio ID Resolution)

**File**: `frontend/src/services/portfolioResolver.ts`

**Purpose**: Dynamic portfolio ID discovery and caching

**Key Methods**:

```typescript
// Portfolio Discovery
getUserPortfolioId(forceRefresh?: boolean): Promise<string | null>
validatePortfolioOwnership(portfolioId: string): Promise<boolean>

// Cache Management
clearCache(): void
refreshPortfolioInfo(): Promise<string | null>

// Manual Override (for backward compatibility)
setUserPortfolioId(portfolioId: string, email?: string | null): void
```

**Cache Strategy**:
- **Memory Cache**: 5-minute TTL, keyed by email/token
- **localStorage Cache**: Indefinite, cleared on logout
- **Backend Fetch**: On cache miss or force refresh

---

## Data Persistence

### Storage Overview

| Data | Storage Type | Key | Duration | Cleared On |
|------|-------------|-----|----------|------------|
| JWT Token | localStorage | `access_token` | 30 min (token expiry) | Logout, token expiry |
| User Email | localStorage | `user_email` | Session | Logout |
| Token Expiry | localStorage | `token_expires_at` | Session | Logout |
| Portfolio ID | localStorage | `portfolio_id` | Session | Logout |
| Portfolio Store | localStorage | `portfolio-storage` | Indefinite | Logout |
| User Object | sessionStorage | `auth_user` | Browser tab | Logout, tab close |
| Conversation ID | localStorage | `conversationId` | Session | Logout, new login |
| Chat History | localStorage | `chatHistory` | Session | Logout, new login |

### Zustand Persistence Middleware

**Location**: `frontend/src/stores/portfolioStore.ts:51-59`

```typescript
persist(
  (set, get) => ({
    // ... store implementation
  }),
  {
    name: 'portfolio-storage',
    version: 2,
    partialize: (state) => ({
      portfolioId: state.portfolioId
      // Only persist ID, fetch name fresh
    })
  }
)
```

**Storage Format**:
```json
{
  "state": {
    "portfolioId": "e23ab931-a033-edfe-ed4f-9d02474780b4"
  },
  "version": 2
}
```

### Hydration Strategy

**On App Load** (`frontend/app/providers.tsx:73-108`):

1. Check localStorage for `access_token`
2. If no token → Redirect to login
3. If token exists → Validate with backend
4. If valid → Fetch user info and portfolio ID
5. Zustand automatically hydrates from localStorage
6. Portfolio data fetching begins

**Hydration in authManager** (`frontend/src/services/authManager.ts:90-123`):

```typescript
private hydrateSession(): void {
  if (this.session || typeof window === 'undefined') return

  const token = localStorage.getItem('access_token')
  if (!token) {
    this.session = null
    return
  }

  const email = localStorage.getItem('user_email') || ''
  const expiresAt = Number(localStorage.getItem('token_expires_at'))
  const portfolioId = localStorage.getItem('portfolio_id') || null

  let user: AuthUser | null = null
  const storedUser = sessionStorage.getItem('auth_user')
  if (storedUser && storedUser !== 'undefined') {
    try {
      user = JSON.parse(storedUser)
    } catch {
      user = null
    }
  }

  this.session = { token, email, expiresAt, portfolioId, user }
}
```

---

## Code References

### Key Files

| File | Purpose | Lines of Code |
|------|---------|---------------|
| `app/providers.tsx` | Auth Context Provider | 152 |
| `services/authManager.ts` | JWT Token Management | 271 |
| `services/chatAuthService.ts` | Cookie Auth + Streaming | 409 |
| `services/portfolioResolver.ts` | Portfolio ID Resolution | 207 |
| `services/portfolioService.ts` | Portfolio Data Fetching | 245 |
| `stores/portfolioStore.ts` | Portfolio ID State | 73 |
| `hooks/usePortfolioData.ts` | Portfolio Data Hook | 158 |
| `components/auth/LoginForm.tsx` | Login UI Component | 178 |
| `app/portfolio/page.tsx` | Portfolio Page | 108 |

### Critical Import Paths

```typescript
// Authentication
import { useAuth } from '../app/providers'
import { authManager } from '@/services/authManager'
import { chatAuthService } from '@/services/chatAuthService'

// Portfolio State
import { usePortfolioStore } from '@/stores/portfolioStore'
import { getPortfolioId, setPortfolioState, clearPortfolioState } from '@/stores/portfolioStore'

// Portfolio Services
import { portfolioResolver } from '@/services/portfolioResolver'
import { loadPortfolioData } from '@/services/portfolioService'

// Hooks
import { usePortfolioData } from '@/hooks/usePortfolioData'
```

### API Endpoints Used

| Endpoint | Method | Purpose | Auth Type |
|----------|--------|---------|-----------|
| `/api/v1/auth/login` | POST | User login | None |
| `/api/v1/auth/logout` | POST | User logout | Cookie |
| `/api/v1/auth/me` | GET | Get current user | JWT + Cookie |
| `/api/v1/data/portfolios` | GET | List user portfolios | JWT |
| `/api/v1/data/portfolio/{id}/complete` | GET | Full portfolio data | JWT |
| `/api/v1/data/positions/details` | GET | Position details | JWT |
| `/api/v1/analytics/portfolio/{id}/factor-exposures` | GET | Factor exposures | JWT |
| `/api/v1/chat/conversations` | POST | Create conversation | JWT + Cookie |
| `/api/v1/chat/send` | POST | Send chat message (SSE) | Cookie |

### State Access Patterns

```typescript
// ✅ CORRECT: Use hooks in components
function MyComponent() {
  const { user, login, logout } = useAuth()
  const { portfolioId } = usePortfolioStore()
  const { positions, loading } = usePortfolioData()
}

// ✅ CORRECT: Use getters in services/utilities
import { getPortfolioId } from '@/stores/portfolioStore'

async function myService() {
  const portfolioId = getPortfolioId()
  const token = authManager.getAccessToken()
}

// ❌ WRONG: Don't call hooks outside components
function myService() {
  const { portfolioId } = usePortfolioStore() // Error!
}
```

---

## Summary

### Authentication Flow Summary

1. **Login** → chatAuthService.login()
2. **Store JWT** → authManager.setSession()
3. **Resolve Portfolio ID** → portfolioResolver.getUserPortfolioId()
4. **Store Portfolio ID** → Zustand portfolioStore
5. **Navigate** → /portfolio page
6. **Load Data** → usePortfolioData() hook
7. **Fetch APIs** → portfolioService.loadPortfolioData()
8. **Display** → Portfolio components

### State Management Summary

- **User Authentication**: React Context (in-memory)
- **JWT Token**: authManager (localStorage + memory)
- **Portfolio ID**: Zustand (localStorage + memory)
- **Portfolio Data**: React useState (in-memory, re-fetched on mount)
- **Chat Auth**: Cookies (HttpOnly, managed by backend)

### Key Design Decisions

1. **No In-App Portfolio Switching**: Each login = one portfolio session
2. **Dual Auth System**: JWT for APIs, cookies for SSE streaming
3. **Aggressive Caching**: 5-minute memory cache, localStorage persistence
4. **Parallel API Calls**: Promise.allSettled for graceful degradation
5. **Zustand for Portfolio ID**: Global state with built-in persistence
6. **React Context for Auth**: Standard pattern for authentication state

### Portfolio ID Persistence

The portfolio ID persists across:
- ✅ Page navigations
- ✅ Browser refreshes
- ✅ Tab closes and reopens (if token valid)
- ❌ Logout
- ❌ Different user login

---

**Document Maintained By**: SigmaSight Engineering Team
**Last Updated**: September 30, 2025
**Related Docs**: `project-structure.md`, `API_AND_DATABASE_SUMMARY.md`
