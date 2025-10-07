# OpenAI ChatKit Migration Plan

## Purpose
- Define the steps required to replace the current OpenAI Responses-based chat integration with OpenAI ChatKit while maintaining service continuity.
- Align backend, frontend, and QA tasks around a shared set of milestones and deliverables.

## Scope
- Applies to the SigmaSight AI chat interaction flow (backend agent modules and frontend chat experience).
- Excludes portfolio analytics APIs that are unrelated to chat.

## Assumptions
- ChatKit access is already provisioned for the SigmaSight OpenAI account.
- No breaking changes are required for portfolio data APIs.
- Existing authentication model (JWT for APIs, HttpOnly cookies for chat streaming) remains in place.

## Workstream Overview
- **Backend Agent**: Replace Responses API calls with ChatKit, update streaming/event handling, and maintain tool invocation parity.
- **Frontend Chat Client**: Adjust SSE parsing, state management, and UI expectations for ChatKit response schema.
- **Testing & Ops**: Expand automated coverage, validate performance, and manage rollout toggles.

## Phase 1 — Discovery & Readiness
- Audit current agent implementation (`backend/app/agent/*`) to document all touchpoints with the Responses API (config, service layer, tool registry, SSE emitters).
- Collect ChatKit technical specifications (request/response schema, streaming protocol, error taxonomy, SDK availability).
- Identify gaps between existing Responses features and ChatKit equivalents (e.g., run metadata, tool invocation shape, token usage limits).
- Confirm required environment variables and secrets; ensure they are compatible with existing config loading patterns.

## Phase 2 — Migration Design
- Draft a delta design memo covering configuration changes, API interface updates, and migration risks; circulate for review.
- Select migration strategy (adapter pattern vs. full replacement) and determine whether dual-path operation is required during rollout.
- Update sequence diagrams and state transitions for chat conversations to reflect ChatKit behavior (especially streaming event flow and retries).
- Define telemetry additions needed to compare ChatKit and Responses performance.

## Phase 3 — Backend Implementation
- Introduce a ChatKit client or adapter within `backend/app/agent/services` that mirrors the existing Responses integration APIs.
- Update request payload construction to match ChatKit message, tool call, and response formats, including any new run/session identifiers.
- Rewrite streaming handlers to process ChatKit event frames (sequence numbers, run IDs, error events) and map them to internal SSE events.
- Ensure tool invocation lifecycle (start/finish events, truncation rules, metadata) remains consistent for downstream consumers.
- Maintain compatibility toggles (e.g., feature flag or configuration switch) so Responses can remain available during testing.

## Phase 4 — Frontend Integration
- Review the chat containers, stores, and utility hooks (e.g., `frontend/src/containers/AiChatContainer`, `streamStore`) for assumptions about SSE payload shape.
- Update client-side streaming parsers to ingest ChatKit event fields (event type, run_id, sequence, retry hints) and surface them to the UI.
- Adjust error handling taxonomy and retry logic to align with ChatKit classifications.
- Verify any analytics or logging endpoints capture the new identifiers emitted by ChatKit.

## Phase 5 — Validation & Testing
- Expand automated tests under `backend/tests/test_agent/` to cover ChatKit request construction, tool dispatch, and error handling.
- Add integration scripts or fixtures that simulate ChatKit streaming responses for both happy path and edge cases (tool errors, truncation, retries).
- Run manual end-to-end tests across demo user portfolios to confirm parity in conversation history, tool usage, and latency.
- Benchmark performance (TTFB, completion time, tokens per second) and compare against historical Responses metrics.

## Phase 6 — Rollout & Monitoring
- Deploy ChatKit support behind a feature flag to staging; run side-by-side sessions comparing Responses vs. ChatKit outputs.
- Instrument logging to capture model, run_id, sequence, token counts, and error codes for post-migration analysis.
- Once parity is confirmed, enable ChatKit in production with a controlled rollout (e.g., percentage-based or per-portfolio allowlist).
- Monitor for regressions, collect user feedback, and keep rollback paths documented until stability is verified.
- After the cooling-off period, retire Responses-specific code paths and update documentation (`CLAUDE.md`, requirements docs) to reflect the new baseline.

## Deliverables
- Discovery findings and delta design memo.
- Updated backend agent modules with ChatKit support and fallback toggles.
- Frontend updates for ChatKit streaming.
- Enhanced automated test suites and manual validation checklist.
- Deployment runbook detailing rollout plan, monitoring, and rollback steps.

## Risks & Mitigations
- **Protocol differences**: Mitigate by implementing an adapter that normalizes ChatKit events before they reach downstream code.
- **Tool compatibility**: Validate all tool definitions against ChatKit schema during testing and fall back to Responses if critical gaps appear.
- **Performance regressions**: Collect metrics during staging rollout and include thresholds in the go/no-go criteria.
- **Operational readiness**: Ensure on-call / support teams are briefed on new telemetry and rollback commands before production cutover.
