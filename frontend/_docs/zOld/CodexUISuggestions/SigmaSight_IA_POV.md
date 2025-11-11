# SigmaSight Application Experience POV (Revision 2)

## Executive Summary
- SigmaSight should take cues from leading aggregators (Empower, Kubera, Personal Capital) by opening with a holistic financial pulse that fuses balances, cash flows, and risk exposure into a single command center. Investors expect to see their entire wealth posture before drilling down; the `RiskMetricsLocal` branch now enables us to blend institutional-grade risk with consumer-grade clarity.
- The **SigmaSightAI container** already wraps our AI copilot logic. We should treat it as a ubiquitous concierge that can surface next actions, explain anomalies, and launch workflows directly from every page. All layout options below assume SigmaSightAI is embedded contextually, not relegated to a single route.
- We outline three navigation models—**Holistic Command Center**, **Risk Playbook Workbench**, and **AI-First Conversational Shell**—each designed to highlight our differentiators: real-time risk diagnostics, tag-driven organization, and AI-assisted decisioning.

## Research Insights from Aggregators & Risk Platforms
1. **Aggregators** emphasize first-glance comprehension: Personal Capital’s dashboard stacks net worth trajectory, cash flow, and investment allocation before inviting deeper analysis; Kubera layers in manual asset tracking with confidence badges; Empower uses smart alerts for drift and fee drag.
2. **Risk platforms** like BlackRock’s Advisor Center or MSCI RiskManager lead with scenario heatmaps and factor decompositions but often bury the narrative. Translating these visuals into "why it matters" copy is crucial for individual investors.
3. **AI-powered fintech apps** (Copilot Money, Violet) weave conversational helpers into every module so users can ask "what changed today?" without context switching.
4. Winning pattern: combine an aggregator-style launchpad, modular deep dives, and on-page AI prompts that feel like a proactive analyst.

## Experience Principles (Retained & Extended)
1. **Holistic first glance** – Always surface an at-a-glance health signal that mixes performance, diversification, liquidity, and alerts.
2. **Journey-based navigation** – Organize routes around investor jobs: assess, diagnose, plan, act, and explain.
3. **Narrative-rich risk** – Convert factor math and warning metadata from `RiskMetricsService` into plain-English insights with recommended actions.
4. **AI everywhere** – SigmaSightAI should be callable from nav, cards, and tables with context payloads (portfolio ID, tag set, warning codes).
5. **Progress tracking** – Show completeness (data coverage, tagging coverage, playbook adoption) so investors feel momentum.

## Option 1 – Holistic Command Center (Recommended)
**Navigation Pillars**
1. **Launchpad** – Default route replacing `/portfolio` with a three-panel overview: Net Worth Stack (aggregated holdings + external connections), Risk Pulse (beta/volatility/drawdown + factor drift badges from `RiskMetricsLocal`), and Action Queue (AI-recommended tasks and alerts). A persistent "Ask SigmaSightAI" bar prompts contextual questions.
2. **Allocations & Research** – Unify public, private, options, and watchlists with tabs, overlaying AI briefs (earnings catalysts, valuation flags) sourced via SigmaSightAI container prompts.
3. **Risk Studio** – Dedicated diagnostics room featuring factor mosaics, scenario timelines, hedging playbooks, and a warning panel sourced from `RiskMetricsService` metadata.
4. **Playbooks & Automation** – Tag management, rule builders, and rebalance templates arranged as cards (Manual Tagging, Smart Rules, Automations). Progress dials show tag coverage and automation adoption.
5. **SigmaSightAI Copilot** – Full-screen chat for multi-step reasoning, saved threads, and shared insights. Launchpad quick actions deep link here with seeded prompts.
6. **Account & Integrations** – Connections, notification preferences, audit log, and risk data quality center.

**Why it wins**: Mirrors aggregator clarity, keeps risk top-center, and frames AI as an embedded analyst.

## Option 2 – Risk Playbook Workbench
**Navigation Pillars**
1. **Today’s Briefing** – Timeline of performance + alerts + AI summary ("Here’s what moved").
2. **Risk Lab** – Expand Launchpad’s Risk Pulse into interactive charts (factor trends, sensitivity sliders, stress tests) with quick hedging recipes.
3. **Opportunities Board** – Merges research and automation: long/short ideas, liquidity needs, tax-loss candidates, all filterable by tags.
4. **Workflow Builder** – Kanban view for tagging, rebalancing, reporting tasks. Each card has "delegate to SigmaSightAI" button.
5. **Collaborate** – Chat plus shared notes, preparing for advisor/client sharing.

**Why it wins**: Emphasizes playbooks and repeatable workflows—ideal for power users managing multiple portfolios.

## Option 3 – AI-First Conversational Shell
**Navigation Pillars**
1. **Conversational Home** – Opening screen is a chat-first interface with snapshot cards pinned above the thread (net worth, risk alerts, cash runway). Users interact primarily via SigmaSightAI, with quick commands pinned below.
2. **Data Rooms** – Contextual drawers (Portfolio, Research, Risk, Automations) slide in as SigmaSightAI references data, letting users inspect details without leaving the conversation.
3. **Builder Mode** – Low-code automation studio where the agent scaffolds scripts/rules when users describe desired workflows.
4. **Settings & Trust Center** – Manage integrations, data permissions, audit trails.

**Why it wins**: Differentiates SigmaSight as an AI-native command center but requires highest behavior change.

## Cross-Option Page Modules
Regardless of option, each page should feature:
- **Summary ribbons** showing status (e.g., "Risk metrics current as of yesterday"), warning badges for sparse data, and CTA to refresh pipeline.
- **Embedded prompts** calling SigmaSightAI with context (portfolio ID, selected tags, warning codes). The SigmaSightAI container already exposes hooks for injecting system prompts alongside user input; use it to pass module metadata.
- **Insight logging** storing AI recommendations with timestamps in Account & Integrations for auditability.

## Differentiators to Spotlight
1. **RiskMetricsLocal-backed analytics** – Local risk pipeline means lower latency and deterministic results, enabling responsive dashboards and scenario toggles.
2. **Tag-centric organization** – Drag-and-drop tagging + rule builders unify asset classes, making SigmaSight feel more flexible than broker dashboards.
3. **AI concierge** – SigmaSightAI container provides reusable actions (summaries, playbooks, explanations) and should be marketed as a digital co-pilot embedded in every surface.

## Implementation Next Steps
1. **Select preferred option** – Run stakeholder workshop; we recommend Option 1 for balance of familiarity and differentiation.
2. **Prototype Launchpad** – Design aggregator-style overview with SigmaSightAI prompt bar and risk badges (beta, volatility, drawdown, warning tags).
3. **Instrument SigmaSightAI hooks** – Standardize a utility for sending context payloads (portfolioId, activePage, warnings) into the container before invoking the assistant.
4. **Refine navigation component** – Update `NavigationDropdown` labels and grouping to match chosen option; add quick actions that launch SigmaSightAI with seeded prompts.
5. **Audit data coverage** – Ensure `RiskMetricsService` outputs include UI-friendly metadata (lookback windows, data freshness) so Launchpad and Risk Studio show trustworthy badges.
6. **Plan phased rollout** – Use feature flags to ship Launchpad modules first, then embed SigmaSightAI entry points across Research, Risk, and Playbooks as we validate usage.
