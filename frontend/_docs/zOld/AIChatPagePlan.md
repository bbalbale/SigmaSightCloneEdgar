# AI Chat Page Plan

## 1. Objectives
- Deliver a dedicated `/ai-chat` page that mirrors the dashboard chat bar UX while exposing a full-width conversation surface underneath.
- Reuse the proven streaming pipeline (`ChatInterface`, chat/stream stores, `useFetchStreaming`, `chatService`, `chatAuthService`) to avoid re-debugging cross-messaging issues.
- Keep authentication, portfolio context, and conversation lifecycle aligned with the existing login + portfolio resolver flow documented in `frontend/app/providers.tsx` and `frontend/_docs/authentication_process.md`.

## 2. Current Chat Architecture Snapshot
- **UI Surface**: `frontend/src/components/chat/ChatInterface.tsx` renders a ShadCN `Sheet` that contains the message list and input; the dashboard header opens this sheet via `openChatSheet()`.
- **Persistent State**: `frontend/src/stores/chatStore.ts` tracks conversations, messages, open state, and mode; it persists to localStorage and syncs conversation IDs with backend events.
- **Streaming State**: `frontend/src/stores/streamStore.ts` manages active runs, buffering, abort controllers, and the message queue that prevents duplicate sends during SSE streams.
- **Transport**: `frontend/src/hooks/useFetchStreaming.ts` orchestrates POST-based SSE streaming through `chatAuthService.authenticatedFetch`, decoding OpenAI Responses payloads and routing events to the stores.
- **Auth Bridge**: `frontend/src/services/chatAuthService.ts` wraps login, cookie refresh, and `authenticatedFetch`; it initializes conversations and keeps JWT + cookie dual auth in sync.
- **Service Layer**: `frontend/src/services/chatService.ts` provides conversation CRUD and non-streaming operations with retry policy logic.
- **Trigger Points**: `PortfolioHeader` uses the shared `ChatInput` (`frontend/src/components/app/ChatInput.tsx`) to capture the message and call `sendChatMessage`, which queues work in the sheet.

## 3. Target UX for `/ai-chat`
- Auto-redirect users into this page when they attempt to open chat elsewhere; this becomes the primary conversation surface.
- Remove the legacy sheet overlay and render a full-width conversation panel embedded in the page.
- Replicate the dashboard chat bar look & feel (title + `ChatInput`) for continuity.
- No ancillary context panes for v1; the conversation pane should stretch the available width and handle all messaging UI.

## 4. Technical Implementation Plan

### Phase 0 - Preconditions & Alignment
1. Confirm `/ai-chat` remains an authenticated route through `useAuth`.
2. Ensure global navigation redirects chat entry points (for example, the dashboard header button) to `/ai-chat` instead of toggling a sheet.
3. Audit `chatAuthService` and the stores to verify conversation initialization still succeeds after removing the sheet component.
4. Capture styling tokens from the dashboard chat bar before we delete the legacy implementation.

### Phase 1 - Page Scaffold
1. Create a thin route at `frontend/app/ai-chat/page.tsx` that simply renders `<AIChatContainer />` (hybrid thin-route pattern).
2. Implement `frontend/src/containers/AIChatContainer.tsx` with `'use client'`, pulling `user` and `portfolioId` from `useAuth()` to personalize headers; keep business logic in the container.
3. Layout: render the chat bar (`ChatInput`) up top and stack the conversation pane below it within a full-width responsive wrapper.
4. Delete or update any sheet triggers (e.g., `openChatSheet`) to push to `/ai-chat`.

### Phase 2 - Conversation Surface Replacement
1. Migrate the core chat UI out of `ChatInterface.tsx` into a new component (e.g., `ChatConversationPane`) that lives in-page rather than inside a sheet.
2. Port the existing message list, streaming indicators, abort controls, and mode selector into the new component while maintaining hooks into `chatStore`, `streamStore`, and `useFetchStreaming`.
3. Update imports across the app to reference the new component and remove the ShadCN `Sheet` dependency.
4. Keep a temporary facade (`ChatInterface` or helper exports) only if other code paths require it; otherwise delete the legacy file once the dashboard is pointed at `/ai-chat`.

