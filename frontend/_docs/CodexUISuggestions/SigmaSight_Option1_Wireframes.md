# SigmaSight Option 1 – Holistic Command Center Wireframes

The low-fidelity wireframes below illustrate the Option 1 navigation and page structure described in `SigmaSight_IA_POV.md`. They are built around a desktop viewport (~1440px) and show how SigmaSightAI, risk metrics, and aggregator-style summaries coexist on screen. Use these as a starting point for high-fidelity design or to brief an AI coding agent.

---

## Launchpad (Default Landing Page)

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Top Nav: [Launchpad] [Allocations & Research] [Risk Studio] [Playbooks] [AI] │
│         [Account]                              Alerts:▲3  •  Last sync: 4h   │
├──────────────────────────────────────────────────────────────────────────────┤
│ GLOBAL ACTION BAR                                                             │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ Ask SigmaSightAI about... [ "What changed today?"             (send) ]   │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
├──────────────────────────────┬──────────────────────────────┬─────────────────┤
│ NET WORTH STACK              │ RISK PULSE                   │ ACTION QUEUE    │
│ ┌───────────────┐            │ ┌───────────────┐            │ ┌────────────┐  │
│ │  $3.2M total  │            │ │ Beta  0.87    │            │ │ Hedging gap│  │
│ │ +42k vs last  │            │ │ Vol   10.2%   │            │ │ • View plan│  │
│ ├───────────────┤            │ │ MaxDD  -8.4%  │            │ ├────────────┤  │
│ │ Asset mix     │            │ ├───────────────┤            │ │ Tax-loss opp│ │
│ │ ▣ ETFs 45%    │            │ │ Drift: Tech ▲ │            │ │ • Review lot│ │
│ │ ▨ Equities30% │            │ │ Warning Badges│            │ ├────────────┤  │
│ │ ▢ Cash 15%    │            │ │ • Sparse priv │            │ │ Rebalance    │ │
│ │ ▤ Alts 10%    │            │ │ • FX exposure │            │ │ • Simulate   │ │
│ └───────────────┘            │ └───────────────┘            │ └────────────┘  │
│ Sparkline & goal progress    │ Factor mini-heatmap + CTA    │ Each item has  │
│ links to Allocations         │ to open Risk Studio with     │ "Explain" (AI) │
│                              │ seeded prompt                │ and "Do it"    │
├──────────────────────────────┴──────────────────────────────┴─────────────────┤
│ SECONDARY ROW                                                                │
│ ┌──────────────┬──────────────┬──────────────┬─────────────────────────────┐ │
│ │ Cash Flow    │ │ Tag Health  │ │ Scenario Lab│ │ Watchlist Movers          │ │
│ │ Inflow $12k  │ │ 78% tagged   │ │ Run 1-click │ │ Top gainers/laggards     │ │
│ │ Outflow $9k  │ │ Gaps: Real Est│ │ stress test │ │ Expand to Allocations &  │ │
│ │ Trend chart  │ │ CTA to Playbk │ │ from Risk   │ │ Research with context    │ │
│ └──────────────┴──────────────┴──────────────┴─────────────────────────────┘ │
├──────────────────────────────────────────────────────────────────────────────┤
│ INSIGHT FEED (AI explanations, system alerts, audit trail snippets)          │
├──────────────────────────────────────────────────────────────────────────────┤
│ FOOTER: Data freshness • Connected institutions • Privacy link • Support     │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Key Behaviors
- **SigmaSightAI Action Bar** carries current portfolio, active module, and warning metadata by default.
- Clicking any card triggers a right-side drawer with detail and contextual AI prompts (e.g., "Explain beta drift").
- Action Queue items include quick actions: "Explain", "Simulate", "Delegate" (launches Copilot page with pre-filled prompt).

---

## Allocations & Research

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Top Nav ... (Allocations & Research active)                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│ Header: Portfolio Allocation • Data freshness badge • Download report        │
├──────────────────────────────────────────────────────────────────────────────┤
│ Tabs: [Overview] [Public Markets] [Private/Alternatives] [Options] [Watchlist]│
├──────────────────────────────┬───────────────────────────────────────────────┤
│ LEFT COLUMN (65%)            │ RIGHT COLUMN (35%)                            │
│ • Allocation sunburst        │ • SigmaSightAI Insight Panel                  │
│ • Sector/geo heatmap         │   - Suggested research briefs                 │
│ • Holdings table with AI     │   - "Ask why overweight tech" button         │
│   "summarize" icon per row   │ • Alert cards (earnings week, valuation flags)│
├──────────────────────────────┴───────────────────────────────────────────────┤
│ Research Drawer trigger row (aggregated news, factor commentary, comparables) │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Key Behaviors
- Clicking "summarize" on a holding sends ticker, weight, and risk notes to SigmaSightAI.
- Tabs swap underlying data tables but retain the right-hand insight panel.

---

## Risk Studio

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Top Nav ... (Risk Studio active)                                             │
├──────────────────────────────────────────────────────────────────────────────┤
│ Header: Risk Pulse • Scenario range selector • Export stress test results    │
├──────────────────────────────┬──────────────────────────────┬─────────────────┤
│ FACTOR MOSAIC                │ SCENARIO TIMELINE            │ WARNING PANEL   │
│ • Heatmap w/ legends         │ • Slider for shocks          │ • List of risk  │
│ • Toggle: absolute vs contrib│ • Snapshot cards per scenario│   warnings with │
│ • "Explain factor" CTA       │ • "Simulate hedge" button    │   severity tags │
├──────────────────────────────┴──────────────────────────────┴─────────────────┤
│ Hedging Playbooks carousel (AI-generated options)                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ Insight log + ability to pin recommendations to Playbooks                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Playbooks & Automation

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Top Nav ... (Playbooks active)                                               │
├──────────────────────────────────────────────────────────────────────────────┤
│ Header: Automation Progress • Coverage meter • "Create new" button          │
├──────────────────────────────┬──────────────────────────────┬─────────────────┤
│ MANUAL TAGGING               │ SMART RULES                  │ AUTOMATIONS     │
│ Card grid with completion %  │ Rule list with toggles       │ Flow builder w/ │
│ CTA: "Tag with AI"           │ CTA: "Suggest rules"         │ timeline + logs │
├──────────────────────────────┴──────────────────────────────┴─────────────────┤
│ Adoption analytics + AI tips                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## SigmaSightAI Copilot (Full Screen)

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Top Nav ... (AI Copilot active)                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│ Left rail: Saved Threads • Templates • Automations created                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Main chat area with context chips (Portfolio, Page of origin, Active alerts) │
│ Quick command bar: [Explain change] [Propose hedge] [Draft plan]             │
│ Response cards can be pinned back to Launchpad Action Queue                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Account & Integrations

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Top Nav ... (Account active)                                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│ Connections matrix • Add new institution button                              │
│ Data quality badges • Audit log timeline • Notification preferences          │
│ SigmaSightAI mini-widget: "Monitor connection health"                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### Flow Summary
1. **Launchpad** offers the holistic overview, quick insights, and cross-links.
2. Cards/deep links pass structured context to **Allocations & Research** or **Risk Studio** via drawers and seeded AI prompts.
3. Recommended actions move into **Playbooks & Automation** for execution or scheduling.
4. Users open **SigmaSightAI Copilot** for deeper reasoning or to delegate tasks, with outputs returning to Launchpad Action Queue.
5. **Account & Integrations** underpins trust by surfacing data freshness and auditability.

Use this document with the existing PRDs to brief designers or AI builders on the intended screen flows.
