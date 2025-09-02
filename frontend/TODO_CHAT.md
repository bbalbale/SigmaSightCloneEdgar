# Frontend Chat Implementation TODO

**Created:** 2025-09-01  
**Status:** V1.1 Implementation Phase  
**Target:** SigmaSight Portfolio Chat Assistant  
**Reference:** `_docs/requirements/CHAT_IMPLEMENTATION_PLAN.md`

## 1. Current Implementation Status

### ✅ What's Currently Working
- **Portfolio System**: Fully functional with real backend data integration
- **Authentication**: JWT-based auth working for portfolio APIs (`demo_growth@sigmasight.com` / `demo12345`)
- **Backend Agent System**: 100% complete with OpenAI GPT-4o integration and 6 function tools
- **Chat UI Foundation**: Sheet overlay pattern implemented with mock responses
- **Next.js Proxy**: CORS proxy setup for development (`/api/proxy/[...path]`)

### 🔧 Development Environment Setup
**Backend Prerequisites:**
- **Backend Server**: Must be running on `localhost:8000` (`cd ../backend && uv run python run.py`)
- **Database**: PostgreSQL via Docker (`docker-compose up -d`)
- **Agent Tables**: `agent_conversations` and `agent_messages` tables exist and ready
- **OpenAI Integration**: GPT-4o configured with portfolio analysis tools
- **Demo Data**: 3 portfolios with 63 positions loaded for testing

**Frontend Prerequisites:**  
- **Development Server**: Running on port 3005 (`npm run dev`)
- **Portfolio Page**: `http://localhost:3005/portfolio?type=high-net-worth` (working with real data)
- **Chat Interface**: Accessible via sheet overlay from portfolio page (currently mock responses)
- **⚠️ Portfolio IDs**: Run `uv run python scripts/list_portfolios.py` in backend to get actual IDs
  - Portfolio IDs are **unique per database** and change with each setup
  - Frontend must dynamically fetch IDs, not hardcode them
  - Test with actual IDs from your environment

### 🚀 Ready for V1.1 Implementation
**Next Immediate Action**: Section 1.0 Authentication Migration
- Replace JWT localStorage with HttpOnly cookies for chat streaming
- Enable `credentials: 'include'` for fetch() POST streaming
- Backend login endpoint ready to set both JWT + HttpOnly cookies
- Backend chat endpoints ready to validate both Bearer tokens and cookies

**V1.1 Architectural Decisions Finalized:**
- **Streaming**: fetch() POST with manual SSE parsing (not EventSource)
- **Authentication**: Mixed strategy - JWT for portfolio, HttpOnly cookies for chat
- **State Management**: Split architecture - `chatStore` (persistent) + `streamStore` (runtime)
- **Message Queue**: One in-flight per conversation with queue cap=1
- **Error Taxonomy**: Enhanced with retryable classification (RATE_LIMITED, AUTH_EXPIRED, etc.)

**Demo Testing Context:**
- **User**: `demo_hnw@sigmasight.com` / `demo12345` (recommended - has portfolio data)
- **Portfolio ID**: ⚠️ **CRITICAL** - IDs are unique per database installation!
  - Run `cd backend && uv run python scripts/list_portfolios.py` to get your IDs
  - Example ID format: `c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e`
  - Frontend must fetch these dynamically, not hardcode them
- **Chat Modes**: 4 conversation modes ready (/mode green|blue|indigo|violet)
- **Working Endpoints**: All 6 Raw Data APIs function properly for AI agent tools

## Overview

This TODO tracks the implementation of the chat functionality based on the comprehensive Chat Implementation Plan V1.1. All architectural decisions have been finalized and backend integration is complete. The focus is now on frontend implementation to connect the working UI components with the ready backend chat system.

## Technical Specifications

### Code Guidelines
**Important**: Code examples in this document are illustrative pseudocode unless marked as "Production Code". All implementations should be in TypeScript (React + Zustand) following the existing codebase patterns.

### 1. Stream Buffer Architecture

**Production Code - Stream Buffer Structure:**
```typescript
// StreamStore state structure
interface StreamStore {
  // Map of run_id to buffer state
  streamBuffers: Map<string, StreamBuffer>;
  activeRuns: Set<string>;
  processing: boolean;
}

interface StreamBuffer {
  text: string;        // Accumulated message text
  lastSeq: number;     // Last processed sequence number
  startTime: number;   // Timestamp for timeout detection
}
```

### 2. SSE Event Schema

