# SigmaSight Agent – Frontend Guidelines (Next.js 14 + SSE)

This document explains how to work on AI-related frontend code in `/frontend`.

Canonical references:

- `/AgentCoPilot/SIGMASIGHT_API_DB_SUMMARY.md`
- `/frontend/src/services/*.ts`
- `/frontend/src/hooks/*.ts`
- `/frontend/src/components/**/*.tsx`
- `/frontend/src/stores/*.ts`

---

## 1. Service-First Architecture

1. **Always use the service layer.**  
   - Do not call `fetch()` directly to FastAPI from components.  
   - Use services such as:
     - `analyticsApi.ts`
     - `portfolioApi.ts`
     - `fundamentalsApi.ts`
     - `positionApiService.ts`
     - `companyProfilesApi.ts`
     - `tagsApi.ts`
     - `chatService.ts` and `chatAuthService.ts`
     - `insightsApi.ts`

2. **Keep AI-specific wiring in services + hooks.**  
   - SSE setup, message streaming, and auth headers should be implemented in service modules (`chatService`, `claudeInsightsService`, etc.) and hooks, not inside components.

---

## 2. Existing AI UI Surfaces

### 2.1 Global Chat

- Services:
  - `src/services/chatService.ts` – conversations + `/chat/send` SSE
  - `src/services/chatAuthService.ts` – auth helpers

- Components:
  - Chat UI components that show conversation history and live streaming text.

### 2.2 SigmaSight AI Page (`/sigmasight-ai`)

- Container:
  - `app/sigmasight-ai/page.tsx` → `SigmaSightAIContainer.tsx`

- Left column (daily insights):
  - Hook: `src/hooks/useAIInsights.ts`
  - Service: `src/services/insightsApi.ts`
  - Display: `src/components/command-center/AIInsightsRow.tsx`

- Right column (chat):
  - Component: `src/components/claude-insights/ClaudeChatInterface.tsx`
  - Store: `src/stores/claudeInsightsStore.ts`
  - Service (SSE): `src/services/claudeInsightsService.ts`

When adding AI to new pages, follow these patterns rather than inventing new ones.

---

## 3. SSE Streaming Contract

The SSE stream for chat (and similar AI endpoints) emits events like:

```txt
event: start
data: {"conversation_id": "...", "run_id": "..."}

event: message
data: {"delta": "partial text ..."}

event: tool_call
data: {"tool_name": "get_portfolio_complete", "tool_args": {...}}

event: tool_result
data: {"tool_call_id": "...", "result": {...}}

event: done
data: {"final_text": "...", "tool_calls_count": 3}

event: error
data: {"message": "error details"}
```

Rules:

1. **Do not rename existing events unless all consumers are updated.**
2. **Streaming state lives in Zustand stores.**
   - For example, `claudeInsightsStore` holds:
     - `conversationId`
     - `messages`
     - `isStreaming`
     - `streamingText`
     - `currentRunId`
     - `error`
3. **Components are consumers, not SSE parsers.**
   - SSE parsing, `EventSource`/`fetch` streaming, and event mapping should reside in service modules.

---

## 4. UI Context Pattern

When embedding the agent in a page, define a **UI context object** in that page and pass it to the chat service/hook.

Example (portfolio overview page):

```ts
const uiContext = {
  page: "portfolio-overview",
  route: "/portfolios/[id]",
  portfolioId: portfolio.id,
  selection: {
    symbol: selectedSymbol ?? null,
  },
};
```

Then use a shared hook like `useSigmaAgent(uiContext)` that:

- wraps the relevant Zustand store,
- calls the shared chat service (e.g. `/api/v1/chat/send` proxy),
- attaches `uiContext` to the request body.

This allows the backend to tailor tools, RAG, and rules per page without hard-coding page behaviors.

---

## 5. Type Safety & Data Contracts

1. **Follow TS interfaces for API responses.**  
   - Types in `src/services` (or dedicated `types.ts` files) should match backend Pydantic schemas.

2. **Do not use fields that don’t exist in types.**  
   - If TS types don’t define a field, and it is not documented in backend schemas, do not use it.

3. **Handle optional fields safely.**  
   - Use optional chaining and sensible defaults in UI.

4. **No speculative fields in request payloads.**  
   - POST/PUT/PATCH bodies must only contain fields documented for the target endpoint.

---

## 6. Auth for AI Endpoints

- All AI endpoints use JWT auth via `Authorization: Bearer <token>`.  
- Use existing helpers in `authManager.ts` and `chatAuthService.ts` to obtain tokens.  
- Do not implement new auth flows for AI endpoints without a clear, documented reason.
