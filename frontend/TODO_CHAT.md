# Frontend Chat Implementation TODO

**Created:** 2025-09-01  
**Status:** V1.1 Implementation Phase  
**Target:** SigmaSight Portfolio Chat Assistant  
**Reference:** `_docs/requirements/CHAT_IMPLEMENTATION_PLAN.md`

## 🎯 Current Implementation Status

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

## 1.0 **V1.1 Implementation**

### 1.1 **Authentication Migration**
- [ ] **1.1.1** Switch from JWT localStorage to HttpOnly cookies
  - [ ] **1.1.1.1** Create cookie-based auth service (`src/services/chatAuthService.ts`)
  - [ ] **1.1.1.2** Modify login flow to set HttpOnly cookies
  - [ ] **1.1.1.3** Update API proxy to forward cookies correctly
  - [ ] **1.1.1.4** Test cookie auth with `/api/v1/auth/me` endpoint
  - [ ] **1.1.1.5** Implement logout with cookie clearing
  - [ ] **1.1.1.6** Test authentication persistence across browser refresh

### **Day 2: Split Store Architecture + Streaming** ⏳
- [ ] **8.1** Split Store Architecture (From Feedback)
  - [ ] **8.1.1** Create separate `streamStore.ts` for runtime state
    - [ ] isStreaming, currentRunId, streamBuffer
    - [ ] abortController, messageQueue, processing flags
  - [ ] **8.1.2** Refactor `chatStore.ts` for persistent data only
    - [ ] conversations, messages (by conversationId), currentConversationId
    - [ ] Remove streaming state (isStreaming, streamingMessage)
  - [ ] **8.1.3** Update ChatInterface to use both stores
  - [ ] **8.1.4** Define comprehensive stream event schema with run_id + seq
    - [ ] Add sequence numbering for event ordering
    - [ ] Ensure all events include run_id for tracing
  - [ ] **8.1.5** Implement buffer → seal reconciliation on 'done' event
    - [ ] Buffer streaming content by run_id until 'done' event
    - [ ] Seal final message content on completion
  - [ ] **8.1.6** Enforce one in-flight per conversation with queue cap=1
    - [ ] Add conversation locks to prevent race conditions
    - [ ] Limit queue to 1 pending message per conversation
    - [ ] Clear queue on cancel/error
  - [ ] **8.1.7** Test performance improvement (fewer re-renders)

- [ ] **2.2** Implement fetch() Streaming Hook
  - [ ] **2.2.1** Create `useFetchStreaming.ts` hook
  - [ ] **2.2.2** Implement POST request with `credentials: 'include'`
  - [ ] **2.2.3** Add manual SSE parsing with ReadableStream
  - [ ] **2.2.4** Handle run_id for deduplication
  - [ ] **2.2.5** Implement stream buffer management
  - [ ] **2.2.6** Add AbortController for cleanup
  - [ ] **2.2.7** Test streaming with mock backend responses

### **Day 3: Backend Integration** ⏳
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

### **Day 4: Message Queue + Error Handling** ⏳
- [ ] **8.2** Client-Side Message Queue (Enhanced)
  - [ ] **8.2.1** Create `useMessageQueue.ts` hook
  - [ ] **8.2.2** Implement enhanced queue management with visual feedback
    - [ ] Only one message processing at a time per conversation
    - [ ] Show "queued" badge for waiting messages
    - [ ] Display processing status
    - [ ] Enforce queue cap=1 (replace queued message if new one sent)
  - [ ] **8.2.3** Integrate with streamStore for queue state
  - [ ] **8.2.4** Add conversation-level locking mechanism
  - [ ] **8.2.5** Test spam prevention (rapid send button clicks)
  - [ ] **8.2.6** Test queue clearing on conversation cancel/error

- [ ] **4.1** Enhanced Error Handling with Taxonomy
  - [ ] **4.1.1** Implement comprehensive error taxonomy with UI behaviors
    - [ ] RATE_LIMITED: retry=true, delay=30s, show rate limit message
    - [ ] AUTH_EXPIRED: retry=false, redirect to login
    - [ ] NETWORK_ERROR: retry=true, delay=5s, show connection issue
    - [ ] SERVER_ERROR: retry=true, delay=10s, show server issue
    - [ ] CLIENT_ERROR: retry=false, show user-friendly validation message
  - [ ] **4.1.2** Add retry logic with exponential backoff per error type
  - [ ] **4.1.3** Implement error-specific UI behaviors and messages
  - [ ] **4.1.4** Handle connection lost scenarios with reconnection
  - [ ] **4.1.5** Test error recovery flows for each error type