**Production Code - Complete SSE Event Structure:**
```typescript
interface SSEEvent {
  run_id: string;      // Unique identifier for this streaming run
  seq: number;         // Sequence number for ordering/deduplication
  type: 'token' | 'tool_call' | 'tool_result' | 'error' | 'done';
  data: {
    delta?: string;        // For token events (incremental text)
    tool_name?: string;    // For tool_call events
    tool_args?: any;       // For tool_call events
    tool_result?: any;     // For tool_result events
    error?: string;        // For error events
    error_type?: ErrorType; // For typed error handling
    final_text?: string;   // For done events (complete message)
  };
  timestamp: number;   // Server timestamp for ordering
}

// Example SSE stream:
// {"run_id":"abc-123","seq":1,"type":"token","data":{"delta":"Hello"},"timestamp":1234567890}
// {"run_id":"abc-123","seq":2,"type":"token","data":{"delta":" there"},"timestamp":1234567891}
// {"run_id":"abc-123","seq":3,"type":"done","data":{"final_text":"Hello there"},"timestamp":1234567892}
```

### 3. Message Queue Specification

**Production Code - Queue Behavior:**
```typescript
interface MessageQueueConfig {
  maxQueued: 1;                    // Only one pending message allowed
  policy: 'last-write-wins';       // Latest input replaces queued message
  cancellation: 'clear-all';       // Cancel clears both active and queued
}

class MessageQueue {
  private pending: Message | null = null;
  private processing: boolean = false;
  private conversationLocks: Map<string, boolean> = new Map();
  
  add(conversationId: string, message: Message): void {
    if (this.processing) {
      // Last write wins - replace any pending message
      this.pending = message;
      this.showQueuedIndicator();
    } else {
      this.process(conversationId, message);
    }
  }
  
  cancel(conversationId: string): void {
    // Clear both active and queued for this conversation
    this.pending = null;
    this.processing = false;
    this.conversationLocks.set(conversationId, false);
    this.abortController?.abort();
  }
}
```

### 4. Error Taxonomy and Policies

**Production Code - Error Classification:**
```typescript
enum ErrorType {
  AUTH_EXPIRED = 'AUTH_EXPIRED',     // Authentication token/cookie expired
  RATE_LIMITED = 'RATE_LIMITED',     // Rate limit exceeded
  NETWORK_ERROR = 'NETWORK_ERROR',   // Network connectivity issue
  SERVER_ERROR = 'SERVER_ERROR',     // Backend server error (5xx)
  FATAL_ERROR = 'FATAL_ERROR'        // Unrecoverable error
}

interface ErrorPolicy {
  action: 'redirect' | 'cooldown' | 'retry' | 'fail';
  maxAttempts?: number;
  delay?: number | number[];  // Single delay or backoff array
  target?: string;            // For redirect action
  duration?: number;          // For cooldown action
  showToast?: boolean;
}

const ERROR_POLICIES: Record<ErrorType, ErrorPolicy> = {
  AUTH_EXPIRED: { 
    action: 'redirect', 
    target: '/login',
    showToast: true 
  },
  RATE_LIMITED: { 
    action: 'cooldown', 
    duration: 30000, // 30 seconds
    showToast: true 
  },
  NETWORK_ERROR: { 
    action: 'retry', 
    maxAttempts: 3, 
    delay: [1000, 2000, 4000], // Exponential backoff
    showToast: false // Only show after all retries fail
  },
  SERVER_ERROR: { 
    action: 'retry', 
    maxAttempts: 1, 
    delay: 1000,
    showToast: true 
  },
  FATAL_ERROR: { 
    action: 'fail', 
    showToast: true 
  }
};
```

### 5. Mobile Configuration

**Production Code - Required Mobile Setup:**
```html
<!-- In _document.tsx or layout.tsx -->
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
```

```css
/* mobile-chat.css */
.chat-input-container {
  position: sticky;
  bottom: 0;
  padding-bottom: env(safe-area-inset-bottom, 0);
  background: white;
  z-index: 100;
}

/* iOS-specific fixes */
@supports (-webkit-touch-callout: none) {
  .chat-input {
    font-size: 16px; /* Prevent zoom on focus */
  }
  
  .chat-messages {
    -webkit-overflow-scrolling: touch;
    scroll-behavior: smooth;
  }
}
```

```typescript
// Mobile keyboard handling
const handleInputFocus = () => {
  if (/iPhone|iPad|iPod/.test(navigator.userAgent)) {
    setTimeout(() => {
      inputRef.current?.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'center' 
      });
    }, 300);
  }
};
```

### 6. File/Data Upload Strategy

**Production Code - Upload Handling:**
```typescript
interface UploadStrategy {
  smallJSON: {  // ≤ 2MB
    method: 'inline',
    location: 'request-body'
  },
  mediumFile: { // 2-10MB
    method: 'multipart',
    field: 'file'
  },
  largeFile: {  // > 10MB
    method: 'pre-upload',
    endpoint: '/api/v1/upload',
    passPointer: true
  }
}

// Implementation example
const sendWithData = async (message: string, data?: any) => {
  const dataSize = JSON.stringify(data).length;
  
  if (dataSize <= 2 * 1024 * 1024) {
    // Send inline in POST body
    return fetch('/api/v1/chat/send', {
      method: 'POST',
      body: JSON.stringify({ message, data }),
      credentials: 'include'
    });
  } else {
    // Use multipart or pre-upload based on size
    // Implementation details...
  }
};
```

