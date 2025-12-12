# SigmaSight Agent – Tools, Data Contracts, and Anti-Hallucination Rules

This document defines how you, the AI coding agent, must interact with SigmaSight’s data, tools, and APIs.

Canonical sources of truth:

- `/AgentCoPilot/SIGMASIGHT_API_DB_SUMMARY.md` – full API & DB summary
- `/backend/app/schemas/*.py` – Pydantic models
- `/backend/app/models/*.py` – ORM models
- `/backend/app/agent/tools/*.py` – tools & registry
- `/backend/app/agent/docs/TOOL_REFERENCE.md` – tool descriptions

---

## 1. Absolute Rules About Data & Fields

1. **Do not invent fields.**  
   You may only use fields that are:
   - present in DB models, OR
   - defined in backend schemas, OR
   - explicitly documented in the API/DB summary or `TOOL_REFERENCE.md`.

2. **Do not silently extend domain models.**  
   Tables such as:
   - `USERS`, `PORTFOLIOS`, `POSITIONS`
   - `PORTFOLIO_SNAPSHOTS`
   - `POSITION_VOLATILITY`, `FACTOR_EXPOSURES`, `POSITION_FACTOR_EXP`
   - `POSITION_MARKET_BETAS`, `POSITION_IR_BETAS`
   - `INCOME_STATEMENTS`, `BALANCE_SHEETS`, `CASH_FLOWS`
   - `COMPANY_PROFILES`
   - `AI_INSIGHTS`, `AI_INSIGHT_TEMPLATES`
   - `agent.CONVERSATIONS`, `agent.MESSAGES`
   are **core domain tables**. Do not change their columns or semantics unless explicitly instructed.

3. **AI infra must be clearly separated.**  
   - New tables like `ai_kb_documents`, `ai_memories`, `ai_feedback` are allowed for RAG and learning.  
   - They should not override or redefine core domain semantics.

4. **No speculative endpoints.**  
   - Use only endpoints listed in `/AgentCoPilot/SIGMASIGHT_API_DB_SUMMARY.md`.  
   - If you need a new endpoint, it must be an explicitly requested change with updated docs.

---

## 2. Tools – Contracts, Not Suggestions

Tools are defined in:

- `backend/app/agent/tools/tool_registry.py`
- `backend/app/agent/tools/handlers.py`
- `backend/app/agent/docs/TOOL_REFERENCE.md`

### 2.1 Using Tools Correctly

1. **Follow `input_schema` exactly.**  
   - When building tool calls in agent code, include only documented fields with correct types.

2. **Trust tool output shapes.**  
   - Use keys that are documented for each tool.  
   - If a field is not in the doc or handler, do not assume it exists.

3. **Prefer tools to raw queries.**  
   - For analytics and portfolio metrics, call tools that wrap analytics endpoints or engines instead of hitting tables yourself.

---

## 3. Core API Groups for the Agent

Full details are in `/AgentCoPilot/SIGMASIGHT_API_DB_SUMMARY.md`. Below is a condensed map of key groups.

### 3.1 Data & Portfolio

- `GET /api/v1/data/portfolios`
- `GET /api/v1/data/portfolio/{id}/complete`
- `GET /api/v1/data/portfolio/{id}/snapshot`
- `GET /api/v1/data/portfolio/{id}/data-quality`
- `GET /api/v1/data/positions/details`
- `GET /api/v1/data/positions/top/{id}`
- `GET /api/v1/data/prices/historical/{id}`
- `GET /api/v1/data/prices/quotes`
- `GET /api/v1/data/factors/etf-prices`
- `GET /api/v1/data/company-profiles`

Use these for raw portfolio & market data.

### 3.2 Portfolio Analytics

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

The agent should rely on these instead of recomputing metrics from raw tables unless explicitly asked.

### 3.3 Aggregate Analytics & Spread Factors

- `GET /api/v1/analytics/overview`
- `GET /api/v1/analytics/breakdown`
- `GET /api/v1/analytics/beta`
- `GET /api/v1/analytics/volatility`
- `GET /api/v1/analytics/factor-exposures`
- `GET /api/v1/analytics/{portfolio_id}/spread-factors`

Use these when reasoning across multiple portfolios.

### 3.4 Fundamentals & Company Profiles

**Fundamentals:**

- `GET /api/v1/fundamentals/{symbol}/income-statement`
- `GET /api/v1/fundamentals/{symbol}/balance-sheet`
- `GET /api/v1/fundamentals/{symbol}/cash-flow`
- `GET /api/v1/fundamentals/{symbol}/analyst-estimates`

