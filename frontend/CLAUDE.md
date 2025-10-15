# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
Updated September 30, 2025

## Project Overview

SigmaSight Frontend - A Next.js 14 multi-page portfolio analytics application with AI chat integration. The frontend is a client-side application that connects to a FastAPI backend through a Next.js proxy layer.

> 🤖 **CRITICAL**: The backend uses **OpenAI Responses API**, NOT Chat Completions API.

> 🤖 **CRITICAL**: Never commit changes unless explicity told to do so.


**Current Status**: Phase 1 Complete (Core infrastructure) - Portfolio page working with real data, multi-page architecture implemented with navigation dropdown and global state management.

---

## Development Commands

### 🐳 Docker Commands (Preferred)
> **📖 Full Docker Guide**: See [DOCKER.md](./DOCKER.md) for comprehensive Docker documentation

```bash
# Using Docker Compose (Recommended - uses .env.local)
cd frontend
docker-compose up -d              # Build and start
docker-compose logs -f            # View logs
docker-compose down               # Stop and remove

# Using Docker directly with env file
docker build -t sigmasight-frontend .
docker run -d -p 3005:3005 --env-file .env.local --name sigmasight-frontend sigmasight-frontend

# Check health
curl http://localhost:3005/api/health
```

### Traditional NPM Commands
```bash
# Development server (port 3005)
cd frontend && npm run dev

# Production build
npm run build && npm run start

# Code quality
npm run lint
npm run type-check

# Testing
npm run test         # Run tests once
npm run test:watch   # Run tests in watch mode

# Install dependencies
npm install
```

### Key Configuration
- **Port**: 3005 (configured to avoid conflicts)
- **Docker Image**: sigmasight-frontend (~210MB optimized, Node 20 LTS)
- **Backend API**: Configured via `.env.local` - switches between local/Railway
- **Authentication**: JWT tokens stored in localStorage
- **Health Check**: `/api/health` endpoint for container monitoring
- **Node.js Requirement**: Node.js 20.0 or higher (updated 2025-10-09)

### Environment Configuration
Backend URL is configured via `.env.local` (not hardcoded):

**Local Backend:**
```bash
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000/api/v1
```

**Railway Backend:**
```bash
BACKEND_URL=https://sigmasight-be-sandbox-frontendrailway.up.railway.app
NEXT_PUBLIC_BACKEND_API_URL=https://sigmasight-be-sandbox-frontendrailway.up.railway.app/api/v1
```

After changing `.env.local`, rebuild:
```bash
docker-compose down && docker-compose up -d --build
```

---

## High-Level Architecture

### Multi-Page Application Structure

```
Landing Pages (Marketing)     Application Pages (Authenticated)
├── / (root redirect)         ├── /portfolio (dashboard)
├── /landing                  ├── /public-positions
└── /login                    ├── /private-positions
                              ├── /organize (strategies & tags)
                              ├── /ai-chat
                              └── /settings
```

### Core Architecture Pattern (Hybrid Approach)

**Modular Pattern** (Portfolio Page - Existing):
- Page file contains composition logic (~230 lines)
- Direct use of hooks and components
- Already implemented and working

**Container Pattern** (New Pages):
- Thin route files (5-15 lines) - just import and render
- Business logic in container components (150-250 lines)
- Better for code splitting and Docker optimization

### Data Flow Architecture

```
User Action
    ↓
Component/Page
    ↓
Custom Hook (data fetching/state)
    ↓
Service Layer (API calls)
    ↓
Next.js Proxy (/api/proxy/*)
    ↓
FastAPI Backend (localhost:8000)
```

---

## Critical Implementation Context

### State Management (Zustand + React Context)

**Global Portfolio ID** - `src/stores/portfolioStore.ts`
- Zustand store with localStorage persistence
- Single source of truth for portfolio ID across all pages
- No URL parameters (cleaner, more secure)
- Cleared only on logout

**Authentication** - `app/providers.tsx`
- React Context for user authentication state
- JWT token management via authManager service
- Protected route handling

