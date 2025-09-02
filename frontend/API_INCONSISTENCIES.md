# API Inconsistencies Documentation

This document tracks inconsistencies in the backend API that the frontend must handle.

## 1. Conversation ID Field Naming ❌

**Issue**: Conversation endpoints return `conversation_id` instead of standard `id`

**Expected** (REST standard):
```json
{
  "id": "136539a2-8a9c-4a20-8d64-e0cc1bb30230",
  "mode": "blue",
  "created_at": "2025-09-02T11:46:27.211455Z"
}
```

**Actual**:
```json
{
  "conversation_id": "136539a2-8a9c-4a20-8d64-e0cc1bb30230",
  "mode": "blue",
  "created_at": "2025-09-02T11:46:27.211455Z"
}
```

**Frontend Workaround**:
```javascript
const id = response.id || response.conversation_id;
```

**Impact**: 
- Breaks REST conventions
- Forces defensive coding throughout frontend
- Inconsistent with other resources (portfolios, positions use `id`)

### **Detailed Analysis (2025-09-02)**

**Root Cause**: Intentional design decision in backend schemas
- Location: `/backend/app/agent/schemas/chat.py`
- Comment in model: "Our canonical ID - returned as conversation_id to frontend"
- Affects: `ConversationResponse`, `ModeChangeResponse`, `MessageSend` schemas

**Semantic Analysis**: ✅ **SAFE TO CHANGE**
After analyzing all layers of the stack, confirmed there is **NO semantic difference** between conversation `id` and other resource `id` fields:

1. **Database Layer**: All `id` fields use identical pattern
   ```python
   # Same for conversations, portfolios, positions, etc.
   id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
   ```

2. **OpenAI Integration**: Conversation ID is only metadata
   - Not passed to OpenAI API (OpenAI doesn't know about our conversation IDs)
   - Only used for client-side correlation in SSE events
   - Provider IDs stored separately (`provider_thread_id`, `provider_run_id`)

3. **Analytics Services**: Same UUID pattern across all services
   ```python
   async def calculate_correlations(portfolio_id: UUID, ...)
   async def stream_chat_completion(conversation_id: str, ...)
   ```

4. **Foreign Keys**: Same referential pattern
   ```python
   portfolio_id: Mapped[UUID] = mapped_column(ForeignKey("portfolios.id"))
   conversation_id: Mapped[UUID] = mapped_column(ForeignKey("agent_conversations.id"))
   ```

**Risk Assessment**: ✅ **ZERO RISK**
- Same data type, generation method, constraints, and purpose
- Clear separation from provider-specific IDs
- Purely cosmetic naming inconsistency

**Fix Strategy**: Change backend schemas to use standard `id` field name

## 2. Missing Endpoints ✅ **RESOLVED**

**Issue**: ~~Several expected endpoints don't exist~~ **DESIGN ALIGNMENT COMPLETE**

- ~~`GET /api/v1/chat/conversations/{id}/messages`~~ - ✅ **REMOVED**: Not needed for session-based chat design
- ~~`GET /api/v1/data/portfolios`~~ - ✅ **FIXED 2025-09-02**: Now implemented and working
- ~~`PATCH /api/v1/chat/conversations/{id}/mode`~~ - ✅ **IMPLEMENTED as PUT**: Backend uses `PUT /conversations/{id}/mode`

**Resolution**:
- ✅ **Portfolio endpoint**: Fixed by implementing missing endpoint
- ✅ **Mode changes**: Backend implemented as PUT (functionally equivalent to PATCH)
- ✅ **Message history**: Removed from requirements - SigmaSight uses session-based chat, not persistent history

## 3. Error Response Format Inconsistency ⚠️

**Issue**: Different endpoints return errors differently

**Variations seen**:
- `{ "detail": "Error message" }` - FastAPI default
- `{ "message": "Error message" }` - Custom handlers
- `{ "error": "Error message" }` - Some services

**Frontend Workaround**:
```javascript
const errorMessage = error.detail || error.message || error.error || 'Unknown error';
```

## 4. Timestamp Format ✅

**Good**: All timestamps consistently use ISO 8601 with Z suffix
```
"2025-09-02T11:46:27.211455Z"
```

## 5. Authentication Mixed Mode ⚠️

**Issue**: Different endpoints expect different auth methods

- Portfolio APIs: JWT Bearer token
- Chat streaming: HttpOnly cookies
- Some endpoints: Accept both

**Frontend Workaround**: 
- Always send both when available
- `Authorization: Bearer ${token}` header
- `credentials: 'include'` for cookies

## Resolution History

### ✅ Fixed Issues
- **2025-09-02**: Implemented `GET /api/v1/data/portfolios` endpoint
  - Backend: Added endpoint in `/backend/app/api/v1/data.py`
  - Frontend: Removed hint-based discovery mechanism
  - Result: Proper REST-compliant portfolio listing

## Recommendations

1. **Backend should standardize on `id` field** for all primary resource identifiers
2. **Error responses should use consistent format** (recommend `detail` as FastAPI standard)
3. **Document which auth method each endpoint expects**
4. ~~Add missing endpoints or document alternatives~~ **Partially addressed**

## Testing Impact

These inconsistencies mean our test scripts need defensive coding:
- Can't assume field names
- Must handle multiple error formats
- Need fallbacks for missing endpoints

This makes tests less effective at catching real issues because they're too forgiving of response variations.