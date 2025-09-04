# Chat Agent End-to-End Flow Documentation

**Purpose**: Comprehensive documentation of the SigmaSight chat agent flow from user query to response, showing the complete architecture and data flow with portfolio ID resolution.

**Status**: Current implementation (Phase 9.12 fixes applied)

**Last Updated**: 2025-09-04

---

## Overview

The SigmaSight chat agent provides portfolio analysis capabilities through a streaming chat interface. Users authenticate via JWT tokens and can ask natural language questions about their portfolios. The system automatically resolves portfolio context and streams OpenAI responses with access to real portfolio data through function tools.

## Architecture Components

```
User Browser
    ↓ HTTP Request + JWT Cookie
FastAPI Chat API (/api/v1/chat/send)
    ↓ Database Query
Portfolio ID Resolution
    ↓ Metadata Storage
Conversation Management
    ↓ System Prompt Template
OpenAI Streaming Service
    ↓ Function Tools
Raw Data APIs (PortfolioDataService)
    ↓ Database Queries
PostgreSQL (Portfolio/Position Data)
    ↓ Server-Sent Events
Streaming Response to Browser
```

## Detailed Flow

### 1. Authentication & Request Initiation

**Entry Point**: `POST /api/v1/chat/send`
**File**: `app/api/v1/chat/send.py`

```python
# User sends message with JWT authentication
{
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "text": "show me my portfolio performance"
}
```

**Authentication Flow**:
1. FastAPI extracts JWT token from HttpOnly cookie (`auth_token`)
2. `get_current_user` dependency validates token and returns `CurrentUser` object
3. User identity is established for database queries

### 2. Conversation Loading & Portfolio Resolution

**File**: `app/api/v1/chat/conversations.py` (conversation creation)
**File**: `app/api/v1/chat/send.py` (conversation loading)

```python
# Load conversation with metadata
result = await db.execute(
    select(Conversation)
    .where(Conversation.id == message_data.conversation_id)
)
conversation = result.scalar_one_or_none()

# Portfolio context extraction
portfolio_id = conversation.meta_data.get("portfolio_id") if conversation.meta_data else None
```

**Portfolio Resolution Process**:
- **New Conversations**: Auto-resolve user's portfolio ID during conversation creation
- **Existing Conversations**: Extract portfolio_id from stored metadata
- **Database Query**: `SELECT id FROM portfolios WHERE user_id = current_user.id`
- **Storage**: Portfolio ID stored in `conversation.meta_data = {"portfolio_id": "uuid"}`

### 3. Message Storage & Context Preparation

**Message Creation**:
```python
# Create user message
user_message = ConversationMessage(
    id=uuid4(),
    conversation_id=conversation.id,
    role="user",
    content=message_text,
    created_at=utc_now()
)

# Create assistant message placeholder
assistant_message = ConversationMessage(
    id=uuid4(),
    conversation_id=conversation.id,
    role="assistant",
    content="",  # Updated during streaming
    created_at=utc_now()
)
```

**Context Assembly**:
- **Message History**: Load last 10 messages for conversation context
- **Portfolio Context**: Format portfolio_id for tool authentication
- **Auth Context**: Extract JWT token for API calls
- **System Prompt**: Template replacement with actual portfolio UUID

### 4. OpenAI Service Integration

**File**: `app/agent/services/openai_service.py`
**Entry Point**: `stream_responses()` method

```python
async for sse_event in openai_service.stream_responses(
    conversation_id=str(conversation.id),
    conversation_mode=conversation.mode,
    message_text=message_text,
    message_history=message_history,
    portfolio_context=portfolio_context,
    auth_context=auth_context
):
```

**System Prompt Template Processing**:
- **Template File**: `app/agent/prompts/common_instructions.md`
- **Placeholder**: `Portfolio ID: {portfolio_id}`
- **Replacement**: Actual UUID like `Portfolio ID: c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e`
- **Result**: OpenAI receives specific portfolio UUID in system context

### 5. OpenAI Function Tool Execution