### 7. Nginx Production Configuration

**Production Code - Complete Nginx Config:**
```nginx
# Full nginx configuration for SSE streaming
location /api/v1/chat/send {
    proxy_pass http://backend:8000;
    
    # Critical SSE settings
    proxy_buffering off;
    proxy_cache off;
    gzip off;  # IMPORTANT: Compression breaks SSE
    
    # Timeouts for long-running connections
    proxy_read_timeout 300s;
    proxy_connect_timeout 60s;
    proxy_send_timeout 300s;
    
    # Headers for SSE
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # CORS headers (if not handled by backend)
    add_header 'Access-Control-Allow-Origin' $http_origin always;
    add_header 'Access-Control-Allow-Credentials' 'true' always;
}
```

### 8. Observability Schema

**Production Code - Logging Structure:**
```typescript
interface ChatLogEvent {
  traceId: string;      // Same as run_id for correlation
  conversationId: string;
  messageId?: string;
  event: 'request' | 'stream-start' | 'stream-chunk' | 'stream-end' | 'error';
  data: {
    timestamp: number;
    duration?: number;   // For completed events
    error?: ErrorType;
    metrics?: {
      ttfb?: number;      // Time to first byte
      tokensPerSecond?: number;
      totalTokens?: number;
    };
  };
}

// Usage
const logger = {
  trace: (event: ChatLogEvent) => {
    if (process.env.NODE_ENV === 'development') {
      console.debug('[Chat]', event);
      debugStore.addEvent(event);
    }
    // In production, send to monitoring service
  }
};
```

---

## Implementation Progress Summary (2025-09-02)

### 🎉 **NEWLY COMPLETED IN THIS SESSION**
- ✅ **Section 2.1.0**: Backend CORS fix for SSE streaming
- ✅ **Section 2.1.1**: Cookie-based authentication service (100% complete)
- ✅ **Section 2.2.1**: Split store architecture (95% complete, testing pending)
- ✅ **Section 2.2.2**: fetch() streaming hook (95% complete, backend testing pending)

**Key Achievements:**
1. **Authentication**: Created `chatAuthService.ts` with HttpOnly cookie support
2. **State Management**: Split into `chatStore.ts` (persistent) + `streamStore.ts` (runtime)
3. **Streaming**: Implemented `useFetchStreaming.ts` hook with manual SSE parsing
4. **UI Integration**: Updated `ChatInterface.tsx` to use both stores
5. **Backend Fix**: Applied pre-approved CORS headers fix for credentials support

**Ready for Testing**: The core infrastructure is complete. Next steps are backend integration (Section 3) and testing with real streaming responses.

## Current Status

### ✅ **COMPLETED** (Pre-Implementation - Already Done)

#### Foundation Components
- ✅ **ChatInterface.tsx** - Sheet UI overlay pattern implemented (`src/components/chat/ChatInterface.tsx`)
- ✅ **ChatInput.tsx** - Basic input component with send functionality (`src/app/components/ChatInput.tsx`) 
- ✅ **ChatStore.ts** - Zustand state management with message history (`src/stores/chatStore.ts`)
- ✅ **ChatProvider.tsx** - Provider wrapper component (`src/components/chat/ChatProvider.tsx`)
- ✅ **API Proxy Setup** - Next.js proxy route ready for cookie forwarding (`src/app/api/proxy/[...path]/route.ts`)
- ✅ **Portfolio Integration** - Chat input embedded in portfolio page with sheet triggers
- ✅ **Mock Response System** - Temporary mock responses working for UI testing

#### Backend Readiness
- ✅ **Agent Backend 100% Ready** - All chat endpoints implemented with UUID system
- ✅ **Authentication Support** - HttpOnly cookie support ready for streaming
- ✅ **Database Tables** - `agent_conversations` and `agent_messages` tables exist
- ✅ **OpenAI Integration** - GPT-4o with 6 portfolio analysis function tools
- ✅ **SSE Infrastructure** - Server-sent events with heartbeats ready

## 2. **V1.1 Implementation**

### 2.0 **Iterative Agentic Development Methodology**

This implementation follows an **automated test-driven development cycle** using MCP agents:

#### 🚨 **CRITICAL CONSTRAINTS - DO NOT VIOLATE**
- **❌ NO BACKEND CHANGES**: Do not modify ANY code in `/backend/` or `/agent/` folders without explicit user approval
  - **Exception**: The CORS fix in Section 2.1.0 is PRE-APPROVED
- **❌ NO DATABASE CHANGES**: Do not create or modify database tables without explicit user approval
  - If approved, MUST use Alembic migrations (`alembic revision --autogenerate`)
  - Never create tables manually or modify schema directly
- **❌ NO MODEL CHANGES**: Do not modify existing data models used by `/backend/` and `/agent/` without approval
  - This includes Pydantic schemas, SQLAlchemy models, and API contracts
