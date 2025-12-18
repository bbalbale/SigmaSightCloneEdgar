# PRD3: AI System Consolidation Plan

## Executive Summary

SigmaSight currently has **3 separate AI systems** that have diverged from the original PRD architecture. This document provides a consolidation plan to merge everything into **ONE cohesive system** built on:

- **OpenAI Responses API** (per PRD1)
- **RAG with pgvector** (knowledge base)
- **18+ registered tools** (portfolio data access)
- **Backend-routed architecture** (secure, no exposed API keys)

**CRITICAL**: Before consolidation, we must first diagnose and fix **Railway environment issues**. Everything works locally but fails on Railway.

**Target Completion**: 2-3 development sessions (diagnosis + consolidation)

---

## Current State Analysis

### Known Issues (As of 2025-12-18)

| Feature | Local (localhost:8000) | Railway | Issue |
|---------|------------------------|---------|-------|
| Generate Insight | WORKING | BROKEN | "Unable to generate insights" - **BUG FOUND & FIXED** |
| Chat Backend API | UNKNOWN | **WORKING** | Tested via curl - tools work, streaming works |
| Chat Frontend | UNKNOWN | BROKEN | Frontend not receiving responses |

### Root Cause Analysis (Completed 2025-12-18)

**Insight Generation Bug (FIXED):**
The `generate_insight` method in `openai_service.py` had a bug in the tool continuation logic:
1. When OpenAI returned tool calls, the code was incorrectly replacing `messages` with just tool outputs
2. This lost the conversation context and broke the continuation
3. The OpenAI Responses API needs the full conversation flow: user → function_call → function_call_output → response

**Fix Applied:**
- Modified tool continuation to **append** function calls and outputs to messages (not replace)
- Added `text` format parameter to match streaming calls
- Removed unused `previous_response_id` logic
- Added detailed debug logging

**Chat Backend:**
- Tested via curl: `/api/v1/chat/send` works correctly
- Tools execute and return data (portfolio, positions, etc.)
- SSE streaming works with token events

**Chat Frontend Issue:**
- Frontend chat interface not receiving responses from working backend
- Likely issue with SSE connection handling or service layer
- Need to investigate `aiChatService.ts` and frontend components

### The 3 Systems

| System | Location | API Key | RAG | Tools | Status |
|--------|----------|---------|-----|-------|--------|
| **1. Frontend Direct** | `services/ai/chatService.ts` | `NEXT_PUBLIC_OPENAI_API_KEY` | NO | NO | BROKEN - key deleted, TO DELETE |
| **2. Backend Chat** | `services/aiChatService.ts` | Backend `OPENAI_API_KEY` | YES | YES | BROKEN on Railway |
| **3. Backend Insights** | `services/insightsApi.ts` | Backend `OPENAI_API_KEY` | Partial | YES | BROKEN on Railway |

### System 1: Frontend Direct OpenAI (TO BE REMOVED)

**Files:**
- `frontend/src/services/ai/chatService.ts` - Direct OpenAI client
- `frontend/app/api/openai-proxy/route.ts` - Edge proxy route
- `frontend/app/api/openai-proxy/chat/completions/route.ts` - Chat completions proxy
- `frontend/src/hooks/useFetchStreaming.ts` - Uses frontend chatService

**Problems:**
- Requires `NEXT_PUBLIC_OPENAI_API_KEY` exposed to browser
- No RAG integration
- No tool calling
- No knowledge base access
- Duplicates backend functionality
- Currently BROKEN (Railway deleted the key)

**Usage:**
- `useFetchStreaming.ts` imports from `@/services/ai/chatService`

### System 2: Backend Chat (TARGET - KEEP)

**Files:**
- `frontend/src/services/aiChatService.ts` - SSE streaming to backend
- `frontend/src/services/chatService.ts` - Conversation CRUD
- `backend/app/api/v1/chat/send.py` - SSE streaming endpoint
- `backend/app/agent/services/openai_service.py` - OpenAI Responses API

**Features:**
- OpenAI Responses API (per PRD1)
- RAG integration with pgvector
- 18+ registered tools
- Knowledge base access
- SSE streaming
- Secure (API key on backend only)

**Usage:**
- `AIChatInterface.tsx` - AI chat page
- `useCopilot.ts` - Copilot hook
- `ChatConversationPane.tsx` - Conversation management

### System 3: Backend Insights (KEEP - USES SAME BACKEND)

