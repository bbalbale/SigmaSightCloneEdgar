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
- **User**: `demo_growth@sigmasight.com` / `demo12345`
- **Portfolio ID**: Maps to actual portfolio data in backend
- **Chat Modes**: 4 conversation modes ready (/mode green|blue|indigo|violet)
- **Working Endpoints**: All 6 Raw Data APIs function properly for AI agent tools

## Overview

This TODO tracks the implementation of the chat functionality based on the comprehensive Chat Implementation Plan V1.1. All architectural decisions have been finalized and backend integration is complete. The focus is now on frontend implementation to connect the working UI components with the ready backend chat system.

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

**Frontend Implementation Tasks:**
- [ ] **2.1.1** Switch from JWT localStorage to HttpOnly cookies
  - [ ] **2.1.1.1** Create cookie-based auth service (`src/services/chatAuthService.ts`)
  - [ ] **2.1.1.2** Update login flow to use existing HttpOnly cookie functionality
  - [ ] **2.1.1.3** Update API proxy to forward cookies correctly with `credentials: 'include'`
  - [ ] **2.1.1.4** Test cookie auth with `/api/v1/auth/me` endpoint
  - [ ] **2.1.1.5** Implement logout to use existing cookie clearing backend
  - [ ] **2.1.1.6** Test authentication persistence across browser refresh

### 2.2 **Split Store Architecture + Streaming**
- [ ] **2.2.1** Split Store Architecture (From Feedback)
  - [ ] **2.2.1.1** Create separate `streamStore.ts` for runtime state
    - [ ] isStreaming, currentRunId, streamBuffer
    - [ ] abortController, messageQueue, processing flags
  - [ ] **2.2.1.2** Refactor `chatStore.ts` for persistent data only
    - [ ] conversations, messages (by conversationId), currentConversationId
    - [ ] Remove streaming state (isStreaming, streamingMessage)
  - [ ] **2.2.1.3** Update ChatInterface to use both stores
  - [ ] **2.2.1.4** Define comprehensive stream event schema with run_id + seq
    - [ ] Add sequence numbering for event ordering
    - [ ] Ensure all events include run_id for tracing
  - [ ] **2.2.1.5** Implement buffer → seal reconciliation on 'done' event
    - [ ] Buffer streaming content by run_id until 'done' event
    - [ ] Seal final message content on completion
  - [ ] **2.2.1.6** Enforce one in-flight per conversation with queue cap=1
    - [ ] Add conversation locks to prevent race conditions
    - [ ] Limit queue to 1 pending message per conversation
    - [ ] Clear queue on cancel/error
  - [ ] **2.2.1.7** Test performance improvement (fewer re-renders)

- [ ] **2.2.2** Implement fetch() Streaming Hook
  - [ ] **2.2.2.1** Create `useFetchStreaming.ts` hook
  - [ ] **2.2.2.2** Implement POST request with `credentials: 'include'`
  - [ ] **2.2.2.3** Add manual SSE parsing with ReadableStream
  - [ ] **2.2.2.4** Handle run_id for deduplication
  - [ ] **2.2.2.5** Implement stream buffer management
  - [ ] **2.2.2.6** Add AbortController for cleanup
  - [ ] **2.2.2.7** Test streaming with mock backend responses

### 3. **Backend Integration**
- [ ] **3.1** Create Chat Service
  - [ ] **3.1.1** Build `chatService.ts` with cookie-based API client
  - [ ] **3.1.2** Implement conversation management methods
    - [ ] createConversation(mode)
    - [ ] listConversations()  
    - [ ] deleteConversation(id)
    - [ ] getMessages(conversationId, limit, cursor)
  - [ ] **3.1.3** Implement message sending with streaming
  - [ ] **3.1.4** Add error handling with retryable classification

- [ ] **3.2** Connect UI to Backend
  - [ ] **3.2.1** Replace mock responses with real API calls
  - [ ] **3.2.2** Implement conversation lifecycle management
  - [ ] **3.2.3** Connect message history loading
  - [ ] **3.2.4** Test with demo user credentials (demo_growth@sigmasight.com)
  - [ ] **3.2.5** Handle conversation creation on first message
  - [ ] **3.2.6** Test mode switching (/mode green|blue|indigo|violet)

