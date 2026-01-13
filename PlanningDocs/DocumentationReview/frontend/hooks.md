# Frontend Hooks Documentation

This document covers all files in `frontend/src/hooks/`.

Custom React hooks encapsulate data fetching logic, API calls, and state management for reuse across components.

---

## Hooks Directory

| File | Purpose | Usage |
|------|---------|-------|
| `useAIInsights.ts` | Fetches and manages AI-generated insights with pagination, filtering, and auto-generation of morning briefings via insightsApi. | Insight pages that need to display AI-generated portfolio analysis and allow users to generate new insights. |
| `useApiClient.ts` | Provides authenticated fetch wrapper that automatically includes Clerk JWT tokens in API requests for secure API calls. | Components that need to make authenticated API calls (alternative to service layer when needed). |
| `useCommandCenterData.ts` | Fetches and aggregates complete portfolio analytics including overview, snapshots, equity changes, and backend aggregate endpoints for multi-portfolio command center view. | Command center dashboard and aggregate view pages that display cross-portfolio metrics and holdings. |
| `useConcentration.ts` | Fetches portfolio concentration metrics (HHI, position weights) via analyticsApi with support for aggregate portfolio view. | Risk metrics pages displaying position concentration analysis and diversification statistics. |
| `useCopilot.ts` | Wraps aiChatStore and provides clean API for AI copilot interaction including message sending, feedback, and conversation management. | AI chat components and containers that need to integrate with the AI copilot assistant. |
| `useCorrelationMatrix.ts` | Fetches correlation matrix for portfolio positions with support for aggregate view of top 25 positions across portfolios. | Portfolio analysis pages displaying position correlations and diversification risk assessment. |
| `useDiversificationScore.ts` | Fetches portfolio diversification metrics via analyticsApi (single portfolio only). | Portfolio analytics pages showing diversification scoring and analysis. |
| `useEquitySearch.ts` | Provides debounced search functionality with pagination for equity discovery with filtering by sector, industry, market cap, and P/E ratio. | Equity search page with advanced filtering and infinite scroll pagination for position research. |
| `useFactorExposures.ts` | Fetches portfolio-level factor betas via analyticsApi with normalization of legacy/new response formats and aggregate support. | Risk metrics hero cards and factor analysis pages showing portfolio factor exposures. |
| `useFundamentals.ts` | Fetches and transforms fundamental financial data (income statements, cash flows, analyst estimates) into unified table structure for display. | Position research and company analysis pages displaying financial fundamentals and growth metrics. |
| `useHomePageData.ts` | Fetches and aggregates home page data including returns, exposures, volatility metrics, and benchmark comparisons. | Home/landing page that displays portfolio overview, performance, and risk metrics. |
| `useInsights.ts` | Fetches and manages insights list for current portfolio with filtering options and auto-refresh capability. | Insights/analysis pages displaying AI-generated portfolio insights and observations. |
| `useMarketBetas.ts` | Fetches market beta comparison data for positions via apiClient (market vs calculated beta analysis). | Position analysis pages showing beta comparisons and market risk metrics. |
| `useMediaQuery.ts` | Custom hook for responsive design that listens to media query changes and returns boolean match status. | Responsive layout components that need to conditionally render based on viewport size (mobile/tablet/desktop). |
| `useMultiPortfolio.ts` | Provides hooks for managing multiple portfolios (usePortfolios, useAggregateAnalytics, usePortfolioBreakdown, usePortfolioMutations, useSelectedPortfolio). | Multi-portfolio dashboard, portfolio switching, and portfolio management pages and components. |
| `useOnboardingStatus.ts` | Polls onboarding batch processing status with grace period and tracks consecutive not_found responses for UI handling. | Onboarding progress pages that need real-time polling of portfolio creation and calculation status. |
| `usePortfolioData.ts` | Loads and manages portfolio data including overview, positions, exposures, factor exposures with optional skipping of factor data. | Main portfolio dashboard and analytics pages that display comprehensive portfolio information. |
| `usePortfolioUpload.ts` | Handles portfolio CSV upload with validation error handling, session management, and triggering batch calculations. | Portfolio onboarding pages where users upload CSV files to create portfolios and positions. |
| `usePositionCorrelations.ts` | Processes correlation matrix to extract top 5 correlations for a position and calculates concentration risk warnings. | Individual position analysis pages showing correlation risks and diversification impact. |
| `usePositionFactorData.ts` | Fetches and merges position factor exposures with company profile betas from multiple sources. | Position detail pages and risk analysis components showing factor exposures and market beta. |
| `usePositionRiskMetrics.ts` | Fetches complete risk metrics for a position combining factor exposures, company profile data, and volatility calculations. | Position detail pages and risk cards displaying comprehensive position risk analysis. |
| `usePositions.ts` | Fetches position data with optional investment class filtering and calculates portfolio totals and position statistics. | Position listing pages and components that display position details with P&L and tags. |
| `usePositionSelection.ts` | Manages position selection state for multi-select operations with maximum 10 selections enforced. | Position management pages with bulk operations and position selection UI components. |
| `usePositionTags.ts` | Provides methods for getting, adding, removing, and replacing tags on positions via tagsApi (successor to deprecated strategiesApi). | Position organizing and tagging pages that allow users to assign and manage position labels. |
| `usePrivatePositions.ts` | Fetches private/alternative positions with enhanced data and target price updates via positionResearchService. | Private positions page displaying alternative investments with target return calculations. |
| `usePublicPositions.ts` | Fetches public equities and ETFs separated into long/short positions with snapshot data and target price management. | Public positions page displaying regular equities and options with separate tracking for longs and shorts. |
| `useRecalculateAnalytics.ts` | Manages manual batch recalculation triggering with polling and elapsed time tracking for power users. | Analytics settings pages allowing users to manually trigger portfolio recalculation and analytics refresh. |
| `useRegistration.ts` | Handles user registration flow with email validation, auto-login, and redirect to portfolio upload page. | Registration/signup page with form validation and automated authentication after account creation. |
| `useRestoreSectorTags.ts` | Manages state for sector tag restoration operation with loading, error, and results tracking. | Portfolio settings pages allowing users to restore default sector classifications to all positions. |
| `useSectorExposure.ts` | Fetches sector exposure metrics vs S&P 500 benchmark with support for aggregate portfolio view. | Risk metrics pages displaying sector allocation, over/underweight analysis, and benchmark comparison. |
| `useSpreadFactors.ts` | Fetches spread factor exposures with availability checking and calculation date metadata. | Options analysis pages displaying spread strategy factor exposures and calculations. |
| `useStressTest.ts` | Fetches stress test scenarios with portfolio impact calculations and support for aggregate view. | Risk analysis pages showing portfolio sensitivity to market stress scenarios. |
| `useTags.ts` | Fetches and manages tags with create, update, delete, and archive functionality plus tag utility helpers. | Tag management pages and components for organizing and managing position labels. |
| `useUserEntitlements.ts` | Fetches user account entitlements including tier, portfolio limits, and AI message usage from /api/v1/auth/me endpoint. | Settings pages and upgrade prompts displaying user subscription status and feature access limits. |
| `useVolatility.ts` | Fetches volatility metrics including realized and forward-looking volatility with support for aggregate portfolio view. | Risk metrics pages displaying portfolio volatility analysis and forecasting. |