**Files:**
- `frontend/src/services/insightsApi.ts` - Insight API client
- `backend/app/api/v1/insights.py` - Insight generation endpoint
- `backend/app/services/analytical_reasoning_service.py` - Orchestration
- `backend/app/agent/services/openai_service.py` - Shared with System 2

**Features:**
- Uses same `openai_service.generate_insight()` as chat
- Has tool access
- Stores insights in database
- Performance tracking

**Usage:**
- `useAIInsights.ts` - Insight generation hook
- `useInsights.ts` - Insight management
- `SigmaSightAIContainer.tsx` - AI page container
- Various insight components

---

## Target Architecture

After consolidation, there will be **ONE AI system**:

```
Frontend                          Backend
--------                          -------

aiChatService.ts  ─────────────>  /api/v1/chat/send
     │                                   │
     │                                   ▼
     │                            openai_service.py
     │                                   │
     │                            ┌──────┴──────┐
     │                            │             │
     │                          RAG          Tools (18+)
     │                      (rag_service)  (tool_registry)
     │                            │             │
     │                            └──────┬──────┘
     │                                   │
     │                            OpenAI Responses API
     │                            (gpt-4o-mini / gpt-5-mini)
     │
insightsApi.ts  ──────────────>  /api/v1/insights/generate
                                         │
                                         ▼
                                  analytical_reasoning_service.py
                                         │
                                         ▼
                                  openai_service.generate_insight()
                                  (same openai_service, same tools)
```

**Key Principle:** All AI calls go through the backend. Frontend NEVER calls OpenAI directly.

---

## Phase 0: Diagnose Railway Issues (MUST DO FIRST)

Before any consolidation, we need to understand why the backend works locally but fails on Railway.

### 0.1 Check Railway Backend Logs

```bash
# View recent logs from Railway backend
railway logs --service sigmasight-be

# Look for:
# - Database connection errors
# - OPENAI_API_KEY usage errors
# - Tool execution failures
# - Auth token issues
```

### 0.2 Verify Railway Environment Variables

**Required for AI features:**
```bash
OPENAI_API_KEY=sk-...        # CRITICAL - must be set
DATABASE_URL=postgresql://...  # Must point to Railway Postgres
```

**Check these are set in Railway Dashboard → Backend Service → Variables**

### 0.3 Test Database Connectivity on Railway

The insight generation needs to:
1. Query portfolios from database
2. Query positions from database
3. Access market data

If the database connection is broken, insights will fail.

```bash
# SSH into Railway and test database
railway run python -c "
from app.database import get_async_session
import asyncio

async def test():
    async with get_async_session() as db:
        from sqlalchemy import text
        result = await db.execute(text('SELECT COUNT(*) FROM portfolios'))
        print(f'Portfolios: {result.scalar()}')

asyncio.run(test())
"
```

### 0.4 Test Tool Authentication on Railway

The chat tools make authenticated API calls. On Railway, the auth token propagation may be failing.

**How tools work:**
1. Frontend sends JWT token to `/api/v1/chat/send`
2. Backend extracts token and passes to tool handlers
3. Tools use token to call other API endpoints (e.g., `/api/v1/data/portfolio/{id}/complete`)

**Potential Railway issues:**
- Token not being extracted from headers correctly
- Internal API calls failing due to Railway networking
- CORS or proxy issues

### 0.5 Diagnostic Checklist

Run these checks on Railway:

- [ ] `OPENAI_API_KEY` is set and valid
- [ ] `DATABASE_URL` points to Railway Postgres
- [ ] Database has portfolio data (run audit script)
- [ ] Backend can connect to database
- [ ] Backend logs show incoming requests
- [ ] Tool calls show auth token present
- [ ] No CORS errors in browser console

### 0.6 Common Railway Issues

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| "Unable to generate insights" | Database query failing | Check DATABASE_URL, run migrations |
| Tools can't see portfolio | Auth token not propagated | Check token extraction in tool handlers |
| 401 errors | OPENAI_API_KEY missing/invalid | Set in Railway variables |
| Timeout errors | Railway cold start | Increase timeout, add keep-alive |
| "No portfolios found" | Database empty | Run seed script on Railway |

---

## Consolidation Plan (After Phase 0 is Complete)

### Phase 1: Remove Frontend Direct System (30 min)

**Goal:** Delete all frontend direct OpenAI code.

#### 1.1 Delete Frontend Direct Files

```bash
# Files to DELETE:
frontend/src/services/ai/chatService.ts
frontend/src/services/ai/  # entire directory if empty after
frontend/app/api/openai-proxy/route.ts
frontend/app/api/openai-proxy/chat/completions/route.ts
frontend/app/api/openai-proxy/  # entire directory
```

