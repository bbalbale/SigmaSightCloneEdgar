# SigmaSight Agent – Task Workflow and Quality Checklist

This document defines *how* you should approach coding tasks in the SigmaSight repo (`/backend`, `/frontend`, `/AgentCoPilot`).

---

## 1. Task Workflow

### Step 1 – Understand the Task

- Read the task description carefully.  
- Identify:
  - affected pages (e.g. `/sigmasight-ai`, portfolio pages),
  - affected endpoints (e.g. `/analytics/portfolio/{id}/overview`, `/chat/send`),
  - affected tools and tables.

### Step 2 – Discover Existing Code & Docs

- Scan relevant directories:
  - `/backend/app/api/v1`
  - `/backend/app/agent`
  - `/backend/app/schemas`, `/backend/app/models`
  - `/frontend/src/services`, `/frontend/src/hooks`, `/frontend/src/components`
  - `/AgentCoPilot/*.md` (including the API/DB summary)

- Reuse patterns from existing implementations:
  - chat SSE,
  - tool calling,
  - analytics fetching,
  - insights generation.

### Step 3 – Plan Changes

Write a short plan (in comments or as a mental checklist), for example:

1. Extend `/backend/app/api/v1/chat.py` to accept `ui_context` in `/chat/send`.
2. Update Responses API wrapper to include page/portfolio info in system prompt.
3. Add `uiContext` argument to frontend chat service and hook.
4. Verify SSE still streams and tools still work.

### Step 4 – Implement

- Apply minimal, focused changes that follow existing style.  
- Use:
  - OpenAI Responses API, not Chat Completions,
  - the tool registry,
  - the service layer on the frontend.

### Step 5 – Verify

- Backend:
  - Types and schemas match existing models.
  - No new or renamed fields on responses unless explicitly required.
  - SSE events (`start`, `message`, `tool_call`, `tool_result`, `done`, `error`) still flow correctly.

- Frontend:
  - TypeScript builds cleanly.
  - New props/fields are consistent with backend contracts.
  - Streaming UI behaves as expected.

### Step 6 – Document

- If behavior or contracts change, update:
  - `/AgentCoPilot/SIGMASIGHT_AGENT_TOOLS_AND_DATA.md` (for tool/data changes),
  - `/AgentCoPilot/SIGMASIGHT_AGENT_BACKEND.md` or `FRONTEND.md` (for new patterns),
  - `/AgentCoPilot/SIGMASIGHT_API_DB_SUMMARY.md` (if endpoints/schemas changed).

---

## 2. Quality Checklist

Before you consider a task complete, verify:

- [ ] I used existing APIs, tools, and patterns where possible.  
- [ ] I did **not** invent new fields on domain tables or API responses.  
- [ ] Any schema changes were explicitly required and include migrations + docs.  
- [ ] AI calls go through OpenAI Responses API, not Chat Completions.  
- [ ] Tool usage matches `TOOL_REFERENCE.md`.  
- [ ] SSE event contract is preserved for chat/insights.  
- [ ] Frontend uses the service layer, not raw `fetch()`.  
- [ ] UI context is passed correctly for new agent integrations.  
- [ ] Relevant `/AgentCoPilot/*.md` docs were updated if I changed behavior or contracts.
