# Frontend Services Documentation

This document covers all files in `frontend/src/services/`.

Services are the API layer that handle all communication with the FastAPI backend. They provide typed methods for calling endpoints and handle authentication, error handling, and response transformation.

---

## Service Files

| File | Purpose | Usage |
|------|---------|-------|
| `adminApiService.ts` | Calls admin dashboard analytics endpoints (`/api/v1/admin/onboarding/*`, `/api/v1/admin/ai/*`, `/api/v1/admin/batch/*`) to retrieve onboarding funnel metrics, AI latency/token/error breakdowns, batch processing history, and dashboard overview data. | Imported by admin dashboard pages and components that display system-level metrics, AI performance analytics, batch processing history, and onboarding analytics. |
| `adminAuthService.ts` | Handles admin-specific authentication separate from regular user auth, managing JWT token storage, session persistence, token refresh, and admin role validation. | Used by admin login page and admin middleware to verify admin credentials and maintain separate admin sessions. |
| `aiChatService.ts` | Manages AI chat via OpenAI Responses API using SSE streaming, creates conversations, sends messages with streaming callbacks, and handles portfolio context passing to the backend. | Imported by AI chat pages and components (CopilotPanel, AIChatContainer) to send messages and receive streamed AI responses. |
| `analyticsApi.ts` | Calls portfolio analytics endpoints (`/api/v1/analytics/portfolio/*`, `/api/v1/analytics/aggregate/*`) for overview, correlations, diversification, factor exposures, stress tests, volatility, sector exposure, and concentration metrics. | Used by usePortfolioData hooks and analytics dashboard components to fetch and display portfolio risk metrics. |
| `apiClient.ts` | Base HTTP client providing axios-like functionality with fetch wrapper, retry logic, timeout handling, interceptors, and automatic Clerk token injection via auth interceptor. | All other services depend on this; imported throughout the application for any API calls. |
| `authManager.ts` | Centralizes JWT token management with Clerk token fallback, session persistence in localStorage/sessionStorage, user caching, portfolio ID management, and token validation. | Used by all authenticated API services and auth flows; imported by login/logout logic and token refresh mechanisms. |
| `benchmarkService.ts` | Calculates and caches benchmark data (SPY, QQQ) including historical returns (1M, 3M, YTD, 1Y), volatility metrics, and daily changes from price and factor ETF endpoints. | Used by portfolio comparison components and benchmarking views to display portfolio performance against S&P 500 and other benchmarks. |
| `chatAuthService.ts` | Handles Bearer token authentication for chat streaming, manages conversation initialization on login, clears stale conversation state on user switch, and provides authenticated fetch for chat messages. | Used by chat authentication middleware and chatService to establish authenticated chat sessions. |
| `chatService.ts` | Manages conversation CRUD operations (`/api/v1/chat/conversations`) including create, list, delete, mode updates, and implements error policies for auth/rate-limit/network errors. | Used by AI chat pages and conversation management components to create/manage chat conversations. |
| `equityChangeService.ts` | Handles equity contributions/withdrawals via `/api/v1/portfolios/{id}/equity-changes`, providing CRUD operations, summary calculations (net flow, contributions, withdrawals), pagination, and CSV export. | Used by portfolio equity tracking components and widgets to record and display cash flows and equity changes. |
| `equitySearchApi.ts` | Provides equity search functionality with filters (sector, industry, market cap, P/E ratio), sorting, and period selection across symbol universe and fundamental data. | Imported by equity search/screener pages and components that allow users to search and filter stocks. |
| `feedbackService.ts` | Submits and retrieves thumbs up/down feedback ratings on AI messages via `/api/v1/chat/messages/{id}/feedback` for offline analysis and knowledge base improvement. | Used by AI chat UI components to submit user feedback on assistant responses. |
| `fundamentalsApi.ts` | Fetches financial statements (income, balance sheet, cash flow) and analyst estimates from database-backed endpoints for comprehensive fundamental analysis of positions. | Used by position research and fundamental analysis components to display income statements, balance sheets, and forward EPS estimates. |
| `insightsApi.ts` | Generates AI insights for portfolios (`/api/v1/insights/generate`) with type filtering (daily_summary, volatility_analysis, etc.), list/get/update operations, and user feedback submission. | Used by insights generation pages and components to create and display AI-generated portfolio analysis. |
| `memoryApi.ts` | Provides user memory CRUD operations (`/api/v1/chat/memories`) for storing preferences, corrections, and context that personalizes AI assistant responses. | Used by AI chat system to store and retrieve user preferences and personalization data. |
| `onboardingService.ts` | Manages user registration, portfolio creation via CSV upload, batch calculation triggering, and real-time onboarding status with activity logs and phase progress tracking. | Used by onboarding pages (registration, portfolio import, setup wizard) to handle user setup flow. |
| `portfolioApi.ts` | Provides comprehensive portfolio operations including CRUD (create/read/update/delete), multi-portfolio support, aggregate analytics across portfolios, and portfolio breakdowns by account. | Used by portfolio management pages, dashboard components, and portfolio listing to fetch/manage portfolios. |
| `portfolioResolver.ts` | Dynamically resolves user's portfolio ID from backend with caching and fallback to deterministic demo mapping for development; replaces hardcoded portfolio ID mappings. | Used by portfolio data fetching hooks to discover which portfolio the user owns. |
| `portfolioService.ts` | Loads complete portfolio data using individual APIs (overview, positions, factor exposures), calculates exposure metrics, transforms position details, and provides portfolio snapshot with target price metrics. | Used by usePortfolioData hook to fetch all data needed for portfolio dashboard. |
| `positionApiService.ts` | Runs in shadow mode comparing API position data vs JSON data, generating comparison reports for API validation during development. | Used by development tools and debugging utilities to validate API vs local data consistency. |
| `positionManagementService.ts` | Provides complete CRUD for positions (`/api/v1/positions/*`) including create, update, soft/hard delete, duplicate checking, symbol validation, and bulk operations. | Used by position management forms, position add/edit dialogs, and bulk import features. |
| `positionResearchService.ts` | Fetches and merges position data from multiple APIs (positions, company profiles, target prices) with caching and calculated fields (returns, equity %, analyst comparisons). | Used by position research components and enhanced position display that needs company data, targets, and analyst estimates. |
| `positionRiskService.ts` | Retrieves position-level risk metrics including factor exposures (beta, growth, momentum, quality, etc.) and company profile data (sector, industry, market cap). | Used by position detail components and risk analysis displays to show individual position factor exposures. |
| `requestManager.ts` | Implements retry logic with exponential backoff, request deduplication, cancellation support, timeout handling, and authenticated fetch with dedicated abort controller management. | Used by services that need advanced retry/dedup capabilities; supports portfolioResolver and other critical fetches. |
| `spreadFactorsApi.ts` | Fetches portfolio spread factor exposures (`/api/v1/analytics/portfolio/{id}/spread-factors`) including growth-value, momentum, size, and quality spreads calculated via 180-day OLS regression. | Used by factor analysis components to display long-short factor exposures and their risk levels. |
| `tagsApi.ts` | Manages both tag CRUD operations (`/api/v1/tags/*`) and position tagging (`/api/v1/positions/{id}/tags`), supporting sector tags, custom tags, and position-tag relationships. | Used by organization page, tag management, and position tagging features. |
| `targetPriceService.ts` | Handles user-defined target price CRUD operations (`/api/v1/target-prices/*`), portfolio target price summary (weighted returns, coverage), and smart upsert pattern. | Used by target price input components and position research cards to manage price targets. |
| `targetPriceUpdateService.ts` | Provides optimistic UI updates for target prices with smart refetch, batched updates (EOY + next year), error rollback, and weighted aggregate return calculations. | Used by position research components to update targets with instant UI feedback. |

