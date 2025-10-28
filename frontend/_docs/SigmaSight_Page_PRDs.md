# SigmaSight Page PRDs & AI Build Prompts (Revision 2)

This document updates our product requirements to reflect the new layout options described in the revised POV. Each section includes:
- **Product Requirements** for Option 1 (Holistic Command Center) – our recommended baseline.
- **Variations** outlining how Options 2 and 3 adjust the experience.
- **AI Build Prompts** tuned for the SigmaSightAI container environment and the `RiskMetricsLocal` data path.

---

## Global Considerations
- **Branch context**: All risk analytics must read from the local pipeline exposed by `RiskMetricsService` and surfaced via `GET /api/v1/analytics/portfolio/{id}/risk-metrics`. Handle warning metadata (`few_snapshots`, `stale_data`) gracefully.
- **SigmaSightAI container**: Use the shared container utilities (see `frontend/src/containers/AIChatContainer.tsx`) to embed contextual prompts. Every page must define at least one quick action that launches the copilot with pre-seeded instructions.
- **Feature flags**: Continue to gate new risk panels behind the experimental flag (`RISK_METRICS_LOCAL_EXPERIMENT`) until backend sign-off.
- **Analytics**: Emit events through the existing `trackEvent` helper with page + module identifiers; include context such as warning codes and selected tags to inform future personalization.

---

## Option 1 (Recommended): Holistic Command Center

### Page 1 – Launchpad (Replaces `/portfolio`)
**Job statement**: “Give me a single glance at how I’m doing, where I’m exposed, and what to do next.”

**Primary modules**
1. **Net Worth Stack** – stacked bar showing account types, asset classes, and external connections. Should support manual assets similar to Kubera.
2. **Risk Pulse** – three metric tiles (beta, annualized volatility, max drawdown) plus sparkline + warning chips sourced from `RiskMetricsService`.
3. **Action Queue** – AI-curated tasks (rebalance, fix data gaps, follow earnings). Each item has CTA buttons: "Open in Research", "Delegate to SigmaSightAI".
4. **SigmaSightAI Prompt Bar** – persistent input with suggested prompts (“Explain today’s volatility jump”, “Draft a rebalance order for underweight tags”).
5. **Supplemental panels** – Factor exposure mosaics, cash runway indicator, portfolio news digest.

**User stories**
- As an investor, I can see my aggregate net worth and diversification at a glance.
- When risk metrics are stale or data is missing, I see warnings and suggested remediation tasks.
- I can delegate an action to SigmaSightAI directly from the Action Queue.

**Data & API needs**
- Existing `usePortfolioData` hook for holdings + exposures.
- Risk metrics endpoint (local pipeline) with warning metadata.
- Notifications API (placeholder) for drift alerts; until ready, stub sample data.

**AI integration**
- Quick actions should call SigmaSightAI with payload `{ intent: 'summarize-risk', metrics, warnings }`.
- Prompt bar seeds assistant with context: `"You are SigmaSightAI inside the Launchpad. User portfolioId=${portfolioId}, warnings=${warningCodes}. Provide succinct advice."`

**Analytics**
- `launchpad_module_viewed` (module_id, warning_state)
- `launchpad_action_taken` (action_type, delegated_to_ai)

**AI build prompt**
```
You are coding inside the SigmaSight frontend (Next.js 14, TypeScript). Build a Launchpad page that replaces the existing portfolio dashboard.
- Structure the page using the container pattern (`app/launchpad/page.tsx` imports `LaunchpadContainer`).
- Compose modules: NetWorthStack, RiskPulseTiles (reading `RiskMetricsService` data), ActionQueue, SigmaSightAIPromptBar, FactorExposureMosaic.
- Pull risk metrics via `/api/proxy/analytics/portfolio/${portfolioId}/risk-metrics` and merge warnings into UI badges.
- Integrate SigmaSightAI quick actions using the shared `useSigmaSightAI()` hook from the SigmaSightAI container.
- Respect the `RISK_METRICS_LOCAL_EXPERIMENT` flag; show fallback copy if disabled.
- Emit analytics events via `trackEvent` when modules mount or actions fire.
Return fully typed React components, hooks, and any supporting utility modules.
```

