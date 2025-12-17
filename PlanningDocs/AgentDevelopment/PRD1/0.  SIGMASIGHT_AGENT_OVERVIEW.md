# SigmaSight AI Coding Agent – Overview

You are an AI coding agent working on **SigmaSight**, a portfolio risk analytics platform.

Your job is to **extend and maintain** SigmaSight’s AI features **without breaking data contracts** or inventing new fields.

Canonical references you must respect:

- `/AgentCoPilot/SIGMASIGHT_API_DB_SUMMARY.md` – API + DB summary 
- `/backend/app/api/v1/*.py` – FastAPI routers
- `/backend/app/schemas/*.py` – Pydantic models
- `/backend/app/models/*.py` – ORM models
- `/backend/app/agent/tools/*.py` – AI tools & registry
- `/frontend/src/services/*.ts` – frontend service layer
- `/frontend/src/components/*.tsx` – React components

---

## 1. Repo Layout (High Level)

- `/backend`  
  FastAPI app, all production APIs, analytics logic, DB models, batch jobs, AI runtime code.

- `/frontend`  
  Next.js 14 app, React components, Zustand stores, API services, AI UI surfaces.

- `/AgentCoPilot`  
  Configuration and docs **for AI coding agents** (you), including:
  - these `.md` instructions,
  - prompt/rule files for tools like Cursor/Windsurf,
  - optional scripts for offline analysis.

Runtime code should live in `/backend` and `/frontend`; `/AgentCoPilot` is for **meta** (instructions, config, analysis).

---

## 2. Global Rules (You MUST Follow These)

1. **Use existing APIs and data models.**  
   - ✅ First, check `/AgentCoPilot/SIGMASIGHT_API_DB_SUMMARY.md`, backend schemas, and models.  
   - ✅ Use only fields, types, and endpoints that actually exist.  
   - ❌ Do **not** invent new JSON properties, DB columns, or endpoints.

2. **No new domain fields unless explicitly requested.**  
   - Domain = portfolios, positions, snapshots, analytics, fundamentals, tags, equity changes, etc.  
   - Any schema change must:
     - be explicitly requested,
     - use Alembic migrations,
     - update Pydantic + TS models,
     - update the API/DB summary doc.

3. **AI infra tables must stay separate.**  
   - You may create AI‑only tables (e.g. `ai_kb_documents`, `ai_memories`) when asked.  
   - Do **not** mix AI logs/metadata into core domain tables unless a task explicitly says so.

4. **Use OpenAI Responses API, not Chat Completions.**  
   - Do **not** use `ChatCompletion` or `/v1/chat/completions`.  
   - Always use the project’s Responses API wrapper(s) used by `/chat/send` and `/insights/generate`.

5. **Respect the tool ecosystem.**  
   - Use tools from `backend/app/agent/tools/tool_registry.py` instead of re-implementing analytics logic.  
   - Do not bypass tools with ad‑hoc SQL when a tool already covers that case.

6. **Small, focused changes > large refactors.**  
   - Extend existing routers, services, and components rather than rewriting them.  
   - Refactors must preserve public API behavior and data contracts.

7. **When in doubt: look it up, don’t make it up.**  
   - If a field/endpoint isn’t defined in code or docs, do **not** assume it exists.

---

## 3. Current AI Surfaces (High Level)

### 3.1 SigmaSight AI Page (`/sigmasight-ai`)

Two-column layout:

- **Left column – Daily Summary Analysis**
  - Uses `useAIInsights` and `insightsApi` in `/frontend`.
  - Backend endpoints:  
    - `POST /api/v1/insights/generate`  
    - `GET /api/v1/insights/portfolio/{portfolio_id}`

- **Right column – Interactive Chat**
  - React: `ClaudeChatInterface`, Zustand store `claudeInsightsStore`.
  - SSE service: `claudeInsightsService` (talks to a backend SSE chat endpoint).
  - Backend: implemented via FastAPI and OpenAI Responses API, emitting SSE events:

    - `start`
    - `message`
    - `tool_call`
    - `tool_result`
    - `done`
    - `error`

### 3.2 Global Chat System

- Backend endpoints:
  - `POST /api/v1/chat/conversations`
  - `GET /api/v1/chat/conversations`
  - `GET /api/v1/chat/conversations/{id}`
  - `PUT /api/v1/chat/conversations/{id}/mode`
  - `DELETE /api/v1/chat/conversations/{id}`
  - `POST /api/v1/chat/send` (SSE streaming)

- Frontend services:
  - `src/services/chatService.ts`
  - `src/services/chatAuthService.ts`

These are the **canonical patterns** for agent chat and streaming.

---

## 4. Task Execution Workflow (Summary)

For any coding task:

1. **Understand the task.**  
   Identify affected pages, endpoints, tools, and tables.

2. **Discover existing code.**  
   Search `/backend` and `/frontend` for similar patterns and reuse them.

3. **Plan small steps.**  
   Write down the minimal set of changes (new route, new hook, new tool, etc.).

4. **Implement.**  
   Use Responses API, existing services, and tools. Don’t touch schemas unless told to.

5. **Verify.**  
   - Types and schemas match existing definitions.  
   - No new fields or endpoints invented.  
   - SSE and tool-calling behavior still work end‑to‑end.

6. **Document.**  
   - If you add endpoints/tools or change behavior, update the relevant `.md` in `/AgentCoPilot`.
