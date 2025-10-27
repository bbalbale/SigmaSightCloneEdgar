# SigmaSight Application Page PRDs & AI Prompts

This document expands on the SigmaSight application experience POV by providing actionable product requirement documents (PRDs) and build prompts for the six core authenticated pages: Overview Hub, Research & Discovery, Playbooks, Risk Diagnostics, AI Copilot, and Account & Integrations. Each PRD is tuned for hand-off to an AI coding agent and aligns with the proposed navigation pillars.

---

## Page: Overview Hub (Dashboard)

### PRD
- **Objective**: Deliver a single glance summary of portfolio health, risk posture, and AI-recommended actions that link to deeper workflows.
- **Primary persona & job**: Self-directed investor assessing whether the portfolio is on track and what needs attention today.
- **User flows**:
  1. Land on `/portfolio` → see Health Score, Risk Pulse, Opportunities Queue → click into detail cards or launch AI insight.
  2. Scroll to detailed metrics, factor exposures, and segmented position lists for drill-down.
- **Key modules**:
  - Health Score tile (aggregate drawdown risk, diversification, goal progress).
  - Risk Pulse tile (top factor movers from existing factor exposures).
  - Opportunities Queue (AI-curated tasks: rebalance, hedge, data fixes; deep links to other pages).
  - Persistent AI prompt bar with suggested intents (open chat pre-filled context).
  - Existing metrics cards, factor exposure cards, filtered position tables reused below hero tiles.
- **Data requirements**:
  - Portfolio summary metrics (existing `usePortfolioData`).
  - Factor exposures, beta deltas, and historical trend stub.
  - AI recommendations endpoint (placeholder service returning list of actions with CTA metadata; allow mocked data).
- **UX & states**:
  - Loading skeletons per tile; empty state messaging (e.g., “No new opportunities”).
  - Error banners tied to data quality issues surfaced by `usePortfolioData`.
  - Responsive layout: hero tiles in grid (3-up desktop, stack on mobile).
- **Actions & integrations**:
  - CTA buttons: “View Factors” → Risk page, “Review Playbook” → Playbooks page.
  - AI prompt bar triggers `/ai-chat` with query params describing context tile.
- **Analytics**:
  - Track tile clicks, AI prompt usage, completion of queued opportunities.
- **Non-goals**: No goal-creation wizard, no new backend risk calculations.
- **Risks/open questions**: Final formula for Health Score TBD; define fallback copy when AI recommendations unavailable.
- **Acceptance criteria**:
  - All modules render with mocked data if services unavailable.
  - Navigation CTAs link correctly.
  - Accessibility: keyboard focus, ARIA labels for tiles, color contrast.

#### Prompt for AI Coding Agent
> Build/extend the `/portfolio` Overview Hub to include Health Score, Risk Pulse, Opportunities Queue, and an AI prompt bar above existing metrics and factor exposure sections. Use existing services/hooks (`usePortfolioData`, factor components) and stub a new `useOpportunitiesQueue` hook returning mocked actions. Ensure responsive layout, loading states, and CTA wiring to `/risk` and `/playbooks`. Add analytics events with our `trackEvent` utility. Preserve current metrics, factor, and position sections below the new hero modules.

---

## Page: Research & Discovery

### PRD
- **Objective**: Consolidate public, private, options, and watchlist research views into one tabbed workspace with AI briefs.
- **Primary persona & job**: Investor evaluating individual holdings and seeking actionable intelligence.
- **User flows**:
  1. Arrive at `/research` → default to Public tab with AI brief and positions table.
  2. Switch tabs (Private, Options, Watchlists) to filter dataset.
  3. Apply filters/sorting, open detail drawers, or launch AI for deeper analysis.
- **Key modules**:
  - Header with AI-generated market brief (fetch via `researchInsightsService`, allow mock).
  - Tab navigation for asset segments, each reusing `EnhancedPositionsSection` with segment-specific props.
  - Inline AI quick actions (e.g., “Explain this position”) per row.
  - Watchlist management CTA linking to modal or future page (stub).
- **Data requirements**:
  - Position datasets segmented by type (extend existing API client to accept `segment` param).
  - AI brief endpoint returning summary paragraphs and highlight chips.
  - Filter definitions reused from current Public Positions container.
- **UX & states**:
  - Loading skeleton for brief and table per tab.
  - Empty state messaging per segment.
  - Sticky filters row when scrolling.
- **Actions & integrations**:
  - “Send to Playbook” action triggers tag modal from Organize module.
  - Inline AI actions open `/ai-chat` with context in query params.
- **Analytics**:
  - Track tab switches, filter usage, AI brief expansion, inline AI actions.
- **Non-goals**: No new chart visualizations; watchlist CRUD can remain mocked.
- **Risks/open questions**: Performance when switching tabs; confirm availability of private/options data.
- **Acceptance criteria**:
  - Tabs render with correct dataset filtering.
  - AI brief gracefully handles null/empty responses.
  - Accessibility: tabs keyboard navigable per WAI-ARIA.