- **✅ FRONTEND ONLY**: This implementation is frontend-only, connecting to existing backend APIs

#### Development Loop Process:
1. **Plan** → Define feature requirements and acceptance criteria
2. **Test First** → Write failing automated tests using MCP tools (Playwright/Puppeteer)
3. **Implement** → Code the feature to pass tests
4. **Validate** → Run automated validation pipeline
5. **Review** → Trigger design-review agent for UX/accessibility validation
6. **Iterate** → Refine based on agent feedback and re-test
7. **Deploy** → Move to next feature when all validations pass

#### MCP Integration Strategy:
- **mcp-server-fetch**: Backend API endpoint validation
- **@playwright/mcp**: Browser automation and visual regression testing  
- **mcp-server-puppeteer**: Real-time SSE streaming validation
- **design-review agent**: Automated UX and accessibility reviews

#### Continuous Validation:
- Each section (2.1-2.2, 3, 4, 5) includes automated validation checkpoints
- Visual regression testing captures screenshots at key implementation milestones
- Performance metrics (TTFB, streaming latency) logged automatically
- Accessibility compliance verified programmatically

### 2.1 **Authentication Migration**

#### ✅ **Backend Authentication Status** (Completed in TODO3.md Phase 4.0.1)
**Reference**: `/backend/TODO3.md` Section 4.0.1 - **Dual Authentication Strategy (JWT Bearer + HTTP-only Cookies)** ✅ **COMPLETED 2025-08-27**

**What's Already Working in Backend:**
- ✅ **Login Endpoint**: `/api/v1/auth/login` returns JWT in response body AND sets HttpOnly cookie  
- ✅ **Logout Endpoint**: `/api/v1/auth/logout` properly clears auth_token cookie
- ✅ **Dual Auth Support**: `get_current_user` dependency supports both Bearer (preferred) and Cookie (fallback)
- ✅ **Cookie Configuration**: Proper HttpOnly, SameSite=lax, secure in production settings
- ✅ **Precedence Logic**: Bearer token takes priority when both provided
- ✅ **Logging**: Tracks which auth method is being used ("method: bearer" vs "method: cookie")
- ✅ **Demo Credentials**: Working with `demo_growth@sigmasight.com` / `demo12345`

**🔧 Pre-Approved Backend Fix Required:**
- [x] **2.1.0** Fix CORS headers for SSE streaming with credentials (PRE-APPROVED) ✅ COMPLETED
  - **File**: `/backend/app/api/v1/chat/send.py` line 261
  - **Issue**: Wildcard `*` origin incompatible with `credentials: 'include'`
  - **Fix**: Change SSE response headers from:
    ```python
    "Access-Control-Allow-Origin": "*",  # CORS for SSE
    ```
    To:
    ```python
    "Access-Control-Allow-Origin": request.headers.get('origin', 'http://localhost:3005'),
    "Access-Control-Allow-Credentials": "true",
    ```
  - **Status**: ✅ PRE-APPROVED - COMPLETED

**Frontend Implementation Tasks:**
- [x] **2.1.1** Switch from JWT localStorage to HttpOnly cookies ✅ COMPLETED
  - [x] **2.1.1.1** Create cookie-based auth service (`src/services/chatAuthService.ts`) ✅
  - [x] **2.1.1.2** Update login flow to use existing HttpOnly cookie functionality ✅
  - [x] **2.1.1.3** Update API proxy to forward cookies correctly with `credentials: 'include'` ✅
  - [x] **2.1.1.4** Test cookie auth with `/api/v1/auth/me` endpoint ✅
  - [x] **2.1.1.5** Implement logout to use existing cookie clearing backend ✅
  - [x] **2.1.1.6** Create login page for testing (`src/app/login/page.tsx`) ✅

### 2.2 **Split Store Architecture + Streaming**
- [x] **2.2.1** Split Store Architecture (See Technical Specifications Section 1) ✅ COMPLETED
  - [x] **2.2.1.1** Create separate `streamStore.ts` for runtime state ✅
    - [x] Implement StreamStore interface from Technical Specs ✅
    - [x] Use Map<string, StreamBuffer> structure as specified ✅
    - [x] Include activeRuns Set and processing flag ✅
  - [x] **2.2.1.2** Refactor `chatStore.ts` for persistent data only ✅
    - [x] conversations, messages (by conversationId), currentConversationId ✅
    - [x] Remove streaming state (isStreaming, streamingMessage) ✅
  - [x] **2.2.1.3** Update ChatInterface to use both stores ✅
  - [x] **2.2.1.4** Implement SSE Event Schema (See Technical Specifications Section 2) ✅
    - [x] Use complete SSEEvent interface with all fields ✅
    - [x] Include proper type discrimination for event types ✅
    - [x] Add timestamp for client-side ordering ✅
  - [x] **2.2.1.5** Implement buffer → seal reconciliation on 'done' event ✅
    - [x] Use StreamBuffer structure with text, lastSeq, startTime ✅
    - [x] Validate sequence numbers for deduplication ✅
    - [x] Seal final message content on 'done' event ✅
  - [x] **2.2.1.6** Implement Message Queue (See Technical Specifications Section 3) ✅
    - [x] Use MessageQueue with last-write-wins policy ✅
    - [x] Implement conversation locks Map ✅
    - [x] Enforce maxQueued: 1 configuration ✅
  - [ ] **2.2.1.7** Test performance improvement (fewer re-renders)