**Chat State** - Split architecture
- `chatStore.ts` - Persistent chat data (conversations, messages)
- `streamStore.ts` - Streaming state (active streams, chunks)

### Portfolio Switching Policy
- **No in-app portfolio switching**
- Users must logout to change portfolios
- Simplifies state management and improves security
- Each login = one portfolio session

### Service Layer Architecture

ALL API calls must go through the service layer. Never make direct `fetch()` calls.

**Available Services** (11 total in `/src/services/`):
- `apiClient.ts` - Base HTTP client with retry logic
- `authManager.ts` - JWT token management
- `portfolioService.ts` - Portfolio data fetching
- `portfolioResolver.ts` - Dynamic portfolio ID resolution
- `analyticsApi.ts` - Analytics endpoints
- `strategiesApi.ts` - Strategy management
- `tagsApi.ts` - Tag management
- `chatService.ts` - Chat messaging
- `chatAuthService.ts` - Chat authentication
- `requestManager.ts` - Request retry and deduplication
- `positionApiService.ts` - Position operations

### Authentication Flow

1. User logs in at `/login`
2. JWT token stored in localStorage as `access_token`
3. Portfolio ID resolved via `portfolioResolver` and stored in Zustand
4. Token used for all API calls via service layer
5. Portfolio ID persists across all page navigations
6. Logout clears both token and portfolio ID

---

## Directory Structure

### Current Structure (As-Is)

```
frontend/
├── app/                        # Next.js App Router
│   ├── api/proxy/              # ✅ Backend proxy (CORS handling)
│   ├── portfolio/              # ✅ Main dashboard (modular pattern)
│   ├── login/                  # ✅ Authentication
│   ├── landing/                # ✅ Marketing page
│   ├── providers.tsx           # ✅ Auth context & global providers
│   ├── layout.tsx              # ✅ Root layout with navigation
│   └── page.tsx                # ✅ Root redirect
│
├── src/                        # Application Source Code
│   ├── stores/                 # State Management
│   │   ├── portfolioStore.ts  # ✅ Global portfolio ID (Zustand)
│   │   ├── chatStore.ts       # ✅ Chat persistent data
│   │   └── streamStore.ts     # ✅ Chat streaming state
│   │
│   ├── services/               # ✅ API Services (11 total)
│   │   ├── apiClient.ts       # Base HTTP client
│   │   ├── authManager.ts     # Authentication
│   │   ├── portfolioService.ts # Portfolio data
│   │   ├── portfolioResolver.ts # Portfolio ID resolution
│   │   ├── analyticsApi.ts    # Analytics
│   │   ├── strategiesApi.ts   # Strategies
│   │   ├── tagsApi.ts         # Tags
│   │   ├── chatService.ts     # Chat messaging
│   │   ├── chatAuthService.ts # Chat auth
│   │   ├── requestManager.ts  # Request management
│   │   └── positionApiService.ts # Positions
│   │
│   ├── components/             # React Components
│   │   ├── navigation/         # ✅ Navigation components
│   │   │   ├── NavigationDropdown.tsx # Dropdown menu (6 pages)
│   │   │   └── NavigationHeader.tsx   # Header with branding
│   │   ├── app/                # App-specific components
│   │   ├── auth/               # Authentication components
│   │   ├── chat/               # Chat components
│   │   ├── portfolio/          # Portfolio components (modular, reusable)
│   │   │   ├── FactorExposureCards.tsx
│   │   │   ├── PortfolioMetrics.tsx
│   │   │   ├── PortfolioPositions.tsx  # 3-column layout
│   │   │   ├── PublicPositions.tsx     # Public equities/ETFs
│   │   │   ├── OptionsPositions.tsx    # Options contracts
│   │   │   └── PrivatePositions.tsx    # Private/alternative
│   │   └── ui/                 # ShadCN UI components
│   │
│   ├── hooks/                  # Custom React Hooks
│   │   └── usePortfolioData.ts # Portfolio data fetching
│   │
│   ├── lib/                    # Utility Libraries
│   │   ├── formatters.ts      # Number & currency formatting
│   │   ├── auth.ts            # Auth utilities
│   │   ├── types.ts           # Shared type definitions
│   │   └── utils.ts           # General utilities
│   │
│   └── config/                 # Configuration
│       └── api.ts             # API endpoints & configs
│
├── _docs/                      # 📚 Documentation (READ THESE!)
│   ├── project-structure.md   # Directory structure & patterns
│   ├── API_AND_DATABASE_SUMMARY.md # Backend API reference
│   └── requirements/           # Implementation guides
│       ├── README.md           # Master index & quick reference
│       ├── 01-MultiPage-Architecture-Overview.md
│       ├── 02-PublicPositions-Implementation.md
│       ├── 03-PrivatePositions-Implementation.md
│       ├── 04-Organize-Implementation.md
│       ├── 05-AIChat-Implementation.md
│       ├── 06-Settings-Implementation.md
│       ├── 07-Services-Reference.md
│       └── 08-Implementation-Checklist.md
│
├── Dockerfile
├── next.config.js
├── tailwind.config.js
└── tsconfig.json
```

