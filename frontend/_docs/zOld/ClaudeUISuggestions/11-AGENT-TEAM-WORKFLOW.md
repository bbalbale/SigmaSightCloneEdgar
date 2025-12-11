# Agent Team Workflow - Specialized AI Development Approach

**Document Version**: 1.0
**Last Updated**: October 31, 2025
**Status**: Agent Coordination Guide

---

## Overview

This document describes how to use specialized AI agents to execute the SigmaSight frontend refactor. Instead of a traditional development team, we leverage Claude's Task tool to spawn specialized agents for different aspects of the project.

---

## Agent Team Structure

```
Project Manager (You + Claude)
    ↓
├─ Design Agent (Visual Design & Mockups)
├─ Architecture Agent (Project Structure & Setup)
├─ Component Builder Agent (React Components)
├─ AI Integration Agent (AI Sidebar & Chat)
├─ API Integration Agent (Backend Connections)
├─ Mobile Agent (Responsive Design)
└─ QA Agent (Testing & Bug Fixes)
```

---

## Agent Roles & Responsibilities

### 1. Design Agent

**Expertise**: UI/UX design, Tailwind CSS, design systems

**Responsibilities**:
- Convert ASCII mockups to high-fidelity Tailwind specifications
- Create component style guides (colors, typography, spacing)
- Design responsive layouts (desktop, tablet, mobile)
- Create design tokens and theme configuration

**Input Documents**:
- `03-COMMAND-CENTER.md` (layout specifications)
- `10-DESIGN-MOCKUPS.md` (visual reference)
- `08-MOBILE-RESPONSIVE-DESIGN.md` (responsive patterns)

**Deliverables**:
- `tailwind.config.js` with custom colors, spacing, typography
- Component style specifications (CSS classes, variants)
- Responsive breakpoint definitions
- Design system documentation

**Example Prompt**:
```
You are an expert UI/UX designer specializing in financial applications.
Review the mockups in /frontend/_docs/ClaudeUISuggestions/10-DESIGN-MOCKUPS.md
and create high-fidelity Tailwind CSS specifications for the Command Center page.

Create:
1. Color palette (primary, success, warning, danger, neutral)
2. Typography scale (heading sizes, body text, monospace for numbers)
3. Spacing system (xs, sm, md, lg, xl)
4. Component variants (metric cards, insight cards, navigation)

Output: tailwind.config.js and component style guide in Markdown.
```

---

### 2. Architecture Agent

**Expertise**: React/Next.js architecture, project structure, state management

**Responsibilities**:
- Set up folder structure for new components
- Configure routing for 4 workspaces
- Set up state management (Zustand stores)
- Create feature flag system for gradual rollout
- Define component interfaces and contracts

**Input Documents**:
- `02-NAVIGATION-ARCHITECTURE.md` (routing structure)
- `07-COMPONENT-LIBRARY.md` (component specifications)
- `06-AI-INTEGRATION-ARCHITECTURE.md` (state requirements)

**Deliverables**:
- Folder structure created (`/components/core`, `/components/ai`, etc.)
- Routing configured (`/command-center`, `/positions`, `/risk`, `/organize`)
- Zustand stores for navigation, AI sidebar, positions state
- Feature flag configuration
- TypeScript interfaces for all major components

**Example Prompt**:
```
You are a senior React/Next.js architect. Set up the project structure
following /frontend/_docs/ClaudeUISuggestions/07-COMPONENT-LIBRARY.md.

Tasks:
1. Create folder structure under src/components/ (core, ai, navigation, positions, risk, ui)
2. Set up Next.js routing for 4 workspaces (/command-center, /positions, /risk, /organize)
3. Create Zustand stores for:
   - Navigation state (currentWorkspace, currentTab, filters)
   - AI sidebar state (isOpen, context, conversationId)
   - Positions state (selectedPositions, filters, sidePanelOpen)
4. Implement feature flag system using environment variables

Output: All folder structure, routing files, and store definitions.
```

---

### 3. Component Builder Agent

**Expertise**: React component development, TypeScript, Storybook

**Responsibilities**:
- Build reusable UI components
- Implement component logic and interactions
- Create TypeScript interfaces
- Write Storybook stories for each component
- Ensure accessibility (ARIA labels, keyboard navigation)

**Input Documents**:
- `07-COMPONENT-LIBRARY.md` (component specs)
- `03-COMMAND-CENTER.md` (Command Center components)
- `04-POSITIONS-WORKSPACE.md` (Positions components)
- `05-RISK-ANALYTICS-WORKSPACE.md` (Risk components)

