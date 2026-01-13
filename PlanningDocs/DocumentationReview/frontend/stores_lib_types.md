# Frontend Stores, Lib, Types Documentation

This document covers `frontend/src/stores/`, `frontend/src/lib/`, `frontend/src/types/`, `frontend/src/contexts/`, and `frontend/src/config/`.

---

## Directory: `stores/` - Zustand State Management

| File | Purpose | Usage |
|------|---------|-------|
| `portfolioStore.ts` | Multi-portfolio management with aggregate view support, includes onboarding session state for bulk uploads. | Used across all pages via `usePortfolioStore()` and `usePortfolioId()` hooks to manage selected portfolio and portfolio list. |
| `chatStore.ts` | Persistent chat data management for conversations and messages with SSE stream coordination. | Used in chat interface to manage conversation history, message creation, and UI state (open/closed). |
| `aiChatStore.ts` | State management for AI chat conversations on the analytics page with streaming support. | Used in AI chat page to manage conversation, messages, streaming state, and error handling. |
| `streamStore.ts` | Runtime streaming state for SSE events, message buffering, sequence validation, and queue management. | Used during active chat streaming to buffer incoming chunks, handle deduplication, and coordinate message queuing. |
| `researchStore.ts` | Tab state, filters, and side panel management for position research with optimistic tagging updates. | Used in research pages for tab switching, filtering (search, tags, sector, P&L), sorting, and correlation matrix data. |
| `adminStore.ts` | Admin authentication and authorization state with persistent storage (separate from user auth). | Used in admin dashboard for checking admin status, managing admin login/logout, and storing admin user data. |

### Test Files

| File | Purpose | Usage |
|------|---------|-------|
| `__tests__/chatStore.test.ts` | Unit tests for chatStore verifying message management and state transitions. | Runs via `npm run test` to validate chatStore functionality. |

---

## Directory: `lib/` - Utility Libraries

| File | Purpose | Usage |
|------|---------|-------|
| `auth.ts` | Client-side authentication utilities for token management and auth headers. | Used by apiClient and services to retrieve JWT tokens, set auth headers, and manage localStorage auth state. |
| `chatManager.ts` | Singleton manager for opening chat and broadcasting user messages to the chat interface. | Used in portfolio pages to trigger chat open from outside React components and pass user input to ChatInterface. |
| `clerkTokenStore.ts` | Token bridge for sharing Clerk JWT tokens with non-React code (like apiClient interceptors). | Used by apiClient interceptor to get current Clerk token and refresh it when expired. |
| `dal.ts` | Server-side data access layer for fetching data (marked 'server-only', uses cookies). | Used in Server Components for server-side data fetching with authentication via cookies. |
| `financialFormatters.ts` | Specialized formatting for financial data (billions/millions with suffixes, percentages, EPS, fiscal years). | Used in portfolio and position displays to format large currency amounts, growth rates, and financial metrics. |
| `formatters.ts` | General number and currency formatting utilities (thousands, percentages, comma-separated). | Used throughout app for formatting numbers, prices, percentages, and currency values with commas. |
| `portfolioType.ts` | Portfolio type detection and management from email domain and localStorage. | Used during login to detect portfolio type (HNW, individual, hedge-fund) and store selection. |
| `themes.ts` | Bloomberg Terminal-style theme system with light/dark mode support and color/typography definitions. | Used by ThemeContext to apply theme colors and typography CSS variables to document root. |
| `types.ts` | Shared TypeScript type definitions for User, Portfolio, Position, FactorExposure, and API responses. | Used throughout app for type safety in components, hooks, and services. |
| `utils.ts` | Tailwind CSS class merging utility (cn function) for conditional styling. | Used in components to merge Tailwind classes with dynamic conditions. |

### `lib/ai/` - AI Integration

| File | Purpose | Usage |
|------|---------|-------|
| `promptManager.ts` | Dynamically loads mode-specific system prompts and injects context variables (portfolio_id). | Used by aiChatService to load and cache system prompts for green/blue/indigo/violet modes. |