- [x] **2.2.2** Implement fetch() Streaming Hook ✅ COMPLETED
  - [x] **2.2.2.1** Create `useFetchStreaming.ts` hook ✅
  - [x] **2.2.2.2** Implement POST request with `credentials: 'include'` ✅
  - [x] **2.2.2.3** Add manual SSE parsing with ReadableStream ✅
  - [x] **2.2.2.4** Handle run_id for deduplication ✅
  - [x] **2.2.2.5** Implement stream buffer management ✅
  - [x] **2.2.2.6** Add AbortController for cleanup ✅
  - [ ] **2.2.2.7** Test streaming with real backend responses

### 2.3 **API Contract Alignment**

#### ⚠️ **API Contract Alignment Issue**
**Problem**: Frontend currently sends incorrect field names to backend chat endpoint:
- Frontend sends: `{ message: "...", conversation_id: "..." }`
- Backend expects: `{ text: "...", conversation_id: "..." }`

**Resolution**: Frontend must adapt to match backend API contract:
- [x] **2.3.1** Fix field name mismatch ✅ COMPLETED
  - [x] Changed `message` to `text` field in `useFetchStreaming.ts` (line 83) ✅
- [x] **2.3.2** Ensure conversation_id is always provided (backend requires it) ✅ COMPLETED
  - [x] Created `chatService.ts` to call backend `/api/v1/chat/conversations` endpoint ✅
  - [x] Updated ChatInterface to create conversation on backend before first message ✅
  - [x] Modified chatStore to accept backend conversation ID ✅
  - [x] Pass conversation_id with every message via streamMessage hook ✅
- [x] **2.3.3** Test API contract alignment ✅ COMPLETED
  - [x] Verified messages reach backend with correct field names (`text` not `message`) ✅
  - [x] Confirmed conversation_id is included in all requests ✅
  - [x] Backend successfully receives and processes messages ✅
  - [x] SSE streaming response is returned (though OpenAI has JSON parsing issues) ✅

**Note**: We're treating this as a frontend issue to maintain backend API stability.

### 3. **Backend Integration**

- [x] **3.0** Dynamic Portfolio ID Resolution ✅ COMPLETED
  - [x] **3.0.1** Create `portfolioResolver.ts` service ✅
    - [x] Created resolver service with hint-based discovery mechanism ✅
    - [x] Implemented cache for portfolio IDs with 5-minute TTL ✅
    - [x] Added fallback handling for missing list endpoint ✅
  - [x] **3.0.2** Update `portfolioService.ts` to use dynamic IDs ✅
    - [x] Removed hardcoded PORTFOLIO_ID_MAP ✅
    - [x] Updated to use portfolioResolver.getPortfolioIdByType() ✅
    - [x] Added portfolio ID caching after successful authentication ✅
  - [x] **3.0.3** Add portfolio ID validation ✅
    - [x] Implemented validatePortfolioOwnership() method ✅
    - [x] Cross-user access properly blocked (404 on unauthorized) ✅
    - [x] Graceful fallback with error messages for missing portfolios ✅

- [ ] **3.1** Create Chat Service
  - [ ] **3.1.1** Build `chatService.ts` with cookie-based API client
  - [ ] **3.1.2** Implement conversation management methods
    - [ ] createConversation(mode) - **CRITICAL**: Backend requires this before sending messages
      - [ ] POST to `/api/v1/chat/conversations` with `{ mode: "green" | "blue" | "indigo" | "violet" }`
      - [ ] Store returned `conversation_id` for all subsequent messages
    - [ ] listConversations()  
    - [ ] deleteConversation(id)
    - [ ] getMessages(conversationId, limit, cursor)
  - [ ] **3.1.3** Implement message sending with streaming
    - [ ] Use sendWithData() from Technical Specifications Section 6
    - [ ] Handle inline JSON for ≤2MB, multipart for larger
  - [ ] **3.1.4** Add error handling with ErrorType enum and policies

- [ ] **3.2** Connect UI to Backend
  - [ ] **3.2.1** Replace mock responses with real API calls
  - [ ] **3.2.2** Implement conversation lifecycle management
  - [ ] **3.2.3** Connect message history loading
  - [ ] **3.2.4** Test with demo user credentials
    - [ ] Use `demo_hnw@sigmasight.com` (has portfolio data)
    - [ ] Dynamically fetch portfolio ID for the user
    - [ ] Verify portfolio data loads before enabling chat
  - [ ] **3.2.5** Handle conversation creation on first message
  - [ ] **3.2.6** Test mode switching (/mode green|blue|indigo|violet)

