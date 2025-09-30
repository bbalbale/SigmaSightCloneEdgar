# DESIGN\_DOC\_FRONTEND\_V1.0.md — Frontend (Next.js) for SigmaSight Agent

> **🚨 UPDATED TO V1.1 CHAT IMPLEMENTATION (2025-09-01)**  
> **DIRECT V1.1 IMPLEMENTATION - No prior frontend version existed**  
> **Note**: File name reflects original planning, but this documents the V1.1 implementation

**Date:** 2025-08-28 (Revised) → **V1.1: 2025-09-01**  
**Owners:** Frontend Engineering  
**Audience:** AI coding agent    
**Status:** ~~Ready for implementation with complete backend integration~~ → **V1.1 Implementation Ready**

> **🚨 CRITICAL REFERENCES**: This document must be read alongside the comprehensive agent documentation:
> 
> **Primary Implementation Guides:**
> - `../../agent/_docs/FRONTEND_AI_GUIDE.md` - **START HERE** - Complete API reference for AI agents
> - `../../agent/_docs/API_CONTRACTS.md` - Full TypeScript interfaces and contracts
> - `../../agent/_docs/SSE_STREAMING_GUIDE.md` - Production-ready SSE implementation
> - `../../agent/_docs/FRONTEND_FEATURES.md` - Detailed UI/UX specifications
> - `../../agent/_docs/FRONTEND_DEV_SETUP.md` - Development environment setup
>
> **Backend Documentation:**
> - `../../backend/AI_AGENT_REFERENCE.md` - Backend patterns and architecture
> - `../../backend/API_IMPLEMENTATION_STATUS.md` - Current API status (100% complete)
> - `../../agent/TODO.md` - Implementation progress (Phases 0-8 complete)

---

## 🔄 V1.1 Implementation Summary

**Note**: This is a **direct V1.1 implementation** - there was no prior v1.0 frontend. V1.1 represents the initial chat frontend implementation with advanced architectural decisions from the start.

**V1.1 Core Architecture:**
- **Mixed Authentication**: JWT for portfolio APIs + HttpOnly cookies for chat streaming
- **fetch() POST streaming**: Enhanced SSE with credentials:'include' and run_id deduplication
- **Split store architecture**: chatStore (persistent) + streamStore (runtime) for performance
- **Enhanced error taxonomy**: Retryable classification with specific UI behaviors
- **Message queue management**: One in-flight per conversation with queue cap=1
- **Enhanced observability**: run_id tracing, sequence numbers, TTFB metrics

**V1.1 Advanced Features:**
- **Mobile-first optimizations** (iOS Safari keyboard fixes, safe area support)
- **Performance instrumentation** (TTFB, tokens-per-second tracking)
- **Production deployment checklist** with streaming configurations
- **Enhanced security** with HttpOnly cookies and mixed auth strategy

---

## 1) Overview & Scope

**Goal:** Build a Next.js frontend that integrates with the fully-implemented SigmaSight chat backend to provide professional portfolio analysis powered by GPT-4o with Raw Data tools.

**✅ Backend Status (2025-08-28):**
- OpenAI integration complete with streaming SSE
- All Raw Data APIs working with real data
- Authentication system fully functional
- 6 portfolio analysis tools ready

**Scope (Phase 1):**

* **V1.1 fetch() POST streaming**: `POST /chat/send` → fetch() with credentials:'include'
* **V1.1 Mixed authentication**: JWT (portfolio) + HttpOnly cookies (chat streaming)  
* **V1.1 Enhanced streaming**: run_id deduplication + sequence numbering
* **V1.1 Split state management**: chatStore + streamStore architecture
* **V1.1 Message queue**: One in-flight per conversation with queue cap=1
* Tool execution indicators + real-time streaming ✅ (unchanged)
* 4 conversation modes: green (educational), blue (quantitative), indigo (strategic), violet (risk-focused) ✅ (unchanged)
* Mode switching via `/mode` commands or UI selector ✅ (unchanged) 
* CORS configured for localhost development ✅ (unchanged)
* **V1.1 Mobile optimization**: iOS Safari keyboard fixes + safe area support