**Deliverables**:
- React components with TypeScript
- Storybook stories for visual testing
- Unit tests (Jest/React Testing Library)
- Component documentation

**Components to Build** (can parallelize with multiple agents):

**Stream 1: Navigation & Hero**
- `TopNavigationBar`
- `WorkspaceTabs`
- `BottomNavigation` (mobile)
- `PortfolioHealthScore`

**Stream 2: Metrics & Visualizations**
- `MetricCard`
- `ExposureGauge`
- `ExposureBreakdown`
- `SectorExposureChart`

**Stream 3: Data Display**
- `AIInsightCard`
- `PositionCard`
- `TopPositionsTable`
- `ActivityFeedItem`

**Example Prompt** (for PortfolioHealthScore):
```
You are an expert React developer. Build the PortfolioHealthScore component
following the spec in /frontend/_docs/ClaudeUISuggestions/03-COMMAND-CENTER.md
(Component Specifications section).

Requirements:
1. TypeScript component with props interface
2. Calculate composite score from beta, volatility, HHI
3. Visual progress bar (0-100 scale)
4. Color coding: 90-100 (green), 70-89 (blue), 50-69 (yellow), <50 (red)
5. Expandable details section (click "Details" to expand)
6. Responsive (hide details on mobile by default)

Output:
- Component file: src/components/core/PortfolioHealthScore/index.tsx
- Types file: src/components/core/PortfolioHealthScore/types.ts
- Storybook story: src/components/core/PortfolioHealthScore/PortfolioHealthScore.stories.tsx
- Unit test: src/components/core/PortfolioHealthScore/PortfolioHealthScore.test.tsx
```

---

### 4. AI Integration Agent

**Expertise**: AI/LLM integration, SSE streaming, context management

**Responsibilities**:
- Build AICopilotSidebar component
- Implement context injection system
- Add "AI Explain" buttons to all components
- Connect to backend AI chat endpoint (SSE streaming)
- Handle conversation history and state

**Input Documents**:
- `06-AI-INTEGRATION-ARCHITECTURE.md` (complete AI system design)

**Deliverables**:
- `AICopilotSidebar` component (persistent, resizable)
- `useAIContext` hook (auto-inject current page context)
- `AIExplainButton` component (contextual quick actions)
- SSE streaming implementation
- Conversation history management

**Example Prompt**:
```
You are an AI integration specialist. Build the AICopilotSidebar component
following /frontend/_docs/ClaudeUISuggestions/06-AI-INTEGRATION-ARCHITECTURE.md.

The sidebar must:
1. Be persistent across pages (global component in layout)
2. Auto-inject context using useAIContext hook:
   - Current page/workspace
   - Selected positions
   - Active filters
   - Visible data
3. Stream responses via SSE from /api/v1/chat/conversations/{id}/send
4. Show conversation history with user/AI message bubbles
5. Include quick action buttons (pre-defined prompts)
6. Display proactive insights (fetched from /api/v1/insights/portfolio/{id})
7. Be resizable (drag left edge to adjust width)
8. Have 3 states: expanded (400px), collapsed (60px icon), hidden

Use TypeScript, Tailwind CSS, and ensure smooth animations.

Output: Complete AICopilotSidebar implementation with all sub-components.
```

---

### 5. API Integration Agent

**Expertise**: React hooks, data fetching, React Query, error handling

**Responsibilities**:
- Create custom hooks for data fetching
- Integrate with existing backend APIs
- Implement loading states, error states, retry logic
- Set up React Query for caching
- Handle authentication and API errors gracefully

**Input Documents**:
- `03-COMMAND-CENTER.md` (Data Sources section)
- `04-POSITIONS-WORKSPACE.md` (API endpoints)
- `05-RISK-ANALYTICS-WORKSPACE.md` (API endpoints)
- `frontend/_docs/API_AND_DATABASE_SUMMARY.md` (existing API reference)

**Deliverables**:
- Custom hooks for each page (e.g., `usePortfolioHealth`, `useExposures`, `usePositions`)
- React Query configuration
- API client wrapper (if needed)
- Error handling utilities

