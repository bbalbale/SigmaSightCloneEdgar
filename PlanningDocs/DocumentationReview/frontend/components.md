# Frontend Components Documentation

This document covers all files in `frontend/src/components/` organized by subdirectory.

---

## admin/

| File | Purpose | Usage |
|------|---------|-------|
| `AdminLoginForm.tsx` | Renders secure admin authentication form with email and password inputs, admin-specific UI with shield branding. | Used in `/admin/login` page for admin-only access to feedback dashboards and system management. |
| `FeedbackDashboard.tsx` | Displays AI learning feedback statistics, negative feedback queue, learned preferences tracking, and manual learning job triggers. | Used in admin pages to monitor feedback patterns, view user corrections, and analyze AI learning progress. |

---

## ai/

| File | Purpose | Usage |
|------|---------|-------|
| `MemoryPanel.tsx` | Displays and manages AI memories (user preferences, context, corrections) that personalize AI assistant responses with add/delete functionality. | Used in settings and chat interfaces to let users manage what the AI remembers about them. |

---

## ai-chat/

| File | Purpose | Usage |
|------|---------|-------|
| `AIChatInterface.tsx` | Full-featured chat UI for AI Insights using OpenAI Responses API with SSE streaming, message history, feedback buttons, and thinking indicators. | Used in `/sigmasight-ai` page for AI analytical reasoning conversations. |

---

## app/

| File | Purpose | Usage |
|------|---------|-------|
| `ChatInput.tsx` | Reusable text input component with send button, keyboard shortcuts (Enter to submit), and disabled state handling. | Used across pages needing quick message input. |
| `Header.tsx` | Marketing page header with SigmaSight branding, navigation links, and login button for unauthenticated users. | Used in landing page layouts. |
| `ThemeToggle.tsx` | Button to switch between light/dark themes using theme context, shows sun/moon icon based on current theme. | Used in navigation headers and settings pages. |

---

## auth/

| File | Purpose | Usage |
|------|---------|-------|
| `LoginForm.tsx` | Full authentication form with email/password inputs, demo account quick-fill buttons, and pre-alpha signup option. | Used in `/login` page with 4 demo portfolio options (HNW, Family Office, Individual, Hedge Fund). |

---

## billing/

| File | Purpose | Usage |
|------|---------|-------|
| `UpgradePrompt.tsx` | Shows inline or blocking alerts when user reaches portfolio or AI message limits with upgrade call-to-action buttons. | Used in portfolio creation dialogs and AI chat interfaces to upsell premium features. |

---

## command-center/

| File | Purpose | Usage |
|------|---------|-------|
| `AIInsightsButton.tsx` | Floating button with sparkles icon that navigates to `/sigmasight-ai` page for AI-powered portfolio analysis. | Used in command center dashboard as CTA for AI insights. |
| `AIInsightsRow.tsx` | Displays AI insights row with recommendations and analysis summary for command center dashboard. | Used in command center page layouts below performance metrics. |
| `HeroMetricsRow.tsx` | Shows 7-column hero metrics: equity balance, net capital flow (30d), target return EOY, gross/net/long/short exposure with percentage calculations. | Used at top of command center dashboard for portfolio overview. |
| `HoldingsTable.tsx` | Responsive wrapper rendering desktop sortable table (11 columns) on ≥768px and mobile cards on <768px. | Used in command center to display all holdings with responsive design. |
| `HoldingsTableDesktop.tsx` | Full-featured holdings table (11 columns) with sorting, filtering by position type, and detailed position metrics. | Rendered on desktop screens in HoldingsTable wrapper. |
| `HoldingsTableMobile.tsx` | Compact position cards for mobile view showing essential info (symbol, value, P&L, target return, beta). | Rendered on mobile screens in HoldingsTable wrapper. |
| `PerformanceMetricsRow.tsx` | Shows 6-column performance metrics: YTD P&L, MTD P&L, cash balance, volatility (historical/current/forward), beta (1Y/90d), stress test. | Used in command center dashboard below hero metrics. |
| `RiskMetricsRow.tsx` | Displays 6 risk metric cards: portfolio beta, top sector, largest position, S&P 500 correlation, stress test impact. | Used in command center for risk overview. |
| `UploadPortfolioBanner.tsx` | CTA banner with blue background directing new users to upload their first portfolio via `/onboarding/upload`. | Used on authenticated pages when user has no portfolio. |