**Available Tools**:
- `get_portfolio_complete` - Full portfolio snapshot
- `get_portfolio_data_quality` - Data completeness assessment
- `get_positions_details` - Position-level information
- `get_prices_historical` - Historical price data
- `get_prices_quotes` - Real-time market quotes
- `get_factor_etf_prices` - Factor ETF analysis data

**Tool Call Process**:
```python
# OpenAI generates tool call
{
    "tool_call_id": "call_abc123",
    "type": "function",
    "function": {
        "name": "get_portfolio_complete",
        "arguments": '{"portfolio_id": "c0510ab8-c6b5-433c-adbc-3f74e1dbdb5e"}'
    }
}
```

**Tool Handler Authentication**:
- Tools receive `auth_context` with JWT token
- Token used to authenticate against Raw Data APIs
- Ensures user can only access their own portfolio data

### 6. Raw Data API Layer

**Service Layer**: `app/services/portfolio_data_service.py`
**API Layer**: `app/api/v1/data.py` endpoints

**Data Flow**:
```python
# Tool calls service layer method
portfolio_service = PortfolioDataService()
result = await portfolio_service.get_top_positions(
    db=db,
    portfolio_id=UUID(portfolio_id),
    limit=20,
    sort_by="market_value"
)

# Service queries database
positions_result = await db.execute(
    select(Position)
    .where(Position.portfolio_id == portfolio_id)
)
```

**Database Queries**:
- **Portfolio Data**: Users, Portfolios, Positions tables
- **Market Data**: MarketDataCache for pricing
- **Calculations**: Greeks, factor exposures, correlations
- **Real-time**: Latest prices and market data

### 7. Response Streaming & Updates

**Server-Sent Events (SSE)**:
```
event: start
data: {"conversation_id": "...", "mode": "blue", "model": "gpt-4"}

event: token
data: {"delta": "Your", "role": "assistant"}

event: tool_call
data: {"tool_name": "get_portfolio_complete", "tool_args": {...}}

event: done
data: {"tool_calls_count": 2, "latency_ms": 1500}
```

**Message Updates**:
```python
# Accumulate content during streaming
assistant_content += data["delta"]

# Update database message
assistant_message.content = assistant_content
assistant_message.provider_message_id = openai_response_id
assistant_message.latency_ms = response_time
await db.commit()
```

### 8. Client-Side Rendering

**Frontend Processing** (`frontend/src/components/chat/`):
- Parse SSE events in real-time
- Render streaming text with markdown support
- Display tool execution indicators
- Handle authentication errors and retries

## Data Security & Access Control

### Portfolio Access Validation

**Multi-Layer Security**:
1. **JWT Authentication**: User identity verification
2. **Conversation Ownership**: `conversation.user_id == current_user.id`
3. **Portfolio Ownership**: `portfolio.user_id == current_user.id`
4. **Service Layer**: All database queries filtered by user context
5. **API Layer**: Additional authentication checks on Raw Data endpoints

### Data Privacy

**Protected Information**:
- Portfolio IDs never exposed in responses
- User data isolated by authentication context
- Database queries always include user_id filters
- OpenAI receives only necessary portfolio context

## Error Handling & Recovery

### Common Failure Scenarios

**1. Missing Portfolio ID** (Phase 9.12 Issue - FIXED):
```
Root Cause: Conversations created without portfolio metadata
Symptom: "portfolio data returned null"
Fix: Auto-resolution during conversation creation
```

**2. Authentication Failures**:
```
Symptom: 401/403 errors in tool calls
Recovery: Token refresh, re-authentication flow
Monitoring: JWT token expiration tracking
```

**3. Service Unavailability**:
```
Symptom: Tool execution timeouts
Recovery: Graceful degradation, cached data
Fallback: Explain service limitations to user
```

### Monitoring & Observability

**Key Metrics**:
- **Conversation Creation Success Rate**: Track portfolio auto-resolution
- **Tool Call Success Rate**: Monitor API availability
- **Response Latency**: OpenAI + database query times
- **Authentication Errors**: JWT token issues

**Logging Correlation**:
```python
# Response ID tracking (Phase 5.8.2.1)
logger.info(
    f"🔗 OpenAI Response Started - "
    f"Response ID: {openai_response_id} | "
    f"Conversation: {conversation.id} | "
    f"User: {current_user.id} | "
    f"Run ID: {run_id}"
)
```