**Example Prompt**:
```
You are a React hooks specialist. Create data fetching hooks for the
Command Center page. Review the APIs documented in
/frontend/_docs/ClaudeUISuggestions/03-COMMAND-CENTER.md (Data Sources section).

Create the following hooks:
1. usePortfolioHealth(portfolioId) - Fetches beta, volatility, HHI
2. useExposures(portfolioId) - Fetches gross, net, long, short exposures
3. useAIInsights(portfolioId) - Fetches proactive AI insights
4. useSectorExposure(portfolioId) - Fetches sector weights vs S&P 500
5. useTopPositions(portfolioId, limit) - Fetches top N positions by value

Requirements:
- Use React Query for caching and automatic refetching
- Handle loading, error, and success states
- Implement retry logic (3 attempts)
- Return data in format expected by components
- Support refresh/refetch functionality

Output: All hooks in src/hooks/ directory with TypeScript types.
```

---

### 6. Mobile Agent

**Expertise**: Responsive design, mobile-first development, touch interactions

**Responsibilities**:
- Make all components responsive (mobile/tablet/desktop)
- Create mobile-specific components (BottomNavigation, swipeable cards)
- Implement touch gestures (swipe, pull-to-refresh)
- Test on multiple devices and browsers
- Optimize performance for mobile networks

**Input Documents**:
- `08-MOBILE-RESPONSIVE-DESIGN.md` (complete mobile patterns guide)

**Deliverables**:
- Responsive versions of all components
- Mobile-specific navigation (BottomNavigation)
- Swipeable metric cards
- Bottom sheet modals
- Pull-to-refresh implementation
- Device testing report

**Example Prompt**:
```
You are a mobile-first frontend developer. Make the Command Center and
Positions pages fully responsive following
/frontend/_docs/ClaudeUISuggestions/08-MOBILE-RESPONSIVE-DESIGN.md.

Implement:
1. Bottom navigation bar for mobile (<768px)
   - 5 items: Home, Positions, Risk, AI, More
   - Fixed at bottom, always visible
   - Badge on AI icon if new insights

2. Swipeable metric cards on mobile
   - Horizontal scroll with snap points
   - Pagination dots below
   - Touch-friendly (44x44px tap targets)

3. Collapsible sections on mobile
   - AI Insights: Collapsed by default, tap to expand
   - Sector Exposure: Collapsed
   - Top Positions: Show top 3, "View All" button

4. Bottom sheets for modals
   - Position details, filters
   - Slide up from bottom, drag to dismiss

5. Responsive breakpoints
   - Mobile: <768px (single column, stacked cards)
   - Tablet: 768-1023px (2-column grid)
   - Desktop: ≥1024px (3-4 column grid)

Test on: iPhone 14, iPad Pro, Samsung Galaxy S23 (browser dev tools).

Output: Fully responsive components with mobile optimizations.
```

---

### 7. QA Agent

**Expertise**: Testing, quality assurance, performance optimization

**Responsibilities**:
- Write unit tests for critical components
- Write E2E tests for user flows
- Perform bug bash (manual testing)
- Run performance audits (Lighthouse)
- Document bugs with reproduction steps

**Input Documents**:
- `02-NAVIGATION-ARCHITECTURE.md` (user flows)
- `09-IMPLEMENTATION-ROADMAP.md` (success criteria)

**Deliverables**:
- Unit test suite (Jest + React Testing Library)
- E2E test suite (Playwright or Cypress)
- Bug report with reproduction steps
- Performance audit report (Lighthouse scores)
- Accessibility audit (WCAG compliance)

**Example Prompt**:
```
You are a QA engineer specializing in React applications. Review the
Command Center and Positions pages and perform comprehensive testing.

Tasks:
1. Write unit tests for:
   - PortfolioHealthScore (score calculation, rendering)
   - MetricCard (value formatting, change indicators)
   - ExposureGauge (gauge rendering, color zones)
   - AIInsightCard (dismissible, action buttons)

2. Write E2E tests for user flows:
   - Navigate from Command Center to Positions
   - Open AI sidebar, send message, receive response
   - Filter positions by tag/sector
   - Open position side panel, view details
   (See flows in /frontend/_docs/ClaudeUISuggestions/02-NAVIGATION-ARCHITECTURE.md)

3. Run Lighthouse audit:
   - Performance score >85
   - Accessibility score >90
   - Best Practices score >90

4. Manual bug bash:
   - Test all interactions (click, hover, keyboard)
   - Test responsive layouts (mobile, tablet, desktop)
   - Test error states (API failures, network errors)
   - Document any bugs found

Output: Test files, bug report, performance audit results.
```

---

## Agent Coordination Workflows

### Workflow 1: Sequential (Safer, Easier to Manage)