### Planned Additions (Container Pattern)

```
app/
├── public-positions/           # 🔄 New route
│   └── page.tsx               # Thin wrapper (8 lines)
├── private-positions/          # 🔄 New route
│   └── page.tsx               # Thin wrapper (8 lines)
├── organize/                   # 🔄 New route
│   └── page.tsx               # Thin wrapper (8 lines)
├── ai-chat/                    # 🔄 New route
│   └── page.tsx               # Thin wrapper (8 lines)
└── settings/                   # 🔄 New route
    └── page.tsx               # Thin wrapper (8 lines)

src/
├── containers/                 # 🔄 New folder
│   ├── PublicPositionsContainer.tsx   (150-250 lines)
│   ├── PrivatePositionsContainer.tsx  (150-250 lines)
│   ├── OrganizeContainer.tsx          (150-250 lines)
│   ├── AIChatContainer.tsx            (150-250 lines)
│   └── SettingsContainer.tsx          (150-250 lines)
│
├── hooks/                      # Expand with new hooks
│   ├── usePositions.ts        # 🔄 Position data hook
│   ├── useStrategies.ts       # 🔄 Strategies hook
│   └── useTags.ts             # 🔄 Tags hook
│
└── components/                 # New feature components
    ├── positions/             # 🔄 Position components
    ├── strategies/            # 🔄 Strategy components
    ├── tags/                  # 🔄 Tag components
    └── settings/              # 🔄 Settings components
```

---

## Page Implementation Pattern

### For Existing Portfolio Page (Modular Pattern - Keep As-Is)
```typescript
// app/portfolio/page.tsx (~230 lines)
'use client'
import { usePortfolioData } from '@/hooks/usePortfolioData'
import { PortfolioMetrics } from '@/components/portfolio/PortfolioMetrics'
import { FactorExposureCards } from '@/components/portfolio/FactorExposureCards'
import { PortfolioPositions } from '@/components/portfolio/PortfolioPositions'

export default function PortfolioPage() {
  const { positions, metrics, factors, loading, error } = usePortfolioData()

  return (
    <div>
      <PortfolioMetrics metrics={metrics} />
      <FactorExposureCards factors={factors} />
      <PortfolioPositions positions={positions} />
    </div>
  )
}
```

### For New Pages (Container Pattern)

**Step 1: Create Custom Hook** (`src/hooks/usePositions.ts`)
```typescript
export function usePositions(investmentClass: string) {
  const { portfolioId } = usePortfolioStore() // Zustand store
  const [positions, setPositions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPositions = async () => {
      // Use existing service - NEVER direct fetch()
      const endpoint = `/api/v1/data/positions/details?portfolio_id=${portfolioId}`
      const response = await apiClient.get(endpoint)
      setPositions(response.positions.filter(p => p.investment_class === investmentClass))
      setLoading(false)
    }
    fetchPositions()
  }, [portfolioId, investmentClass])

  return { positions, loading }
}
```