#### 1.2 Update useFetchStreaming.ts

The `useFetchStreaming.ts` hook currently imports from the wrong service. Options:

**Option A (Recommended): Delete and migrate callers to aiChatService**
- Delete `frontend/src/hooks/useFetchStreaming.ts`
- Update any callers to use `aiChatService.sendMessage()` instead

**Option B: Rewrite to use aiChatService**
- Keep the hook but change its implementation to use `aiChatService`

#### 1.3 Remove Environment Variable

```bash
# Remove from Railway frontend service:
NEXT_PUBLIC_OPENAI_API_KEY  # DELETE - no longer needed
```

### Phase 2: Verify Backend Chat System (15 min)

**Goal:** Ensure the target system is fully functional.

#### 2.1 Verify OpenAI API Key

```bash
# Railway backend service must have:
OPENAI_API_KEY=sk-...  # Required for all AI features
```

#### 2.2 Test Chat Endpoint

```bash
# Test /api/v1/chat/send
curl -X POST https://your-backend.railway.app/api/v1/chat/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode": "green"}'
```

#### 2.3 Test Insight Generation

```bash
# Test /api/v1/insights/generate
curl -X POST https://your-backend.railway.app/api/v1/insights/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"portfolio_id": "...", "insight_type": "morning_briefing"}'
```

### Phase 3: Consolidate Chat Services (20 min)

**Goal:** Ensure one clear chat service pattern.

#### 3.1 Service Responsibilities

Keep these services with clear responsibilities:

| Service | Responsibility |
|---------|---------------|
| `aiChatService.ts` | SSE streaming to `/api/v1/chat/send` |
| `chatService.ts` | Conversation CRUD (create, list, delete) |
| `chatAuthService.ts` | Authentication helpers |
| `insightsApi.ts` | Insight generation via `/api/v1/insights/generate` |

#### 3.2 Update Frontend Components

Ensure all chat components use the correct services:

```typescript
// CORRECT - use aiChatService for streaming
import { sendMessage, createNewConversation } from '@/services/aiChatService'

// CORRECT - use chatService for CRUD
import { chatService } from '@/services/chatService'

// WRONG - delete these imports
// import { chatService } from '@/services/ai/chatService'  // DELETE
```

### Phase 4: Cleanup and Documentation (15 min)

#### 4.1 Update CLAUDE.md Files

Update `frontend/CLAUDE.md` to reflect:
- Only ONE AI system (backend-routed)
- No `NEXT_PUBLIC_OPENAI_API_KEY` needed
- Service layer is the only way to make AI calls

#### 4.2 Update Environment Documentation

Update `.env.example` files:

**Backend `.env`:**
```bash
OPENAI_API_KEY=sk-...  # Required - used for chat, insights, RAG embeddings
```

**Frontend `.env.local`:**
```bash
# No OPENAI keys needed - all AI calls go through backend
NEXT_PUBLIC_BACKEND_API_URL=https://your-backend.railway.app/api/v1
```

---

## Files to Delete

```
frontend/
├── src/
│   ├── services/
│   │   └── ai/
│   │       └── chatService.ts          # DELETE
│   └── hooks/
│       └── useFetchStreaming.ts        # DELETE (or rewrite)
└── app/
    └── api/
        └── openai-proxy/
            ├── route.ts                # DELETE
            └── chat/
                └── completions/
                    └── route.ts        # DELETE
```

## Files to Keep

```
frontend/
├── src/
│   ├── services/
│   │   ├── aiChatService.ts            # KEEP - SSE streaming
│   │   ├── chatService.ts              # KEEP - Conversation CRUD
│   │   ├── chatAuthService.ts          # KEEP - Auth helpers
│   │   └── insightsApi.ts              # KEEP - Insight generation
│   └── hooks/
│       ├── useCopilot.ts               # KEEP - Uses aiChatService
│       ├── useAIInsights.ts            # KEEP - Uses insightsApi
│       └── useInsights.ts              # KEEP - Uses insightsApi

backend/
├── app/
│   ├── agent/
│   │   ├── services/
│   │   │   ├── openai_service.py       # KEEP - Core LLM service
│   │   │   ├── rag_service.py          # KEEP - RAG embeddings
│   │   │   └── memory_service.py       # KEEP - User memories
│   │   ├── tools/
│   │   │   ├── tool_registry.py        # KEEP - 18+ tools
│   │   │   └── handlers.py             # KEEP - Tool implementations
│   │   └── prompts/                    # KEEP - Prompt templates
│   └── api/v1/
│       ├── chat/
│       │   └── send.py                 # KEEP - SSE endpoint
│       └── insights.py                 # KEEP - Insight generation
```

