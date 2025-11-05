# SigmaSight AI Experience Refinement

**Date**: November 5, 2025  
**Author**: Codex (analysis for planning only)  
**Scope**: Frontend SigmaSight AI page (`frontend/app/sigmasight-ai/page.tsx`) and related chat/insights experience

---

## Objectives
- Make the SigmaSight AI page feel like a professional daily command center for portfolio managers and self-directed traders.
- Reinforce the “trusted partner” tone from planning docs while keeping the workflow fast and explainable.
- Surface richer analytics without overwhelming the user; guide them toward the next best question or action.

---

## Current Observations
- **Split layout** (Daily Summary left, Chat right) is clean but minimal – little framing, no status about data freshness, and no link between the two panels.
- **Insight generation** is entirely manual and single-threaded (one “Generate” button). Results appear as flat cards without clear follow-up actions or severity guidance beyond the badge.
- **Chat interface** offers raw conversation streaming but lacks onboarding, preset prompts, or the “trusted partner” scaffolding described in `18-CONVERSATIONAL-AI-PARTNER-VISION.md`.
- **Tone calibration** and severity definitions live in docs, not in-product. Users never see what “warning” vs. “critical” means.
- **Inline styling** is pervasive; the visual language leans more “prototype” than “advisor workstation.” Accessibility (contrast, focus states) and responsiveness need another pass.

---

## Recommendations

### 1. Frame the Experience Around a Daily Portfolio Pulse
- Add a hero panel above the grid with: last refresh time, active portfolio name, total value / daily P&L, and a “Today’s focus” sentence sourced from the latest insight.
- Auto-trigger the daily summary on first visit each calendar day (with clear messaging and ability to re-run).
- Include benchmark comparison chips (e.g., `vs S&P 500`, `vs custom benchmark`) to give context, mirroring what PM tools such as BlackRock Aladdin and Morgan Stanley Advisor produce.

### 2. Tie Insights and Chat into One Feedback Loop
- Provide “Send to Chat” and “Ask Follow-up” buttons on each insight card that prefill the chat input with a context-aware prompt.
- Surface a shared activity timeline (“AI Activity Today”) listing generated insights, tool calls, and user questions; let users jump back into any point.
- When Claude completes a tool-heavy response, surface mini-metrics (tool names, key figures) inside the chat bubble with copy-to-clipboard snippets for downstream reporting.

### 3. Level Up Conversation Design (Trusted Partner Tone)
- Embed the severity legend and tone expectations directly in the UI (e.g., collapsible “How we rate severity” panel) so users know why language sounds softer and how to interpret color coding.
- Offer quick-start prompts that reflect partner-style questions: “Ask about liquidity positioning,” “Review concentration vs benchmark,” “Discuss hedging ideas.” Rotate suggestions based on portfolio diagnostics (e.g., concentration risk → surface diversification prompt).
- Add portfolio context headers to each assistant response (`Portfolio: Balanced Individual | Date: Nov 5 | Data window: 180 days`) to reinforce credibility and acknowledge data limitations automatically.

### 4. Expand Analytical Surface Area Without Overload
- Break the left column into tabs or filters (e.g., `All`, `Risk`, `Performance`, `Opportunities`) so power users can zero in on relevant analyses.
- Allow users to pick focus areas when generating insights (liquidity, concentration, factor exposure, stress scenarios). The backend already supports `user_question` and `focus_area`; expose that via UI with descriptive help text.
- Introduce “macro” buttons under the chat composer for high-value tool chains (e.g., `Run Fed Shock Stress Test`, `Compare growth tilt to benchmark`, `Summarize option Greeks`), each sending a structured message to Claude.
- Highlight data limitations inline: if a tool lacks coverage (e.g., missing option Greeks), show a subtle banner linking to data quality checks (`get_portfolio_data_quality`).

### 5. Improve Usability, Trust, and Professional Polish
- Replace inline styles with theme tokens / utility classes from the design system to ensure consistent dark/light behavior, hover/focus states, and spacing.
- Add stateful progress indicators: a top-level banner when insights are generating (“Analyzing 63 positions… step 2/4”), and a chat-side indicator for tool execution progress.
- Strengthen error handling with remediation guidance (“Authentication expired – log in again”, “Backend timeout – retry in 30s”). Log errors to an in-app diagnostics panel for quick debugging during Phase 4.
- Provide compliance-friendly touches: a dismissible disclaimer (“Advisory output is informational; confirm before trading”) and a timestamped export/print option for insight bundles.

### 6. Set Up for Iterative Learning
- Instrument key events (prompt usage, tool combos, dismiss reasons) and show lightweight metrics in an admin/debug view to decide which quick actions resonate.
- Add per-message feedback controls (“Was this helpful? 👍/👎”) that pipe into `insightsApi.submitFeedback` for closed-loop improvements.
- Support multi-portfolio workflows by adding a switcher and reflecting the current selection in both insights and chat context.