**Step 2: Create Container** (`src/containers/PublicPositionsContainer.tsx`)
```typescript
'use client'
import { usePositions } from '@/hooks/usePositions'
import { PositionsTable } from '@/components/positions/PositionsTable'

export function PublicPositionsContainer() {
  const { positions, loading } = usePositions('PUBLIC')

  if (loading) return <div>Loading...</div>

  return (
    <div>
      <h1>Public Positions</h1>
      <PositionsTable positions={positions} />
    </div>
  )
}
```

**Step 3: Create Thin Page** (`app/public-positions/page.tsx`)
```typescript
'use client'
import { PublicPositionsContainer } from '@/containers/PublicPositionsContainer'

export default function PublicPositionsPage() {
  return <PublicPositionsContainer />
}
```

---

## Critical Rules & Best Practices

### ✅ DO These Things

1. **Use Existing Services** - All 11 services are available, use them
2. **Client Components Only** - All pages use `'use client'` directive
3. **Thin Page Files** - New pages should be 5-15 lines max
4. **Zustand for Portfolio ID** - Access via `usePortfolioStore()` hook
5. **Service Layer for API** - NEVER direct `fetch()` calls
6. **Import with @/ Alias** - Use absolute imports (`@/services/apiClient`)
7. **Reuse Components** - Portfolio components are modular and reusable
8. **Follow the Pattern** - Hook → Components → Container → Page
9. **Check Documentation** - Read `_docs/requirements/` for implementation guides

### ❌ DON'T Do These Things

1. **No Server Components** - No RSC, no `'server-only'`
2. **No Direct API Calls** - Never `fetch('http://localhost:8000/...')`
3. **No Hardcoded IDs** - Always use `portfolioResolver.getUserPortfolioId()`
4. **No Recreating Services** - Check if service exists first
5. **No cookies() from next/headers** - Not available client-side
6. **No Fat Page Files** - Move logic to containers and hooks
7. **No URL Parameters** - Portfolio ID is in Zustand, not URL

---

## Backend Integration

### Connecting to Railway Backend

By default, frontend connects to **local backend** (`http://localhost:8000`).

**To connect to Railway backend**:
- See **[RAILWAY_BACKEND_SETUP.md](./RAILWAY_BACKEND_SETUP.md)** for complete guide
- Quick: Update `.env` → `NEXT_PUBLIC_BACKEND_API_URL=https://your-app.railway.app/api/v1`
- Restart frontend → Hard refresh browser

### API Proxy Pattern
All API calls route through Next.js proxy to handle CORS:

```typescript
// ✅ CORRECT: Use service layer
import { apiClient } from '@/services/apiClient'
const data = await apiClient.get('/api/v1/data/positions/details')

// ❌ WRONG: Direct backend call
const response = await fetch('http://localhost:8000/api/v1/data/positions')
```

### Demo Credentials
- **High Net Worth**: `demo_hnw@sigmasight.com` / `demo12345`
- **Individual**: `demo_individual@sigmasight.com` / `demo12345`
- **Hedge Fund**: `demo_hedgefundstyle@sigmasight.com` / `demo12345`

### Investment Classes
- **PUBLIC**: Regular equities, ETFs (LONG/SHORT position types)
- **OPTIONS**: Options contracts (LC/LP/SC/SP position types)
- **PRIVATE**: Private/alternative investments

---

## Key Files and Their Purpose

### State Management
- `stores/portfolioStore.ts` - Global portfolio ID with Zustand
- `stores/chatStore.ts` - Chat persistent data
- `stores/streamStore.ts` - Chat streaming state
- `app/providers.tsx` - Auth context and global providers