```
Day 1: Design Agent
  ↓ (Produces design specs)
Day 2: Architecture Agent
  ↓ (Uses design specs, creates structure)
Days 3-5: Component Builder Agents
  ↓ (Use architecture + design)
Days 6-7: AI Integration Agent
  ↓ (Integrates with components)
Days 8-9: Integration + Mobile Agents
  ↓ (Assemble pages, make responsive)
Day 10: QA Agent
  ↓ (Test everything)
```

**Advantages**:
- Clear dependencies, no conflicts
- Easier to manage (one agent at a time)
- Easier to review and provide feedback

**Disadvantages**:
- Slower (10 days minimum)
- Agents idle while waiting for dependencies

---

### Workflow 2: Parallel (Faster, More Complex)

```
Days 1-2: Design + Architecture (parallel, coordinate)
  ↓
Days 3-5: Component Builder 1 + Component Builder 2 + API Agent (parallel)
  ↓
Days 6-7: AI Integration Agent (uses completed components)
  ↓
Days 8-9: Integration + Mobile (parallel)
  ↓
Day 10: QA + Demo Prep
```

**Advantages**:
- Faster (can compress to 7-8 days)
- Multiple agents working simultaneously

**Disadvantages**:
- More coordination overhead
- Potential conflicts (agents may duplicate work)
- Harder to review (multiple outputs at once)

---

### Workflow 3: Parallel with Checkpoints (Recommended)

```
Days 1-2: Design + Architecture (parallel)
  → CHECKPOINT: Review design specs + folder structure

Days 3-5: Component Builders (2 streams) + API Agent (parallel)
  → CHECKPOINT: Review components, ensure they render correctly

Days 6-7: AI Integration Agent
  → CHECKPOINT: Test AI sidebar, ensure streaming works

Days 8-9: Integration + Mobile (parallel)
  → CHECKPOINT: Test pages, ensure responsive

Day 10: QA + Demo Prep
  → FINAL DEMO
```

**Checkpoints = You review outputs, provide feedback, course-correct before proceeding**

**Advantages**:
- Balances speed with control
- Catch issues early (at checkpoints)
- Agents can work in parallel between checkpoints

