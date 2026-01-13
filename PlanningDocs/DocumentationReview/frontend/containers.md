# Frontend Containers Documentation

This document covers all files in `frontend/src/containers/`.

Containers are page-level components that handle data fetching, state management, and orchestrate the layout of child components. Each container is imported by a thin page file in the `app/` directory.

---

## Container Files

| File | Purpose | Usage |
|------|---------|-------|
| `CommandCenterContainer.tsx` | Fetches and displays portfolio overview with hero metrics, performance metrics, holdings table across all accounts with optional filtering by individual portfolio. | Imported by `/command-center` page to display the main portfolio dashboard. |
| `DashboardContainer.tsx` | Fetches portfolio data (metrics, positions, factor exposures, spread factors) and orchestrates layout displaying portfolio header, metrics, and factor exposure cards. | Imported by `/portfolio` page (legacy route) for the main analytics dashboard. |
| `EquitySearchContainer.tsx` | Manages equity search functionality with debounced search input, filtering by sector/market cap/PE ratio, sorting by various columns, and period selection (TTM/Last Year/Forward/Last Quarter). | Imported by `/equity-search` page to provide searchable equity screening interface. |
| `HomeContainer.tsx` | Fetches and displays aggregated portfolio returns, exposures, volatility metrics across all sections, plus AI chat widget on a home dashboard. | Imported by `/home` page for the portfolio overview homepage. |
| `OrganizeContainer.tsx` | Manages position tagging with drag-drop functionality, tag creation/deletion, position filtering by tag, and sector tag restoration across position types (long stocks, short stocks, options, private). | Imported by `/organize` page for position organization and tagging interface. |
| `PositionManagementContainer.tsx` | Fetches positions for selected portfolio, manages position creation/editing/deletion with detail sheet and create dialog, handles refresh and state management. | Embedded as a component within settings or standalone for position management CRUD operations. |
| `ResearchAndAnalyzeContainer.tsx` | Fetches enhanced position data for multi-portfolio aggregate or single portfolio view, manages filtering/sorting, consolidates multiple lots per ticker, and handles correlation matrix fetching. | Imported by `/research-and-analyze` page for detailed position research and analysis. |
| `RiskMetricsContainer.tsx` | Fetches all risk analytics via custom hooks (factor exposures, spread factors, correlation matrix, stress test, volatility, sector exposure) with support for aggregate equity-weighted view across multiple portfolios. | Imported by `/risk-metrics` page to display comprehensive risk analysis and scenario testing. |
| `SettingsContainer.tsx` | Manages user settings including account/billing info, portfolio management, recalculation of analytics, and AI memory panel configuration. | Imported by `/settings` page for user preferences and account configuration. |
| `SigmaSightAIContainer.tsx` | Fetches AI-generated insights with filtering/generation capabilities and displays them alongside copilot chat panel with prefill message passing for deeper analysis. | Imported by `/sigmasight-ai` page for AI-powered portfolio insights and analysis chat. |
| `TestUserCreationContainer.tsx` | Handles test user account creation form with email, password validation, and portfolio file upload with file type validation. | Imported by test user creation page (development/testing only). |

---

## Container Pattern

All containers follow a consistent pattern:

1. **Data Fetching**: Use custom hooks (usePortfolioData, useFactorExposures, etc.) to fetch data
2. **State Management**: Manage local UI state (filters, selections, modals)
3. **Layout Orchestration**: Compose child components in a grid/flex layout
4. **Error Handling**: Display error states and loading skeletons
5. **Responsive Design**: Adapt layout for mobile/desktop viewports

---

## Page-to-Container Mapping

| Page Route | Container |
|------------|-----------|
| `/command-center` | CommandCenterContainer |
| `/home` | HomeContainer |
| `/risk-metrics` | RiskMetricsContainer |
| `/research-and-analyze` | ResearchAndAnalyzeContainer |
| `/sigmasight-ai` | SigmaSightAIContainer |
| `/settings` | SettingsContainer |
| `/equity-search` | EquitySearchContainer |
| `/organize` | OrganizeContainer |
| `/portfolio` (legacy) | DashboardContainer |

---

## Summary Statistics

- **Total Containers**: 11 files
- **Multi-Portfolio Support**: 4 (CommandCenter, Research, RiskMetrics, Home)
- **AI Integration**: 2 (SigmaSightAI, Home)
- **Position Management**: 3 (Organize, PositionManagement, Dashboard)