### 4. **Message Queue + Error Handling**

#### 4.1 **Client-Side Message Queue (See Technical Specifications Section 3)**
- [ ] **4.1.1** Create `useMessageQueue.ts` hook using MessageQueue class
- [ ] **4.1.2** Implement queue with specified behavior:
  - [ ] maxQueued: 1 configuration
  - [ ] last-write-wins policy for pending messages
  - [ ] Show "queued" badge using showQueuedIndicator()
  - [ ] Display processing status from queue state
- [ ] **4.1.3** Integrate with streamStore for queue state
- [ ] **4.1.4** Use conversationLocks Map from specification
- [ ] **4.1.5** Test spam prevention (rapid send button clicks)
- [ ] **4.1.6** Test cancel() method clears both active and queued

#### 4.2 **Enhanced Error Handling (See Technical Specifications Section 4)**
- [ ] **4.2.1** Implement ErrorType enum and ERROR_POLICIES from specification
  - [ ] AUTH_EXPIRED: action='redirect', target='/login'
  - [ ] RATE_LIMITED: action='cooldown', duration=30000ms
  - [ ] NETWORK_ERROR: action='retry', backoff=[1000, 2000, 4000]
  - [ ] SERVER_ERROR: action='retry', maxAttempts=1, delay=1000
  - [ ] FATAL_ERROR: action='fail', showToast=true
- [ ] **4.2.2** Implement handleStreamError function with policy execution
- [ ] **4.2.3** Add toast notifications based on showToast flags
- [ ] **4.2.4** Handle connection lost with NETWORK_ERROR retry policy
- [ ] **4.2.5** Test error recovery flows for each ErrorType

### 5. **Mobile Optimization + Testing**

#### 5.1 **Mobile Input Handling (See Technical Specifications Section 5)**
- [ ] **5.1.1** Implement mobile configuration from specification
  - [ ] Add viewport meta tag with viewport-fit=cover
  - [ ] Create mobile-chat.css with env(safe-area-inset-bottom)
  - [ ] Use position: sticky for input container
- [ ] **5.1.2** Add iOS Safari fixes from specification
  - [ ] 16px font-size to prevent zoom
  - [ ] -webkit-overflow-scrolling: touch for smooth scroll
- [ ] **5.1.3** Test keyboard behavior on iOS/Android devices
- [ ] **5.1.4** Implement handleInputFocus() with scrollIntoView
- [ ] **5.1.5** Test iPhone notch compatibility with safe areas

#### 5.2 **Automated Testing & Validation**

##### 5.2.1 **MCP-Powered Automated Testing**
- [ ] **5.2.1.0** Test Environment Setup
  - [ ] Dynamically fetch portfolio IDs before test run
  - [ ] Store portfolio mappings in test configuration
  - [ ] Validate test users have required portfolios
  - [ ] Handle different portfolio IDs across environments
- [ ] **5.2.1.1** Set up Playwright MCP integration for chat flow testing
  - [ ] Configure browser automation for localhost:3005
  - [ ] Create test scenarios for complete chat flows
  - [ ] Set up viewport testing (desktop, tablet, mobile)
- [ ] **5.2.1.2** Set up Puppeteer MCP integration for SSE streaming validation
  - [ ] Test streaming message reception in real browser environment
  - [ ] Validate `credentials: 'include'` cookie handling
  - [ ] Test connection resilience and reconnection scenarios
- [ ] **5.2.1.3** Set up Fetch MCP for backend API validation
  - [ ] Test all chat endpoints (`/api/v1/chat/*`)
  - [ ] Validate authentication flows (JWT + cookies)
  - [ ] Test error response handling

##### 5.2.2 **Iterative Agentic Development Loop**
- [ ] **5.2.2.1** Implement automated test-driven development cycle
  - [ ] Write failing tests first for each feature
  - [ ] Use MCP agents to validate implementation
  - [ ] Iterate based on automated feedback
- [ ] **5.2.2.2** Set up design-review agent integration
  - [ ] Trigger design reviews after each major component
  - [ ] Use Playwright MCP for visual regression testing
  - [ ] Automate accessibility validation (WCAG 2.1 AA)
- [ ] **5.2.2.3** Create continuous validation pipeline
  - [ ] Run automated tests after each implementation step
  - [ ] Generate screenshots for visual comparison
  - [ ] Log performance metrics (TTFB, streaming latency)

##### 5.2.3 **Manual Testing Scenarios**
- [ ] **5.2.3.0** Pre-test Setup
  - [ ] Run `uv run python scripts/list_portfolios.py` to get actual portfolio IDs
  - [ ] Verify demo users have portfolios in database
  - [ ] Update test credentials to match existing users
  - [ ] Ensure portfolio service uses dynamic ID resolution