These return periodic data with fields documented in `fundamentals.py` and the summary doc.

**Company Profiles:**

- `GET /api/v1/data/company-profiles`  
  Query modes:
  - `symbols` (public data, no ownership check),
  - `position_ids` (ownership required),
  - `portfolio_id` (ownership required).

Do not invent new keys under these responses; use the listed 53+ fields only.

### 3.5 Target Prices & Equity Changes

**Target Prices:**

- `POST /api/v1/target-prices/{portfolio_id}`
- `GET /api/v1/target-prices/{portfolio_id}`
- `GET /api/v1/target-prices/{portfolio_id}/summary`
- `GET /api/v1/target-prices/target/{id}`
- `PUT /api/v1/target-prices/target/{id}`
- `DELETE /api/v1/target-prices/target/{id}`
- `POST /api/v1/target-prices/{portfolio_id}/bulk`
- `PUT /api/v1/target-prices/{portfolio_id}/bulk-update`
- `POST /api/v1/target-prices/{portfolio_id}/import-csv`
- `POST /api/v1/target-prices/{portfolio_id}/export`

Backed by `PORTFOLIO_TARGET_PRICES`.

**Equity Changes:**

- `GET /api/v1/portfolios/{portfolio_id}/equity-changes`
- `POST /api/v1/portfolios/{portfolio_id}/equity-changes`
- `GET /api/v1/portfolios/{portfolio_id}/equity-changes/summary`
- `GET /api/v1/portfolios/{portfolio_id}/equity-changes/export`
- `GET /api/v1/portfolios/{portfolio_id}/equity-changes/{id}`
- `PUT /api/v1/portfolios/{portfolio_id}/equity-changes/{id}`
- `DELETE /api/v1/portfolios/{portfolio_id}/equity-changes/{id}`

Backed by `EQUITY_CHANGES`.

### 3.6 Tags & Position Management

**Position CRUD & helpers:**

- `POST /api/v1/positions`
- `POST /api/v1/positions/bulk`
- `GET /api/v1/positions/{id}`
- `PUT /api/v1/positions/{id}`
- `DELETE /api/v1/positions/{id}`
- `DELETE /api/v1/positions/bulk`
- `POST /api/v1/positions/validate-symbol`
- `GET /api/v1/positions/check-duplicate`
- `GET /api/v1/positions/tags-for-symbol`

**Tagging (preferred path):**

- `POST /api/v1/positions/{id}/tags`
- `DELETE /api/v1/positions/{id}/tags`
- `GET /api/v1/positions/{id}/tags`
- `PATCH /api/v1/positions/{id}/tags`
- `GET /api/v1/tags/{tag_id}/positions`

**Tag Management:**

- `POST /api/v1/tags/`
- `GET /api/v1/tags/`
- `GET /api/v1/tags/{id}`
- `PATCH /api/v1/tags/{id}`
- `POST /api/v1/tags/{id}/archive`
- `POST /api/v1/tags/{id}/restore`
- `POST /api/v1/tags/defaults`

These are backed by `TAGS_V2` and `POSITION_TAGS`. Use them for tagging; do not reintroduce “strategies” endpoints.

### 3.7 Insights & Chat

**Insights:**

- `POST /api/v1/insights/generate`
- `GET /api/v1/insights/portfolio/{portfolio_id}`
- `GET /api/v1/insights/{insight_id}`
- `PATCH /api/v1/insights/{insight_id}`
- `POST /api/v1/insights/{insight_id}/feedback`

Backed by:

- `AI_INSIGHTS`
- `AI_INSIGHT_TEMPLATES`

**Chat:**

- `POST /api/v1/chat/conversations`
- `GET /api/v1/chat/conversations`
- `GET /api/v1/chat/conversations/{id}`
- `PUT /api/v1/chat/conversations/{id}/mode`
- `DELETE /api/v1/chat/conversations/{id}`
- `POST /api/v1/chat/send` (SSE)

Backed by:

- `agent.CONVERSATIONS`
- `agent.MESSAGES`

These are the canonical chat/agent tables and endpoints.

---

## 4. Anti-Hallucination Checklist

Before you finish any change that touches data, confirm:

- [ ] All fields used are defined in DB models, schemas, or docs.  
- [ ] No new keys were added to core domain responses.  
- [ ] I reused existing endpoints/tools wherever possible.  
- [ ] Any new endpoint/tool is documented and doesn’t change existing contracts.  
- [ ] For AI behavior, I used:
  - [ ] OpenAI Responses API  
  - [ ] tool registry  
  - [ ] the SSE event contract used by `/chat/send` and the SigmaSight AI page.