### 4. **Message Queue + Error Handling**

#### 4.1 **Client-Side Message Queue (Enhanced)**
- [ ] **4.1.1** Create `useMessageQueue.ts` hook
- [ ] **4.1.2** Implement enhanced queue management with visual feedback
  - [ ] Only one message processing at a time per conversation
  - [ ] Show "queued" badge for waiting messages
  - [ ] Display processing status
  - [ ] Enforce queue cap=1 (replace queued message if new one sent)
- [ ] **4.1.3** Integrate with streamStore for queue state
- [ ] **4.1.4** Add conversation-level locking mechanism
- [ ] **4.1.5** Test spam prevention (rapid send button clicks)
- [ ] **4.1.6** Test queue clearing on conversation cancel/error

#### 4.2 **Enhanced Error Handling with Taxonomy**
- [ ] **4.2.1** Implement comprehensive error taxonomy with UI behaviors
  - [ ] RATE_LIMITED: retry=true, delay=30s, show rate limit message
  - [ ] AUTH_EXPIRED: retry=false, redirect to login
  - [ ] NETWORK_ERROR: retry=true, delay=5s, show connection issue
  - [ ] SERVER_ERROR: retry=true, delay=10s, show server issue
  - [ ] CLIENT_ERROR: retry=false, show user-friendly validation message
- [ ] **4.2.2** Add retry logic with exponential backoff per error type
- [ ] **4.2.3** Implement error-specific UI behaviors and messages
- [ ] **4.2.4** Handle connection lost scenarios with reconnection
- [ ] **4.2.5** Test error recovery flows for each error type

### 5. **Mobile Optimization + Testing**

#### 5.1 **Mobile Input Handling (From Feedback)**
- [ ] **5.1.1** Create `mobile-chat.css` with environment variables
  - [ ] Use `env(safe-area-inset-bottom)` for iOS safe areas
  - [ ] Implement `scroll-margin-bottom` for input visibility
- [ ] **5.1.2** Add iOS Safari specific fixes with `@supports`
- [ ] **5.1.3** Test keyboard behavior on iOS/Android devices
- [ ] **5.1.4** Implement scroll-into-view on input focus
- [ ] **5.1.5** Test iPhone notch compatibility

#### 5.2 **Automated Testing & Validation**

##### 5.2.1 **MCP-Powered Automated Testing**
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
- [ ] **5.2.3.1** Test complete message flow (send → stream → display)
- [ ] **5.2.3.2** Test conversation persistence across page refresh  
- [ ] **5.2.3.3** Test mode switching functionality
- [ ] **5.2.3.4** Test error scenarios (network loss, auth expiry)
- [ ] **5.2.3.5** Test mobile responsiveness on real devices
- [ ] **5.2.3.6** Verify no console errors or memory leaks

## 6. **Polish & Deploy**

### 6.1 **Debugging + Bug Fixes**
#### 6.1.1 **Enhanced Observability & Performance Instrumentation**
- [ ] **6.1.1.1** Create `chatLogger.ts` with comprehensive trace context
  - [ ] Use existing backend UUIDs (conversation_id, message_id, request_id)
  - [ ] Implement structured logging with timestamps
  - [ ] Add error classification and retryable flags
- [ ] **6.1.1.2** Create `debugStore.ts` for development debugging
  - [ ] Store request history and streaming events
  - [ ] Implement debug info aggregation
  - [ ] Add development debug panel (conditional)
- [ ] **6.1.1.3** Implement performance instrumentation tied to run_id
  - [ ] Track TTFB (time to first byte) per streaming request
  - [ ] Measure tokens-per-second during streaming
  - [ ] Record total duration per conversation turn
  - [ ] Link all metrics to run_id for tracing
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
    - [ ] Enhanced nginx configuration for SSE endpoints
      - [ ] proxy_buffering off, proxy_cache off
      - [ ] gzip off (disable compression for streaming)
      - [ ] proxy_read_timeout 300s, proxy_connect_timeout 60s
      - [ ] proxy_send_timeout 300s
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