---

## common/

| File | Purpose | Usage |
|------|---------|-------|
| `BasePositionCard.tsx` | Reusable card component displaying position with primary/secondary text, values, and color-coded value (positive/negative/neutral). | Used as base for all position cards (StockPositionCard, OptionPositionCard, PrivatePositionCard). |
| `PositionList.tsx` | Renders ordered list of position components with section headers and optional filtering/sorting. | Used across portfolio pages to display groups of positions. |
| `PositionSectionHeader.tsx` | Section header with title, count badge, and optional actions (collapse, export). | Used above each position category in portfolio pages. |

---

## copilot/

| File | Purpose | Usage |
|------|---------|-------|
| `CopilotButton.tsx` | Floating action button with sparkles icon showing unread indicator, opens CopilotSheet on click, configurable position. | Used on multiple pages as persistent AI copilot entry point. |
| `CopilotPanel.tsx` | Chat panel component displaying conversation history and message input, integrates with AI chat store. | Used inside CopilotSheet for full-width copilot experience. |
| `CopilotSheet.tsx` | Side sheet container for copilot interface, slides in from right with close button and header. | Used on pages that need inline copilot access without full page navigation. |
| `index.ts` | Barrel export file exporting CopilotButton, CopilotPanel, CopilotSheet components. | Used for convenient imports: `import { CopilotButton } from '@/components/copilot'`. |

---

## Root Level Components

| File | Purpose | Usage |
|------|---------|-------|
| `DataQualityIndicator.tsx` | Shows data freshness status (current/stale/aging) with color-coded badge and tooltip explaining data age. | Used in portfolio headers to indicate if market data needs refresh. |
| `DataSourceIndicator.tsx` | Displays badge showing which data provider sourced the information (YFinance, Polygon, FMP, FRED). | Used in position detail sheets and analytics panels. |
| `PortfolioSelectionDialog.tsx` | Modal dialog for switching active portfolio with list of user's portfolios. | Used in navigation for portfolio selection. |
| `ThemeSelector.tsx` | Theme selection component with light/dark/auto options and visual indicators. | Used in settings page. |

---

## equity-search/

| File | Purpose | Usage |
|------|---------|-------|
| `EquitySearchFilters.tsx` | Filter controls for equity search (sector, market cap, valuation, growth metrics) with reset functionality. | Used above equity search table on `/equity-search` page. |
| `EquitySearchTable.tsx` | Responsive table of equity search results with columns (symbol, company, sector, market cap, P/E, etc.) and sorting. | Used in equity search page to display filtered results. |
| `PeriodSelector.tsx` | Dropdown to select time period for performance metrics (1Y, YTD, 3M, 1M, 1W) in research views. | Used in research and analyze page for period-based analysis. |

---

## home/

| File | Purpose | Usage |
|------|---------|-------|
| `BenchmarkMetricGroup.tsx` | Card showing portfolio vs benchmark comparison metrics (return, volatility, Sharpe ratio). | Used in home page analytics section. |
| `ExposuresRow.tsx` | Displays factor exposure rows with long/short exposure percentages and contribution to returns. | Used in home dashboard. |
| `HomeAIChatRow.tsx` | Section promoting AI chat functionality with quick-start suggestions and navigation button. | Used in home page to encourage AI feature adoption. |
| `index.ts` | Barrel export for home components. | Used for convenient imports from home directory. |
| `InlineInsightCard.tsx` | Compact insight card with title, description, and optional action button, styled for inline display. | Used in home page insights section. |
| `MetricCard.tsx` | Reusable metric card showing label, value (with color coding), and optional sub-value. | Used throughout home page for key metrics display. |
| `ReturnsRow.tsx` | Row displaying return metrics: YTD, MTD, QTD with color-coded positive/negative values. | Used in home dashboard. |
| `VolatilityRow.tsx` | Row displaying historical, current, and forward volatility metrics with comparison. | Used in home dashboard. |