**✅ Available Features:**
- Complete conversation management (create/delete/list/history)
- Real portfolio analysis with 6 working tools
- Message persistence and conversation history
- Error handling with retry logic

---

## 2) Architecture & Integration

```
Frontend (Next.js 15 + React)
  ├─ POST /api/v1/auth/login         → { access_token, user }
  ├─ GET  /api/v1/auth/me            → { user, portfolios }
  ├─ POST /api/v1/chat/conversations → { conversation_id }
  ├─ GET  /api/v1/chat/conversations → { conversations[] }
  ├─ DELETE /api/v1/chat/conversations/{id}
  ├─ GET  /api/v1/chat/conversations/{id}/messages → { messages[] }
  └─ POST /api/v1/chat/send          → SSE Stream (text/event-stream)
                                        │
                                        └─ Backend ↔ OpenAI GPT-4o
                                             ├─ 6 Portfolio Analysis Tools
                                             └─ Real-time streaming response
```

**✅ Current Implementation Notes:**

* **Authentication**: JWT Bearer tokens with `Authorization: Bearer ${token}` header
* **CORS**: Configured for `http://localhost:3000` and `http://localhost:5173` 
* **SSE Format**: Direct streaming from `/chat/send` (single-step, not two-step)
* **Tools Available**: `get_portfolio_complete`, `get_portfolio_data_quality`, `get_positions_details`, `get_prices_historical`, `get_current_quotes`, `get_factor_etf_prices`
* **Models**: Using `gpt-4o` (not gpt-5 due to org verification requirements)
* **Security**: All API keys secured on backend, frontend never calls OpenAI directly

**🔗 Reference**: See `../../agent/_docs/API_CONTRACTS.md` for complete TypeScript interfaces

---

## 3) File Structure & Assets

```
frontend/
├── src/app/
│   ├── layout.tsx
│   ├── page.tsx                 # redirect to /chat
│   ├── login/page.tsx
│   └── chat/page.tsx            # main chat interface
├── src/components/
│   ├── auth/LoginForm.tsx
│   ├── chat/
│   │   ├── ChatContainer.tsx
│   │   ├── MessageList.tsx
│   │   ├── MessageInput.tsx
│   │   ├── ToolBreadcrumbs.tsx
│   │   └── CodeInterpreterResult.tsx
│   └── ui/{LoadingSpinner,ErrorDisplay}.tsx
├── src/hooks/
│   ├── useAuth.ts               # ✅ (enhanced with cookie detection)
│   ├── ~~useSSEChat.ts~~        # 🗑️ Replaced by V1.1 hooks
│   ├── useChat.ts               # 🆕 V1.1: Persistent data management
│   ├── useStreaming.ts          # 🆕 V1.1: Runtime streaming state
│   ├── useMessageQueue.ts       # 🆕 V1.1: Queue with cap=1
│   └── useSlashCommands.ts      # ✅ (unchanged)
├── src/stores/                  # 🆕 V1.1: Split store architecture
│   ├── chatStore.ts             # Conversations, messages by ID
│   └── streamStore.ts           # Streaming, queue, buffer, abort
├── src/lib/
│   ├── api.ts                   # 🔄 V1.1: Enhanced with mixed auth
│   └── types.ts                 # 🔄 V1.1: Enhanced with run_id, sequences
├── src/utils/
│   ├── ~~sse.ts~~               # 🗑️ Replaced by fetch() streaming
│   ├── streamParser.ts          # 🆕 V1.1: ReadableStream parser
│   ├── errorTaxonomy.ts         # 🆕 V1.1: Enhanced error handling
│   └── slashCommands.ts         # ✅ (unchanged)
├── public/assets/sigmasight-logo.png
├── globals.css  tailwind.config.js  postcss.config.js  tsconfig.json
└── package.json
```

---

## 4) Authentication (JWT Bearer Tokens)