#### Prompt for AI Coding Agent
> Implement a `/research` route using the container pattern. Create `ResearchContainer` that renders an AI market brief, tabbed segments (Public, Private, Options, Watchlists), and reuses `EnhancedPositionsSection` per tab. Integrate filters from `PublicPositionsContainer`, add mocked `useResearchInsights` hook for AI briefs, and wire inline AI quick actions to `/ai-chat`. Ensure skeleton loading, empty states, analytics tracking, and ARIA-compliant tabs.

---

## Page: Playbooks (Portfolio Organization & Automation)

### PRD
- **Objective**: Transform Organize into a Playbooks hub that blends manual tagging with automation setup.
- **Primary persona & job**: Investor or advisor organizing holdings and configuring repeatable actions.
- **User flows**:
  1. Visit `/playbooks` → land on Manual Tagging tab with existing drag-and-drop groups.
  2. Switch to Automation Rules tab to define/tag automation (stub backend).
  3. View Tag Coverage metrics and launch AI to suggest playbooks.
- **Key modules**:
  - Tabbed layout: Manual Tagging (reuse `OrganizeContainer` core), Automation Rules (new list + modal), Templates (future stub list).
  - Tag Coverage metrics card showing % of positions tagged, untagged exposure, last updated.
  - AI assistant sidebar recommending automations.
- **Data requirements**:
  - Existing tagging data from Zustand store/services.
  - Automation configs (mocked array with name, trigger, status).
  - Coverage metrics calculated from positions + tags (compute client-side).
- **UX & states**:
  - Preserve drag-and-drop interactions.
  - Modal for creating/editing automation rules (form validation, allow mock save).
  - Empty states for automation/template tabs with CTA to create new.
- **Actions & integrations**:
  - “Send to AI” buttons push current tag selection to `/ai-chat` intent.
  - Automation toggle should update local state and show toast.
- **Analytics**:
  - Track tab usage, automation creation, AI sidebar interactions.
- **Non-goals**: No backend persistence; no calendar scheduling.
- **Risks/open questions**: Need to confirm automation rule schema with backend team.
- **Acceptance criteria**:
  - Manual tagging parity with current Organize page.
  - Automation tab supports create/edit/delete in local state.
  - Tag coverage metrics update on tag changes.

#### Prompt for AI Coding Agent
> Refactor the existing Organize experience into `/playbooks`. Create a `PlaybooksContainer` with tabs for Manual Tagging (wrap existing drag-and-drop components), Automation Rules (local-state CRUD with modal), and Templates (placeholder list). Add a Tag Coverage metrics card fed by current portfolio + tag data, plus an AI recommendations sidebar using mocked `usePlaybookSuggestions`. Ensure analytics events, responsive layout, and no regressions to tagging UX.

---

## Page: Risk Diagnostics

### PRD
- **Objective**: Provide a dedicated surface for factor decomposition, stress testing, and hedging ideas.
- **Primary persona & job**: Investor monitoring portfolio risk drivers and evaluating mitigation strategies.
- **User flows**:
  1. Navigate to `/risk` → see risk overview cards and factor trend charts.
  2. Drill into factor detail drawers, review hedging suggestions tied to tags or positions.
  3. Save/view scenarios (mocked) for future reference.
- **Key modules**:
  - Risk overview tiles (Volatility, Drawdown, Concentration) derived from existing metrics.
  - Factor mosaic (grid of factor cards with sparkline trend and exposure delta).
  - Scenario list with ability to load mock stress test results.
  - Hedging playbook suggestions linking to Playbooks/Research.
- **Data requirements**:
  - Factor exposures and historical trends (extend service to include sparkline data; mock if necessary).
  - Scenario definitions with outcome metrics (local JSON stub).
  - Hedging ideas from `riskAdvisoryService` (mocked array referencing tags/positions).
- **UX & states**:
  - Loading skeletons for each module.
  - Empty state copy if scenarios not yet saved.
  - Detail drawer/side panel for factor deep dives (include chart, narrative, actions).
- **Actions & integrations**:
  - “View in Research” deep links to `/research?symbol=...`.
  - “Add hedge to Playbook” button opens automation modal in `/playbooks` (via shared context or routing).
  - AI quick prompt: “Summarize today’s risk changes”.
- **Analytics**:
  - Track factor card interactions, scenario loads, hedging CTA clicks.
- **Non-goals**: No real-time risk recalculation; no backend persistence for scenarios yet.
- **Risks/open questions**: Performance of sparkline charts; alignment with backend timeline for risk data.
- **Acceptance criteria**:
  - Factor cards render using real/mock data with trend sparkline.
  - Scenario list interacts with detail panel and handles empty state.
  - Hedging suggestions visible with clear CTAs and tooltips.

