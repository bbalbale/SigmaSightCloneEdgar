# Implementation Roadmap - 12-Week Execution Plan

**Document Version**: 1.0
**Last Updated**: October 30, 2025
**Timeline**: 12 weeks (3 phases)

---

## Overview

This document provides a week-by-week execution plan for the SigmaSight frontend refactor. The project is divided into 3 phases over 12 weeks, with clear deliverables and success criteria for each phase.

---

## Phase 1: Foundation (Weeks 1-4)

**Goal**: Establish new architecture, eliminate navigation pain points

---

### Week 1: Infrastructure & Navigation

**Deliverables**:
- [x] Set up new component structure (`/components/core`, `/components/ai`, etc.)
- [x] Create TopNavigationBar component
- [x] Create workspace routing (`/command-center`, `/positions`, `/risk`, `/organize`)
- [x] Implement feature flag system (`ENABLE_NEW_NAVIGATION`)
- [x] Create loading skeletons for all major components

**Implementation Tasks**:
1. **Component Structure**:
   ```bash
   src/components/
   ├── core/        # MetricCard, PortfolioHealthScore, ExposureGauge
   ├── ai/          # AICopilotSidebar, AIInsightCard, AIExplainButton
   ├── navigation/  # TopNavigationBar, WorkspaceTabs, BottomNavigation
   ├── positions/   # PositionCard, PositionTable, PositionSidePanel
   ├── risk/        # SectorExposureChart, CorrelationMatrix, StressTestCard
   └── ui/          # Button, Input, Modal, LoadingSkeleton
   ```

2. **Top Navigation Bar**:
   - Logo (clickable, returns to Command Center)
   - Workspace tabs (Command Center, Positions, Risk, Organize)
   - User menu dropdown (Profile, Settings, Logout)
   - AI Copilot toggle button

3. **Routing**:
   - `/` or `/command-center` (default)
   - `/positions` (with sub-routes: `/positions/long`, `/positions/short`, etc.)
   - `/risk` (with sub-routes: `/risk/exposure`, `/risk/factors`, etc.)
   - `/organize`

4. **Feature Flags**:
   ```typescript
   const FEATURE_FLAGS = {
     ENABLE_NEW_NAVIGATION: process.env.NEXT_PUBLIC_NEW_NAV === 'true',
     ENABLE_AI_SIDEBAR: process.env.NEXT_PUBLIC_AI_SIDEBAR === 'true'
   }
   ```

**Success Criteria**:
- Top navigation renders correctly on all pages
- Routing works (can navigate between workspaces)
- Feature flag system functional (can toggle new/old navigation)

**Testing**:
- Manual testing: Navigate between all workspaces
- Unit tests: TopNavigationBar component
- E2E tests: Navigation flow

---

### Week 2: Command Center (Part 1)

**Deliverables**:
- [x] PortfolioHealthScore component
- [x] MetricCard component (Net Worth, Exposure, P&L)
- [x] ExposureGauge component
- [x] ExposureBreakdown component
- [x] Command Center page layout (desktop)

**Implementation Tasks**:
1. **PortfolioHealthScore**:
   - Calculate composite score (beta, volatility, HHI, correlation)
   - Visual progress bar (0-100)
   - Color coding (green/blue/yellow/red)
   - "Details" expandable section

2. **MetricCard**:
   - Reusable card component
   - Props: title, value, change (MTD/YTD), sparkline
   - Responsive (hide sparkline/YTD on mobile)

3. **ExposureGauge**:
   - Gauge visualization (-100% to +100%)
   - Indicator showing current net exposure
   - Color zones (green: net long, red: net short, gray: neutral)

4. **API Integration**:
   - Fetch portfolio overview (`/api/v1/analytics/portfolio/{id}/overview`)
   - Fetch position details (`/api/v1/data/positions/details`)
   - Calculate exposures (gross, net, long, short)

**Success Criteria**:
- Command Center loads with hero metrics visible
- Health score calculated correctly
- Exposure gauge displays accurately
- All metrics update on data refresh