### 4.1 Login page (`/login`)

* **API:** `POST /api/v1/auth/login` with `{ email, password }`
* **Response:** `{ access_token: "jwt...", token_type: "bearer", user: {...} }`
* **Storage:** Token stored in `localStorage` as `auth_token`
* **Redirect:** `/chat` on success; show inline error on 401/400

**✅ Test Credentials:**
```javascript
const TEST_USER = {
  email: "demo_growth@sigmasight.com", 
  password: "demo12345"
}
```

### 4.2 Auth hook (`useAuth`)

* **Token Management:** Load from localStorage on mount, set Authorization header
* **Current User:** `GET /api/v1/auth/me` returns user + portfolio info
* **401 Handling:** Redirect to `/login` and clear stored token
* **Logout:** `POST /api/v1/auth/logout` + clear localStorage

**🔗 Reference**: See `../../agent/_docs/FRONTEND_AI_GUIDE.md` for complete auth implementation

### 4.3 Route protection  

* `/chat` guards unauthenticated users → `/login`
* All API calls include `Authorization: Bearer ${token}` header
* SSE connections include auth header for streaming

---

## 5) Chat Flow (Single-step SSE Streaming)

### 5.1 ✅ Current Implementation Contract

**Single-step flow**: `POST /chat/send` → direct SSE stream response

```javascript
// Request
POST /api/v1/chat/send
Headers: {
  'Authorization': 'Bearer ${token}',
  'Content-Type': 'application/json',
  'Accept': 'text/event-stream'
}
Body: {
  conversation_id: "uuid",
  text: "What is my portfolio value?"
}

// Response: SSE stream with events
```

**🔗 Reference**: See `../../agent/_docs/SSE_STREAMING_GUIDE.md` for complete implementation

### 5.2 ✅ SSE Event Types (Already Working)

* **`start`** → `{ conversation_id, mode, model }` - Stream initialization  
* **`message`** → `{ delta, role }` - Text chunks from AI response
* **`tool_started`** → `{ tool_name, arguments }` - Tool execution begins
* **`tool_finished`** → `{ tool_name, result, duration_ms }` - Tool execution complete
* **`done`** → `{ tool_calls_count, latency_ms }` - Response complete
* **`error`** → `{ message, retryable }` - Error occurred
* **`heartbeat`** → `{ timestamp }` - Keep connection alive

### 5.3 Hook Implementation (`useChat`)

**✅ Reference Implementation Available**: `../../agent/_docs/SSE_STREAMING_GUIDE.md`

Key features:
* **Real-time streaming**: Parse SSE events and update UI progressively
* **Tool execution tracking**: Show when AI is using portfolio analysis tools
* **Error handling**: Reconnection logic with exponential backoff  
* **Message persistence**: Store conversations in database
* **Abort control**: Cancel streaming on new message send

### 5.4 Authentication & Reliability

* **JWT Headers**: Include `Authorization: Bearer ${token}` for SSE
* **Reconnection**: Automatic retry with backoff on connection loss
* **Heartbeats**: Server sends periodic keep-alive events
* **CORS**: Pre-configured for localhost development

---

## 6) Conversation & Mode Management

### 6.1 ✅ Conversation Management (Full CRUD Available)

**✅ Complete API Implementation:**
* **Create**: `POST /api/v1/chat/conversations` → `{ conversation_id, mode, created_at }`
* **List**: `GET /api/v1/chat/conversations` → `{ conversations[], total_count }`  
* **Delete**: `DELETE /api/v1/chat/conversations/{id}`
* **History**: `GET /api/v1/chat/conversations/{id}/messages` → `{ messages[] }`

**Storage Strategy:**
* Store current `conversation_id` in state management (Zustand/Context)
* Persist conversation list from API calls
* Auto-create new conversation if none selected

**🔗 Reference**: Complete conversation management in `../../agent/_docs/API_CONTRACTS.md`

### 6.2 ✅ Four Conversation Modes (Working)