#### Prompt for AI Coding Agent
> Create a `/risk` route with `RiskDiagnosticsContainer` delivering risk overview tiles, factor mosaic with sparklines, scenario list, and hedging suggestions. Reuse factor exposure data from the dashboard, augment with mocked trend data via `useRiskInsights`. Implement detail drawers, loading states, analytics tracking, and CTAs linking to `/research` and `/playbooks`. Include AI quick prompt component to launch `/ai-chat` focused on risk changes.

---

## Page: AI Copilot

### PRD
- **Objective**: Evolve `/ai-chat` into the command center for conversational analysis, presets, and contextual entry points.
- **Primary persona & job**: Investor seeking narrative insights or task execution through natural language.
- **User flows**:
  1. Open AI Copilot page → view conversation history and preset intents.
  2. Select a preset (e.g., “Assess diversification”) or type custom prompt.
  3. Review assistant response, trigger follow-up actions (export, push to Playbooks).
- **Key modules**:
  - Preset gallery (cards or chips) with categories: Risk, Research, Operations.
  - Conversation pane with streaming responses, status chips, and context breadcrumb.
  - Context inspector showing current portfolio, selected tags, or positions referenced.
  - Export/share actions (copy, download transcript stub).
- **Data requirements**:
  - Existing AI chat service and message store.
  - Preset definitions (static JSON with title, description, prompt, icon).
  - Context data from portfolio store and query params (when launched from other pages).
- **UX & states**:
  - Loading indicator for streaming responses.
  - Empty state when no conversation yet with CTA to pick a preset.
  - Error handling for API failures with retry.
- **Actions & integrations**:
  - Preset selection pre-fills chat input and triggers send.
  - “Send to Playbook” pushes summary to automation tab (mocked handshake).
  - Shortcut to open mini chat (future) but include stub link.
- **Analytics**:
  - Track preset usage, message count, export actions.
- **Non-goals**: No voice input or real backend export yet.
- **Risks/open questions**: Session persistence length; handling large context payloads.
- **Acceptance criteria**:
  - Presets render and initiate conversations.
  - Context inspector updates when launched with query params.
  - Error and empty states fully designed.

#### Prompt for AI Coding Agent
> Enhance `/ai-chat` by adding a preset gallery, context inspector, and export actions while keeping existing streaming chat behavior. Implement presets as a configurable JSON, wire selections to pre-fill and send messages via the current chat service, and show context from query params + portfolio store. Add analytics events, loading/error states, and ensure accessibility for keyboard navigation.

---

## Page: Account & Integrations (Settings)

### PRD
- **Objective**: Expand Settings into a central hub for account management, data connections, notifications, and audit trails.
- **Primary persona & job**: Investor managing account preferences and ensuring data integrity.
- **User flows**:
  1. Visit `/settings` → review account profile and security details.
  2. Connect or manage custodial integrations and data sources.
  3. Configure notifications/automation toggles and review activity logs.
- **Key modules**:
  - Account profile card (name, email, plan, edit modal).
  - Security section (2FA status, password update link placeholder).
  - Integrations list (broker connections, status badges, connect/disconnect buttons).
  - Notifications & automation preferences (toggles, frequency selectors).
  - Audit log table showing recent actions/alerts sourced from data quality errors.
- **Data requirements**:
  - User profile from auth store/service.
  - Integrations data (mock service returning providers, status, last sync).
  - Notification preferences (local state with save stub).
  - Audit events (reuse errors/warnings from `usePortfolioData` fallback or mock list).
- **UX & states**:
  - Inline editing modals with validation.
  - Loading skeleton for integrations list.
  - Empty state messaging for audit log.
  - Toast confirmations after preference updates.
- **Actions & integrations**:
  - “Reconnect” buttons trigger mock API and update status.
  - “View data quality report” links to `/portfolio` data quality section.
  - AI helper chip offering to audit settings (launch `/ai-chat`).
- **Analytics**:
  - Track integration connect/disconnect, notification toggles, audit log views.
- **Non-goals**: No billing management; no real OAuth flows yet.
- **Risks/open questions**: Final list of supported custodians.
- **Acceptance criteria**:
  - All sections render with mocked data if backend unavailable.
  - Preference changes persist in session (local store) and show confirmations.
  - Accessibility coverage for forms and tables.

#### Prompt for AI Coding Agent
> Rework `/settings` into an Account & Integrations hub with profile, security, integrations, notification preferences, and audit log modules. Use existing auth store for profile basics, create mocked hooks for integrations and audit events, and wire action buttons with optimistic updates + toasts. Ensure responsive layout, accessible forms, analytics tracking, and AI helper link to `/ai-chat`.

---

## Implementation Guidance for AI Agents
- Follow the container pattern: thin route files importing containers from `src/containers`.
- Reuse existing hooks/services where noted; create new hooks under `src/hooks` when stubbing data.
- All new modules should emit analytics via `trackEvent` and respect the current design system (`@/components/ui`).
- Ensure navigation dropdown labels align with page names and routes once implemented.