---

## insights/

| File | Purpose | Usage |
|------|---------|-------|
| `GenerateInsightModal.tsx` | Modal dialog with form to generate new AI insights with topic selection and description input. | Used in insights page to create new insights. |
| `index.ts` | Barrel export for insights components. | Used for convenient imports from insights directory. |
| `InsightCard.tsx` | Card displaying single insight with title, preview, creation date, and detail button. | Used in insights list to show individual insights. |
| `InsightDetailModal.tsx` | Full insight details modal with complete text, metadata, sharing options, and delete button. | Used to display full insight when clicking detail on InsightCard. |
| `InsightsList.tsx` | Container displaying list of insights with filters, sorting, and generate button. | Used in insights page main content area. |

---

## navigation/

| File | Purpose | Usage |
|------|---------|-------|
| `BottomNavigation.tsx` | Mobile-optimized navigation bar at bottom with 6 page icons and labels. | Used on mobile views for page navigation. |
| `ConditionalNavigationHeader.tsx` | Wrapper that shows appropriate navigation (authenticated vs unauthenticated). | Used in root layout to conditionally render navigation. |
| `NavigationDropdown.tsx` | Dropdown menu with 6 main pages (Home, Command Center, Equity Search, Risk Metrics, Research & Analyze, SigmaSight AI). | Used in top navigation bar for page selection. |
| `NavigationHeader.tsx` | Header wrapper rendering TopNavigationBar with branding and navigation controls. | Used in root layout above page content. |
| `TopNavigationBar.tsx` | Full navigation bar with SigmaSight logo, navigation dropdown, user dropdown, theme toggle. | Used in root layout for top-level navigation. |
| `UserDropdown.tsx` | Dropdown menu with user profile, settings link, and logout button. | Used in top navigation bar. |

---

## onboarding/

| File | Purpose | Usage |
|------|---------|-------|
| `ActivityLog.tsx` | Displays timeline of onboarding activities (portfolio upload, position imports, calculations started). | Used in onboarding progress page. |
| `ActivityLogEntry.tsx` | Single activity log entry with timestamp, status indicator, and description. | Used in ActivityLog component. |
| `DownloadLogButton.tsx` | Button to export onboarding activity log as JSON or CSV file. | Used in onboarding progress page. |
| `InviteCodeForm.tsx` | Form for entering pre-alpha invite code with validation and submission. | Used in onboarding flow for access control. |
| `OnboardingComplete.tsx` | Completion screen shown after successful portfolio import with next steps and dashboard link. | Used as final onboarding step. |
| `OnboardingError.tsx` | Error state display with error message and retry/contact support options. | Used when onboarding fails. |
| `OnboardingProgress.tsx` | Progress tracker showing onboarding phases (upload, validation, processing, calculations) with status indicators. | Used in onboarding page during portfolio processing. |
| `OnboardingStatusUnavailable.tsx` | Fallback message when onboarding status cannot be retrieved. | Used when backend onboarding API is unavailable. |
| `PhaseList.tsx` | Displays list of onboarding phases with status badges and detailed info. | Used in onboarding progress tracking. |
| `PhaseListItem.tsx` | Single phase item with title, status, progress percentage, and details. | Used in PhaseList component. |
| `PortfolioUploadForm.tsx` | Form for portfolio CSV upload with file picker, validation, and submit button. | Used in onboarding upload step. |
| `RegistrationForm.tsx` | User registration form with email, password, name, and verification fields. | Used in registration/signup flow. |
| `ValidationErrors.tsx` | List display of portfolio validation errors during import. | Used in onboarding when import has issues. |

---

## organize/