## Configuration & Environment

### Required Environment Variables

```bash
# OpenAI Integration
OPENAI_API_KEY=sk-...
MODEL_DEFAULT=gpt-4o-2024-08-06

# Database
DATABASE_URL=postgresql+asyncpg://...

# JWT Authentication
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Market Data (for tool functions)
POLYGON_API_KEY=your-key
FMP_API_KEY=your-key
```

### Mode Configuration

**Available Modes**:
- `green` - Teaching/educational responses
- `blue` - Quantitative/concise analysis  
- `indigo` - Strategic/narrative insights
- `violet` - Risk-focused/conservative

**Mode Switching**:
```python
# Via chat command
/mode blue

# Via API endpoint
PUT /api/v1/chat/conversations/{id}/mode
{"mode": "indigo"}
```

## Performance Characteristics

### Typical Response Times

**Fast Queries** (cached data): 500-1000ms
- Portfolio summary
- Top positions
- Basic metrics

**Medium Queries** (database + calculation): 1500-3000ms
- Historical analysis
- Factor exposures
- Performance comparisons

**Complex Queries** (multiple tools + analysis): 3000-8000ms
- Comprehensive portfolio analysis
- Multi-timeframe comparisons
- Risk scenario modeling

### Scalability Considerations

**Database Connections**:
- Async connection pooling
- Query optimization for large portfolios
- Indexed UUID lookups

**OpenAI API**:
- Rate limiting compliance
- Response streaming for user experience
- Error retry with exponential backoff

**Memory Usage**:
- Message history truncation (10 messages)
- Large dataset streaming
- Garbage collection of completed conversations

## Development & Testing

### Local Testing Flow

```bash
# 1. Start services
docker-compose up -d
cd backend && uv run python run.py
cd frontend && npm run dev

# 2. Authenticate
curl -X POST http://localhost:8001/api/v1/auth/login \
  -d '{"email": "demo@sigmasight.io", "password": "demo12345"}'

# 3. Create conversation
curl -X POST http://localhost:8001/api/v1/chat/conversations \
  -H "Cookie: auth_token=..." \
  -d '{"mode": "blue"}'

# 4. Send message
curl -X POST http://localhost:8001/api/v1/chat/send \
  -H "Cookie: auth_token=..." \
  -d '{"conversation_id": "...", "text": "show my portfolio"}'
```

### Testing Scenarios

**Authentication Tests**:
- Valid JWT token processing
- Expired token handling
- Missing token recovery

**Portfolio Resolution Tests**:
- New user conversation creation
- Multiple portfolio handling
- Edge cases (no portfolios)

**Tool Execution Tests**:
- All function tools with real data
- Error handling and graceful degradation
- Response time monitoring

## Future Improvements

### Planned Enhancements

**Conversation Features**:
- Message editing and regeneration
- Conversation branching
- Export conversation history

**Portfolio Context**:
- Multi-portfolio selection
- Portfolio comparison mode
- Benchmark integration

**Performance Optimization**:
- Response caching strategies
- Parallel tool execution
- Database query optimization

**Monitoring & Analytics**:
- User interaction patterns
- Tool usage analytics
- Performance bottleneck identification

---

## Quick Reference

### Key Files
- `app/api/v1/chat/send.py` - Main streaming endpoint
- `app/api/v1/chat/conversations.py` - Conversation management
- `app/agent/services/openai_service.py` - OpenAI integration
- `app/services/portfolio_data_service.py` - Data access layer
- `app/agent/prompts/common_instructions.md` - System prompt template

### Critical Dependencies
- JWT authentication via HttpOnly cookies
- PostgreSQL for conversation and portfolio storage
- OpenAI API for natural language processing
- Server-Sent Events for real-time streaming

### Monitoring Points
- Portfolio auto-resolution success rate
- OpenAI response correlation IDs
- Database query performance
- Authentication token validity

This documentation reflects the current implementation with Phase 9.12 fixes applied. The system provides robust portfolio analysis capabilities through natural language interaction while maintaining security and performance standards.