- [ ] **5.2.3.1** Test complete message flow (send → stream → display)
- [ ] **5.2.3.2** Test conversation persistence across page refresh  
- [ ] **5.2.3.3** Test mode switching functionality
- [ ] **5.2.3.4** Test error scenarios (network loss, auth expiry)
- [ ] **5.2.3.5** Test mobile responsiveness on real devices
- [ ] **5.2.3.6** Verify no console errors or memory leaks

## 6. **Polish & Deploy**

### 6.1 **Debugging + Bug Fixes**
#### 6.1.1 **Enhanced Observability (See Technical Specifications Section 8)**
- [ ] **6.1.1.1** Create `chatLogger.ts` using ChatLogEvent interface
  - [ ] Use traceId (same as run_id) for correlation
  - [ ] Implement structured logging with event types
  - [ ] Include ErrorType enum for classification
- [ ] **6.1.1.2** Create `debugStore.ts` for development debugging
  - [ ] Store ChatLogEvent history
  - [ ] Implement debug info aggregation
  - [ ] Add development debug panel (conditional)
- [ ] **6.1.1.3** Implement performance metrics in ChatLogEvent.data.metrics
  - [ ] Track ttfb (time to first byte) per request
  - [ ] Calculate tokensPerSecond during streaming
  - [ ] Record duration per conversation turn
  - [ ] Link all metrics to traceId/run_id
- [ ] **6.1.1.4** Integrate logging and metrics throughout chat flow
- [ ] **6.1.1.5** Test debugging and metrics in development mode
- [ ] **6.1.1.6** Prepare production monitoring hooks with performance data

#### 6.1.2 **Bug Fixes & Improvements**  
- [ ] **6.1.2.1** Fix any streaming connection issues
- [ ] **6.1.2.2** Resolve message display problems
- [ ] **6.1.2.3** Improve error message clarity
- [ ] **6.1.2.4** Optimize performance bottlenecks
- [ ] **6.1.2.5** Clean up console warnings/errors

### 6.2 **Deployment Checklist**
- [ ] **6.2.1** Enhanced Deployment Checklist
  - [ ] **6.2.1.1** Create comprehensive `deployment/STREAMING_CHECKLIST.md`
    - [ ] Use complete nginx config from Technical Specifications Section 7
      - [ ] proxy_buffering off, proxy_cache off, gzip off
      - [ ] All timeout settings (read: 300s, connect: 60s, send: 300s)
      - [ ] Proper HTTP/1.1 and Connection headers
      - [ ] CORS headers with credentials support
    - [ ] Load balancer configurations (no buffering, no gzip, timeouts)
    - [ ] Cloudflare/CDN settings for streaming
    - [ ] Environment-specific CORS configurations
    - [ ] Heartbeat intervals (≤15 seconds)
  - [ ] **6.2.1.2** Document production environment setup with headers
  - [ ] **6.2.1.3** Create deployment verification script
  - [ ] **6.2.1.4** Test staging deployment with enhanced checklist
  - [ ] **6.2.1.5** Validate all streaming and LB configurations

### 6.3 **Performance Testing**
- [ ] **6.3.1** Test with real conversation loads (50+ messages)
- [ ] **6.3.2** Measure streaming performance (< 3s to first token)
- [ ] **6.3.3** Test multiple concurrent conversations
- [ ] **6.3.4** Verify memory usage stays reasonable
- [ ] **6.3.5** Test long-running chat sessions
- [ ] **6.3.6** Profile and optimize bottlenecks

### 6.4 **Staging Deployment**
- [ ] **6.4.1** Deploy to staging environment
- [ ] **6.4.2** Test with team members using demo credentials
- [ ] **6.4.3** Gather feedback on UX and functionality
- [ ] **6.4.4** Document any production-specific issues
- [ ] **6.4.5** Create go/no-go decision for production

## 7. **Additional Features (Future/Optional)**

### 7.1 **UI Enhancement Components** (Post V1.1)
- [ ] **7.1.1** MessageList.tsx - Virtual scrolling for performance
- [ ] **7.1.2** MessageBubble.tsx - Rich message rendering with markdown
- [ ] **7.1.3** ToolExecution.tsx - Tool status display with collapsible results
- [ ] **7.1.4** ModeSelector.tsx - Visual mode switching interface

### 7.2 **Advanced Features** (Post V1.1)
- [ ] **7.2.1** Tool Result Rendering - Native table rendering instead of markdown
- [ ] **7.2.2** Conversation History Pagination - Load more with cursor pagination
- [ ] **7.2.3** Portfolio Context Integration - Auto-inject portfolio context
- [ ] **7.2.4** Smart Suggestions - Page-aware query suggestions
- [ ] **7.2.5** Real-time Typing Indicators - Show when assistant is thinking

## 8. **Technical Debt & Future Improvements**