---

### Page 2 – Allocations & Research
**Job statement**: “Help me explore holdings, ideas, and coverage gaps across asset classes.”

**Modules**
1. **Asset Tabs** – Public, Private, Options, Watchlists, External Accounts.
2. **AI Brief Strip** – contextual summary card at top of each tab (“AI notes: 2 earnings this week, 1 untagged private deal”).
3. **Position Tables** – reuse existing EnhancedPositionsSection with aggregator-inspired highlight rows (e.g., drift > 5%).
4. **Tag coverage bar** – show coverage per asset tab.
5. **In-line SigmaSightAI** – "Explain this position" button opens side drawer chat seeded with position metadata.

**AI build prompt**
```
Implement an AllocationsResearchContainer that unifies public/private/options/watchlist data.
- Fetch data via existing services; ensure compatibility with RiskMetricsLocal tags.
- Render AI Brief using a call to SigmaSightAI container (`generateBrief({ portfolioId, tab })`).
- Provide buttons in each row to launch SigmaSightAI with position context.
- Emit analytics for tab switches and AI launches.
```

**Variations**
- *Option 2*: Rename page to **Opportunities Board**. Add Kanban swimlanes (Ideas, Data Fixes, Actions) fed by AI scoring.
- *Option 3*: Convert to a slide-in **Data Room** that opens from chat; layout becomes vertical sections instead of full page.

---

### Page 3 – Risk Studio
**Job statement**: “Diagnose factor exposures, run scenarios, and understand potential drawdowns.”

**Modules**
1. **Factor Mosaic** – grid of factor cards with trend charts + SigmaSightAI "explain" button.
2. **Scenario Timeline** – slider to compare baseline vs shocks (rate hike, sector rotation). Start with static presets; mark advanced simulations as “coming soon”.
3. **Warning Console** – table summarizing warnings from risk metrics (e.g., `few_snapshots`), plus CTA to fetch more data.
4. **Hedging Playbooks** – curated actions linking to Playbooks & Automation page.
5. **AI Ask Strip** – prompts like “How would a 1% rate hike affect my beta?”

**AI build prompt**
```
Create RiskStudioContainer with modules for factor visualization, scenario cards, warning console, and AI ask strip.
- Consume risk metrics + factor exposure data.
- Support feature flag gating for scenario components.
- Use SigmaSightAI container hooks to request explanations or hedging suggestions.
- Track interactions (scenario_selected, warning_expand, ai_prompt_sent).
```

**Variations**
- *Option 2*: Rename to **Risk Lab**. Add control panel with sliders for stress test parameters.
- *Option 3*: Implement as collapsible drawer launched from AI conversation when user types "show me risk".

---

### Page 4 – Playbooks & Automation
**Job statement**: “Organize portfolio tags, automate rules, and manage workflows.”

**Modules**
1. **Manual Tagging Tab** – reuse OrganizeContainer drag-and-drop UI.
2. **Smart Rules Tab** – wizard for auto-tagging (conditions, actions) with AI-suggested templates.
3. **Automation Library** – cards for rebalancing scripts, hedging, reminders; each can be handed to SigmaSightAI for execution guidance.
4. **Progress Tracker** – dial showing percentage of holdings covered by tags/automations.

**AI build prompt**
```
Refactor OrganizeContainer into PlaybooksAutomationContainer with tabbed navigation (Manual, Smart Rules, Automations).
- Persist rule configurations via backend (stub service if needed).
- Offer "Generate rule with SigmaSightAI" CTA that pre-fills description and hands off to copilot.
- Display tag coverage metrics using existing tagging state selectors.
```

