# SigmaSight Application Experience POV

## Executive Summary
- Individual investors value a fast path to understanding "Am I on track? Where am I exposed? What should I do next?"—competitive products such as Personal Capital, Fidelity Portfolio Analysis, and Kubera lead with a consolidated health score, contextual insights, and clear calls to action. SigmaSight can differentiate by pairing institutional-grade risk analytics with human-readable storytelling, automation, and an AI copilot that understands the portfolio's structure.
- The current application already surfaces a multi-asset dashboard, in-depth public equity research, tagging workflows, and an AI assistant. Leaning into these strengths while clarifying navigation, bundling workflows around core jobs, and amplifying proactive guidance will deliver a cohesive, high-value experience.

## Current Experience Snapshot
### Navigation & Page Framework
- The authenticated navigation dropdown centers on six destinations—Dashboard, Public Positions, Private Positions, Organize, AI Chat, and Settings—presented within a sticky header once a user is logged in.【F:frontend/src/components/navigation/NavigationDropdown.tsx†L31-L126】【F:frontend/app/layout.tsx†L5-L34】
- Authenticated routes currently render through client-side containers that respect theme preferences, providing consistent theming scaffolding across pages.【F:frontend/app/portfolio/page.tsx†L1-L107】【F:frontend/src/containers/PublicPositionsContainer.tsx†L2-L102】

### Portfolio Overview Dashboard
- The dashboard orchestrates portfolio loading with `usePortfolioData`, rendering a header, summary metrics, factor exposure cards, filters, and segmented position lists once data resolves.【F:frontend/app/portfolio/page.tsx†L20-L101】【F:frontend/src/hooks/usePortfolioData.ts†L32-L155】
- Summary metrics are displayed as responsive cards with sentiment-aware coloring, supporting quick scanning of performance, risk, or exposure KPIs.【F:frontend/src/components/portfolio/PortfolioMetrics.tsx†L19-L62】
- Factor exposure chips translate betas and dollar exposures into sortable cards, hinting at SigmaSight's quantitative depth.【F:frontend/src/components/portfolio/FactorExposureCards.tsx†L12-L148】

### Research & Organization Workflows
- Public Positions offers analyst consensus, return expectations, and filtering/sorting for long and short books, aligning with research workflows.【F:frontend/src/containers/PublicPositionsContainer.tsx†L8-L101】【F:frontend/src/components/positions/EnhancedPositionsSection.tsx†L1-L149】
- The Organize workspace combines drag-and-drop tagging, multi-asset segmentation (public, private, options), and tag management in a single page, already delivering a differentiated organizing mechanic.【F:frontend/src/containers/OrganizeContainer.tsx†L13-L517】

### AI Copilot
- The AI Chat page anchors SigmaSight's conversational assistant with portfolio-aware context, status chips, and streaming conversation pane, signaling a powerful advisor experience.【F:frontend/src/containers/AIChatContainer.tsx†L11-L108】

## Competitive Landscape Insights
- **Aggregators (Personal Capital, Kubera, Empower)** lead with a holistic balance sheet summary, goal tracking, and alerts for drifts or cash flow anomalies. They emphasize "one-glance" clarity plus dig-deeper modules.
- **Brokerage platforms (Fidelity, Schwab, Vanguard)** highlight daily P&L, sector exposures, and alert banners; risk tools are often hidden under analytics tabs, making advanced insights harder to find.
- **Institutional risk suites (BlackRock Aladdin, MSCI BarraOne)** surface factor decomposition, stress testing, and scenario analysis but are dense and require training; they lack human-friendly guidance.
- **Robo-advisors (Betterment, Wealthfront)** differentiate with automated actions, nudges, and simulation tools (tax-loss harvesting, goal projections) that convert insights into recommendations.

Key takeaways: combine the consumer-grade clarity of aggregators, the automation of robo-advisors, and the analytics depth of institutional platforms, while keeping SigmaSight's AI fabric front-and-center.

## Guiding Experience Principles
1. **Jobs-to-be-done alignment** – Organize navigation around user jobs: Understand portfolio health, Diagnose risk, Act on insights, and Collaborate with the AI copilot.
2. **Progressive depth** – Lead with digestible summaries, then let users drill into positions, factors, or scenarios without losing context.
3. **Actionable storytelling** – Every analytics surface should answer "What changed? Why it matters? What should I do?" with copy, alerts, or AI suggestions.
4. **Automation-first** – Promote automations (tag rules, rebalance suggestions, hedging playbooks) so the app feels like an always-on analyst.
5. **AI as navigator** – Treat the AI assistant as a shortcut to any task: triage errors, summarize risk, tag positions, or launch simulations.