### Core Services (Use These!)
- `apiClient.ts` - Base HTTP client (all services use this)
- `authManager.ts` - JWT token management
- `portfolioResolver.ts` - Dynamic portfolio ID resolution
- `portfolioService.ts` - Portfolio data fetching
- `analyticsApi.ts` - Analytics endpoints
- `strategiesApi.ts` - Strategy management API
- `tagsApi.ts` - Tag management API
- `chatService.ts` - Chat messaging
- `positionApiService.ts` - Position operations

### Navigation
- `components/navigation/NavigationDropdown.tsx` - 6-page dropdown menu
- `components/navigation/NavigationHeader.tsx` - Header with branding
- `app/layout.tsx` - Root layout with providers and navigation

### Portfolio Components (Reusable)
- `PortfolioMetrics.tsx` - Summary metrics cards
- `FactorExposureCards.tsx` - Factor exposure display
- `PortfolioPositions.tsx` - 3-column investment class layout
- `PublicPositions.tsx` - Public equity positions
- `OptionsPositions.tsx` - Options contracts display
- `PrivatePositions.tsx` - Private/alternative positions

### Chat System
- `ChatInterface.tsx` - Sheet-based chat overlay
- `chatService.ts` - Conversation management
- `chatAuthService.ts` - Cookie-based auth for streaming

---

## Development Workflow

### Before Starting Implementation
1. Read `_docs/requirements/README.md` (Master guide with all context)
2. Read `_docs/requirements/01-MultiPage-Architecture-Overview.md`
3. Read `_docs/requirements/07-Services-Reference.md` (Service methods & usage)
4. Review `_docs/project-structure.md` (Current structure)
5. Check `_docs/API_AND_DATABASE_SUMMARY.md` (Backend API reference)

### During Implementation
1. Follow implementation guides in `_docs/requirements/`
2. Use existing services - check `07-Services-Reference.md` first
3. Follow the pattern: Hook → Components → Container → Page
4. Test incrementally after each component
5. Verify authentication flow works

### Testing Approach
1. **MANDATORY**: Login first at `/login` to establish authentication
2. Check localStorage for `access_token` to verify auth
3. Verify portfolio ID is set in Zustand store
4. Test API calls through browser DevTools Network tab
5. Verify all pages accessible via navigation dropdown

---

## Architectural Decisions

### Why Zustand for Portfolio ID?
- Persists across page navigations
- No URL parameter pollution
- Cleaner URLs and better security
- Single source of truth
- Better for thousands of users

### Why No In-App Portfolio Switching?
- Simplifies state management
- Better security and session isolation
- Each login = one portfolio session
- Reduces state complexity

### Why Container Pattern for New Pages?
- Better Docker optimization (code splitting)
- Clear separation of concerns
- Easier testing and maintenance
- Follows Next.js best practices

### Why Keep Portfolio Page Modular?
- Already implemented and working well
- No need to change working code
- ~230 lines is reasonable for a page file
- Demonstrates alternative valid pattern

### Why Client-Side Only?
- Backend is FastAPI (not Next.js backend)
- Simplifies architecture
- Avoids SSR complexity
- Better for SPA-like experience

---

## Implementation Progress

### ✅ Phase 1: Core Setup & State Management (COMPLETE)
- ✅ Zustand portfolioStore for global portfolio ID
- ✅ Auth context in providers.tsx
- ✅ NavigationDropdown with 6 pages
- ✅ NavigationHeader component
- ✅ Updated layout.tsx with providers and navigation
- ✅ Portfolio page working with real data

### 🔄 Phase 2: Data Hooks (PENDING)
- [ ] Create `usePositions.ts` hook
- [ ] Create `useStrategies.ts` hook
- [ ] Create `useTags.ts` hook

### 🔄 Phase 3-6: Pages & Containers (PENDING)
- [ ] Public Positions page with container
- [ ] Private Positions page with container
- [ ] Organize page with container (strategies + tags)
- [ ] AI Chat page with container
- [ ] Settings page with container

---

## Important Documentation

