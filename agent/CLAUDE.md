# CLAUDE.md

> **Updated for V1.1 Chat Implementation - Mixed Auth & fetch() Streaming**

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**V1.1 Critical Updates**:
- **Authentication**: Mixed strategy (JWT for portfolio, HttpOnly cookies for chat streaming)
- **Streaming**: fetch() POST with credentials:'include' instead of EventSource
- **State Management**: Frontend uses split store architecture (chatStore + streamStore)
- **Message Queue**: One in-flight per conversation with queue cap=1
- **Error Handling**: Enhanced taxonomy with retryable classification

## 🚨 CRITICAL: Autonomous Development Guidelines

### Things Requiring EXPLICIT User Help
**YOU MUST ASK THE USER TO:**
1. **Environment Setup**
   - Add OpenAI API key to backend/.env file (`OPENAI_API_KEY=sk-...`)
   - Launch Docker Desktop application before running PostgreSQL
   - Verify Docker containers are running: `docker-compose up -d`

2. **External Services**
   - Obtain API keys (OpenAI, Polygon, FMP, FRED)
   - Verify API key validity with providers
   - Set up monitoring/alerting services

### Things Requiring EXPLICIT Permission
**NEVER DO WITHOUT APPROVAL:**

1. **Database Changes**
   - ❌ Modifying ANY existing backend tables (users, portfolios, positions)
   - ❌ Creating database changes without Alembic migrations
   - ✅ OK: Creating new agent_* prefixed tables via Alembic ONLY