### **Day 5: Mobile Optimization + Testing** ⏳
- [ ] **8.3** Mobile Input Handling (From Feedback)
  - [ ] **8.3.1** Create `mobile-chat.css` with environment variables
    - [ ] Use `env(safe-area-inset-bottom)` for iOS safe areas
    - [ ] Implement `scroll-margin-bottom` for input visibility
  - [ ] **8.3.2** Add iOS Safari specific fixes with `@supports`
  - [ ] **8.3.3** Test keyboard behavior on iOS/Android devices
  - [ ] **8.3.4** Implement scroll-into-view on input focus
  - [ ] **8.3.5** Test iPhone notch compatibility

- [ ] **5.1** Basic Testing
  - [ ] **5.1.1** Test complete message flow (send → stream → display)
  - [ ] **5.1.2** Test conversation persistence across page refresh
  - [ ] **5.1.3** Test mode switching functionality
  - [ ] **5.1.4** Test error scenarios (network loss, auth expiry)
  - [ ] **5.1.5** Test mobile responsiveness
  - [ ] **5.1.6** Verify no console errors or memory leaks

## 🎯 **WEEK 2 - Polish & Deploy**

### **Day 1-2: Debugging + Bug Fixes** ⏳
- [ ] **6.1** Enhanced Observability & Performance Instrumentation
  - [ ] **6.1.1** Create `chatLogger.ts` with comprehensive trace context
    - [ ] Use existing backend UUIDs (conversation_id, message_id, request_id)
    - [ ] Implement structured logging with timestamps
    - [ ] Add error classification and retryable flags
  - [ ] **6.1.2** Create `debugStore.ts` for development debugging
    - [ ] Store request history and streaming events
    - [ ] Implement debug info aggregation
    - [ ] Add development debug panel (conditional)
  - [ ] **6.1.3** Implement performance instrumentation tied to run_id
    - [ ] Track TTFB (time to first byte) per streaming request
    - [ ] Measure tokens-per-second during streaming
    - [ ] Record total duration per conversation turn
    - [ ] Link all metrics to run_id for tracing
  - [ ] **6.1.4** Integrate logging and metrics throughout chat flow
  - [ ] **6.1.5** Test debugging and metrics in development mode
  - [ ] **6.1.6** Prepare production monitoring hooks with performance data

- [ ] **6.2** Bug Fixes & Improvements  
  - [ ] **6.2.1** Fix any streaming connection issues
  - [ ] **6.2.2** Resolve message display problems
  - [ ] **6.2.3** Improve error message clarity
  - [ ] **6.2.4** Optimize performance bottlenecks
  - [ ] **6.2.5** Clean up console warnings/errors

### **Day 3: Deployment Checklist** ⏳
- [ ] **7.1** Enhanced Deployment Checklist
  - [ ] **7.1.1** Create comprehensive `deployment/STREAMING_CHECKLIST.md`
    - [ ] Enhanced nginx configuration for SSE endpoints
      - [ ] proxy_buffering off, proxy_cache off
      - [ ] gzip off (disable compression for streaming)
      - [ ] proxy_read_timeout 300s, proxy_connect_timeout 60s
      - [ ] proxy_send_timeout 300s
    - [ ] Load balancer configurations (no buffering, no gzip, timeouts)
    - [ ] Cloudflare/CDN settings for streaming
    - [ ] Environment-specific CORS configurations
    - [ ] Heartbeat intervals (≤15 seconds)
  - [ ] **7.1.2** Document production environment setup with headers
  - [ ] **7.1.3** Create deployment verification script
  - [ ] **7.1.4** Test staging deployment with enhanced checklist
  - [ ] **7.1.5** Validate all streaming and LB configurations

### **Day 4: Performance Testing** ⏳
- [ ] **8.1** Performance Testing
  - [ ] **8.1.1** Test with real conversation loads (50+ messages)
  - [ ] **8.1.2** Measure streaming performance (< 3s to first token)
  - [ ] **8.1.3** Test multiple concurrent conversations
  - [ ] **8.1.4** Verify memory usage stays reasonable
  - [ ] **8.1.5** Test long-running chat sessions
  - [ ] **8.1.6** Profile and optimize bottlenecks

### **Day 5: Staging Deployment** ⏳
- [ ] **9.1** Staging Deployment
  - [ ] **9.1.1** Deploy to staging environment
  - [ ] **9.1.2** Test with team members using demo credentials
  - [ ] **9.1.3** Gather feedback on UX and functionality
  - [ ] **9.1.4** Document any production-specific issues
  - [ ] **9.1.5** Create go/no-go decision for production