### `lib/ai/prompts/` - AI Prompt Files

| File | Purpose | Usage |
|------|---------|-------|
| `blue_v001.ts` | System prompt for blue mode (investment analysis focus). | Loaded by promptManager for blue mode conversations. |
| `blue_v001.md` | Markdown source for blue mode prompt. | Reference documentation for blue mode prompt content. |
| `green_v001.ts` | System prompt for green mode (portfolio overview focus). | Loaded by promptManager for green mode conversations. |
| `green_v001.md` | Markdown source for green mode prompt. | Reference documentation for green mode prompt content. |
| `indigo_v001.ts` | System prompt for indigo mode (risk analysis focus). | Loaded by promptManager for indigo mode conversations. |
| `indigo_v001.md` | Markdown source for indigo mode prompt. | Reference documentation for indigo mode prompt content. |
| `violet_v001.ts` | System prompt for violet mode (sector analysis focus). | Loaded by promptManager for violet mode conversations. |
| `violet_v001.md` | Markdown source for violet mode prompt. | Reference documentation for violet mode prompt content. |
| `common_instructions.ts` | Common instructions shared across all modes. | Prepended to mode-specific prompts by promptManager. |
| `common_instructions.md` | Markdown source for common instructions. | Reference documentation for common instructions. |

---

## Directory: `types/` - TypeScript Type Definitions

| File | Purpose | Usage |
|------|---------|-------|
| `analytics.ts` | API response types for analytics endpoints (portfolio overview, correlations, factor exposures, volatility, sector exposure, concentration, stress tests). | Used in analytics hooks and components to type API responses and provide type safety for analytics data. |
| `portfolio.ts` | Portfolio data types (info, metadata, snapshots, exposures, Greeks, factor analysis, positions summary). | Used in portfolio pages and data fetching hooks to type portfolio report data and API responses. |
| `positions.ts` | Position view types for public, options, and private positions with tags support. | Used in position components to type position data across different investment classes. |
| `strategies.ts` | Strategy types (strategy detail, metrics, tags) and tag management types (deprecated, use tags.ts instead). | Legacy types still used in organize page but being phased out in favor of position tagging. |
| `tags.ts` | Position tag type definitions (PositionTag interface for tag shape consistency). | Used across UI components, services, and stores to maintain consistent tag data structure. |

---

## Directory: `contexts/` - React Context Providers

| File | Purpose | Usage |
|------|---------|-------|
| `ThemeContext.tsx` | Theme management context with light/dark mode support, applies CSS variables and theme configuration. | Wrapped around app in providers.tsx to enable theme switching and provide useTheme() hook to all components. |

---

## Directory: `config/` - Configuration Files

| File | Purpose | Usage |
|------|---------|-------|
| `api.ts` | Centralized API configuration (base URL, endpoints, timeouts, retry settings, demo portfolio IDs). | Imported by all services and hooks to access API endpoints, base URL, and request configuration presets. |

---

## Summary Statistics

### Stores
- **Total Store Files**: 6 (+ 1 test file)
- **Purpose**: Global state management with Zustand

### Lib
- **Total Lib Files**: 10 core files + 11 AI prompt files
- **Purpose**: Utility functions, formatters, auth helpers

### Types
- **Total Type Files**: 5 files
- **Purpose**: TypeScript definitions for type safety

### Contexts
- **Total Context Files**: 1 file
- **Purpose**: React context providers

### Config
- **Total Config Files**: 1 file
- **Purpose**: Centralized API configuration

---

## Architecture Patterns

1. **Zustand Stores**: Simple, direct state management without boilerplate
2. **Type-Safe API**: All API responses typed via types/ directory
3. **Centralized Config**: Single source of truth for API endpoints
4. **AI Prompt System**: Mode-based prompts loaded dynamically
5. **Theme System**: CSS variables for Bloomberg Terminal-style theming
