# ChatGPT‑like Wrapper App (Reasoning + Browsing) — Build Notes for Coding Agent

This document is a practical implementation brief for building an application that “feels like ChatGPT” while using the OpenAI API directly.

Key themes:
- Use **the same chat-alias model** ChatGPT uses (or close equivalents).
- Persist **conversation state** (so it doesn’t feel forgetful).
- Expose **reasoning depth** + **verbosity** controls.
- Enable **tools** (web browsing, files, code execution) and surface citations.
- Make the **UX** feel like ChatGPT (streaming, markdown, regenerate, etc.).

---

## 1) Default model choice

### Everyday chat default
Use:
- `model = "gpt-5.2-chat-latest"`

Rationale: this is the “ChatGPT-like” alias intended for everyday chat behavior.

### Optional: routing for harder reasoning
If you want “better reasoning” than the chat-default, consider routing some prompts to:
- `gpt-5.2-pro` for deep reasoning tasks (tradeoff: higher cost/latency)
- `gpt-5.2` when you want code execution (Code Interpreter) + strong reasoning

(Your router can be simple: if the user asks for multi-step planning / synthesis / investment thesis → pro; if they ask for calculations/analysis → gpt-5.2 with code_interpreter; else → chat-latest.)

---

## 2) Persist conversation state (this is critical)

### Use Conversations API + Responses API
Persist state by creating a durable conversation object once per user/session and reusing its ID.

High-level flow:
1. Create a conversation: `conversation = client.conversations.create()`
2. For each turn, call `client.responses.create(...)` and pass `conversation=conversation.id`
3. Store `conversation.id` in your DB keyed by user/session.

This prevents the “stateless chatbot” feeling.

---

## 3) Reasoning depth controls (`reasoning.effort`)

The model can trade speed/cost vs depth by adjusting:

```json
"reasoning": { "effort": "none" | "low" | "medium" | "high" | "xhigh" }
```

Suggested defaults:
- Default (fast): `reasoning.effort = "none"`
- Upgrade for “hard questions”: `reasoning.effort = "medium"` or `"high"`
- For the deepest reasoning paths (when latency is acceptable): `"xhigh"`

Practical pattern:
- Implement a UI toggle (e.g., “Fast / Balanced / Deep”).
- Or auto-escalate: if the user asks for “deep dive”, “investment thesis”, “compare scenarios”, “root cause analysis”, etc.

---

## 4) Output verbosity controls (`text.verbosity`)

Control how expansive responses feel:

```json
"text": { "verbosity": "low" | "medium" | "high" }
```

Recommended default:
- `text.verbosity = "medium"`

Why it matters:
- If you default to `"low"`, users often perceive the model as “weaker” even if it’s equally correct—just shorter.

---

## 5) Output length caps (`max_output_tokens`)

Use `max_output_tokens` to cap response length (cost control + prevents runaway).

Suggested defaults:
- Chat: 800–1500
- “Deep analysis mode”: 2000–4000 (or more, depending on your use case)

Also consider:
- A “continue” button that sends a follow-up prompt (“continue”) if users want more.

---

## 6) Tools: what to enable to match ChatGPT

ChatGPT is not “just the model.” The *product* feels smart because it can use tools.

### Built-in tools (OpenAI-hosted)
Enable these when relevant:

- **`web_search`**: current events, factual freshness, citations
- **`file_search`**: “chat with your docs”
- **`code_interpreter`**: math, data transforms, spreadsheets, charts
- **computer use / remote MCP** (optional): agentic workflows (depends on product needs)

### Custom tools (your app)
Anything domain-specific (e.g., live market data, internal systems, CRM, etc.) should be implemented as your own tool/function and exposed via tool calling.

Example (finance):
- `get_quote(ticker)`
- `get_candles(ticker, interval, start, end)`
- `get_news(ticker, since, limit)`
- `get_events(ticker)`
- `get_fundamentals(ticker)`

Important note:
- These *stock tools are not “built into ChatGPT” as named functions*. You either:
  - implement them yourself (and integrate a data provider), or
  - rely on web_search for news + some pricing info (not recommended for “live quote accuracy”).

---

## 7) Web browsing with `web_search` (and citations)

To replicate “ChatGPT browsing,” enable the built-in web search tool rather than scraping.

Minimum example:

```python
response = client.responses.create(
  model="gpt-5.2",
  tools=[{"type": "web_search"}],
  input="What happened with Apple today?"
)
print(response.output_text)
```

UI requirements:
- Render citations as clickable links (don’t hide them).
- Show a “Sources” section if you’re building for research/investing workflows.

---

## 8) Streaming tokens (ChatGPT-like UX)

Streaming makes the assistant feel responsive and “alive.”

Use:
- `stream: true`
- Server-Sent Events (SSE) in your client.

Your UI should:
- stream partial text as it arrives
- handle tool call events (if streaming tool use)
- show a “stop generating” button

---

## 9) Minimum Python skeleton (non-production)

```python
from openai import OpenAI
client = OpenAI()

# Create a durable conversation once per user/session
conv = client.conversations.create()

def chat(user_text: str) -> str:
    resp = client.responses.create(
        model="gpt-5.2-chat-latest",
        conversation=conv.id,
        input=[{"role": "user", "content": user_text}],
        reasoning={"effort": "none"},        # bump to medium/high for harder tasks
        text={"verbosity": "medium"},        # set "high" for more expansive responses
        max_output_tokens=1200,              # tune based on your cost/UX needs
        # tools=[{"type": "web_search"}],    # enable when needed
        # stream=True,                       # enable for streaming UX
    )
    return resp.output_text
```

---

## 10) Implementation checklist (what engineering should actually do)

**State**
- [ ] DB table for `user_id → conversation_id`
- [ ] Rotate / expire conversations if desired (privacy + storage controls)

**Controls**
- [ ] UI/flags for reasoning depth: none ↔ medium/high/xhigh
- [ ] UI/flags for verbosity: low/medium/high
- [ ] Token cap per mode

**Tools**
- [ ] Add `web_search` for freshness + citations
- [ ] Add `file_search` if you have document workflows
- [ ] Add `code_interpreter` if you do analytics / spreadsheets
- [ ] Build domain tools (e.g., stock feed) via function calling

**UX**
- [ ] Streaming via SSE
- [ ] Markdown rendering (code blocks, tables)
- [ ] Copy buttons for code and answers
- [ ] Regenerate / edit last message / continue
- [ ] Visible citations and sources

**Reliability**
- [ ] Timestamp & source of market data
- [ ] Guardrails: don’t hallucinate tickers; validate symbol inputs
- [ ] Logging of tool calls + outcomes for debugging

---

## 11) Official doc references (for the coding agent)

```text
Models: GPT‑5.2 Chat alias (gpt-5.2-chat-latest)
https://platform.openai.com/docs/models/gpt-5.2-chat-latest

Conversation state guide (Conversations API + Responses API)
https://platform.openai.com/docs/guides/conversation-state

GPT‑5.2 controls: reasoning.effort, text.verbosity, max_output_tokens
https://platform.openai.com/docs/guides/latest-model

Responses API reference (streaming, parameters, etc.)
https://platform.openai.com/docs/api-reference/responses

Responses API streaming events
https://platform.openai.com/docs/api-reference/responses-streaming
```
