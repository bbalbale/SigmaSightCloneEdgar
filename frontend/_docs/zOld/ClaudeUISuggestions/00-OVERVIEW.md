# SigmaSight Frontend Refactor - Overview & Vision

**Document Version**: 1.0
**Last Updated**: October 30, 2025
**Author**: Product Strategy
**Status**: Comprehensive Redesign Plan

---

## Executive Summary

SigmaSight is undergoing a comprehensive frontend redesign to transform from a feature-rich but fragmented platform into a best-in-class portfolio risk management experience for high net worth (HNW) investors. This document outlines the vision, strategy, and execution plan for the refactor.

### Current State: The Problem

**What We Have**:
- Sophisticated backend with 59 API endpoints across 9 categories
- Advanced risk analytics (factor exposures, stress testing, correlations, volatility)
- AI capabilities (Claude-powered chat and insights)
- Multi-asset class support (equities, options, private investments)
- Position tagging and target price tracking

**What's Wrong**:
- **Navigation chaos**: 9 separate pages in flat dropdown, no visual hierarchy
- **Fragmented workflows**: Users navigate across multiple pages to complete related tasks
- **AI siloed**: AI exists on dedicated pages, feels "bolted-on" rather than integrated
- **Desktop-only**: Not optimized for mobile/tablet use
- **Missing narrative**: No clear "so what" or daily active usage driver
- **Buried differentiator**: Exposure concepts (net/gross/long/short) not prominent

### Target State: The Vision

**What We're Building**:
- **4 unified workspaces** (vs 9 fragmented pages): Command Center, Positions, Risk Analytics, Organize
- **Exposure-first design**: Net/gross/long/short metrics prominently displayed, not buried
- **Ambient AI copilot**: AI woven throughout experience, accessible everywhere with context
- **Mobile-optimized**: Full functionality on desktop, tablet, and mobile
- **Daily active usage**: Proactive insights, alerts, and recommendations drive habitual engagement
- **Professional-grade UX**: Rival Bloomberg and Addepar while remaining accessible

---

## Strategic Positioning

### Market Opportunity

**Target Audience**: High net worth investors actively managing portfolios of long, short, options, and private investments

**Competitive Landscape**:
- **Bloomberg Professional**: Gold standard for professionals, $2,000+/month, desktop-centric
- **Addepar**: Wealth management platform for advisors, $10K+ annual, complex setup
- **eMoney**: Financial planning focus, not portfolio analytics depth
- **Consumer apps** (Robinhood, Fidelity, E*TRADE): Ignore sophisticated concepts like net exposure

**SigmaSight's Unique Position**:
- **Professional-grade analytics** at consumer-friendly price point
- **Exposure-centric** design that sophisticated investors need (ignored by consumer apps)
- **AI-first** approach making institutional risk tools accessible
- **Multi-asset class** support including options and private investments
- **Self-directed** for active managers, not advisor-dependent

### Key Differentiators

1. **Exposure Concepts**: Every professional portfolio manager thinks in terms of net/gross/long/short exposure. Consumer apps ignore this entirely, showing only "holdings" and "cash balance"

2. **Ambient AI**: Unlike chatbots confined to one page, our AI copilot is woven throughout the experience, providing contextual insights at the point of decision

3. **Institutional Analytics, Accessible UX**: We bring Bloomberg-caliber risk analytics (factor exposures, stress testing, correlation analysis) with consumer-friendly explanations via AI

4. **Multi-Asset Class Sophistication**: Support for options (LC/LP/SC/SP), short positions, and private investments—not just long equities like consumer apps

---

## Vision & Principles

### Design Principles

#### 1. Exposure-First
**Principle**: Net, gross, long, and short exposures should be immediately visible, not buried in position tables

**Why**: This is how professional investors think. "I'm 60% long, 40% short, net 20% long" tells the risk story instantly

**How**: Hero metrics at top of Command Center, exposure gauge visualization, always-on exposure summary bar

#### 2. Ambient AI, Not Chatbot
**Principle**: AI should be woven into workflows, not confined to a chat page

**Why**: Users don't want to context-switch to ask questions. They want help where they are, when they need it

**How**: Persistent AI sidebar, "AI Explain" buttons on every metric, proactive insights and alerts, contextual quick actions

#### 3. Progressive Disclosure
**Principle**: Start with summary, allow drill-down to details, all without navigation