2. **API Contract Changes**
   - ❌ Modifying existing backend Pydantic models in app/schemas/
   - ❌ Changing existing endpoint signatures
   - ⚠️ V1.1: Login endpoint MUST set both JWT and HttpOnly cookies
   - ⚠️ V1.1: Chat endpoints MUST support credentials:'include' for cookies
   - ✅ OK: Adding optional run_id parameter for deduplication
   - ✅ OK: Creating new /api/v1/chat/* endpoints

3. **Authentication & Security** (V1.1 Mixed Strategy)
   - ❌ Breaking changes to JWT token generation/validation
   - ⚠️ V1.1: Login MUST set HttpOnly cookies for chat in addition to JWT
   - ⚠️ V1.1: Chat endpoints MUST validate both Bearer tokens AND cookies
   - ✅ OK: Mixed auth - JWT for portfolio APIs, cookies for streaming
   - ✅ OK: Using existing auth dependencies with cookie support

4. **External Service Integration**
   - ❌ Adding new paid API dependencies
   - ❌ Changing OpenAI usage patterns that increase costs
   - ✅ OK: Using configured OpenAI with existing key

5. **Architectural Decisions**
   - ❌ Changing Agent/Backend service separation
   - ❌ Modifying communication protocols (REST/SSE)
   - ✅ OK: Following established patterns in TODO.md

## Project Overview

SigmaSight Agent - A backend chat API that connects OpenAI with portfolio analysis tools via SSE streaming. The agent answers portfolio questions using function calling to Raw Data APIs.

**Current Status**: Phase 8+ Complete - Full implementation with OpenAI integration, prompts, and documentation. Ready for frontend development and production testing.

## Architecture

### High-Level Design
```
User → POST /chat/send → Backend Agent → OpenAI gpt-4o → Tools → Raw Data APIs
                              ↓
                        SSE Stream Response
```

The agent is a **backend-only** service that:
1. Receives chat messages via REST API
2. Authenticates using JWT Bearer tokens (from main backend)
3. Calls OpenAI with function tools mapped to Raw Data endpoints
4. Streams responses back via Server-Sent Events (SSE)

### Key Architectural Decisions
- **Vendor-agnostic conversation IDs**: Use our UUID as primary key, store provider IDs as metadata
- **No pagination**: Hard caps on tool responses (5 symbols, 180 days, 200 positions)
- **SSE streaming**: Not WebSockets, use text/event-stream with heartbeats
- **Backend-only OpenAI**: Never expose API keys to frontend
- **UTC ISO 8601**: All timestamps use Z suffix format

## Development Commands

### Backend Integration
```bash
# The agent runs as part of the main backend
cd ../backend
uv run python run.py              # Start development server with agent endpoints

# Database migrations for conversation tables
cd ../backend
uv run alembic revision --autogenerate -m "Add conversation tables for agent"
uv run alembic upgrade head

# Run tests (when implemented)
cd ../backend
uv run pytest tests/test_agent/
```

### Environment Setup
Required in backend/.env:
```
OPENAI_API_KEY=sk-...
MODEL_DEFAULT=gpt-4o              # Use gpt-4o for streaming (gpt-5 requires org verification)
MODEL_FALLBACK=gpt-4o-mini        # Fallback model
SSE_HEARTBEAT_INTERVAL_MS=15000
AGENT_CACHE_TTL=600
```

## File Structure & Implementation Path

### Phase 0: Prerequisites (Current)
1. Update `backend/app/config.py` with OpenAI settings
2. Create conversation models in `backend/app/models/conversations.py`
3. Run Alembic migration

### Phase 1: Chat Module
Create in `backend/app/api/v1/chat/`:
- `router.py` - FastAPI router registration
- `conversations.py` - POST /chat/conversations endpoint
- `send.py` - POST /chat/send SSE endpoint
- `tools.py` - Tool handler implementations
- `schemas.py` - Pydantic models

### Phase 2: Tool Handlers
Map 6 Raw Data endpoints to OpenAI function tools:
- `get_portfolio_complete` → `/api/v1/data/portfolio/{id}/complete`
- `get_portfolio_data_quality` → `/api/v1/data/portfolio/{id}/data-quality`
- `get_positions_details` → `/api/v1/data/positions/details`
- `get_prices_historical` → `/api/v1/data/prices/historical/{id}`
- `get_current_quotes` → `/api/v1/data/prices/quotes`
- `get_factor_etf_prices` → `/api/v1/data/factors/etf-prices`

### Phase 3: Prompts
Create in `backend/app/agent/prompts/`:
- `green_v001.md` - Educational, explanatory mode (default)
- `blue_v001.md` - Concise, quantitative mode
- `indigo_v001.md` - Strategic, narrative mode
- `violet_v001.md` - Conservative, risk-focused mode

## Critical Context

### What Already Exists (Don't Rebuild)
- **Authentication**: JWT Bearer tokens in `backend/app/core/dependencies.py`
- **Database patterns**: Async SQLAlchemy in `backend/app/database.py`
- **Raw Data APIs**: 100% working with real data (need parameter enhancements)
- **UTC datetime**: Already standardized with utilities in `backend/app/core/datetime_utils.py`

### What Needs Building
- Chat endpoints (`/chat/conversations`, `/chat/send`)
- SSE streaming implementation
- Tool handler wrappers with caps/truncation
- OpenAI integration
- Conversation state management

## Key Documents

### Requirements
- `TODO.md` - Comprehensive implementation plan with phases
- `_docs/requirements/PRD_AGENT_V1.0.md` - Product requirements
- `_docs/requirements/DESIGN_DOC_AGENT_V1.0.md` - Technical design (Section 18 has existing infrastructure)

### Backend Context
- `../backend/API_IMPLEMENTATION_STATUS.md` - Raw Data APIs are 100% complete
- `../backend/AI_AGENT_REFERENCE.md` - Backend patterns and common issues
- `../backend/TODO3.md` - Backend Phase 3 completion status

## Success Metrics
- Stream start ≤ 3s p50
- Complete response ≤ 8-10s p95
- 80% pass rate on 15 golden queries
- No hallucinated values

## Common Gotchas & Solutions

### Original Issues (Keep These)
1. **Auth uses dual support**: Both Bearer tokens (existing) AND cookies (for SSE). Login endpoint sets both
2. **Models need registration**: Add conversation models to `backend/app/database.py` init_db()
3. **Use pydantic_settings pattern**: Settings fields need `Field(..., env="VAR_NAME")`
4. **Raw Data APIs need enhancements**: Add caps, meta objects, parameter validation
5. **ALWAYS use Alembic**: Never create tables manually, always use migrations
6. **Import errors**: Check PYTHONPATH includes backend directory
7. **Docker required**: PostgreSQL runs in Docker, ensure Docker Desktop is running
8. **Service layer pattern**: New agent endpoints need service layer (PortfolioDataService)

### V1.1 Frontend Integration Issues
9. **Authentication Flow Changes**:
   - Login response MUST include both access_token AND set HttpOnly cookies
   - Frontend uses JWT for portfolio APIs, cookies automatically for chat streaming
   - Chat endpoints receive credentials:'include' in fetch requests
   - Logout must clear both localStorage JWT AND HttpOnly cookies

10. **OpenAI Model Compatibility**:
   - Use `gpt-4o` for production streaming (gpt-4o-turbo also available)
   - Use `max_completion_tokens` not `max_tokens` parameter
   - Don't set `temperature` parameter (only default value 1.0 supported)
   - Check `.env` file MODEL_DEFAULT - it overrides config.py defaults!

11. **Critical Import Paths** (These WILL trip you up):
   - ✅ `from app.services.portfolio_data_service import PortfolioDataService`
   - ❌ ~~`from app.agent.services.portfolio_data_service`~~ (doesn't exist)
   - ✅ `from app.agent.tools.tool_registry import tool_registry`
   - ❌ ~~`from app.agent.services.tool_registry`~~ (wrong location)
   - ⚠️ Tool registry needs singleton instance: Add `tool_registry = ToolRegistry()` at module level

12. **Conversation Model Specifics**:
   - No `portfolio_id` field on Conversation model
   - Portfolio context stored in metadata: `conversation.meta_data.get("portfolio_id")`
   - PromptManager.get_system_prompt() expects `user_context` not `portfolio_context`

13. **Demo User Credentials** (for testing):
   - Email: `demo_growth@sigmasight.com` (NOT john.demo@sigmasight.com)
   - Password: `demo12345`
   - Other demo users: demo_value@, demo_balanced@, etc.

14. **V1.1 Enhanced SSE Response Parsing**:
   ```python
   # V1.1: Enhanced SSE format with run_id and sequence
   # Format: "event: type\nrun_id: uuid\nsequence: 1\ndata: json\n\n"
   async for line in response.content:
       line_text = line.decode('utf-8').strip()
       if line_text.startswith('event:'):
           event_type = line_text.split(':', 1)[1].strip()
       elif line_text.startswith('run_id:'):
           run_id = line_text.split(':', 1)[1].strip()
       elif line_text.startswith('data:'):
           data = json.loads(line_text.split(':', 1)[1])
           # V1.1: Include run_id for deduplication
   ```

15. **Original SSE Response Parsing**:
   ```python
   # SSE format: "event: type\ndata: json\n\n"
   async for line in response.content:
       line_text = line.decode('utf-8').strip()
       if line_text.startswith('event:'):
           event_type = line_text.split(':', 1)[1].strip()
       elif line_text.startswith('data:'):
           data = json.loads(line_text.split(':', 1)[1])
   ```

16. **OpenAI Function Definitions**:
   - Tool registry doesn't auto-generate OpenAI schemas
   - Must manually define in `_get_tool_definitions()` with proper OpenAI format
   - Each tool needs: name, description, parameters (with type, properties, required)

17. **V1.1 Enhanced SSE Event Types**:
   - Add run_id field to all SSE events for deduplication
   - Add sequence field for event ordering
   - Enhanced error events with retryable taxonomy
   - Add performance metrics (TTFB, tokens-per-second)

18. **Missing SSE Event Types**:
   - If you see missing SSE events, add to `app/agent/schemas/sse.py`:
     - SSEToolStartedEvent
     - SSEToolFinishedEvent
     - SSEHeartbeatEvent