---

## Revised Execution Order

**The order matters. Do NOT skip ahead.**

```
Phase 0: Diagnose Railway Issues
    │
    ├── 0.1 Check logs
    ├── 0.2 Verify env vars
    ├── 0.3 Test database
    ├── 0.4 Test tool auth
    └── 0.5 Fix identified issues
         │
         ▼
    [Railway backend working?]
         │
    YES ─┴── NO → Fix before proceeding
         │
         ▼
Phase 1: Remove Frontend Direct System
    │
    ▼
Phase 2: Verify Backend Chat System
    │
    ▼
Phase 3: Consolidate Chat Services
    │
    ▼
Phase 4: Cleanup and Documentation
```

---

## Verification Checklist

### Phase 0 Complete (Railway Working):

- [ ] Railway backend logs show no database errors
- [ ] `OPENAI_API_KEY` set and valid on Railway backend
- [ ] Database has portfolio data (3 portfolios, 63 positions)
- [ ] Generate Insight works on Railway (returns insight, not error)
- [ ] Chat can access portfolio via tools on Railway

### Phases 1-4 Complete (Consolidation Done):

- [ ] `NEXT_PUBLIC_OPENAI_API_KEY` removed from Railway frontend
- [ ] `/api/openai-proxy/` routes deleted
- [ ] `services/ai/chatService.ts` deleted
- [ ] `useFetchStreaming.ts` deleted or rewritten
- [ ] Chat works via `aiChatService.ts` → `/api/v1/chat/send`
- [ ] Insights work via `insightsApi.ts` → `/api/v1/insights/generate`
- [ ] RAG documents are being retrieved (check backend logs)
- [ ] Tools are being called (check backend logs for tool_call events)
- [ ] No TypeScript errors (`npm run type-check`)
- [ ] Frontend builds successfully (`npm run build`)

---

## Post-Consolidation Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │ aiChatService   │    │ insightsApi     │                    │
│  │ (SSE streaming) │    │ (REST)          │                    │
│  └────────┬────────┘    └────────┬────────┘                    │
│           │                      │                              │
└───────────┼──────────────────────┼──────────────────────────────┘
            │                      │
            ▼                      ▼
┌───────────────────────────────────────────────────────────────────┐
│                         BACKEND                                   │
│                                                                   │
│  ┌─────────────────┐    ┌─────────────────────────┐              │
│  │ /chat/send      │    │ /insights/generate      │              │
│  │ (SSE)           │    │ (REST)                  │              │
│  └────────┬────────┘    └────────┬────────────────┘              │
│           │                      │                                │
│           ▼                      ▼                                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    openai_service.py                        │  │
│  │                                                             │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │  │
│  │  │ RAG Service │  │ Tool        │  │ Prompt Manager      │ │  │
│  │  │ (pgvector)  │  │ Registry    │  │                     │ │  │
│  │  └─────────────┘  │ (18+ tools) │  └─────────────────────┘ │  │
│  │                   └─────────────┘                          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              │                                    │
│                              ▼                                    │
│                    ┌─────────────────────┐                       │
│                    │ OpenAI Responses    │                       │
│                    │ API                 │                       │
│                    │ (gpt-4o-mini)       │                       │
│                    └─────────────────────┘                       │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Benefits of Consolidation

1. **Security**: No API keys exposed to browser
2. **Consistency**: One LLM interface, one set of tools
3. **RAG**: All AI calls benefit from knowledge base
4. **Tools**: All AI calls can use portfolio data tools
5. **Maintainability**: One system to maintain, debug, and improve
6. **Cost Control**: All API usage goes through backend (can add rate limiting, caching)
7. **Observability**: All AI calls logged in one place

---

## Appendix: PRD1 Compliance

This consolidation aligns with PRD1 Section 1.1:

> "For SigmaSight's current stack (Python backend, Next.js frontend, Railway hosting), we use **OpenAI as the default provider**"

And Rule 4 from the Overview:

> "Use OpenAI Responses API, not Chat Completions."

The consolidated system:
- Uses OpenAI as the sole provider
- Uses Responses API (not Chat Completions)
- Routes all calls through backend
- Leverages RAG and tools as designed

---

**Document Created**: 2025-12-18
**Author**: Claude (AI Coding Agent)
**Status**: Ready for execution
