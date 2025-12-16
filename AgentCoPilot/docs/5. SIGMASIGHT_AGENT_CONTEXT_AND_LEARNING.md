# SigmaSight Agent – Context, RAG, and Learning

This document defines how SigmaSight’s agent should handle **context** and **learning over time** without retraining the base model.

---

## 1. Conceptual Layers

The model is stateless. “Learning” happens in these layers:

1. **UI context** – what the user is looking at/doing right now.
2. **Knowledge base (RAG)** – indexed docs, tool docs, FAQs, domain guides.
3. **Memory & rules** – persistent user/tenant/global behavior and policies.
4. **Logs & feedback** – stored in existing agent/insights tables and optional AI infra tables.

---

## 2. UI Context

Frontend should send a `ui_context` object with each agent request, e.g.:

```json
{
  "page": "portfolio-overview",
  "route": "/portfolios/[id]",
  "portfolio_id": "uuid-here",
  "selection": {
    "symbol": "AAPL"
  }
}
```

Backend usage:

- Include this context in the **system message** to OpenAI Responses API.  
- Use it to:
  - select tools (e.g. volatility tools on risk pages),
  - filter knowledge base docs (scoped to page/feature),
  - load relevant rules/memories.

When adding agent support to new pages, extend `ui_context` rather than hard-coding per-page logic.

---

## 3. Knowledge Base (RAG)

To give the agent up-to-date product/domain knowledge, use a dedicated table like:

```sql
CREATE TABLE ai_kb_documents (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  scope       text NOT NULL,   -- 'global', 'page:portfolio-overview', 'tenant:XYZ', etc.
  title       text NOT NULL,
  content     text NOT NULL,
  metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
  embedding   vector(1536),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
```

**Populate with:**

- Tool docs (`TOOL_REFERENCE.md`)  
- Feature specs / product docs  
- Curated Q&A from real user interactions  
- Domain primers (risk, portfolio theory, methodology)

**Retrieve with:**

- Embedding model (e.g. `text-embedding-3-small`)  
- Filter by `scope` where possible (global + page + tenant)  
- Use only a few top matches per request (e.g. 3–5 documents)

Include retrieved snippets in an assistant message, clearly marked as reference material.

---

## 4. Conversations & Logs (Existing Agent Tables)

Use existing tables for chat logs:

- `agent.CONVERSATIONS`
- `agent.MESSAGES`

They should store:

- `conversation_id`, `user_id`, `portfolio_id`, `mode`, `provider`  
- For each message:
  - `role` (`user`, `assistant`, `tool`),
  - `content`,
  - `tool_calls` (if applicable),
  - `created_at`.

Do **not** create parallel conversation/message tables unless explicitly instructed.  
If you need more metadata (e.g. tags, categories, embeddings), either:

- extend these tables via explicit migrations, **or**
- create AI-only tables keyed by `conversation_id` / `message_id`.

---

## 5. Feedback & Ratings

For insights, existing fields include:

- `AI_INSIGHTS.user_rating`
- `AI_INSIGHTS.user_feedback`

For chat messages, you may introduce a small AI-specific feedback table:

```sql
CREATE TABLE ai_feedback (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id  uuid NOT NULL,      -- references agent.MESSAGES.id
  rating      text NOT NULL,      -- 'up' | 'down'
  edited_text text,
  created_at  timestamptz NOT NULL DEFAULT now()
);
```

Frontend can POST feedback (thumbs up/down, edited response) and backend stores it here.  
Offline jobs can then aggregate this feedback.

---

## 6. Memory & Rules

Use a dedicated table for persistent preferences/constraints:

```sql
CREATE TABLE ai_memories (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid,
  tenant_id   uuid,
  scope       text NOT NULL,        -- 'user', 'tenant', 'global'
  content     text NOT NULL,        -- short rule or fact
  tags        jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at  timestamptz NOT NULL DEFAULT now()
);
```

Examples:

- Global: “Do not provide tax advice; always suggest consulting a tax professional.”  
- Tenant: “Default reporting currency is EUR for this client.”  
- User: “Prefers minimal math and visual explanations.”

At runtime:

- Select memories where:
  - `scope = 'global'`, or
  - `scope = 'tenant' AND tenant_id = current tenant`, or
  - `scope = 'user' AND user_id = current user`.
- Optionally filter by page/feature tags in `tags`.  
- Include them early in the **system message** as “Rules and preferences”.

---

## 7. Context Assembly Pattern

When calling the Responses API, build messages in this order:

1. **System message**  
   - Role: `system`  
   - Content includes:
     - agent role (SigmaSight portfolio risk assistant),
     - UI context (page, route, portfolio_id, selection),
     - relevant global/tenant/user rules from `ai_memories`,
     - key invariant policies.

2. **Conversation summary (optional)**  
   - For long chats, summarize prior messages from `agent.MESSAGES` using a helper model and include it as an assistant message.

3. **Knowledge base snippets**  
   - Assistant message with selected `ai_kb_documents` snippets.

4. **User message**  
   - Latest user input.

Then call Responses API with:

- `input=messages`  
- `tools=` filtered by page/feature (via tool registry)  
- `metadata` including `conversation_id`, `user_id`, `portfolio_id`, `page`

---

## 8. Learning Loop (Offline)

Scheduled/offline jobs can:

1. Read from:
   - `agent.MESSAGES` (chat)
   - `AI_INSIGHTS` (insights usage)
   - `ai_feedback` (if present)

2. Compute embeddings for questions and cluster them by similarity.

3. For high-volume or low-rating clusters:
   - Create/update `ai_kb_documents` entries with better explanations,
   - Add or refine rules in `ai_memories`,
   - Propose or implement new tools where a clear analytic need is unmet.

Constraints:

- Do not change core domain schema unless explicitly asked.  
- Keep heavy analysis out of the runtime path; run it via batch jobs or admin-only tools.