**Testing**:
- Unit tests: Each component in isolation
- Integration tests: Data fetching and calculation
- Visual regression tests: Screenshot comparison

---

### Week 3: Command Center (Part 2) + AI Sidebar

**Deliverables**:
- [x] SectorExposureChart component
- [x] FactorExposuresSummary component
- [x] TopPositionsTable component
- [x] AICopilotSidebar component (initial version)
- [x] Complete Command Center page

**Implementation Tasks**:
1. **SectorExposureChart**:
   - Bar chart (portfolio vs S&P 500)
   - Delta highlighting (+X% vs SPY)
   - Color coding (overweight: green, underweight: red)
   - Click sector → filter positions

2. **AI Copilot Sidebar**:
   - Slide-out sidebar (right side, 400px width)
   - Chat input + message history
   - Quick action buttons
   - Persistent across page changes (global component)
   - Resizable (drag left edge)

3. **Context Injection**:
   - Auto-inject current page, selected positions, filters
   - useAIContext hook

4. **API Integration**:
   - Sector exposure: `/api/v1/analytics/portfolio/{id}/sector-exposure`
   - Factor exposures: `/api/v1/analytics/portfolio/{id}/factor-exposures`
   - AI chat: `/api/v1/chat/conversations/{id}/send` (SSE streaming)

**Success Criteria**:
- Command Center fully functional (all components)
- AI sidebar opens/closes smoothly
- AI chat working (send message, receive response)
- Context automatically injected into AI prompts

**Testing**:
- Manual testing: Full Command Center workflow
- AI testing: Send test prompts, verify responses
- Performance: Page load time <3s

---

### Week 4: Positions Workspace

**Deliverables**:
- [x] Unified Positions page (All/Long/Short/Options/Private tabs)
- [x] PositionCard component
- [x] Position filters (tag, sector, P&L, search)
- [x] PositionSidePanel component
- [x] Merge 4 position pages into 1

**Implementation Tasks**:
1. **Tab Navigation**:
   - WorkspaceTabs component
   - URL routing: `/positions/long`, `/positions/short`, etc.
   - Active tab highlighted

2. **Position Cards**:
   - Symbol, name, value, P&L, type (long/short)
   - Tags, sector, quick actions
   - Checkbox for multi-select
   - Click → open side panel

3. **Filters**:
   - Search bar (debounced, 300ms)
   - Tag dropdown (multi-select)
   - Sector dropdown
   - P&L filter (gainers/losers/all)

4. **Side Panel**:
   - Opens on position click
   - Shows: overview, risk metrics, correlations, target price
   - Actions: Edit tags, set target price, AI explain
   - Closeable (X button, click outside, ESC key)

**Success Criteria**:
- All 4 position pages deprecated (redirects to unified page)
- Tabs work (can switch between All/Long/Short/Options/Private)
- Filters functional (search, tag, sector, P&L)
- Side panel opens with position details

**Testing**:
- Manual testing: Navigate tabs, apply filters, open side panel
- Unit tests: PositionCard, filters
- E2E tests: Full positions workflow

---

## Phase 2: AI Integration & Mobile (Weeks 5-8)

**Goal**: Make AI core to the experience, optimize for mobile

---

### Week 5: AI Insights & Contextual Actions

**Deliverables**:
- [x] AIInsightCard component
- [x] Proactive AI insights (backend batch job)
- [x] AI Insights section on Command Center
- [x] "AI Explain" buttons on all major components

**Implementation Tasks**:
1. **Backend: Insight Generation**:
   - Batch job runs nightly (or hourly)
   - Detects: concentration, volatility spikes, correlation changes
   - Stores insights in database (`ai_insights` table)
   - New endpoint: `/api/v1/insights/portfolio/{id}`

2. **AI Insight Cards**:
   - Types: warning, info, success, suggestion
   - Title, summary, actions (buttons)
   - Dismissible (user can hide)