---

## Implementation Notes & Sequencing
- **Quick wins**: hero framing, severity legend, quick-start prompts, improved error copy, replace inline button styling with shared components.
- **Near-term iterations**: integrate “Send to Chat” actions, focus-area picker, streaming progress treatment, data limitation badges.
- **Longer-term**: shared activity timeline, macro tool chains, analytics instrumentation dashboard, printable/exportable reports.
- Coordinate conversational tone changes with backend prompt updates outlined in `18-CONVERSATIONAL-AI-PARTNER-VISION.md` and ensure Claude’s responses reference severity definitions embedded in the UI.

---

## Open Questions for Product & Design
- Should daily summaries auto-run for every portfolio, or only for starred/primary ones?
- Do we need distinct personas (e.g., “Long-term allocator” vs “Active trader”) that adjust default prompts, severity thresholds, and recommended macros?
- What compliance/disclaimer language is required before enabling downloadable reports or sharing insights externally?

---

---

## Execution Blueprint: Multi-Model Insight Fabric

### Phase 0: Foundations (1–2 sprints)
- Inventory current Anthropic/OpenAI usage (`anthropic_provider.py`, OpenAI Responses endpoints) and validate token accounting plus rate limits.
- Add a lightweight model registry (JSON/YAML) that records provider, model ID, context window, tool support, latency target, and per-token cost.
- Extend logging middleware so every provider call captures `correlation_id`, latency, token count, tool invocations, and error codes into Postgres/Grafana.
- Prepare Perplexity integration but gate behind a feature flag until privacy/compliance review is complete.

### Phase 1: Deterministic Task Router (≈2 sprints)
- Implement a `ModelRouter` module that inspects request intent (context length, tool depth, external context flag, latency budget, cost ceiling).
- Encode routing rules:
  - **Claude Sonnet 4** for conversational planning and multi-tool synthesis.
  - **OpenAI Responses (GPT-4.1/4o)** for deterministic transforms (JSON normalization, SQL/code generation, tabular summaries).
  - **Perplexity API** only when market context is requested and compliance opt-in is present.
- Return routing metadata with every response so the UI can display provider badges and give visibility into model selection.

### Phase 2: Tool Augmentation Flow (2–3 sprints)
- Refactor tool execution to use a provider-agnostic interface while keeping actual analytics inside `tool_registry`.
- Let Claude produce investigative plans; delegate heavy data reshaping to OpenAI via executor endpoints that return schema-validated JSON.
- Wrap Perplexity as a controlled tool (`get_market_context`) that returns snippet + citation; sanitize results and store citations alongside insight artifacts.
- Ensure all cross-model steps share a `conversation_run_id` for observability and rollback.

### Phase 3: User-Facing Enablement
- Update chat UI to surface provider badges, tool usage summaries, and disclaimers when external research is involved.
- Add macro buttons (e.g., “Run Fed Shock Stress Test”) that bundle intents across models/tools via the router.
- Wire “Send to Chat” actions so insight cards can seed orchestrated conversations without manual copy/paste.

---

## Quality & Governance Plan

### Evaluation Harness
- Build an anonymized portfolio scenario library (balanced, concentrated, illiquid, derivatives-heavy) to replay through each provider on a nightly/weekly schedule.
- Create `scripts/evaluate_models.py` to capture severity assignments, referenced metrics, tone compliance, and latency deltas per model.
- Add tone linting aligned with `18-CONVERSATIONAL-AI-PARTNER-VISION.md` (e.g., prefer “I noticed…” vs prescriptive language) and fail the run if outputs drift.

### Guardrails & Compliance
- Introduce provider-specific sanitizers: redact PII, enforce tool allow-lists, clamp outbound payload size before any external API call.
- Require explicit user opt-in (UI toggle + audit log entry) before enabling Perplexity/web research for a session.
- Apply per-request timeouts and token ceilings; on breach, fall back to internal-only analysis with user-visible notification.
- Persist prompts/responses (with hashed identifiers) for audit and incident response workflows.

### Observability & Feedback
- Extend `insightsApi.submitFeedback` to include `model_used`, `tool_chain`, `latency_ms`, and `content_hash` for downstream analytics.
- Build Grafana/Metabase dashboards covering cost per provider, fallback frequency, SLA adherence, and reported errors.
- Schedule quarterly manual transcript reviews with product + compliance to ensure severity rubric, disclosures, and citations remain accurate.

---

**Next Step**: Align with design/PM on the framing & component updates, then socialize the execution blueprint with backend/ML leads to sequence router, tooling, and governance workstreams before coding begins.