**Variations**
- *Option 2*: Rename to **Workflow Builder**; present modules as Kanban columns (Ideas → In Progress → Automated).
- *Option 3*: Expose as **Builder Mode** overlay triggered from chat; UI shifts to step-by-step AI-guided wizard.

---

### Page 5 – SigmaSightAI Copilot
**Job statement**: “Conversationally manage the portfolio, ask questions, and trigger automations.”

**Modules**
1. **Conversation Threads** – existing chat view with saved threads.
2. **Preset Gallery** – "Explain daily moves", "Draft rebalance", "Summarize risk warnings".
3. **Context Capsules** – show currently active portfolio, tag filters, warning states.
4. **Shared Actions Log** – timeline of AI recommendations and whether user executed them.

**AI build prompt**
```
Enhance AIChatContainer to add preset gallery, context capsules, and action log.
- Pull warnings from RiskMetricsLocal endpoint when chat loads.
- Allow presets to inject structured system prompts.
- Persist action log to local storage (placeholder) with view filters.
```

**Variations**
- *Option 2*: Rebrand page as **Collaborate** with shared notes and export to PDF.
- *Option 3*: This becomes the default **Conversational Home**; embed Launchpad summary cards above the chat thread.

---

### Page 6 – Account & Integrations
**Job statement**: “Manage connections, notifications, and data quality.”

**Modules**
1. **Connection Manager** – list of brokerage/API connections with sync status.
2. **Notification Preferences** – toggles for alerts (risk spikes, drift, data gaps).
3. **Data Quality Center** – scoreboard of missing positions, stale prices, warning counts.
4. **Audit Trail** – chronological list of SigmaSightAI-generated actions and user decisions.

**AI build prompt**
```
Build AccountIntegrationsContainer with sections for connections, notifications, data quality, audit trail.
- Surface warning counts from RiskMetricsService metadata.
- Provide "Ask SigmaSightAI" buttons next to each warning to request remediation steps.
- Track toggles and connection events.
```

**Variations**
- *Option 2*: Add workflow status (e.g., automation success/fail) and integrate with Workflow Builder board.
- *Option 3*: Rename to **Settings & Trust Center**, focusing on permissions and data transparency for AI interactions.

---

## Option 2 Summary Adjustments
If we pursue the **Risk Playbook Workbench**:
- Rename Launchpad to **Today’s Briefing** and emphasize chronological feed (cards sorted by time) plus AI-generated daily summary.
- Allocations & Research becomes **Opportunities Board** with Kanban layout and AI scoring chips.
- Playbooks & Automation shifts to **Workflow Builder** with columns representing state; analytics track card movement.
- SigmaSightAI Copilot evolves into **Collaborate** combining chat, shared notes, and export tools.
- Add shared workspace metadata (owner, collaborators) to each module.

## Option 3 Summary Adjustments
For the **AI-First Conversational Shell**:
- Default route is the SigmaSightAI Copilot page with Launchpad widgets pinned as cards.
- Other pages manifest as drawers summoned by AI commands; navigation dropdown becomes secondary quick launcher.
- Each module should expose a `renderInDrawer` variation compatible with chat-first interactions.
- Prioritize voice input/output and multi-step AI workflows.

---

## Implementation Roadmap
1. Validate preferred option with stakeholders; prototype Launchpad/Today’s Briefing or Conversational Home accordingly.
2. Sprint 1: Stand up Launchpad (or Conversational Home) with Risk Pulse, Action Queue, AI prompt bar.
3. Sprint 2: Ship Allocations/Opportunities workspace and Risk Studio/Lab, ensuring SigmaSightAI integration for explanations.
4. Sprint 3: Refactor Organize into Playbooks/Workflow Builder and expand AI Copilot with presets + logging.
5. Sprint 4: Harden Account & Integrations, add audit trails, and finalize analytics instrumentation.
6. Continuous: Capture user feedback, iterate on SigmaSightAI prompt templates, and expand automation library.
