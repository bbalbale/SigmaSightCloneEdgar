# OpenAI Streaming Parser Bug Report

**Priority**: High | **Impact**: Core AI functionality broken | **Status**: Ready for Implementation

## 🎯 Issue Summary

The backend OpenAI streaming response parser fails with a JSON parsing error, preventing AI responses from reaching the frontend chat interface. The chat system is fully functional except users see "Thinking..." indefinitely instead of actual AI responses.

## 🔍 Root Cause Analysis

### Error Details
- **Location**: `backend/app/agent/services/openai_service.py`
- **Error Message**: `"OpenAI streaming error: Expecting value: line 1 column 1 (char 0)"`
- **Error Type**: JSON parsing failure when processing OpenAI's Server-Sent Events response
- **Frequency**: Every chat message that reaches OpenAI

### Evidence
1. ✅ **OpenAI API calls succeed**: Backend logs show `HTTP/1.1 200 OK` from `https://api.openai.com/v1/chat/completions`
2. ✅ **SSE infrastructure works**: Frontend receives `event: start`, `event: error`, `event: done`
3. ❌ **Missing token events**: No `event: token` events sent to frontend
4. ❌ **JSON parser crashes**: Backend attempts to parse streaming chunks as single JSON object

## 📂 Code Locations

### Primary Files to Modify
1. **`backend/app/agent/services/openai_service.py`** - Main OpenAI integration (CRITICAL)
2. **`backend/app/api/v1/chat/send.py`** - SSE endpoint that calls OpenAI service
3. **`backend/app/agent/schemas/sse.py`** - SSE event definitions

### Reference Files (Context)
4. **`backend/app/agent/models/conversations.py`** - Database models
5. **`backend/app/agent/prompts/prompt_manager.py`** - Prompt management
6. **`backend/app/core/logging.py`** - Logging configuration

### Frontend Files (Working - Don't Modify)
7. **`frontend/src/hooks/useFetchStreaming.ts`** - SSE client (receives events)
8. **`frontend/src/components/chat/ChatInterface.tsx`** - Chat UI (handles tokens)

## 🛠 Technical Implementation Required

### Problem: Incorrect OpenAI Stream Parsing

**Current Issue**: Backend treats OpenAI streaming response as bulk JSON instead of line-by-line SSE format.

**OpenAI Streaming Format** (what backend receives):
```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":123,"model":"gpt-4o","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":123,"model":"gpt-4o","choices":[{"index":0,"delta":{"content":" world"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":123,"model":"gpt-4o","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

**Required Processing**:
1. Parse line-by-line (not bulk JSON)
2. Extract `data:` prefix from each line
3. Handle `data: [DONE]` termination
4. Parse each data line as separate JSON object
5. Extract `choices[0].delta.content` when present
6. Send as `event: token` SSE events to frontend

### Expected Fix Pattern

```python
# In openai_service.py - approximate implementation needed
async def stream_chat_response(self, messages, conversation_id):
    try:
        # Make OpenAI API call with stream=True
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True
        )
        
        # Process streaming response line by line
        async for chunk in response:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                
                # Send as SSE event to frontend
                yield SSETokenEvent(
                    run_id=run_id,
                    seq=sequence_number,
                    data={"delta": token}
                )
                sequence_number += 1
                
        # Send completion event
        yield SSEDoneEvent(run_id=run_id, data={"final_text": accumulated_text})
        
    except Exception as e:
        logger.error(f"OpenAI streaming error: {e}")
        yield SSEErrorEvent(
            run_id=run_id, 
            data={"error": str(e), "error_type": "SERVER_ERROR"}
        )
```

## 🔗 Context Documents

### Essential Reading
1. **`backend/CLAUDE.md`** - AI agent instructions and context
2. **`backend/AI_AGENT_REFERENCE.md`** - Complete codebase reference
3. **`agent/TODO.md`** - Full implementation plan and context
4. **`frontend/TODO_CHAT.md`** - Frontend integration status (cross-referenced)

### API Documentation
5. **OpenAI Streaming API**: https://platform.openai.com/docs/api-reference/streaming
6. **Server-Sent Events**: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events

### Configuration Files
7. **`backend/app/config.py`** - OpenAI model settings
8. **`backend/.env`** - API keys and environment config

## 🧪 Testing

### Test Commands
```bash
# 1. Start backend
cd backend && uv run python run.py

# 2. Start frontend  
cd frontend && npm run dev

# 3. Test integration
node frontend/test-chat-integration.js
```

### Test URLs
- **Frontend**: http://localhost:3005/portfolio?type=high-net-worth
- **Demo Credentials**: demo_hnw@sigmasight.com / demo12345

### Expected Results After Fix
- User sends message → sees blue bubble (✅ already working)
- Assistant responds → sees gray bubble with actual AI response (❌ currently shows "Thinking...")
- Console logs show: "Received token: [token]" events (❌ currently no token logs)

## 🚨 Critical Implementation Notes

### Authentication
- **Backend Auth**: Uses existing JWT/cookie validation in `send.py`
- **OpenAI Auth**: Uses `OPENAI_API_KEY` from environment
- **DO NOT MODIFY**: Authentication is working correctly

### Database
- **Conversations**: Created properly via `/api/v1/chat/conversations`
- **Messages**: Should be stored after streaming completes
- **DO NOT MODIFY**: Database operations working correctly

### Frontend Integration
- **SSE Client**: `useFetchStreaming.ts` correctly processes `event: token`
- **Chat UI**: `ChatInterface.tsx` updates message content in real-time
- **DO NOT MODIFY**: Frontend SSE handling is working correctly

### Error Handling
- **Graceful Degradation**: Frontend shows "No response received." if stream fails
- **Logging**: Use existing logger from `app.core.logging`
- **Maintain**: Current error handling patterns

## 🎯 Success Criteria

### Functional Requirements
1. **Token Streaming**: Frontend receives `event: token` events with delta content
2. **Message Completion**: Assistant messages show full AI responses
3. **Error Recovery**: Graceful handling of OpenAI API failures
4. **Performance**: Stream starts within 3 seconds, completes within 10 seconds

### Technical Validation
1. **Backend Logs**: No more "JSON parsing" errors
2. **Frontend Console**: Shows "Received token" debug messages
3. **Chat UI**: Assistant messages replace "Thinking..." with actual responses
4. **Integration Test**: `test-chat-integration.js` shows token events received

## 📋 Implementation Checklist

- [ ] **Analyze current `openai_service.py` implementation**
- [ ] **Identify specific JSON parsing failure point**
- [ ] **Implement line-by-line SSE parsing**
- [ ] **Extract delta content from OpenAI chunks**
- [ ] **Send proper `event: token` SSE events**
- [ ] **Handle `[DONE]` termination correctly**
- [ ] **Test with frontend integration**
- [ ] **Verify chat UI shows AI responses**
- [ ] **Update error handling if needed**
- [ ] **Run integration tests to confirm fix**

## 🔄 Post-Implementation

After fixing, update:
1. **`frontend/TODO_CHAT.md`** - Mark OpenAI streaming issue as resolved
2. **`agent/TODO.md`** - Update Phase status if applicable
3. **Git commit** with detailed fix description

---

**Created**: 2025-09-02
**Frontend Integration Status**: ✅ Complete - Ready for AI responses
**Priority**: High - Core functionality blocked
**Estimated Fix Time**: 2-4 hours for experienced backend developer