### Phase 3 - Hook Chat Bar to Streaming Pipeline
1. Inside `AIChatContainer`, ensure a conversation exists via `useChatStore.getState().currentConversationId`; create one if absent before dispatching messages.
2. Replace `sendChatMessage` usage with a new helper that immediately invokes `streamMessage` for the inline panel while still respecting `useStreamStore.queueMessage` when a run is active.
3. Wire cancel/abort actions directly to `useFetchStreaming.abortStream` so they remain visible within the inline layout.
4. Update navigation or keyboard shortcuts that previously opened the sheet to call `router.push('/ai-chat')` instead.

### Phase 4 - Visual Integration & Responsiveness
1. Wrap the conversation pane in a responsive container (flex column, max width, padding) that matches other authenticated pages.
2. Confirm theme awareness by reusing `ThemeContext` values for background and typography shifts.
3. Remove sheet-specific styles and clean up unused CSS classes.

### Phase 5 - Validation & Hardening
1. Extend existing chat store tests or add a dedicated component smoke test ensuring the inline surface renders with seeded state.
2. Manual QA scenarios:
   - Fresh login -> auto-redirect/visit `/ai-chat` -> send message -> confirm streaming response.
   - Ongoing stream + submit another prompt -> verify queueing behavior.
   - Auth expiry (force logout) -> confirm redirect per `ErrorType.AUTH_EXPIRED` handling.
   - Network drop simulation -> verify retry/cooldown messaging.
3. Confirm localStorage keys remain in sync (no duplicate `conversationId` entries) and that reloading `/ai-chat` restores context.
4. Validate accessibility: focus order from chat bar into conversation window and appropriate aria/announcement for streaming state.

## 5. Data & Messaging Flow Confirmation
1. All chat requests must continue through `chatAuthService.authenticatedFetch` to preserve cookie + JWT dual auth.
2. Conversation creation/updating remains centralized in `chatService` and `useChatStore.createConversation`; no new endpoints should be introduced.
3. Enrich chat context by packaging portfolio metadata, factor exposures, and current exposure metrics into each message payload (or pre-message context) so the LLM receives the latest analytics snapshot.
4. Introduce an LLM system persona along the lines of "You are a sophisticated portfolio risk analytics agent, well versed in BARRA factor models and portfolio optimization," and apply it consistently for every conversation/run.
5. Streaming responses continue to propagate through `useFetchStreaming` -> `useStreamStore.addToBuffer` -> `useChatStore.updateMessage`; the inline pane listens to the same stores—no additional synchronization layer required.
6. Mode changes initiated from the inline panel should call `chatStore.setMode` and `chatService.updateConversationMode` to keep backend and UI aligned.

## 6. Risks & Mitigations
- **Context Payload Drift**: Adding factor exposure data increases payload size; establish serialization/validation to prevent malformed context from breaking the stream.
- **Persona Consistency**: Forgetting to set the system persona could change answers; enforce via a single helper that wraps every chat call.
- **State Migration**: Removing `ChatInterface` may leave orphaned imports/state; plan a repo-wide search and clean-up once the page flow is live.
- **Streaming Abort Handling**: Inline layout must expose cancel controls; ensure `AbortController` clean-up so we do not leak requests.
- **Performance**: Larger context packages could slow first-token latency; monitor metrics and trim payloads if necessary.

## 7. Confirmed Decisions
- Redirect all chat entry points to `/ai-chat`; legacy sheet overlay will be removed.
- Inline chat panel occupies full width with no auxiliary context panes.
- Chat context must include portfolio metadata, factor exposures, and exposure metrics, plus a consistent risk-analytics persona prompt.
- `ChatInterface.tsx` can be deleted once the page implementation is stable and fully communicating with OpenAI.

## 8. Acceptance & Validation Checklist
- [ ] Thin route + container created without adding business logic to `page.tsx`.
- [ ] Conversation surface extracted and reused by both sheet and inline page with no duplicate streaming code.
- [ ] Chat bar submits through existing stores/services and respects message queueing.
- [ ] Streaming indicators, mode selector, and error states visible in inline layout.
- [ ] Auth expiry, network errors, and refresh flows behave the same as current implementation.
- [ ] Documentation updated (or annotated) where code deviates from `_docs/requirements/05-AIChat-Implementation.md` to avoid future confusion.