| File | Purpose | Usage |
|------|---------|-------|
| `CombineModal.tsx` | Modal dialog for combining/consolidating multiple positions into one. | Used in organize page position management. |
| `CombinePositionsButton.tsx` | Button to open combine positions modal with validation. | Used in organize page. |
| `LongPositionsList.tsx` | Displays all long equity positions with tagging capability. | Used in organize page for long position organization. |
| `OptionsPositionsList.tsx` | Displays options positions (all types) with tagging and management. | Used in organize page for options management. |
| `PositionSelectionGrid.tsx` | Grid for multi-select positions for bulk operations (combine, tag, delete). | Used in organize page for bulk actions. |
| `PrivatePositionsList.tsx` | Displays private/alternative positions with tagging capability. | Used in organize page for private investment organization. |
| `SelectablePositionCard.tsx` | Position card with checkbox for multi-select in bulk operations. | Used in PositionSelectionGrid. |
| `ShortOptionsPositionsList.tsx` | Displays short options positions specifically. | Used in organize page. |
| `ShortPositionsList.tsx` | Displays all short equity positions with tagging capability. | Used in organize page for short position organization. |
| `TagBadge.tsx` | Small badge component showing tag name with color and optional delete button. | Used in position cards and organize page. |
| `TagCreator.tsx` | Input form for creating new tags with name and color picker. | Used in organize page. |
| `TagList.tsx` | Displays all tags with create/delete functionality and confirmation dialogs. | Used in organize page tag management section. |

---

## portfolio/

| File | Purpose | Usage |
|------|---------|-------|
| `AccountFilter.tsx` | Dropdown/button to filter holdings by account/portfolio (for multi-portfolio users). | Used in portfolio page header. |
| `AccountSummaryCard.tsx` | Card showing summary metrics for single account (value, return, allocation). | Used in multi-portfolio views. |
| `FactorExposureCards.tsx` | Grid of cards showing factor exposures (market, size, value, momentum, quality, volatility betas). | Used in portfolio page factor analytics section. |
| `FilterBar.tsx` | Horizontal filter controls (by sector, position type, account, investment class). | Used above position lists in portfolio page. |
| `ManageEquitySidePanel.tsx` | Side panel for managing equity positions (edit, delete, combine, tag). | Used when clicking position in portfolio page. |
| `ManagePositionsSidePanel.tsx` | Generic side panel for position management with type-specific actions. | Used in portfolio page position details. |
| `OptionsPositions.tsx` | Section displaying all options positions with nested contracts view. | Used in portfolio page. |
| `PortfolioError.tsx` | Error state display with error message and retry button. | Used when portfolio data fails to load. |
| `PortfolioHeader.tsx` | Header section with portfolio name, total value, key metrics, and action buttons. | Used at top of portfolio page. |
| `PortfolioMetrics.tsx` | Grid of metric cards (6 columns on desktop) showing key portfolio metrics. | Used in portfolio page below header. |
| `PortfolioPositions.tsx` | 3-column layout wrapper for Public/Options/Private positions sections. | Used as main content container in portfolio page. |
| `PositionCategoryExposureCards.tsx` | Cards showing exposure breakdown by investment class (public, options, private). | Used in portfolio page. |
| `PrivatePositions.tsx` | Section displaying all private/alternative positions. | Used in portfolio page third column. |
| `PublicPositions.tsx` | Section displaying all public equity and ETF positions. | Used in portfolio page first column. |
| `SpreadFactorCards.tsx` | Cards showing factor spread/skew analysis between long and short. | Used in portfolio page for L/S portfolio analysis. |
| `TagEditor.tsx` | Modal/sheet for editing tags assigned to a position. | Used in position detail modals. |
| `VolatilityMetrics.tsx` | Card showing portfolio volatility metrics (historical, current, forward) with forecast. | Used in portfolio page. |

---

## positions/

| File | Purpose | Usage |
|------|---------|-------|
| `CreatePositionDialog.tsx` | Modal form to manually create new position with symbol, quantity, entry price. | Used in portfolio pages to add positions without CSV upload. |
| `EnhancedPositionsSection.tsx` | Full-featured positions section with filters, sorting, bulk actions, and inline details. | Used in portfolio and organize pages. |
| `FactorBetaCard.tsx` | Card showing position's factor betas (market, size, value, momentum, quality, volatility). | Used in position detail sheets. |
| `OptionPositionCard.tsx` | Card for displaying single option contract with strike, expiry, Greeks, and metrics. | Used in options positions list. |
| `OrganizePositionCard.tsx` | Position card optimized for organize page with enhanced tagging UI. | Used in organize page position display. |
| `PositionDetailSheet.tsx` | Slide-out detail panel with comprehensive position information and management options. | Used when clicking position in list/card. |
| `PositionManagementTable.tsx` | Table view of positions with inline edit, delete, and tagging actions. | Used in portfolio admin sections. |
| `PrivatePositionCard.tsx` | Card for private/alternative positions with valuation and risk metrics. | Used in private positions list. |
| `ResearchPositionCard.tsx` | Position card optimized for research view with extended metrics and company info. | Used in research and analyze page. |
| `StockPositionCard.tsx` | Card for public equity position with symbol, company, sector, value, P&L, target return. | Used in public positions list. |