## Proposed App Organization
### 1. Overview Hub (Dashboard)
- Keep `/portfolio` as the primary landing page but elevate it into an "Overview Hub" with three tiles: **Health Score**, **Risk Pulse**, and **Opportunities Queue**. Health Score aggregates drawdown risk, diversification, and goal progress; Risk Pulse surfaces factor spikes from `FactorExposureCards`; Opportunities Queue lists AI-curated actions (rebalances, hedges, data quality fixes) with deep links to Organize or Research.【F:frontend/app/portfolio/page.tsx†L62-L101】【F:frontend/src/components/portfolio/FactorExposureCards.tsx†L12-L148】
- Add an always-visible AI prompt bar summarizing "Ask SigmaSight to..." suggestions that open the chat with pre-filled intents, reusing the existing assistant pipeline.【F:frontend/src/containers/AIChatContainer.tsx†L47-L105】

### 2. Research & Discovery
- Merge Public and (future) Private Positions into a **Research** workspace with tabs for Public, Private, Options, and Watchlists. Reuse the EnhancedPositionsSection filters to maintain continuity while enabling cross-segment comparisons.【F:frontend/src/containers/PublicPositionsContainer.tsx†L53-L101】【F:frontend/src/components/positions/EnhancedPositionsSection.tsx†L18-L149】
- Introduce AI-generated briefs (earnings catalysts, sentiment shifts) at the top of each tab to contrast SigmaSight with static broker research.

### 3. Portfolio Organization & Playbooks
- Preserve the Organize page as a dedicated **Playbooks** area that combines tagging, smart groups, and automation setup. The existing drag-and-drop tagging UX becomes the first tab (**Manual Tagging**). Additional tabs can host rule builders (e.g., auto-tag by sector) and rebalancing templates that output to the AI for execution.【F:frontend/src/containers/OrganizeContainer.tsx†L161-L517】
- Surface "tag coverage" metrics (percentage of positions tagged, untagged exposure) next to the TagList header to reinforce progress.

### 4. Risk Diagnostics
- Carve out a new **Risk** section focusing on factor decomposition, scenario analysis, and stress tests. Begin by elevating the existing Factor Exposure cards into a richer mosaic with trend charts and hedging ideas that link back to Organize tags or Research positions.【F:frontend/src/components/portfolio/FactorExposureCards.tsx†L12-L148】
- Layer in saved scenarios (rate shock, sector rotation) and simulation outputs once backend endpoints mature.

### 5. AI Copilot Everywhere
- Maintain `/ai-chat` as the full-screen assistant, but embed mini chat widgets in every primary surface so users can ask context-aware questions without losing place. The AI page can host conversation presets ("Assess diversification", "Draft quarterly letter", "Explain today's factor moves"), leveraging the current layout's header & callouts.【F:frontend/src/containers/AIChatContainer.tsx†L58-L108】

### 6. Settings & Integrations
- Expand Settings into an **Account & Integrations** area: custody connections, notification preferences, automation toggles, and audit logs. Highlight data quality alerts from `usePortfolioData` error handling to encourage proactive fixes.【F:frontend/src/hooks/usePortfolioData.ts†L38-L123】

## Differentiators to Spotlight
1. **Context-aware AI Analyst** – Unlike static research portals, SigmaSight's assistant references real-time portfolio IDs, names, and factor context for tailored guidance.【F:frontend/src/containers/AIChatContainer.tsx†L15-L105】
2. **Tag-centric organization across asset classes** – Drag-and-drop tagging spanning public, private, and options positions makes categorization effortless compared to spreadsheets or manual labels in broker apps.【F:frontend/src/containers/OrganizeContainer.tsx†L161-L517】
3. **Institutional-grade factor analytics in a consumer UX** – Factor exposure chips, summary metrics, and segmented position lists translate complex risk math into intuitive visuals.【F:frontend/app/portfolio/page.tsx†L62-L101】【F:frontend/src/components/portfolio/PortfolioMetrics.tsx†L19-L62】【F:frontend/src/components/portfolio/FactorExposureCards.tsx†L12-L148】

## Implementation Next Steps
1. **Refine navigation labels and grouping** – Update the dropdown to mirror the proposed pillars (Overview, Research, Playbooks, Risk, Copilot, Settings) and add secondary quick links for upcoming automations.【F:frontend/src/components/navigation/NavigationDropdown.tsx†L31-L126】
2. **Design Overview Hub prototypes** – Create lo-fi mocks showing Health Score, Risk Pulse, and Opportunities Queue modules stacked above existing metrics and factor cards to validate layout and copy needs.【F:frontend/app/portfolio/page.tsx†L62-L101】
3. **Inventory AI entry points** – Map where inline chat launchers should live (metrics cards, tag lists, research tables) and define the context payload each should send to the assistant.【F:frontend/src/components/portfolio/PortfolioMetrics.tsx†L27-L58】【F:frontend/src/containers/OrganizeContainer.tsx†L201-L517】
4. **Prioritize automation concepts** – Align with backend on feasibility for rule-based tagging, risk alerts, and hedging playbooks so UI affordances ship alongside actionable capabilities.【F:frontend/src/hooks/usePortfolioData.ts†L38-L155】