3. **Contextual "AI Explain" Buttons**:
   - Add to: PositionCard, MetricCard, SectorExposure, FactorExposures
   - Each button pre-loads context (position, metric, etc.)
   - Click → AI sidebar opens with explanation

**Success Criteria**:
- Insights generated and displayed on Command Center
- "AI Explain" buttons functional on all components
- AI responses are contextual (know what user clicked)

**Testing**:
- Manual testing: Click "AI Explain" on various components
- Backend testing: Insight generation logic
- User testing: Do insights make sense? Are they helpful?

---

### Week 6: Risk Analytics Workspace

**Deliverables**:
- [x] Risk Analytics page with tabs (Exposure, Factors, Correlations, Scenarios, Volatility)
- [x] CorrelationMatrix component
- [x] StressTestCard component
- [x] Always-on benchmark comparison

**Implementation Tasks**:
1. **Tab Structure**:
   - Exposure (sector exposure, concentration)
   - Factors (portfolio & position-level)
   - Correlations (heatmap, diversification score)
   - Scenarios (pre-built stress tests)
   - Volatility (current, forecast, decomposition)

2. **Components**:
   - CorrelationMatrix: Heatmap, highlight high correlations
   - StressTestCard: Click to run, show results
   - BenchmarkComparison: Always show vs S&P 500

3. **API Integration**:
   - Correlation matrix: `/api/v1/analytics/portfolio/{id}/correlation-matrix`
   - Stress tests: `/api/v1/analytics/portfolio/{id}/stress-test`
   - Volatility: `/api/v1/analytics/portfolio/{id}/volatility`

**Success Criteria**:
- All 5 tabs functional
- Benchmark comparison shown on every metric
- Stress tests can be run, results displayed

**Testing**:
- Manual testing: Navigate tabs, run stress tests
- Visual testing: Correlation matrix renders correctly
- Data testing: Verify calculations match backend

---

### Week 7: Mobile Optimization (Part 1)

**Deliverables**:
- [x] Bottom navigation bar (mobile)
- [x] Responsive Command Center layout
- [x] Swipeable metric cards (mobile)
- [x] Collapsible sections (mobile)

**Implementation Tasks**:
1. **Bottom Navigation**:
   - 5 items: Home, Positions, Risk, AI, More
   - Fixed at bottom (always visible)
   - Active state highlighted
   - Badge on AI (if new insights)

2. **Responsive Layouts**:
   - Mobile (<768px): Single column, swipeable cards
   - Tablet (768-1023px): 2-column grid
   - Desktop (≥1024px): 3-4 column grid

3. **Collapsible Sections**:
   - AI Insights: Collapsed by default on mobile, expand on tap
   - Sector Exposure: Collapsed
   - Factor Exposures: Collapsed
   - Top Positions: Show top 3, "View All" button

4. **Touch Optimizations**:
   - Tap targets 44x44px minimum
   - Swipe gestures (metric cards, navigation)
   - Pull-to-refresh

**Success Criteria**:
- Bottom nav works on mobile
- Command Center fully responsive (mobile, tablet, desktop)
- Swipe gestures functional
- All sections accessible on mobile

**Testing**:
- Device testing: iPhone, iPad, Android phone/tablet
- Browser testing: Safari (iOS), Chrome (Android)
- Accessibility testing: VoiceOver, TalkBack

---

### Week 8: Mobile Optimization (Part 2)

**Deliverables**:
- [x] Responsive Positions workspace
- [x] Responsive Risk Analytics workspace
- [x] Bottom sheet modals (mobile)
- [x] Mobile AI sidebar (full-screen overlay)

**Implementation Tasks**:
1. **Responsive Positions**:
   - Compact position cards on mobile
   - Filters in bottom sheet (not inline dropdowns)
   - Swipe left on card → Quick actions
   - Infinite scroll (not pagination)

2. **Responsive Risk Analytics**:
   - Tabs scrollable horizontally on mobile
   - Charts optimized for small screens
   - Correlation matrix: Pan/zoom on mobile