---

## research-and-analyze/

| File | Purpose | Usage |
|------|---------|-------|
| `CompactReturnsCards.tsx` | Small return metric cards (YTD, MTD, 3M, 1Y) for research section. | Used in research page header. |
| `CompactTagBar.tsx` | Horizontal scrollable tag bar showing position tags. | Used in research table views. |
| `CorrelationDebugger.tsx` | Development component for testing correlation matrix rendering and data. | Used during development only. |
| `CorrelationsSection.tsx` | Full correlation matrix display with position/sector selections and heatmap. | Used in research and analyze page. |
| `FinancialsTab.tsx` | Tab showing income statement, balance sheet, and cash flow statements. | Used in research position detail. |
| `FinancialSummaryTable.tsx` | Table displaying key financial metrics (revenue, earnings, margins, ratios). | Used in research financials section. |
| `MetricSection.tsx` | Reusable section container for research metrics with title and content. | Used to organize research page layout. |
| `PositionSidePanel.tsx` | Detailed side panel for position research with company info, financials, analysis. | Used when clicking position in research table. |
| `ResearchTableMobile.tsx` | Mobile-optimized card view of positions for research page on <768px. | Used in ResearchTableView wrapper on mobile. |
| `ResearchTableView.tsx` | Responsive wrapper rendering desktop table on ≥768px and mobile cards on <768px. | Main component in research and analyze page. |
| `ResearchTableViewDesktop.tsx` | Full 9-column research table with sortable headers and expandable rows. | Used in ResearchTableView wrapper on desktop. |
| `StickyTagBar.tsx` | Responsive wrapper for sticky tag filtering bar. | Used above research table. |
| `StickyTagBarDesktop.tsx` | Desktop sticky tag bar with horizontal scrolling and filter actions. | Rendered in StickyTagBar on desktop. |
| `StickyTagBarMobile.tsx` | Mobile sticky tag bar with modal tag selector. | Rendered in StickyTagBar on mobile. |
| `TableFooter.tsx` | Footer showing total rows, selected rows, and pagination. | Used below research table. |
| `ViewAllTagsModal.tsx` | Modal displaying all available tags with multi-select and apply. | Used in sticky tag bar mobile view. |

---

## risk/

| File | Purpose | Usage |
|------|---------|-------|
| `CorrelationMatrix.tsx` | Heatmap correlation matrix of portfolio holdings colored by correlation strength. | Used in risk analytics section of portfolio. |
| `DiversificationScore.tsx` | Card showing portfolio diversification score (0-100) with explanation and recommendations. | Used in risk page. |
| `StressTest.tsx` | Scenario analysis showing portfolio value changes under stress scenarios (market ±1%, ±2%, etc.). | Used in risk page for stress testing. |
| `StressTest_temp.tsx` | Temporary/alternate stress test component (likely being replaced). | Legacy component, usage being phased out. |
| `VolatilityMetrics.tsx` | Card showing volatility metrics with historical, current, and forward forecasts. | Used in risk page. |

---

## risk-metrics/

| File | Purpose | Usage |
|------|---------|-------|
| `ConcentrationMetrics.tsx` | Displays concentration analysis (HHI, top 10 weight, sector concentration). | Used in `/risk-metrics` page. |
| `FactorExposureCards.tsx` | Cards showing portfolio's exposure to factor betas (market, size, value, momentum, quality, volatility). | Used in risk metrics page. |
| `FactorExposureHeroRow.tsx` | Hero-sized factor exposure display with 6-column layout and large typography. | Used at top of risk metrics page. |
| `MarketBetaComparison.tsx` | Chart comparing portfolio beta vs benchmark beta over time. | Used in risk metrics page. |
| `SectorExposure.tsx` | Pie/bar chart showing portfolio sector allocation vs S&P 500 allocation. | Used in risk metrics page. |

