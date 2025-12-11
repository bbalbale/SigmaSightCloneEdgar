# Navigation Architecture - Information Architecture & User Flows

**Document Version**: 1.0
**Last Updated**: October 30, 2025
**Status**: Detailed Specification

---

## Table of Contents

1. [Overview](#overview)
2. [Current vs Proposed Structure](#current-vs-proposed-structure)
3. [Navigation Patterns](#navigation-patterns)
4. [User Flows](#user-flows)
5. [Information Architecture](#information-architecture)
6. [Implementation Details](#implementation-details)

---

## Overview

### Problem Statement

**Current State**: 9 separate pages in a flat dropdown menu
- No visual hierarchy or grouping
- Unclear which pages are primary vs secondary
- Redundant position views across 4 pages (Dashboard, Portfolio Holdings, Public Positions, Private Positions)
- Context switching required for related tasks
- AI siloed on 2 separate pages

**User Impact**:
- High navigation friction (multiple clicks to complete simple tasks)
- Cognitive load ("Where do I find X?")
- Low feature discovery (hidden in dropdown)
- Fragmented experience

### Solution Overview

**New Structure**: 4 primary workspaces + persistent AI sidebar
- **Command Center**: Portfolio health, exposure, insights (replaces Dashboard)
- **Positions**: Unified position view with tabs (replaces 4 position pages)
- **Risk Analytics**: Enhanced risk metrics (replaces Risk Metrics)
- **Organize**: Enhanced tagging/organization (retained)
- **AI Copilot**: Persistent sidebar (replaces 2 AI pages)
- **Settings**: Moved to user menu dropdown (retained)

**Benefits**:
- 50% reduction in navigation clicks
- Clear hierarchy (workspaces vs utilities)
- Related features grouped logically
- AI accessible everywhere
- Progressive disclosure (tabs within workspaces)

---

## Current vs Proposed Structure

### Current Navigation (9 Pages)

```
NavigationDropdown (All pages in flat list)
├─ Dashboard
├─ Portfolio Holdings
├─ Public Positions
├─ Private Positions
├─ Risk Metrics
├─ Organize
├─ SigmaSight AI
├─ AI Chat
└─ Settings
```

**Problems**:
1. **No grouping**: Position-related pages (Holdings, Public, Private) not visually grouped
2. **Redundancy**: 4 different pages show positions (Dashboard has positions too)
3. **AI fragmentation**: Two separate AI pages (SigmaSight AI vs AI Chat)
4. **Flat hierarchy**: All pages treated equally, no indication of importance
5. **Hidden features**: Users don't discover features in long dropdown

### Proposed Navigation (4 Workspaces)

```
Top Navigation Bar
┌────────────────────────────────────────────────────────┐
│ [SigmaSight]  Command Center  Positions  Risk  Organize  [User Menu ▾]  [AI ✨] │
└────────────────────────────────────────────────────────┘

User Menu Dropdown:
├─ Profile
├─ Settings
├─ Help & Support
└─ Logout

AI Copilot:
└─ Persistent sidebar (slide-out), accessible from all pages
```

**Workspace Structure**:

**1. Command Center** (Home / Primary View)
   - Replaces: Dashboard
   - Purpose: Portfolio health overview, exposure summary, key insights
   - Default landing page

**2. Positions** (Unified Position Management)
   - Replaces: Portfolio Holdings, Public Positions, Private Positions
   - Purpose: View and manage all positions
   - Sub-navigation: Tabs (All | Long | Short | Options | Private)

**3. Risk Analytics** (Risk Management Hub)
   - Replaces: Risk Metrics
   - Purpose: Factor exposures, correlations, stress testing, volatility
   - Sub-navigation: Tabs (Exposure | Factors | Correlations | Scenarios | Volatility)

**4. Organize** (Tagging & Organization)
   - Retained from current
   - Purpose: Tag positions, create custom groupings
   - Enhanced with AI-suggested tags

**AI Copilot** (Persistent Sidebar)
   - Replaces: SigmaSight AI, AI Chat
   - Purpose: Contextual AI assistance, accessible everywhere
   - Always available, auto-injects current context

**Settings** (Utility)
   - Moved to User Menu dropdown
   - Purpose: User preferences, account settings

---

## Navigation Patterns

### Primary Navigation: Top Bar

**Layout**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│  [SigmaSight Logo]   [Command Center]  [Positions]  [Risk]  [Organize]  │
│                                                    [User ▾]  [AI ✨]     │
└─────────────────────────────────────────────────────────────────────────┘
```

**Components**:

1. **Logo** (Left)
   - Clickable → Returns to Command Center
   - Always visible

2. **Workspace Tabs** (Center-Left)
   - Command Center, Positions, Risk Analytics, Organize
   - Active tab highlighted (underline, bold, or color)
   - Hover state for non-active tabs

3. **User Menu** (Right)
   - User name + portfolio name (if multiple portfolios)
   - Dropdown: Profile, Settings, Help, Logout
   - Avatar icon (initials or photo)

4. **AI Copilot Toggle** (Far Right)
   - Always visible
   - Badge if new insights available (e.g., "3")
   - Click → Opens/closes AI sidebar

**Behavior**:
- Sticky header (stays visible when scrolling)
- Responsive (collapses to hamburger on mobile)
- Keyboard shortcuts: Cmd+1 (Command Center), Cmd+2 (Positions), Cmd+3 (Risk), Cmd+4 (Organize), Cmd+J (AI)

### Secondary Navigation: Tabs Within Workspaces

**Example: Positions Workspace**
```
┌─────────────────────────────────────────────────────────────────────────┐
│  Positions                                                              │
│  ─────────                                                              │
│  [All] [Long] [Short] [Options] [Private]                              │
│  ══════                                                                 │
│                                                                         │
│  [Content for selected tab...]                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Behavior**:
- Tabs for sub-categories within workspace
- Active tab highlighted (underline or fill)
- URL updates on tab change (e.g., `/positions/long`)
- Back button navigates through tab history

**Example: Risk Analytics Workspace**
```
┌─────────────────────────────────────────────────────────────────────────┐
│  Risk Analytics                                                         │
│  ──────────────                                                         │
│  [Exposure] [Factors] [Correlations] [Scenarios] [Volatility]          │
│  ═════════                                                              │
│                                                                         │
│  [Content for selected tab...]                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tertiary Navigation: Breadcrumbs

**Use Case**: When drilling into specific position or analysis

**Example**:
```
Command Center > Positions > Long > NVDA

or

Risk Analytics > Factors > Technology Sector
```

**Behavior**:
- Shows path to current view
- Each segment clickable to navigate back
- Only appears when 3+ levels deep

### AI Copilot: Persistent Sidebar

**Layout**:
```
┌────────────────────────────────────┬──────────────────────┐
│  Main Content Area                 │  AI Copilot          │
│                                    │  ──────────          │
│  [Command Center, Positions, etc.] │  💬 Ask me anything  │
│                                    │  [_______________]   │
│                                    │                      │
│                                    │  Quick Actions:      │
│                                    │  • Explain exposure  │
│                                    │  • Analyze risks     │
│                                    │  • Suggest rebalance │
│                                    │                      │
│                                    │  Recent Insights:    │
│                                    │  ⚠ Tech at 45%...    │
│                                    │  ✓ On track for...   │
│                                    │                      │
│                                    │  [Minimize]          │
└────────────────────────────────────┴──────────────────────┘
```

**States**:
- **Expanded** (default, 300-400px width): Full sidebar visible
- **Collapsed**: Only AI icon visible (far right), click to expand
- **Hidden**: User can hide completely (preference saved)

**Behavior**:
- Persists across page changes (follows user)
- Auto-injects context (current page, selections)
- Conversation history maintained
- Resizable (drag left edge to adjust width)
- Can be moved to left side (preference)

### Mobile Navigation: Bottom Bar

**Layout** (Mobile Only):
```
┌────────────────────────────────┐
│                                │
│     Content Area               │
│                                │
│                                │
├────────────────────────────────┤
│  [🏠]  [📊]  [⚠️]  [✨]  [☰]  │  ← Bottom navigation
└────────────────────────────────┘
```

**Buttons** (5 max):
1. **Home Icon**: Command Center
2. **Chart Icon**: Positions
3. **Warning Icon**: Risk Analytics
4. **Sparkle Icon**: AI Copilot
5. **Menu Icon**: Organize, Settings, More

**Behavior**:
- Fixed position at bottom (always visible)
- Active page highlighted
- Badge notifications on AI icon
- Tap "More" → Full menu sheet

---

## User Flows

### Flow 1: Morning Review

**Goal**: Check portfolio health, review overnight changes

**Current Flow** (Painful):
1. Login → Dashboard (3 metrics cards, factor exposures)
2. Click dropdown → Portfolio Holdings (to see position details)
3. Click dropdown → Risk Metrics (to check volatility, correlations)
4. Click dropdown → SigmaSight AI (to ask "What changed?")
5. Wait 25-30 seconds for AI insights
6. Navigate back to Dashboard

**Total**: 5 page loads, 4 navigation actions, 30+ seconds, context switching

**New Flow** (Streamlined):
1. Login → Command Center (lands here by default)
2. See at a glance:
   - Portfolio health score: 82/100
   - Net worth: $500K (+$2,500 MTD)
   - Exposure: 20% net long (gauge visualization)
   - AI insights cards: "Tech up 10% this month", "Volatility spike detected"
3. Click "AI Explain" on any insight → Sidebar opens with full explanation
4. Scroll down → See top positions, sector exposure, factor summary
5. Done

**Total**: 1 page load, 0 navigation actions, <5 seconds

**Improvement**: 80% reduction in time, zero context switching

---

### Flow 2: Analyze Specific Position

**Goal**: Understand risk profile of NVDA holding

**Current Flow**:
1. Dashboard → See NVDA in positions list
2. Click dropdown → Portfolio Holdings (to see full details)
3. Find NVDA in table (scroll if many positions)
4. Click dropdown → Risk Metrics → Factor Exposures (to see NVDA's factors)
5. Scroll to find NVDA in factor table
6. Click dropdown → Risk Metrics → Correlations (to see NVDA correlations)
7. Find NVDA in correlation matrix
8. Click dropdown → AI Chat (to ask "Should I trim NVDA?")

**Total**: 7 page loads, 6 navigation actions, lots of scrolling

**New Flow**:
1. Command Center → See NVDA in top positions
2. Click NVDA → Side panel opens with:
   - Position details (qty, avg cost, current price, P&L)
   - Risk metrics (beta, volatility, factor exposures)
   - Correlations (top correlated positions)
   - AI quick actions: "Explain", "Analyze risk", "Suggest action"
3. Click "Analyze risk" → AI sidebar explains:
   - "NVDA is high-beta (1.85), contributing to portfolio volatility"
   - "Correlation with MSFT is 0.92 (concentration risk)"
   - "Consider trimming or hedging tech exposure"
4. Done

**Total**: 1 page load, 2 clicks (click NVDA, click AI button), all in-context

**Improvement**: 85% reduction in actions, zero navigation, AI proactively suggests action

---

### Flow 3: Rebalance Portfolio

**Goal**: Reduce tech exposure from 45% to 35%

**Current Flow**:
1. Dashboard → Note tech concentration (but no clear guidance)
2. Click dropdown → Risk Metrics → Sector Exposure (to see exact %)
3. Mentally calculate: "Need to trim $X from tech positions"
4. Click dropdown → Portfolio Holdings (to see tech positions)
5. Filter/scroll to find tech positions
6. Manually calculate which to trim (NVDA? META? Both?)
7. Click dropdown → AI Chat (to ask "How should I rebalance?")
8. AI suggests: "Trim NVDA and META by X shares each"
9. Manually calculate trade details, tax impact
10. Open broker separately, place trades manually

**Total**: 8+ page loads, complex mental math, external broker site

**New Flow**:
1. Command Center → AI insights card: "Tech at 45%, +15% vs S&P 500"
2. Click "Suggest rebalancing" → AI workflow starts in sidebar:
   - "Goal: Reduce tech to 35%?"
   - User: "Yes"
   - AI: "Here are 3 options..." (trim, hedge, rotate)
   - User: "Option 1: Trim NVDA and META"
   - AI: Shows trades, tax impact, portfolio impact
   - User: "Generate order list"
   - AI: Provides CSV export or copy-to-clipboard
3. (Future) Integrate with broker API to submit orders directly

**Total**: 1 page, AI-guided workflow, auto-calculated trades

**Improvement**: 90% reduction in complexity, AI handles all calculations

---

### Flow 4: Research New Position Idea

**Goal**: Evaluate adding JPM to portfolio

**Current Flow**:
1. Dashboard → No clear path (not a current holding)
2. Click dropdown → Portfolio Holdings (but JPM not there)
3. Exit SigmaSight → Google "JPM stock beta"
4. Exit SigmaSight → Google "JPM financials"
5. Return to SigmaSight → Click AI Chat
6. Ask "Should I add JPM to my portfolio?"
7. AI responds with generic analysis
8. User must manually cross-reference with current portfolio

**Total**: Multiple external sites, fragmented context

**New Flow**:
1. Command Center → AI Copilot sidebar always visible
2. User asks: "Should I add JPM to my portfolio?"
3. AI (with portfolio context):
   - "Your financials exposure is 12%, -1% vs S&P 500"
   - "JPM would increase financials exposure and reduce tech concentration"
   - Fetches company profile (backend endpoint): "JPM beta is 1.15, similar to portfolio"
   - "Adding $50K JPM would shift portfolio:"
     - Tech: 45% → 42%
     - Financials: 12% → 15%
     - Beta: 1.15 → 1.14 (slightly less volatile)
   - "Correlation with existing positions: Low (0.32 avg), good diversification"
   - "Recommendation: JPM would improve diversification. Consider adding."
4. Done

**Total**: 1 conversation, AI pulls all data, contextual analysis

**Improvement**: Zero external research, AI does all cross-referencing

---

## Information Architecture

### Workspace Details

#### 1. Command Center

**Purpose**: Primary landing page, portfolio health at a glance

**Content Hierarchy**:
```
Command Center
├─ Hero Section
│  ├─ Portfolio Health Score (composite metric)
│  ├─ Net Worth + Change MTD/YTD
│  └─ Quick Stats (Beta, Volatility, HHI)
│
├─ Exposure Summary
│  ├─ Net Exposure Gauge (-100% to +100%)
│  ├─ Gross/Long/Short Breakdown
│  └─ Exposure Bars (visual)
│
├─ AI Insights & Alerts
│  ├─ Proactive insight cards (tech concentration, volatility spike, etc.)
│  ├─ Anomaly detection alerts
│  └─ "What you should know today" summary
│
├─ Sector Exposure vs S&P 500
│  └─ Bar chart with delta highlighting
│
├─ Factor Exposures Summary
│  └─ Top 3 factor tilts (Growth, Size, Momentum, etc.)
│
├─ Top Positions (by absolute value)
│  ├─ Position cards with quick actions
│  └─ "AI Explain" buttons
│
└─ Recent Activity Feed
   └─ Trades, price changes, alerts (last 7 days)
```

**Navigation Out**:
- Click position → Opens Positions workspace (filtered to that position)
- Click sector → Opens Risk Analytics > Exposure (filtered to sector)
- Click factor → Opens Risk Analytics > Factors (factor detail)
- Click "View all positions" → Positions workspace
- Click "Full risk analysis" → Risk Analytics workspace

---

#### 2. Positions

**Purpose**: Unified view of all positions across asset classes

**Content Hierarchy**:
```
Positions Workspace
├─ Tab Navigation
│  ├─ All (default)
│  ├─ Long (LONG positions only)
│  ├─ Short (SHORT positions only)
│  ├─ Options (LC, LP, SC, SP)
│  └─ Private (PRIVATE investment_class)
│
├─ Filters & Search
│  ├─ Search bar (by symbol, name)
│  ├─ Filter by tag
│  ├─ Filter by sector
│  ├─ Filter by size (large, medium, small)
│  └─ Filter by P&L (gainers, losers)
│
├─ Summary Bar (always visible at top)
│  ├─ Total positions count
│  ├─ Total market value
│  ├─ Total P&L (absolute + %)
│  └─ Exposure summary (gross, net)
│
├─ Position List/Table
│  ├─ Position cards (default) or table view (toggle)
│  ├─ Sortable columns (symbol, value, P&L, beta, etc.)
│  ├─ Multi-select (checkbox) for bulk operations
│  └─ Quick actions per position:
│     ├─ [Analyze Risk] → Opens side panel with risk details
│     ├─ [Tag] → Add/remove tags
│     ├─ [Target Price] → Set/edit target price
│     └─ [AI Explain] → AI sidebar explains position
│
└─ Side Panel (opens when position clicked)
   ├─ Position details (qty, avg cost, current price, P&L)
   ├─ Risk metrics (beta, volatility, sector)
   ├─ Factor exposures
   ├─ Correlations with top positions
   ├─ Company profile summary (if available)
   ├─ Target price tracking (if set)
   └─ Quick actions (Tag, AI Explain, Set Target)
```

**Navigation Out**:
- Click "Analyze Risk" → Risk Analytics workspace (pre-filtered to position)
- Click sector tag → Filters to positions in that sector
- Click custom tag → Filters to tagged positions
- Click "AI Explain" → AI sidebar opens (context: this position)

---

#### 3. Risk Analytics

**Purpose**: Deep-dive risk analysis, stress testing, correlations

**Content Hierarchy**:
```
Risk Analytics Workspace
├─ Tab Navigation
│  ├─ Exposure (default)
│  ├─ Factors
│  ├─ Correlations
│  ├─ Scenarios (stress testing)
│  └─ Volatility
│
├─ Benchmark Selector (applies to all tabs)
│  └─ Dropdown: S&P 500 (default), NASDAQ, Russell 2000, Custom
│
├─ [Exposure Tab]
│  ├─ Exposure Summary (gross, net, long, short)
│  ├─ Sector Exposure vs Benchmark (bar chart)
│  ├─ Concentration Metrics (top 10, HHI)
│  ├─ AI Explain: "Your portfolio is concentrated in..."
│  └─ Suggested actions (diversify, hedge, etc.)
│
├─ [Factors Tab]
│  ├─ Portfolio-level factor exposures (Size, Value, Momentum, Quality, Market Beta)
│  ├─ Factor exposure chart (bar chart vs benchmark)
│  ├─ Position-level factor table (which positions drive factor tilts)
│  ├─ Factor performance attribution
│  └─ AI Explain: "Your Growth tilt of +2.3σ is driven by NVDA, META..."
│
├─ [Correlations Tab]
│  ├─ Correlation matrix (heatmap)
│  ├─ Top correlated pairs (concentration risk)
│  ├─ Diversification score
│  ├─ AI Explain: "NVDA and MSFT are highly correlated (0.92), creating concentration risk"
│  └─ Suggested hedges
│
├─ [Scenarios Tab]
│  ├─ Pre-built scenarios (Tech crash -20%, Rate hike +0.50%, Market crash -10%, etc.)
│  ├─ Scenario cards (click to run)
│  ├─ Results table (position-level impact)
│  ├─ Portfolio-level impact summary
│  ├─ AI Explain: "In a tech crash scenario, your portfolio would lose $X due to..."
│  └─ (Future) Custom scenario builder
│
└─ [Volatility Tab]
   ├─ Current portfolio volatility (annualized)
   ├─ Volatility trend chart (historical)
   ├─ HAR forecast (1-day, 1-week, 1-month)
   ├─ Volatility decomposition (which positions contribute most)
   ├─ Comparison vs benchmark
   └─ AI Explain: "Volatility spiked from 15% to 21% due to tech sector rotation"
```

**Navigation Out**:
- Click position in any table → Opens Positions workspace (side panel for that position)
- Click factor → Expands factor detail view
- Click sector → Filters to sector positions
- Click "AI Explain" → AI sidebar opens (context: current tab + selections)

---

#### 4. Organize

**Purpose**: Tag positions, create custom groupings

**Content Hierarchy**:
```
Organize Workspace
├─ Tag Management
│  ├─ Create new tag (name, color)
│  ├─ Edit existing tags
│  ├─ Delete tags (bulk)
│  └─ AI-suggested tags (based on sector, theme, risk profile)
│
├─ Position Tagging Interface
│  ├─ Drag-and-drop (position → tag bucket)
│  ├─ Multi-select + tag (bulk tagging)
│  ├─ Auto-tag suggestions from AI
│  └─ Tag filters (show positions by tag)
│
├─ Tag Groups
│  ├─ Display tagged positions grouped by tag
│  ├─ Aggregate metrics per tag (total value, P&L, exposure)
│  └─ Quick actions (view as portfolio, analyze risk)
│
└─ AI Smart Tagging
   ├─ "Suggest tags for untagged positions" button
   ├─ AI analyzes positions (sector, market cap, factor exposures)
   ├─ Suggests tags: "Core Holdings", "Growth", "Value", "Hedge", "Speculative", etc.
   ├─ User reviews, accepts/rejects in batch
   └─ Tags applied
```

**Navigation Out**:
- Click tagged group → Positions workspace (filtered to tag)
- Click "Analyze risk" for tag group → Risk Analytics (filtered to tag)
- Click "AI Explain" → AI sidebar explains tag strategy

---

### URL Structure

**Pattern**: `/workspace/tab?filters`

**Examples**:

**Command Center**:
- `/` or `/command-center` (default landing)

**Positions**:
- `/positions` (All tab, no filters)
- `/positions/long` (Long tab)
- `/positions/short` (Short tab)
- `/positions/options` (Options tab)
- `/positions/private` (Private tab)
- `/positions?tag=core-holdings` (filtered by tag)
- `/positions?sector=technology` (filtered by sector)
- `/positions/long?tag=growth&sector=technology` (multiple filters)

**Risk Analytics**:
- `/risk` (Exposure tab, default)
- `/risk/exposure` (explicit)
- `/risk/factors` (Factors tab)
- `/risk/correlations` (Correlations tab)
- `/risk/scenarios` (Scenarios tab)
- `/risk/volatility` (Volatility tab)
- `/risk/factors?position=NVDA` (filtered to position)

**Organize**:
- `/organize` (default)
- `/organize?tag=core-holdings` (filtered to tag)

**Settings**:
- `/settings` (accessed via user menu)

**AI Copilot**:
- State managed client-side (sidebar open/closed)
- No dedicated URL (accessible from all pages)

---

## Implementation Details

### Component Architecture

**Navigation Components**:

```typescript
// Top navigation bar
<TopNavigationBar>
  <Logo />
  <WorkspaceTabs
    active="command-center"
    tabs={['command-center', 'positions', 'risk', 'organize']}
  />
  <UserMenu />
  <AICopilotToggle />
</TopNavigationBar>

// Workspace-specific tab navigation
<WorkspaceTabs>
  <Tab value="all" label="All" />
  <Tab value="long" label="Long" />
  <Tab value="short" label="Short" />
  <Tab value="options" label="Options" />
  <Tab value="private" label="Private" />
</WorkspaceTabs>

// AI Copilot sidebar
<AICopilotSidebar
  isOpen={sidebarOpen}
  context={currentContext}  // auto-injected based on page
  onClose={() => setSidebarOpen(false)}
/>

// Mobile bottom navigation
<BottomNavigation>
  <NavButton icon="home" label="Command Center" />
  <NavButton icon="chart" label="Positions" />
  <NavButton icon="warning" label="Risk" />
  <NavButton icon="sparkle" label="AI" badge={3} />
  <NavButton icon="menu" label="More" />
</BottomNavigation>
```

### State Management

**Navigation State** (Zustand Store):

```typescript
interface NavigationState {
  currentWorkspace: 'command-center' | 'positions' | 'risk' | 'organize'
  currentTab: string | null  // e.g., 'long', 'factors', etc.
  filters: {
    tag?: string
    sector?: string
    positionType?: string
    // ... other filters
  }
  aiSidebarOpen: boolean
  aiSidebarContext: object  // current page context for AI
}
```

**URL Sync**:
- Use Next.js router to sync state with URL
- Navigate programmatically: `router.push('/positions/long?tag=growth')`
- Parse URL params on page load to restore state

### Responsive Breakpoints

**Desktop** (≥1024px):
- Top navigation bar (full width)
- Multi-column layouts (2-4 columns)
- AI sidebar (300-400px width, resizable)
- Side panels for position details

**Tablet** (768px - 1023px):
- Top navigation bar (may collapse some items)
- 2-column layouts
- AI sidebar (full screen overlay when open)
- Bottom sheets for position details

**Mobile** (<768px):
- Hamburger menu (top navigation collapses)
- Bottom navigation bar (primary)
- 1-column layouts (cards stack)
- AI sidebar (full screen overlay)
- Bottom sheets for all modals

### Keyboard Shortcuts

**Global**:
- `Cmd/Ctrl + K`: Command palette (quick navigation)
- `Cmd/Ctrl + J`: Toggle AI Copilot
- `Cmd/Ctrl + /`: Focus search
- `Esc`: Close modals/panels

**Navigation**:
- `Cmd/Ctrl + 1`: Command Center
- `Cmd/Ctrl + 2`: Positions
- `Cmd/Ctrl + 3`: Risk Analytics
- `Cmd/Ctrl + 4`: Organize

**Workspace-Specific** (Positions):
- `Alt + A`: All tab
- `Alt + L`: Long tab
- `Alt + S`: Short tab
- `Alt + O`: Options tab
- `Alt + P`: Private tab

### Accessibility

**ARIA Labels**:
- All navigation elements have aria-labels
- Active page indicated with `aria-current="page"`
- Tab navigation uses `role="tablist"`, `role="tab"`, `role="tabpanel"`

**Keyboard Navigation**:
- Tab key navigates through all interactive elements
- Arrow keys navigate within tab lists
- Enter/Space activates buttons

**Screen Reader Support**:
- Announce page changes
- Announce AI sidebar open/close
- Announce loading states

---

## Migration Strategy

### Phase 1: Parallel Implementation (Week 1-2)

**Approach**: Build new navigation alongside old (feature flag)

**Steps**:
1. Create new TopNavigationBar component
2. Create workspace pages (Command Center, Positions, Risk, Organize)
3. Feature flag: `ENABLE_NEW_NAVIGATION` (default: false)
4. Users opt-in to beta test new navigation

**Fallback**: Users can toggle back to old navigation at any time

---

### Phase 2: Gradual Rollout (Week 3)

**Approach**: Enable new navigation for 25% of users (A/B test)

**Metrics to Track**:
- Navigation clicks per session
- Time to complete common tasks
- Page load count per session
- User satisfaction (survey)
- Bug reports

**Success Criteria**: New navigation shows 30%+ improvement in metrics

---

### Phase 3: Full Migration (Week 4)

**Approach**: Enable for 100% of users, deprecate old navigation

**Steps**:
1. Onboarding tour for new users ("Welcome to the new SigmaSight!")
2. One-time tooltip for existing users ("Navigation has moved")
3. Help documentation updated
4. Remove old navigation code

**Support**: In-app help messages for 2 weeks post-launch

---

## Success Metrics

**Quantitative**:
- Navigation clicks per session: -50% (target)
- Page loads per session: -40% (target)
- Time to complete tasks: -40% (target)
- AI sidebar usage: 3+ interactions per session (target)

**Qualitative**:
- "Easy to find what I need": 85%+ agree (survey)
- "New navigation is better than old": 80%+ agree (survey)
- Support tickets ("Where is X?"): -60% (target)

**Monitoring**:
- Track navigation patterns with analytics (Mixpanel, Amplitude, etc.)
- Heatmaps to see where users click most
- Session recordings to identify friction points

---

## Conclusion

The new navigation architecture reduces complexity from 9 fragmented pages to 4 unified workspaces, eliminates redundancy (4 position pages → 1), and makes AI accessible everywhere (not siloed on 2 separate pages). This aligns with best practices from Bloomberg (workspace model), Addepar (drill-down hierarchy), and modern fintech (ambient AI).

**Key Innovations**:
1. **Workspace-based navigation** (vs flat page list)
2. **Persistent AI sidebar** (vs separate AI pages)
3. **Progressive disclosure** (tabs, side panels vs full pages)
4. **Mobile-first responsive** (bottom nav, swipeable cards)
5. **Contextual quick actions** (no navigation required)

**Next**: Read `03-COMMAND-CENTER.md` for detailed specification of the primary landing page.
