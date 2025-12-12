# SigmaSight Agent – Backend Guidelines (FastAPI + Responses API)

This document explains how to work on **backend AI functionality** in `/backend` without breaking APIs or data contracts.

Canonical references:

- `/AgentCoPilot/SIGMASIGHT_API_DB_SUMMARY.md`
- `/backend/app/api/v1/*.py` – routers
- `/backend/app/schemas/*.py` – Pydantic schemas
- `/backend/app/models/*.py` – ORM models
- `/backend/app/agent/**/*.py` – agent, tools, and AI runtime

---

## 1. FastAPI & Data Access Rules

1. **Extend existing routers.**  
   - Register new endpoints in `app/api/v1/router.py` or existing router modules.  
   - Do not create a new FastAPI application.

2. **Use existing data access patterns.**  
   - Follow the project’s repository/service style and SQLAlchemy usage.  
   - Prefer reusing functions that already implement analytics or data fetches.

3. **No silent schema changes.**  
   - Do not alter DB columns, enum values, or response shapes unless the task explicitly requires it.  
   - When schema changes are requested:
     - create an Alembic migration,
     - update Pydantic schemas,
     - update `/AgentCoPilot/SIGMASIGHT_API_DB_SUMMARY.md`.

---

## 2. AI Runtime – OpenAI Responses API Only

SigmaSight uses **OpenAI Responses API** for AI reasoning and streaming.

### 2.1 Forbidden

- Do **not** use:
  - `openai.ChatCompletion.create`
  - `/v1/chat/completions`
  - Legacy Anthropic chat APIs in new code

### 2.2 Typical Responses Pattern (Conceptual)

Real code may differ, but the flow is:

```python
messages = [...]  # system + context + user messages

response_stream = responses_client.create(
    model="gpt-5-mini",         # or "gpt-5.1" for heavy tasks
    input=messages,
    tools=tools,                # from tool_registry
    stream=True,
    metadata={
        "user_id": user_id,
        "conversation_id": str(conversation_id),
        "page": ui_context.get("page"),
        "portfolio_id": ui_context.get("portfolio_id"),
    },
)
```

You must:

- Listen for function/tool-calling events from Responses.
- Dispatch to `tool_registry` / `handlers.py`.
- Send tool results back via Responses (e.g., using `previous_response_id` or follow-up calls).
- Map Responses text deltas to SSE events returned by FastAPI.

Always follow the existing `/chat/send` or `/insights/generate` implementation as a baseline.

---

## 3. Tool Registry & Analytics

Tools are the **official bridge** between the model and analytics/data.

**Key files (under `/backend/app/agent`):**

- `tools/tool_registry.py` – maps tool names to implementations and schemas
- `tools/handlers.py` – actual implementations that hit DB/services
- `docs/TOOL_REFERENCE.md` – textual description of tool behaviors and shapes

### 3.1 Rules for Tools

1. **Prefer tools over ad hoc analytics code.**  
   - If a tool already exists for “portfolio overview”, “factor exposures”, “stress test”, etc., use it.

2. **Do not change tool signatures without updating everything.**  
   - For any change to `name`, `input_schema`, or output structure:
     - update `TOOL_REFERENCE.md`,
     - update `handlers.py`,
     - update all agent code that constructs or consumes that tool.

3. **Add new tools only where needed.**  
   - New tools should be narrow, composable, and typically call existing endpoints or internal services.  
   - Document them thoroughly.

---

## 4. Key Endpoint Categories for AI Use

The full list is in `/AgentCoPilot/SIGMASIGHT_API_DB_SUMMARY.md`. Key groups for AI behavior include:

### 4.1 Data & Portfolio

- `GET /api/v1/data/portfolios`
- `GET /api/v1/data/portfolio/{id}/complete`
- `GET /api/v1/data/portfolio/{id}/snapshot`
- `GET /api/v1/data/portfolio/{id}/data-quality`
- `GET /api/v1/data/positions/details`
- `GET /api/v1/data/prices/historical/{id}`
- `GET /api/v1/data/prices/quotes`
- `GET /api/v1/data/factors/etf-prices`
- `GET /api/v1/data/company-profiles`

### 4.2 Portfolio Analytics

- `GET /api/v1/analytics/portfolio/{id}/overview`
- `GET /api/v1/analytics/portfolio/{id}/factor-exposures`
- `GET /api/v1/analytics/portfolio/{id}/positions/factor-exposures`
- `GET /api/v1/analytics/portfolio/{id}/sector-exposure`
- `GET /api/v1/analytics/portfolio/{id}/concentration`
- `GET /api/v1/analytics/portfolio/{id}/volatility`
- `GET /api/v1/analytics/portfolio/{id}/stress-test`
- `GET /api/v1/analytics/portfolio/{id}/correlation-matrix`
- `GET /api/v1/analytics/portfolio/{id}/beta-comparison`
- `GET /api/v1/analytics/portfolio/{id}/beta-calculated-90d`
- `GET /api/v1/analytics/portfolio/{id}/beta-provider-1y`

Use these or their internal counterparts instead of recomputing metrics from raw tables unless a task explicitly demands new analytics.

### 4.3 Fundamentals & Profiles

- `GET /api/v1/fundamentals/{symbol}/income-statement`
- `GET /api/v1/fundamentals/{symbol}/balance-sheet`
- `GET /api/v1/fundamentals/{symbol}/cash-flow`
- `GET /api/v1/fundamentals/{symbol}/analyst-estimates`
- `GET /api/v1/data/company-profiles`

Rely on the documented fields; do not invent new keys in these responses.

### 4.4 Insights & Chat

- Insights:
  - `POST /api/v1/insights/generate`
  - `GET /api/v1/insights/portfolio/{portfolio_id}`
  - `GET /api/v1/insights/{insight_id}`
  - `PATCH /api/v1/insights/{insight_id}`
  - `POST /api/v1/insights/{insight_id}/feedback`

- Chat:
  - `POST /api/v1/chat/conversations`
  - `GET /api/v1/chat/conversations`
  - `GET /api/v1/chat/conversations/{id}`
  - `PUT /api/v1/chat/conversations/{id}/mode`
  - `DELETE /api/v1/chat/conversations/{id}`
  - `POST /api/v1/chat/send` (SSE)

Existing tables:

- `AI_INSIGHTS`, `AI_INSIGHT_TEMPLATES`
- `agent.CONVERSATIONS`, `agent.MESSAGES`

Use these as **canonical** for insights and chat history.

---

## 5. AI Infra Tables

When implementing RAG or learning features, prefer AI-only tables such as:

- `ai_kb_documents` – for KB docs & embeddings
- `ai_memories` – for user/tenant/global rules
- `ai_feedback` – for per-message ratings

See `SIGMASIGHT_AGENT_CONTEXT_AND_LEARNING.md` for suggested schemas and rules.

Keep AI infra separate from core domain tables.