## 10.0 **Additional Features (Future/Optional)**

### 10.1 **UI Enhancement Components** (Post V1.1)
- [ ] **10.1.1** MessageList.tsx - Virtual scrolling for performance
- [ ] **10.1.2** MessageBubble.tsx - Rich message rendering with markdown
- [ ] **10.1.3** ToolExecution.tsx - Tool status display with collapsible results
- [ ] **10.1.4** ModeSelector.tsx - Visual mode switching interface

### 10.2 **Advanced Features** (Post V1.1)
- [ ] **10.2.1** Tool Result Rendering - Native table rendering instead of markdown
- [ ] **10.2.2** Conversation History Pagination - Load more with cursor pagination
- [ ] **10.2.3** Portfolio Context Integration - Auto-inject portfolio context
- [ ] **10.2.4** Smart Suggestions - Page-aware query suggestions
- [ ] **10.2.5** Real-time Typing Indicators - Show when assistant is thinking

## 11.0 **Technical Debt & Future Improvements**

### 11.1 **Code Quality**
- [ ] **11.1.1** Add unit tests for chat services and hooks
- [ ] **11.1.2** Add E2E tests for critical chat flows  
- [ ] **11.1.3** Implement comprehensive error boundaries
- [ ] **11.1.4** Add TypeScript types for all API responses
- [ ] **11.1.5** Document component APIs and service methods

### 11.2 **Production Readiness**
- [ ] **11.2.1** Remove API proxy for production (configure backend CORS)
- [ ] **11.2.2** Implement refresh token rotation
- [ ] **11.2.3** Add request caching with proper invalidation
- [ ] **11.2.4** Set up production monitoring and alerting
- [ ] **11.2.5** Create backup/recovery procedures for chat data

## 12.0 **Success Metrics**

### 12.1 **Technical Metrics**
- [ ] **12.1.1** < 3s to first token response
- [ ] **12.1.2** < 10s complete response time
- [ ] **12.1.3** < 1% error rate in production
- [ ] **12.1.4** 99% streaming uptime

### 12.2 **User Experience Metrics** 
- [ ] **12.2.1** > 50% user engagement rate
- [ ] **12.2.2** > 3 messages per chat session
- [ ] **12.2.3** < 10% conversation abandonment rate
- [ ] **12.2.4** > 4.0 user satisfaction score

## 13.0 **Key Dependencies & Constraints**

### 13.1 **External Dependencies**
- [ ] **13.1.1** Backend agent system (✅ Ready)
- [ ] **13.1.2** OpenAI API access (✅ Available)
- [ ] **13.1.3** Demo user credentials (✅ Working)
- [ ] **13.1.4** PostgreSQL database (✅ Set up)

### 13.2 **Technical Constraints**
- [ ] **13.2.1** Must maintain existing portfolio system (no breaking changes)
- [ ] **13.2.2** Must support mobile browsers (iOS Safari, Android Chrome)
- [ ] **13.2.3** Must handle 50+ concurrent users
- [ ] **13.2.4** Must work with Next.js proxy in development

## 14.0 **Notes & Decisions**

### 14.1 **Architecture Decisions Made**
- [ ] **14.1.1** fetch() POST streaming over EventSource (better control, JSON payloads) ✅
- [ ] **14.1.2** HttpOnly cookies over JWT localStorage (security, SSE compatibility) ✅
- [ ] **14.1.3** Mixed auth strategy (JWT for portfolio, cookies for chat) ✅
- [ ] **14.1.4** Split store architecture (performance optimization) ✅
- [ ] **14.1.5** Client-side message queue (UX improvement) ✅

### 14.2 **Key Implementation Guidelines**
- [ ] **14.2.1** Always use existing backend UUID system for tracing
- [ ] **14.2.2** Maintain backward compatibility with portfolio system
- [ ] **14.2.3** Prioritize mobile experience (60%+ mobile users expected)
- [ ] **14.2.4** Follow V1.1 simplifications (defer complex features)
- [ ] **14.2.5** Test with demo credentials before real user testing

---

**Implementation Priority**: 
- **Sections 1.0-5.0** are **CRITICAL** for basic functionality
- **Sections 6.0-9.0** are **IMPORTANT** for production readiness  
- **Sections 10.0+** are **NICE-TO-HAVE** for future releases

**Next Action**: Begin with 1.0 Authentication Migration - this unblocks all subsequent work.