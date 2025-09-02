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

## 2. Missing Endpoints ⚠️

**Issue**: Several expected endpoints don't exist

- `GET /api/v1/chat/conversations/{id}/messages` - Message history (needed for chat history)
- `GET /api/v1/data/portfolios` - **Documented but NOT implemented** (returns 404)
- `PATCH /api/v1/chat/conversations/{id}/mode` - Update conversation mode

**Frontend Workaround**: 
- Return empty data on 404
- Use hint-based discovery for portfolios
- Mode changes only through new conversations

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

## Recommendations

1. **Backend should standardize on `id` field** for all primary resource identifiers
2. **Error responses should use consistent format** (recommend `detail` as FastAPI standard)
3. **Document which auth method each endpoint expects**
4. **Add missing endpoints or document alternatives**

## Testing Impact

These inconsistencies mean our test scripts need defensive coding:
- Can't assume field names
- Must handle multiple error formats
- Need fallbacks for missing endpoints

This makes tests less effective at catching real issues because they're too forgiving of response variations.