**Why**: Reduces cognitive load, keeps users in flow, prevents information overload

**How**: Expandable cards, side panels for details, inline analytics, tabbed workspaces

#### 4. Benchmark-Relative
**Principle**: Always show portfolio metrics relative to a benchmark (S&P 500)

**Why**: Absolute numbers lack context. "45% tech" means nothing without knowing S&P 500 is 30% tech

**How**: Side-by-side comparisons, delta highlighting ("+15% vs SPY"), benchmark overlays on charts

#### 5. Mobile-Capable
**Principle**: Full functionality on all devices, not just desktop

**Why**: HNW investors check portfolios on-the-go. Mobile is table stakes, not nice-to-have

**How**: Mobile-first responsive design, bottom navigation, swipe gestures, one-handed optimization

---

## Success Metrics

### Engagement Metrics

| Metric | Current | Target | Rationale |
|--------|---------|--------|-----------|
| **Daily Active Users** | Baseline | 2x | Proactive AI insights drive daily check-ins |
| **Avg Session Duration** | Baseline | +30% | Unified workspaces reduce friction, increase engagement |
| **AI Interactions/Session** | <1 | 3+ | Ambient AI makes it easy to ask questions |
| **Risk Analytics Views** | Baseline | +100% | Better navigation increases discovery |
| **Mobile Sessions** | Baseline | +50% | Responsive redesign unlocks mobile usage |

### Efficiency Metrics

| Metric | Current | Target | Rationale |
|--------|---------|--------|-----------|
| **Time to Complete Tasks** | Baseline | -40% | Reduced navigation, inline actions |
| **Navigation Clicks/Session** | Baseline | -50% | 4 workspaces vs 9 pages |
| **Time to Insight** | Baseline | -50% | AI explanations, contextual quick actions |
| **Page Load Count** | Baseline | -40% | Unified views, no page-hopping |

### Adoption Metrics

| Metric | Current | Target | Rationale |
|--------|---------|--------|-----------|
| **Position Tagging Adoption** | Baseline | 70%+ | Smart AI suggestions make it easy |
| **AI Feature Usage** | <20% | 80%+ | Ambient integration increases discoverability |
| **Benchmark Comparison Usage** | 0% | 80%+ | New feature, prominently placed |
| **Target Price Tracking** | Baseline | +50% | Better integration with positions view |

### Satisfaction Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Overall Satisfaction** | 4.5/5 | Post-session survey |
| **"AI is helpful"** | 80%+ agree | Quarterly user survey |
| **"Easy to find what I need"** | 85%+ agree | Task completion study |
| **"Mobile experience"** | 4/5+ | App store ratings, surveys |
| **Net Promoter Score (NPS)** | 50+ | Standard NPS survey |

---

## Implementation Strategy

### Phased Rollout

#### **Phase 1: Foundation (Weeks 1-4)**
**Goal**: Establish new architecture, eliminate navigation pain points

**Deliverables**:
- Navigation consolidation (9 pages → 4 workspaces)
- Persistent AI sidebar with context injection
- Command Center (exposure-first dashboard redesign)
- Unified Positions workspace (merge 4 position pages)

**Success Criteria**:
- Navigation clicks reduced by 40%+
- Users can state exposure in <5 seconds
- AI accessible from all pages

#### **Phase 2: AI Integration (Weeks 5-8)**
**Goal**: Make AI core to the experience, drive daily engagement

**Deliverables**:
- Proactive AI insights (anomaly detection, daily summaries)
- Contextual quick actions ("AI Explain" buttons everywhere)
- Mobile-optimized responsive design
- Enhanced Risk Analytics with benchmark comparisons

**Success Criteria**:
- AI interactions increase to 3+ per session
- Daily active users increase by 25%+
- Mobile sessions functional and growing

#### **Phase 3: Advanced Features (Weeks 9-12)**
**Goal**: Power-user tools, competitive differentiation

**Deliverables**:
- Rebalancing assistant (AI-powered trade calculations)
- Hedge recommendation engine
- Smart tagging with AI suggestions
- Advanced scenario builder

**Success Criteria**:
- Power users adopt advanced tools (50%+ usage)
- Portfolio actions (rebalancing, hedging) increase
- User retention improves

### Technical Approach