3. **Bottom Sheets**:
   - Use for: Filters, position details, modals
   - Slide up from bottom
   - Drag handle, swipe to dismiss
   - Backdrop dimmed

4. **Mobile AI Sidebar**:
   - Full-screen overlay on mobile (not sidebar)
   - Slide in from right
   - Close button, swipe right to dismiss

**Success Criteria**:
- All workspaces fully responsive
- Bottom sheets working on mobile
- AI sidebar accessible on mobile
- Performance: Page load <3s on 4G

**Testing**:
- Device testing: Multiple devices, orientations
- Network testing: 4G, 3G, offline
- Performance testing: Lighthouse, WebPageTest

---

## Phase 3: Advanced Features (Weeks 9-12)

**Goal**: Power-user tools, workflow assistants

---

### Week 9: AI Workflow Assistants (Part 1)

**Deliverables**:
- [x] Rebalancing assistant workflow
- [x] Multi-step AI conversations
- [x] Trade calculation engine

**Implementation Tasks**:
1. **Rebalancing Workflow**:
   - Step 1: User states intent ("Reduce tech to 38%")
   - Step 2: AI calculates options (trim, rotate, hedge)
   - Step 3: User selects approach
   - Step 4: AI shows detailed plan (trades, tax impact, portfolio impact)
   - Step 5: Generate order list (CSV export)

2. **Multi-Step Conversations**:
   - AI maintains conversation state
   - Buttons for user selections (not just text input)
   - Progress indicator (Step 1 of 4)

3. **Backend: Trade Calculator**:
   - Calculate trades needed to reach target allocation
   - Tax impact estimation (short-term vs long-term gains)
   - Portfolio impact simulation

**Success Criteria**:
- Rebalancing workflow functional end-to-end
- AI guides user through all steps
- Order list generated correctly

**Testing**:
- Manual testing: Complete full rebalancing workflow
- Calculation testing: Verify trade calculations
- User testing: Is workflow intuitive?

---

### Week 10: AI Workflow Assistants (Part 2)

**Deliverables**:
- [x] Hedge recommendation workflow
- [x] Smart tagging with AI suggestions
- [x] Performance attribution workflow

**Implementation Tasks**:
1. **Hedge Recommendation**:
   - Analyze portfolio risk (sector concentration, factor tilts)
   - Suggest hedge instruments (index puts, sector shorts, pair trades)
   - Show pros/cons, costs, expected effectiveness

2. **Smart Tagging**:
   - AI analyzes untagged positions
   - Suggests tags based on: sector, market cap, factor exposures, valuation
   - Batch accept/reject interface
   - Auto-apply accepted tags

3. **Performance Attribution**:
   - User asks: "Why did my portfolio change X% this month?"
   - AI breaks down: position-level, sector-level, factor-level
   - Shows top contributors/detractors

**Success Criteria**:
- All 3 workflows functional
- AI suggestions are helpful and accurate
- Users can complete workflows in <2 minutes

**Testing**:
- Manual testing: Run each workflow
- Accuracy testing: AI suggestions make sense
- User testing: Measure workflow completion rate

---

### Week 11: Advanced Risk Features

**Deliverables**:
- [x] Custom scenario builder
- [x] Monte Carlo simulations
- [x] Historical scenario playback
- [x] Risk budgets and alerts

**Implementation Tasks**:
1. **Custom Scenario Builder**:
   - User defines shocks (e.g., "Tech -15%, Rates +0.75%")
   - AI runs simulation
   - Shows position-level and portfolio-level impact

2. **Monte Carlo Simulations**:
   - Generate 10,000 random scenarios
   - Show distribution of outcomes (histogram)
   - Value at Risk (VaR), Conditional VaR

3. **Historical Scenarios**:
   - Pre-built: 2008 Financial Crisis, COVID Crash, Dot-Com Bubble
   - "Replay" historical scenario on current portfolio
   - Shows how portfolio would have performed