---

## Test Files

| File | Purpose | Usage |
|------|---------|-------|
| `__tests__/analyticsApi.test.ts` | Unit tests for analyticsApi verifying Authorization header injection, API endpoint routing, and response handling via vitest framework. | Runs via `npm run test` to validate analyticsApi functionality. |

---

## Service Categories

### Core Infrastructure
- `apiClient.ts` - Base HTTP client
- `authManager.ts` - Token management
- `requestManager.ts` - Retry/dedup logic

### Portfolio Services
- `portfolioApi.ts` - Portfolio CRUD
- `portfolioService.ts` - Portfolio data loading
- `portfolioResolver.ts` - Portfolio ID resolution

### Analytics Services
- `analyticsApi.ts` - Risk analytics
- `benchmarkService.ts` - Benchmark data
- `spreadFactorsApi.ts` - Factor spreads

### Position Services
- `positionManagementService.ts` - Position CRUD
- `positionResearchService.ts` - Research data
- `positionRiskService.ts` - Position risk
- `positionApiService.ts` - API validation

### AI Services
- `aiChatService.ts` - AI chat with SSE
- `chatService.ts` - Conversation management
- `chatAuthService.ts` - Chat authentication
- `feedbackService.ts` - Message feedback
- `memoryApi.ts` - AI memories
- `insightsApi.ts` - AI insights

### User Services
- `onboardingService.ts` - User onboarding
- `equityChangeService.ts` - Cash flows
- `tagsApi.ts` - Tag management
- `targetPriceService.ts` - Target prices
- `targetPriceUpdateService.ts` - Target updates

### Admin Services
- `adminApiService.ts` - Admin analytics
- `adminAuthService.ts` - Admin auth

### Search Services
- `equitySearchApi.ts` - Stock search
- `fundamentalsApi.ts` - Financial data

---

## Summary Statistics

- **Total Services**: 28 files
- **Test Files**: 1 file
- **Core Infrastructure**: 3 services
- **Portfolio Services**: 3 services
- **Analytics Services**: 3 services
- **Position Services**: 4 services
- **AI Services**: 6 services
- **User Services**: 5 services
- **Admin Services**: 2 services
- **Search Services**: 2 services