**Disadvantages**:
- Requires discipline (don't skip checkpoints)
- May need to redo work if checkpoint fails

---

## How to Launch Agents

### Method 1: Via Project Manager (Claude)

**You say**: "Launch Design Agent to create Tailwind specs for Command Center"

**Claude (me) does**:
```
1. Formulates specialized prompt for Design Agent
2. Includes relevant documentation context
3. Launches agent via Task tool
4. Agent returns design specifications
5. I present results to you for review
```

**Advantages**:
- I handle agent coordination
- Context is automatically included
- Easier for you (just tell me what you need)

---

### Method 2: Direct Agent Invocation (You)

**You can directly invoke agents yourself**:

```
Use the Task tool:

subagent_type: "general-purpose"
prompt: "You are a Design Agent. Review /frontend/_docs/ClaudeUISuggestions/10-DESIGN-MOCKUPS.md
and create Tailwind CSS specifications for the Command Center page. Include color palette,
typography, spacing, and component styles."
description: "Design Agent - Tailwind specs"
```

**Advantages**:
- You have direct control
- No intermediary (me)

**Disadvantages**:
- You need to formulate prompts yourself
- Need to manage context manually

---

## Agent Handoffs

**How agents pass work to each other**:

### Example: Design → Architecture → Component Builder

**Step 1: Design Agent Output**
```
tailwind.config.js:
{
  colors: {
    primary: '#3B82F6',
    success: '#10B981',
    ...
  },
  spacing: { xs: '4px', sm: '8px', ... }
}

Component styles:
- MetricCard: rounded-lg, p-6, bg-white, shadow-md
- PortfolioHealthScore: p-8, border-2, border-blue-500
```

**Step 2: Architecture Agent Input**
- Receives Design Agent output
- Creates `tailwind.config.js` file in project
- Sets up folder structure
- Defines component interfaces using design tokens

**Architecture Agent Output**
```
Folder structure:
src/components/core/MetricCard/
  ├─ index.tsx (component skeleton)
  ├─ types.ts (props interface)
  ├─ styles.ts (Tailwind classes)

Zustand stores:
navigationStore.ts
aiStore.ts
positionsStore.ts
```

**Step 3: Component Builder Input**
- Receives Architecture Agent output
- Receives Design Agent output (for styling)
- Implements component logic

**Component Builder Output**
```
src/components/core/MetricCard/index.tsx:
export const MetricCard = ({ title, value, change }: MetricCardProps) => {
  return (
    <div className="rounded-lg p-6 bg-white shadow-md">
      <h3 className="text-sm text-gray-600">{title}</h3>
      <p className="text-2xl font-bold">{formatCurrency(value)}</p>
      {change && <ChangeIndicator {...change} />}
    </div>
  )
}
```

**Key**: Each agent's output becomes the next agent's input. This is why checkpoints are important - verify work before next agent starts.

---

## Best Practices

### 1. Clear Boundaries
- Each agent has specific responsibilities
- Avoid overlap (e.g., don't have 2 agents building same component)
- Document what each agent is responsible for

### 2. Checkpoints Are Critical
- Review agent output before proceeding
- Don't launch dependent agents until dependencies are verified
- Be willing to redo work if checkpoint reveals issues

### 3. Provide Detailed Context
- Give agents all relevant documentation
- Specify exact files to reference
- Clarify constraints (e.g., "must use existing API", "reuse existing hooks")

### 4. Iterative Refinement
- First pass may not be perfect
- Provide feedback, ask agent to refine
- Multiple iterations are normal

### 5. Version Control
- Commit after each agent completes work
- Easy to rollback if agent produces bad code
- Clear history of what each agent contributed

### 6. Test Early, Test Often
- Don't wait until Day 10 for testing
- Have QA Agent review components as they're built
- Catch issues early when they're easier to fix

---

## Sample 10-Day Sprint Timeline

### **Days 1-2: Foundation**
- **Design Agent**: Create Tailwind specs, design tokens
- **Architecture Agent**: Set up folder structure, routing, state management
- **Checkpoint**: Review design + architecture, approve before proceeding

### **Days 3-5: Core Components**
- **Component Builder Agent 1**: Navigation, Hero (TopNav, HealthScore, MetricCards)
- **Component Builder Agent 2**: Analytics (SectorChart, Factors, Positions Table)
- **API Integration Agent**: Data hooks (usePortfolioHealth, useExposures, etc.)
- **Checkpoint**: Review components, ensure they render with real data

### **Days 6-7: AI Integration**
- **AI Integration Agent**: Build AICopilotSidebar, context injection, AI Explain buttons
- **Checkpoint**: Test AI sidebar, verify SSE streaming works

### **Days 8-9: Assembly + Mobile**
- **Integration Agent**: Assemble Command Center + Positions pages
- **Mobile Agent**: Make all components responsive
- **Checkpoint**: Test pages on desktop, tablet, mobile

### **Day 10: QA + Demo**
- **QA Agent**: Unit tests, E2E tests, bug bash, performance audit
- **You**: Demo preparation, user invitations, feedback collection

---

## Success Criteria

**Agent outputs are successful if**:
- ✅ Code compiles without TypeScript errors
- ✅ Components render correctly in Storybook
- ✅ All tests pass (unit + E2E)
- ✅ Lighthouse score >85 (performance)
- ✅ Meets accessibility standards (WCAG AA)
- ✅ Responsive across all breakpoints
- ✅ Works with real backend API data

---

## Troubleshooting

### Problem: Agent produces broken code
**Solution**:
- Provide more specific requirements
- Reference exact examples from existing codebase
- Ask agent to explain reasoning, then refine

### Problem: Agents produce conflicting code
**Solution**:
- Ensure clear boundaries (each agent owns specific files)
- Use locking mechanism (Agent 1 owns folder X, Agent 2 owns folder Y)
- Review architecture agent's folder structure before proceeding

### Problem: Agent output doesn't match design
**Solution**:
- Provide design specs explicitly (Tailwind classes, exact spacing)
- Show examples from mockups
- Ask agent to compare output with mockup, self-correct

### Problem: Too slow, not hitting 10-day deadline
**Solution**:
- Run more agents in parallel (3-4 Component Builders at once)
- Reduce scope (cut P2 features, focus on P0)
- Skip checkpoints (risky, but faster)

---

## Conclusion

The specialized agent approach allows rapid development by parallelizing work across multiple AI agents with clear responsibilities. Success requires:

1. **Clear specifications** (the 11 docs provide this)
2. **Good coordination** (checkpoints between agent handoffs)
3. **Iterative refinement** (review and refine agent outputs)
4. **Version control** (commit after each agent, easy rollback)

With proper coordination, a 10-day sprint is achievable for Phase 1 (Command Center + Positions + Navigation + AI Sidebar).

---

**Next**: Ready to launch your first agent? Start with Design Agent or Architecture Agent depending on whether you need design specs first.