4. **Risk Budgets**:
   - User sets limits (max VaR, max sector exposure, max single-stock)
   - AI monitors, alerts when approaching limit
   - Visual "risk gauge" (used/available risk budget)

**Success Criteria**:
- Custom scenarios can be built and run
- Monte Carlo simulations complete in <10s
- Historical scenarios replay correctly
- Risk alerts fire when limits approached

**Testing**:
- Manual testing: Build custom scenario, run Monte Carlo
- Performance testing: Simulation speed
- Accuracy testing: Historical scenario results

---

### Week 12: Polish, Testing, Launch

**Deliverables**:
- [x] Bug fixes and polish
- [x] User onboarding tour
- [x] Performance optimizations
- [x] Documentation updates
- [x] Launch preparation

**Implementation Tasks**:
1. **Bug Fixes**:
   - Address all high/medium priority bugs
   - Code review of all new components
   - Refactoring where needed

2. **User Onboarding**:
   - First-time user tour (tooltips, highlights)
   - "What's New" modal for existing users
   - Help documentation

3. **Performance**:
   - Code splitting optimizations
   - Lazy loading for below-fold content
   - Image optimization
   - Bundle size reduction

4. **Documentation**:
   - Update README files
   - Component documentation (Storybook)
   - API documentation (if new endpoints added)

5. **Launch Prep**:
   - Feature flag rollout plan (10% → 25% → 50% → 100%)
   - Rollback plan if critical issues
   - Monitoring and alerts
   - Communication plan (email users, blog post)

**Success Criteria**:
- Zero high-priority bugs
- Page load <3s (desktop), <5s (mobile)
- Lighthouse score >90
- User satisfaction >4/5 in post-launch survey

**Testing**:
- Regression testing: All features
- Load testing: Simulate 1000 concurrent users
- User acceptance testing: 10-20 beta users

---

## Success Metrics (Post-Launch)

**Engagement** (Measure after 30 days):
- Daily active users: 2x baseline (target)
- AI interactions per session: 3+ (vs <1 currently)
- Average session duration: +30%
- Mobile sessions: +50%

**Efficiency** (Measure after 7 days):
- Navigation clicks per session: -50%
- Time to complete common tasks: -40%
- Page load count per session: -40%

**Adoption** (Measure after 30 days):
- AI usage: 80%+ of users (vs <20% currently)
- Mobile usage: 30%+ of sessions (vs <10% currently)
- Benchmark comparison feature: 80%+ usage

**Satisfaction** (Survey after 14 days):
- User satisfaction: 4.5/5 (target)
- "AI is helpful": 80%+ agree
- "Easy to find what I need": 85%+ agree
- Net Promoter Score (NPS): 50+ (target)

---

## Risk Mitigation

**Technical Risks**:
1. **Performance degradation**: Mitigate with lazy loading, code splitting, caching
2. **Browser compatibility**: Test on all major browsers, use polyfills
3. **Mobile performance**: Optimize for slower devices, reduce bundle size

**User Adoption Risks**:
1. **Resistance to change**: Mitigate with onboarding tour, gradual rollout, feedback loop
2. **Feature overload**: Phase rollout, progressive disclosure, hide advanced features until needed
3. **AI inaccuracy**: Human-in-the-loop, disclaimers, confidence scores

**Project Risks**:
1. **Scope creep**: Strict phase boundaries, MVP mindset, product owner approval required
2. **Timeline delays**: Buffer time in Weeks 11-12, prioritize P0 features
3. **Resource constraints**: Consider hiring contractors for specific tasks (mobile optimization, design)

---

## Conclusion

This 12-week roadmap provides a structured path from current fragmented state to best-in-class experience. By delivering in 3 phases (Foundation, AI Integration, Advanced Features), we ensure incremental value delivery with clear milestones and success criteria at each stage.

**Next**: See `10-DESIGN-MOCKUPS.md` for visual specifications and layouts.