**Available Modes:**
* **`green`** (default): 🟢 Educational - Explains concepts with context and teaching
* **`blue`**: 🔵 Quantitative - Focuses on numbers, metrics, and precise analysis  
* **`indigo`**: 🟣 Strategic - Provides big-picture insights and strategic narratives
* **`violet`**: 🟤 Risk-Focused - Emphasizes conservative analysis and risk assessment

**Mode Switching Options:**
1. **Slash Commands**: Send `/mode blue` message to switch modes
2. **UI Selector**: Dropdown/buttons in conversation interface
3. **Per-Conversation**: Each conversation maintains its own mode

**🔗 Reference**: See `../../agent/prompts/` for complete mode implementations

---

## 7) Rendering

### 7.1 ✅ Message Model (Complete TypeScript Definitions)

```ts
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;           // streamed for assistant
  timestamp: Date;           // Date object (convert from ISO)
  streaming?: boolean;       // indicates if message is still being streamed
  toolCalls?: ToolExecution[];
  metadata?: {
    model?: string;
    tokens?: number;
    cost_usd?: number;
  };
}
```

**🔗 Reference**: Complete message types in `../../agent/_docs/API_CONTRACTS.md`

### 7.2 ✅ Tool Breadcrumbs (Live Tool Execution Tracking)

```ts
export interface ToolExecution {
  tool_name: string;
  duration_ms?: number;
  status: 'running' | 'completed' | 'error';
  result?: any;
  metadata?: {
    rows_returned?: number;
    truncated?: boolean;
    suggested_params?: Record<string, unknown>;
  };
}
```

**Real-time Updates via SSE:**
- `tool_started` event: Tool begins execution
- `tool_finished` event: Tool completes with results and timing
- `error` event: Tool fails with error details

**🔗 Reference**: Complete tool execution patterns in `../../agent/_docs/SSE_STREAMING_GUIDE.md`

### 7.3 ✅ Portfolio Analysis Results

**Tool Results Display:**
- Portfolio data tables (positions, performance metrics)
- Market data visualizations (price charts, volatility)
- Risk analysis outputs (factor exposures, correlations)
- Financial calculations (returns, Sharpe ratios, drawdowns)

**Rendering Strategy:**
- JSON data tables: Responsive HTML tables
- Large datasets: Pagination or virtual scrolling
- Charts: Simple line/bar charts for key metrics
- Code blocks: Syntax highlighting for calculations

**🔗 Reference**: Complete data visualization patterns in `../../agent/_docs/FRONTEND_FEATURES.md`

### 7.4 Markdown safety

* Use `react-markdown` + `rehype-sanitize` (no inline HTML by default)

---

## 8) Error Handling

**Buckets & UX**

* **Auth (401)**: backend sends an `error` event `{ code: 401 }` then closes → redirect `/login`
* **Rate limit (429)**: show toast “Cooling down 10s…”, backoff on next send
* **Tool failure**: show toast with `suggested_params` if present; message remains but annotate with a warning
* **SSE connection**: show “Connection lost. Retry?” with a button; closing a run to send a new message is **not** an error (normal)

Developer logging: log type, original error, and request context to console (dev builds only)

---

## 9) Performance & UX

* **Connection start** < 3s p50; **answer complete** < 8–10s p95 (one or two tool calls)
* ~~Only one live EventSource at a time~~ → **V1.1**: One in-flight request per conversation with queue cap=1
* Keyboard: `Enter` send, `Shift+Enter` newline
* Accessibility: streamed container has `aria-live="polite"`

---

## 10) ✅ API Layer Implementation (`src/lib/api.ts`)

**Working Endpoints:**
* `login({ email, password })` → POST `/api/v1/auth/login` → `{ access_token, user }`
* `createConversation({ mode })` → POST `/api/v1/chat/conversations` → `{ conversation_id }`
* `getConversations()` → GET `/api/v1/chat/conversations` → `{ conversations[] }`
* `deleteConversation(id)` → DELETE `/api/v1/chat/conversations/{id}`
* `sendMessage({ conversation_id, text })` → POST `/api/v1/chat/send` → SSE stream