---

## Hook Categories

### Portfolio Data Hooks
- `usePortfolioData` - Main portfolio loader
- `useMultiPortfolio` - Multi-portfolio management
- `useCommandCenterData` - Dashboard aggregation
- `useHomePageData` - Home page metrics

### Analytics Hooks
- `useFactorExposures` - Factor betas
- `useCorrelationMatrix` - Position correlations
- `useDiversificationScore` - Diversification metrics
- `useConcentration` - Concentration analysis
- `useSectorExposure` - Sector allocation
- `useVolatility` - Volatility metrics
- `useStressTest` - Stress testing
- `useSpreadFactors` - Spread analysis

### Position Hooks
- `usePositions` - Position list
- `usePublicPositions` - Public equities
- `usePrivatePositions` - Private investments
- `usePositionTags` - Tag management
- `usePositionSelection` - Multi-select
- `usePositionRiskMetrics` - Position risk
- `usePositionFactorData` - Position factors
- `usePositionCorrelations` - Position correlations
- `useMarketBetas` - Beta comparison

### AI & Insights Hooks
- `useAIInsights` - AI insights
- `useInsights` - Insights list
- `useCopilot` - AI copilot

### User & Auth Hooks
- `useRegistration` - User signup
- `useUserEntitlements` - Subscription tier
- `useOnboardingStatus` - Onboarding progress
- `usePortfolioUpload` - CSV upload

### Utility Hooks
- `useApiClient` - Authenticated fetch
- `useMediaQuery` - Responsive design
- `useRecalculateAnalytics` - Manual refresh
- `useRestoreSectorTags` - Tag restoration
- `useTags` - Tag CRUD
- `useEquitySearch` - Stock search
- `useFundamentals` - Financial data

---

## Summary Statistics

- **Total Hooks**: 35 files
- **Analytics Hooks**: 10
- **Position Hooks**: 9
- **Portfolio Hooks**: 4
- **AI/Insights Hooks**: 3
- **User/Auth Hooks**: 4
- **Utility Hooks**: 7