---

## settings/

| File | Purpose | Usage |
|------|---------|-------|
| `AccountBillingSettings.tsx` | Shows billing plan, usage limits, upgrade prompts, and payment method management. | Used in `/settings` page billing section. |
| `BriefingSettings.tsx` | Controls for email briefing frequency, content preferences, and notification settings. | Used in settings page. |
| `PortfolioManagement.tsx` | Interface for managing portfolios (view, delete, set default). | Used in settings page portfolio section. |

---

## ui/ (ShadCN Components)

| File | Purpose | Usage |
|------|---------|-------|
| `alert.tsx` | ShadCN UI Alert component for displaying notifications and alerts. | Used throughout app in error/success messages. |
| `alert-dialog.tsx` | ShadCN UI AlertDialog component for confirmation dialogs. | Used for delete confirmations and critical actions. |
| `badge.tsx` | ShadCN UI Badge component for tag/label display. | Used in tags, position types, sectors. |
| `button.tsx` | ShadCN UI Button component with variants (primary, outline, ghost, destructive). | Used throughout app for all buttons. |
| `card.tsx` | ShadCN UI Card component for content containers. | Used as base for metric cards, position cards. |
| `dialog.tsx` | ShadCN UI Dialog component for modals. | Used for create/edit dialogs. |
| `dropdown-menu.tsx` | ShadCN UI DropdownMenu component for context menus. | Used in navigation and position actions. |
| `input.tsx` | ShadCN UI Input component for text fields. | Used in forms throughout. |
| `label.tsx` | ShadCN UI Label component for form labels. | Used in forms. |
| `progress.tsx` | ShadCN UI Progress bar component for showing completion percentage. | Used in onboarding progress, file uploads. |
| `select.tsx` | ShadCN UI Select dropdown component. | Used in filter dropdowns and selectors. |
| `separator.tsx` | ShadCN UI Separator component for visual dividers. | Used to separate content sections. |
| `sheet.tsx` | ShadCN UI Sheet component for slide-out panels. | Used in position detail side panels. |
| `skeleton.tsx` | ShadCN UI Skeleton component for loading states. | Used as loading placeholders. |
| `tabs.tsx` | ShadCN UI Tabs component for tabbed interfaces. | Used in research financials, settings sections. |
| `textarea.tsx` | ShadCN UI Textarea component for multi-line text input. | Used in AI chat message input. |
| `ThemedCard.tsx` | Custom card component using CSS variables for theme support. | Used instead of Card in themed sections. |
| `tooltip.tsx` | ShadCN UI Tooltip component for hover info. | Used in metric cards and data quality indicators. |

---

## Summary Statistics

**Total Components: 163 files**

| Directory | Count | Primary Use |
|-----------|-------|-------------|
| ui/ | 18 | ShadCN UI components |
| research-and-analyze/ | 17 | Position research |
| portfolio/ | 17 | Portfolio display |
| onboarding/ | 13 | User onboarding |
| organize/ | 12 | Position organization |
| positions/ | 10 | Position cards/sheets |
| command-center/ | 9 | Main dashboard |
| home/ | 8 | Home page |
| navigation/ | 6 | App navigation |
| insights/ | 5 | AI insights |
| risk/ | 5 | Risk analysis |
| risk-metrics/ | 5 | Risk metrics page |
| copilot/ | 4 | AI copilot |
| equity-search/ | 3 | Stock search |
| settings/ | 3 | User settings |
| common/ | 3 | Shared components |
| app/ | 3 | App-level |
| admin/ | 2 | Admin dashboard |
| Root level | 4 | Shared utilities |
| ai-chat/ | 1 | AI chat |
| ai/ | 1 | AI memory |
| auth/ | 1 | Authentication |
| billing/ | 1 | Billing prompts |