**Architecture**:
- Maintain existing Next.js 14 + React 18 + TypeScript stack
- Enhance component library with new workspace components
- Unify AI systems (merge backend Responses API and frontend Chat Completions)
- Implement responsive grid system (mobile-first)
- Create new state management for workspace contexts

**Migration Strategy**:
- Feature-flag new workspaces (gradual rollout)
- A/B test Command Center vs old Dashboard
- Maintain backward compatibility during transition
- User onboarding flow for new navigation
- Comprehensive testing before each phase launch

---

## Key Changes Summary

### Navigation: 9 Pages → 4 Workspaces

**Old Structure**:
1. Dashboard
2. Portfolio Holdings
3. Public Positions
4. Private Positions
5. Risk Metrics
6. Organize
7. SigmaSight AI
8. AI Chat
9. Settings

**New Structure**:
1. **Command Center** (replaces Dashboard)
2. **Positions** (replaces Portfolio Holdings, Public, Private)
3. **Risk Analytics** (replaces Risk Metrics)
4. **Organize** (enhanced)
5. Settings (moved to dropdown)

**AI Integration**: Persistent sidebar accessible from all workspaces (replaces SigmaSight AI and AI Chat pages)

### Command Center: Exposure-First Dashboard

**Key Changes**:
- **Hero metrics**: Net worth, net exposure, gross exposure at top
- **Exposure gauge**: Visual representation of net exposure (-100% to +100%)
- **Portfolio health score**: Composite metric (beta, volatility, concentration)
- **AI insights cards**: Proactive alerts and recommendations
- **Benchmark comparison**: Sector exposure vs S&P 500 always visible
- **Quick actions**: "AI Explain" on every position and metric

### Positions: Unified Workspace

**Key Changes**:
- **Tabbed view**: All | Long | Short | Options | Private (one page, not four)
- **Inline actions**: Analyze, Tag, Target Price, AI Explain (no navigation required)
- **Side panel details**: Click position → panel slides out with analytics
- **Multi-select**: Bulk operations (tag, analyze as group)
- **Smart filters**: By tag, sector, size, P&L, custom criteria

### AI: Everywhere, Not Somewhere

**Key Changes**:
- **Persistent sidebar**: Follows user across all pages, maintains context
- **Auto-context injection**: AI knows current page, selections, filters
- **Quick action buttons**: "AI Explain" on positions, metrics, charts
- **Proactive insights**: Daily summary, anomaly alerts, recommendations
- **Conversation history**: Persisted across sessions, searchable

### Mobile: Full Functionality

**Key Changes**:
- **Bottom navigation**: Thumb-friendly (Positions | Risk | AI | More)
- **Swipe gestures**: Horizontal swipe between workspaces
- **Card-based layout**: Stacked cards vs multi-column on mobile
- **Collapsible sections**: Tap to expand details, default collapsed
- **One-handed optimization**: Critical actions in reach zone

---

## Risk Mitigation

### Potential Risks

**1. User Resistance to Change**
- **Risk**: Users accustomed to current structure may resist new navigation
- **Mitigation**:
  - Feature flags for gradual rollout
  - User onboarding tour explaining changes
  - Keep old navigation available for 2 weeks during transition
  - Gather feedback early and iterate

**2. Technical Complexity**
- **Risk**: Unifying AI systems and creating responsive workspaces is complex
- **Mitigation**:
  - Phased approach (build incrementally, test thoroughly)
  - Maintain backward compatibility during migration
  - Comprehensive testing at each phase
  - Rollback plan if critical issues arise

**3. Mobile Performance**
- **Risk**: Complex analytics may be slow on mobile devices
- **Mitigation**:
  - Mobile-first design with progressive enhancement
  - Lazy loading for heavy components
  - Simplified views on small screens
  - Performance budgets and monitoring

**4. AI Cost Escalation**
- **Risk**: Ambient AI (more interactions) increases OpenAI costs
- **Mitigation**:
  - Use Claude Haiku for simple explanations (cheaper)
  - Cache common AI responses
  - Rate limiting per user
  - Monitor costs closely, adjust if needed

**5. Scope Creep**
- **Risk**: "Just one more feature" delays launch
- **Mitigation**:
  - Strict phase definitions and timelines
  - Feature freeze after each phase
  - MVP mindset (ship, learn, iterate)
  - Product owner approval required for scope changes