**~~Single-Step SSE (No run_id needed)~~ → V1.1 Enhanced Streaming:**
```typescript
// V1.1: fetch() POST with credentials and run_id
const response = await fetch('/api/v1/chat/send', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream'
    // No Authorization header for chat
  },
  credentials: 'include', // V1.1: HttpOnly cookies
  body: JSON.stringify({ 
    conversation_id, 
    text,
    run_id: crypto.randomUUID() // V1.1: Required for deduplication
  })
});
```

**🔗 V1.1 Reference**: Complete **enhanced API client** with mixed auth in `../../agent/_docs/FRONTEND_DEV_SETUP.md`

---

## 11) ✅ Complete Type Definitions (`src/lib/types.ts`)

**SSE Event Types:**
```typescript
type SSEEventData = 
  | { event: "start"; data: { conversation_id: string; mode: string } }
  | { event: "message"; data: { delta: string; role: string } }
  | { event: "tool_started"; data: { tool_name: string } }
  | { event: "tool_finished"; data: { tool_name: string; duration_ms: number; result: any } }
  | { event: "error"; data: { code?: number; message: string } }
  | { event: "done"; data: { tool_calls_count: number; tokens?: number } }
```

**Core Types:**
* `ConversationMode`: `'green' | 'blue' | 'indigo' | 'violet'`
* `ConversationSummary`: Conversation list item
* `User`, `LoginResponse`, `CurrentUserResponse`: Auth types

**🔗 V1.1 Reference**: All **enhanced TypeScript interfaces** with run_id and sequencing in `../../agent/_docs/API_CONTRACTS.md`

---

## 12) ✅ SSE Implementation (`src/hooks/useSSE.ts`)

**Complete SSE Hook:**
```typescript
export function useSSE(options: UseSSEOptions = {}) {
  const { onMessage, onError, onOpen, onClose } = options;
  
  const connect = useCallback(async (url: string, headers: Record<string, string>) => {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Accept': 'text/event-stream', ...headers },
      signal: abortController.signal
    });
    
    await processSSEStream(response, onMessage, onError);
  }, []);
}
```

**Stream Processing:**
- Line-by-line parsing with buffering
- JSON parsing with error handling
- Automatic reconnection with exponential backoff
- AbortController for cleanup

**🔗 V1.1 Reference**: **Updated fetch() POST implementation** in `../../agent/_docs/SSE_STREAMING_GUIDE.md`

---

## 13) ✅ Mode Switching (Multiple Methods)

**Option 1: Slash Commands**
```typescript
// Recognize /mode commands
if (text.startsWith('/mode ')) {
  const mode = text.replace('/mode ', '').trim();
  if (['green', 'blue', 'indigo', 'violet'].includes(mode)) {
    // Update conversation mode
    return { type: 'mode_change', mode, shouldSend: false };
  }
}
```

**Option 2: UI Mode Selector**
- Dropdown or button group in chat interface
- Visual indicators for each mode (colors/icons)
- Persistent per conversation

**Option 3: API Mode Override**
- Pass `mode` parameter to `/chat/send`
- Temporary mode switch for single message

**🔗 Reference**: Mode implementation details in `../../agent/_docs/FRONTEND_FEATURES.md`

---

## 14) ✅ Conversation State Management

**State Persistence Strategy:**
```typescript
// Use Zustand for conversation state
interface ChatState {
  conversations: ConversationSummary[];
  currentConversationId: string | null;
  messages: ChatMessage[];
  // ... other state
}

// Load conversations on app start
const loadConversations = async () => {
  const conversations = await api.getConversations();
  setConversations(conversations);
  
  // Auto-select or create conversation
  if (conversations.length === 0) {
    const newConv = await api.createConversation();
    selectConversation(newConv.conversation_id);
  }
};
```

**🔗 V1.1 Reference**: Complete **split store patterns** in `../../agent/_docs/FRONTEND_DEV_SETUP.md`