### Must-Read Documents
1. **`_docs/requirements/README.md`** - Master index and quick reference (START HERE)
2. **`_docs/requirements/01-MultiPage-Architecture-Overview.md`** - Architecture patterns
3. **`_docs/requirements/07-Services-Reference.md`** - Complete service reference
4. **`_docs/project-structure.md`** - Directory structure and patterns
5. **`_docs/API_AND_DATABASE_SUMMARY.md`** - Backend API endpoints

### Implementation Guides (When Needed)
- `02-PublicPositions-Implementation.md` - Public positions page
- `03-PrivatePositions-Implementation.md` - Private positions page
- `04-Organize-Implementation.md` - Strategies and tags page
- `05-AIChat-Implementation.md` - AI chat page
- `06-Settings-Implementation.md` - Settings page
- `08-Implementation-Checklist.md` - Phase-by-phase checklist

---

## Common Pitfalls & Solutions

### Issue: Service not found
**Solution**: Check `_docs/requirements/07-Services-Reference.md` for correct import path

### Issue: Portfolio ID is null
**Solution**:
1. Verify user is logged in
2. Check `portfolioResolver.getUserPortfolioId()` called
3. Verify backend has portfolio for user
4. Check Zustand store state

### Issue: API call fails with CORS
**Solution**: Verify call goes through `/api/proxy/` route, not direct to backend

### Issue: Component not rendering
**Solution**:
1. Check `'use client'` directive present
2. Verify imports use `@/` alias correctly
3. Check browser console for errors

### Issue: Authentication errors
**Solution**:
1. Must login first at `/login`
2. Check localStorage for `access_token`
3. Verify token not expired
4. Check authManager service

### Issue: Docker build fails
**Solution**:
```bash
# Clear Docker cache and rebuild
docker build --no-cache -t sigmasight-frontend .

# Check detailed build logs
docker build --progress=plain -t sigmasight-frontend .
```

### Issue: TypeScript errors
**Solution**:
- Ensure `downlevelIteration: true` in tsconfig.json
- Run `npm run type-check` to validate all types
- Check that all dependencies are installed

### Issue: Port already in use
**Solution**:
```bash
# Use different port
npm run dev -- -p 3006

# Or with Docker
docker run -p 3006:3005 sigmasight-frontend
```

### Issue: Missing dependencies after git pull
**Solution**:
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

---

## Quick Reference

### Import Patterns
```typescript
// Services
import { apiClient } from '@/services/apiClient'
import { authManager } from '@/services/authManager'
import strategiesApi from '@/services/strategiesApi'

// State
import { usePortfolioStore } from '@/stores/portfolioStore'

// Components
import { NavigationDropdown } from '@/components/navigation/NavigationDropdown'
import { Button } from '@/components/ui/button'

// Hooks
import { usePortfolioData } from '@/hooks/usePortfolioData'

// Containers
import { PublicPositionsContainer } from '@/containers/PublicPositionsContainer'
```

### Getting Portfolio ID
```typescript
// In React components
const { portfolioId } = usePortfolioStore()

// Outside React
import { getPortfolioId } from '@/stores/portfolioStore'
const portfolioId = getPortfolioId()
```

### Making API Calls
```typescript
// ✅ CORRECT
import { apiClient } from '@/services/apiClient'
const data = await apiClient.get('/api/v1/data/positions/details')

// ❌ WRONG
const response = await fetch('http://localhost:8000/api/v1/data/positions')
```

---

## Summary

**Architecture**: Hybrid approach (modular + container patterns)
**State**: Zustand for portfolio ID, React Context for auth
**Services**: 11 existing services, always use them
**Pages**: 6 authenticated pages with dropdown navigation
**Backend**: FastAPI via Next.js proxy
**Authentication**: JWT in localStorage, mandatory login flow
**Documentation**: Comprehensive guides in `_docs/requirements/`
**Pattern**: Hook → Components → Container → Page
**Status**: Phase 1 complete, ready for new page implementation

The frontend follows a pragmatic, maintainable architecture with clear separation of concerns. All implementation details are documented in `_docs/requirements/` - always start there before implementing new features.