---

## Timeline & Resources

### Timeline

**Phase 1**: Weeks 1-4 (Foundation)
**Phase 2**: Weeks 5-8 (AI Integration)
**Phase 3**: Weeks 9-12 (Advanced Features)
**Total**: 12 weeks to full launch

### Resources Required

**Development**:
- 1 Senior Frontend Engineer (full-time, 12 weeks)
- 1 Frontend Engineer (full-time, weeks 5-12 for mobile)
- Backend support (part-time, for AI system unification)

**Design**:
- 1 Product Designer (full-time, weeks 1-4 for mockups, part-time thereafter)
- UX research (user testing after each phase)

**Product**:
- 1 Product Manager (ongoing, prioritization and user feedback)

**QA**:
- 1 QA Engineer (part-time, weeks 3-12 for testing)
- User beta testing group (10-20 users)

---

## Next Steps

### Immediate Actions (Week 1)

1. **Stakeholder Alignment**
   - Review this document with leadership
   - Confirm strategic direction
   - Approve budget and timeline

2. **Design Kickoff**
   - Create high-fidelity mockups for Command Center
   - Design Positions workspace UI
   - Establish component design system

3. **Technical Planning**
   - Architect responsive grid system
   - Plan AI sidebar component structure
   - Define state management for workspaces

4. **User Research**
   - Interview 5-10 users about current pain points
   - Validate exposure-first approach with HNW investors
   - Test navigation concepts (card sorting exercise)

### Reading Order for This Documentation

1. **00-OVERVIEW.md** (this document) - Start here for vision and strategy
2. **01-RESEARCH-FINDINGS.md** - Competitive analysis and market insights
3. **02-NAVIGATION-ARCHITECTURE.md** - Detailed navigation redesign
4. **03-COMMAND-CENTER.md** - Dashboard specification
5. **04-POSITIONS-WORKSPACE.md** - Positions view specification
6. **05-RISK-ANALYTICS-WORKSPACE.md** - Risk metrics enhancement
7. **06-AI-INTEGRATION-ARCHITECTURE.md** - Ambient AI system design
8. **07-COMPONENT-LIBRARY.md** - Component specifications
9. **08-MOBILE-RESPONSIVE-DESIGN.md** - Mobile patterns and responsive design
10. **09-IMPLEMENTATION-ROADMAP.md** - Week-by-week execution plan
11. **10-DESIGN-MOCKUPS.md** - Visual specifications and layouts

---

## Document Index

| Document | Purpose | Audience |
|----------|---------|----------|
| 00-OVERVIEW.md | Vision, strategy, success metrics | Leadership, stakeholders |
| 01-RESEARCH-FINDINGS.md | Competitive analysis, market research | Product, design, engineering |
| 02-NAVIGATION-ARCHITECTURE.md | Information architecture, user flows | Product, design, engineering |
| 03-COMMAND-CENTER.md | Dashboard specification | Design, frontend engineering |
| 04-POSITIONS-WORKSPACE.md | Positions view specification | Design, frontend engineering |
| 05-RISK-ANALYTICS-WORKSPACE.md | Risk metrics specification | Design, frontend engineering |
| 06-AI-INTEGRATION-ARCHITECTURE.md | AI system design | Engineering (frontend & backend) |
| 07-COMPONENT-LIBRARY.md | Component specifications | Frontend engineering |
| 08-MOBILE-RESPONSIVE-DESIGN.md | Mobile/responsive patterns | Design, frontend engineering |
| 09-IMPLEMENTATION-ROADMAP.md | Week-by-week execution plan | Project management, engineering |
| 10-DESIGN-MOCKUPS.md | Visual specifications | Design, frontend engineering |

---

## Conclusion

This comprehensive redesign will transform SigmaSight from a capable but fragmented tool into a best-in-class experience for HNW investors. By consolidating navigation, emphasizing exposure concepts, weaving AI throughout, and optimizing for mobile, we create a unique market position: **professional-grade portfolio risk analytics made accessible through ambient AI**.

The phased approach allows us to ship incrementally, gather feedback, and course-correct. With clear success metrics and a 12-week timeline, we can deliver a compelling product that drives daily active usage and competitive differentiation.

**Next**: Read `01-RESEARCH-FINDINGS.md` for detailed competitive analysis and UX patterns that inform this strategy.