---

## 15) Telemetry (client‑side)

* After `done`, compute `duration_ms` and send:

```json
{
  "run_id":"run_…",
  "conversation_id":"conv_…",
  "mode":"analyst-blue",
  "duration_ms": 5120,
  "tool_calls": 2,
  "tool_names": ["get_positions_details","get_prices_historical"],
  "tokens_prompt": null,
  "tokens_completion": null,
  "model": "gpt-5",
  "cost_est_usd": null,
  "rating": null
}
```

* **Note:** if backend later includes token/cost in `done`, populate those fields.

---

## 16) Responsive Design (minimal)

* Use existing `globals.css` breakpoints and spacing
* On mobile: input full width; breadcrumbs collapsed; header compact

---

## 17) ✅ Ready-to-Implement Architecture

**Phase 1: Core Setup (1-2 days)**
1. Next.js project with TypeScript + Tailwind
2. JWT authentication with login form
3. Basic routing and protected routes
4. API client with Bearer token handling

**Phase 2: Chat Implementation (2-3 days)**
1. SSE streaming hook implementation
2. Chat UI with message bubbles
3. Real-time streaming and tool execution display
4. Conversation management (create/list/delete)

**Phase 3: Polish & Features (1-2 days)**
1. Mode switching UI and slash commands
2. Error handling and reconnection logic
3. Mobile responsive design
4. Performance optimization

**🚀 Accelerated Development**: All backend APIs working, complete documentation available

**🔗 Reference**: Step-by-step setup in `../../agent/_docs/FRONTEND_DEV_SETUP.md`

---

## 18) ✅ Current Backend Status & Success Criteria

### ✅ Backend Implementation Complete (2025-08-28)

**All Required APIs Working:**
- Authentication system with JWT tokens ✅
- Complete conversation CRUD operations ✅  
- Real-time SSE streaming with OpenAI GPT-4o ✅
- 6 portfolio analysis tools functional ✅
- Error handling and reconnection logic ✅
- Message persistence and history ✅

**Performance Targets Met:**
- SSE stream start: < 3 seconds ✅
- Tool execution: Real portfolio data ✅
- OpenAI responses: GPT-4o streaming ✅

### Frontend Success Criteria

* ✅ **Single-step SSE streaming** (POST /chat/send → direct stream)
* ✅ **JWT Bearer token authentication** (localStorage + Authorization header)
* ✅ **Four conversation modes** (green/blue/indigo/violet) with mode switching
* ✅ **Complete conversation management** (create/list/delete/history)
* ✅ **Real portfolio analysis** with 6 working tools
* ✅ **CORS configuration** for localhost development
* ✅ **Mobile-responsive design** requirements

**🚀 V1.1 Ready for Implementation**: All backend APIs enhanced for mixed auth and advanced streaming

---

## 🆕 V1.1 Implementation Guide

### V1.1 Critical Architecture Changes

**1. Split Store Pattern (Performance Optimization)**
```typescript
// chatStore.ts - Persistent data
interface ChatState {
  conversations: ConversationSummary[];
  currentConversationId: string | null;
  messages: Record<string, ChatMessage[]>; // By conversationId
}

// streamStore.ts - Runtime state  
interface StreamState {
  isStreaming: boolean;
  currentRunId: string | null;
  streamBuffer: string;
  messageQueue: Array<{conversationId: string; text: string}>; // Cap=1
  processing: boolean;
  abortController: AbortController | null;
}
```

**2. Enhanced fetch() POST Streaming**
```typescript
// V1.1 Implementation
const response = await fetch('/api/v1/chat/send', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream'
  },
  credentials: 'include', // HttpOnly cookies
  body: JSON.stringify({
    conversation_id: conversationId,
    text,
    run_id: crypto.randomUUID() // Client-generated
  })
});
```