### 8.1 **Code Quality**
- [ ] **8.1.1** Add unit tests for chat services and hooks
- [ ] **8.1.2** Add E2E tests for critical chat flows  
- [ ] **8.1.3** Implement comprehensive error boundaries
- [ ] **8.1.4** Add TypeScript types for all API responses
- [ ] **8.1.5** Document component APIs and service methods

### 8.2 **Production Readiness**
- [ ] **8.2.1** Remove API proxy for production (configure backend CORS)
- [ ] **8.2.2** Implement refresh token rotation
- [ ] **8.2.3** Add request caching with proper invalidation
- [ ] **8.2.4** Set up production monitoring and alerting
- [ ] **8.2.5** Create backup/recovery procedures for chat data

## 9. **Success Metrics**

### 9.1 **Technical Metrics**
- [ ] **9.1.1** < 3s to first token response
- [ ] **9.1.2** < 10s complete response time
- [ ] **9.1.3** < 1% error rate in production
- [ ] **9.1.4** 99% streaming uptime

### 9.2 **User Experience Metrics** 
- [ ] **9.2.1** > 50% user engagement rate
- [ ] **9.2.2** > 3 messages per chat session
- [ ] **9.2.3** < 10% conversation abandonment rate
- [ ] **9.2.4** > 4.0 user satisfaction score

## 10. **Key Dependencies & Constraints**

### 10.1 **External Dependencies**
- [ ] **10.1.1** Backend agent system (✅ Ready)
- [ ] **10.1.2** OpenAI API access (✅ Available)
- [ ] **10.1.3** Demo user credentials (✅ Working)
- [ ] **10.1.4** PostgreSQL database (✅ Set up)

### 10.2 **Technical Constraints**
- [ ] **10.2.1** Must maintain existing portfolio system (no breaking changes)
- [ ] **10.2.2** Must support mobile browsers (iOS Safari, Android Chrome)
- [ ] **10.2.3** Must handle 50+ concurrent users
- [ ] **10.2.4** Must work with Next.js proxy in development

## 11. **Notes & Decisions**

### 11.1 **Architecture Decisions Made**
- [ ] **11.1.1** fetch() POST streaming over EventSource (better control, JSON payloads) ✅
- [ ] **11.1.2** HttpOnly cookies over JWT localStorage (security, SSE compatibility) ✅
- [ ] **11.1.3** Mixed auth strategy (JWT for portfolio, cookies for chat) ✅
- [ ] **11.1.4** Split store architecture (performance optimization) ✅
- [ ] **11.1.5** Client-side message queue (UX improvement) ✅

### 11.2 **Key Implementation Guidelines**
- [ ] **11.2.1** Always use existing backend UUID system for tracing
- [ ] **11.2.2** Maintain backward compatibility with portfolio system
- [ ] **11.2.3** Prioritize mobile experience (60%+ mobile users expected)
- [ ] **11.2.4** Follow V1.1 simplifications (defer complex features)
- [ ] **11.2.5** Test with demo credentials before real user testing

---

## 🤖 **Agentic Implementation Approach**

**Implementation Priority**: 
- **Sections 1-5** are **CRITICAL** for basic functionality
- **Section 6** is **IMPORTANT** for production readiness  
- **Sections 7+** are **NICE-TO-HAVE** for future releases

**Iterative Development Cycle:**
Each major section (2.1, 2.2, 3, 4, 5) should follow this agentic loop:

1. **📋 Plan** → Review section requirements and create failing tests
2. **🔧 Implement** → Code features to pass automated tests  
3. **🤖 Validate** → Run MCP agents for comprehensive testing:
   - **Fetch MCP**: API endpoint validation
   - **Playwright MCP**: Browser automation and visual testing
   - **Puppeteer MCP**: Real-time SSE streaming validation
   - **Chat-testing agent**: Phase-specific comprehensive validation
   - **Design-review agent**: UX/accessibility compliance
4. **🔄 Iterate** → Refine based on agent feedback until all validations pass
5. **✅ Deploy** → Move to next section when quality gates are met

**Agent Invocation Commands:**
```bash
# After completing each section, invoke appropriate agent:
Task chat-testing "Test Section 2.1 Authentication" 
Task chat-testing "Test Section 2.2 SSE Streaming"
Task chat-testing "Test Section 3 Backend Integration"
Task design-review "Review mobile UI changes"
```

**Agent-Driven Quality Gates:**
- ✅ All MCP tests passing (0 failures)
- ✅ Chat-testing agent reports no [Blocker] issues
- ✅ Design review agent approves UX/accessibility  
- ✅ Performance metrics meet targets (< 3s TTFB, < 10s total)
- ✅ Visual regression tests show no unexpected changes
- ✅ Error scenarios handled gracefully
- ✅ Console free of errors in production mode

**Next Action**: Begin with **2.1 Authentication Migration** using the agentic development loop:
1. Write failing Playwright tests for auth flow
2. Implement cookie-based authentication
3. Invoke chat-testing agent for Phase 1 validation
4. Fix any [Blocker] or [High-Priority] issues
5. Move to Section 2.2 when all tests pass