**3. Enhanced Error Taxonomy**
```typescript
interface V1_1_ErrorHandling {
  RATE_LIMITED: { retry: true, delay: 30000, message: 'Rate limited' };
  AUTH_EXPIRED: { retry: false, redirect: '/login' };
  NETWORK_ERROR: { retry: true, delay: 5000, message: 'Connection issue' };
  SERVER_ERROR: { retry: true, delay: 10000, message: 'Server issue' };
  CLIENT_ERROR: { retry: false, message: 'Validation error' };
}
```

**4. Mobile-First Enhancements**
```css
/* V1.1 iOS Safari fixes */
.chat-input {
  padding-bottom: env(safe-area-inset-bottom);
  scroll-margin-bottom: 120px;
}

@supports (-webkit-touch-callout: none) {
  .ios-safari-fixes {
    /* iOS-specific keyboard handling */
  }
}
```

**🔗 V1.1 References**: All implementation patterns updated in `/agent/_docs/` files

---

## 🚀 Implementation Status & Next Steps

### ✅ All Prerequisites Complete (2025-08-29)

**Backend Infrastructure Ready:**
- Authentication system with JWT tokens ✅
- Complete SSE streaming with OpenAI GPT-4o ✅  
- 6 portfolio analysis tools working with real data ✅
- CORS configuration for development ✅
- Error handling and reconnection logic ✅

**Complete Documentation Available:**
- `../../agent/_docs/FRONTEND_AI_GUIDE.md` - API endpoints and authentication
- `../../agent/_docs/API_CONTRACTS.md` - TypeScript interfaces and contracts  
- `../../agent/_docs/SSE_STREAMING_GUIDE.md` - Production SSE implementation
- `../../agent/_docs/FRONTEND_FEATURES.md` - UI/UX specifications
- `../../agent/_docs/FRONTEND_DEV_SETUP.md` - Next.js setup and configuration

### 🎯 V1.1 AI Agent Implementation Guide

**Step 1: Project Setup**
```bash
npx create-next-app@latest sigmasight-frontend --typescript --tailwind --eslint --app --src-dir
cd sigmasight-frontend
```

**Step 2: V1.1 Dependencies** (from updated FRONTEND_DEV_SETUP.md)
```bash
npm install @tanstack/react-query zustand react-hook-form zod lucide-react
npm install zustand/middleware # For persist in split stores
```

**Step 3: V1.1 Environment Configuration**
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_V1_1_FEATURES=true # Enable V1.1 features
```

**Step 4: V1.1 Core Features Implementation**
1. **Mixed Authentication**: JWT (localStorage) + HttpOnly cookies
2. **fetch() POST streaming**: Replace EventSource with ReadableStream parsing
3. **Split store architecture**: chatStore + streamStore
4. **Enhanced message queue**: One in-flight per conversation, cap=1
5. **Mobile optimizations**: iOS Safari keyboard fixes
6. Mode switching (4 modes: green/blue/indigo/violet) ✅ (unchanged)

### 📋 V1.1 Success Criteria Checklist

**Core Functionality:**
- [ ] User can login with demo credentials (demo_growth@sigmasight.com / demo12345)
- [ ] Login sets both JWT (localStorage) AND HttpOnly cookies
- [ ] Chat interface streams responses via fetch() POST (not EventSource)
- [ ] Tool execution shows live progress indicators ✅ (unchanged)
- [ ] Mode switching works (slash commands + UI selector) ✅ (unchanged)
- [ ] Conversation management (create/list/delete) ✅ (unchanged)

**V1.1 Enhancements:**
- [ ] **Split stores**: chatStore (persistent) + streamStore (runtime) working
- [ ] **Message queue**: One in-flight per conversation with queue cap=1
- [ ] **Enhanced errors**: Error taxonomy with retryable classification
- [ ] **Mobile optimization**: iOS Safari keyboard fixes and safe area support
- [ ] **Observability**: run_id tracing and performance metrics (TTFB)
- [ ] **Production ready**: Deployment checklist with streaming configurations

**🏁 V1.1 Ready for Implementation**: All V1.1 documentation updated, enhanced backend compatibility, split store patterns ready.
