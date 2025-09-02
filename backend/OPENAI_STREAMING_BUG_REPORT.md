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

### Key Findings
- **[contract_mismatch]** Backend currently emits `event: message` with JSON lacking `type` and `seq`, while the frontend (`frontend/src/hooks/useFetchStreaming.ts`) switches on `eventData.type` and deduplicates using `seq`. Result: token chunks are ignored.
- **[tool_args_parsing]** `openai_service.py` likely raises `JSONDecodeError` when attempting `json.loads` on tool call `arguments` if empty/partial. This exception aborts streaming.
- **[sse_event_names]** Backend schemas in `backend/app/agent/schemas/sse.py` document events like `start|message|tool_call|tool_result|error|done`. No explicit `token` event exists yet; introducing `token` makes the contract unambiguous for incremental deltas.
- **[proxy_requirements]** The proxy must forward `Accept: text/event-stream` and `Authorization` for POST/PUT/DELETE and preserve `Set-Cookie` on streaming responses. Frontend proxy route `frontend/src/app/api/proxy/[...path]/route.ts` has been updated; verify behavior end-to-end.

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

## 🧩 Current Implementation Analysis

- **`backend/app/agent/services/openai_service.py`**
  - Emits `event: message` with payload `{"delta":"...","role":"assistant"}` via `SSEMessageEvent` (lines ~314-319). Missing `type`, `seq`, and `run_id` required by the frontend.
  - Heartbeat: `event: heartbeat` with `data: {"type":"heartbeat"}` (lines ~301-307). No `seq` and not following the normalized contract shape.
  - Tool calls: accumulates `delta.tool_calls` chunks (lines ~321-338), then gates execution on `finish_reason == "tool_calls"` (line ~340). Arguments are parsed with `json.loads(...)` without a guard (line ~344), which can raise `JSONDecodeError` on partial JSON.
  - Emits `event: tool_started` and `event: tool_finished` (lines ~346-379) instead of `tool_call` / `tool_result` planned by the normalized SSE contract.
  - `event: done` uses `SSEDoneEvent` (lines ~408-413) without `seq` and without `data: { final_text }`.

Concrete examples of current emitted frames (as of current code):
```text
event: message
data: {"delta":"Hello","role":"assistant"}

event: tool_started
data: {"tool_name":"get_prices_historical","arguments":{"portfolio_id":"..."}}

event: tool_finished
data: {"tool_name":"get_prices_historical","result":{...},"duration_ms":100}

event: done
data: {"tool_calls_count":1,"total_tokens":0}
```

Why malformed relative to frontend contract (`frontend/src/hooks/useFetchStreaming.ts`):
- Missing `type` and `seq` fields → tokens ignored and dedup logic cannot operate.
- `event: message` is not handled; frontend expects `type: 'token'` with `data.delta`.
- Tool events use `tool_started/tool_finished` rather than `tool_call/tool_result`.
- `done` lacks `data.final_text` and `seq`.

## 🛠 Technical Implementation Required

### Problem: Incorrect OpenAI Stream Parsing

**Current Issue**: Backend treats OpenAI streaming response as bulk JSON instead of consuming chunk-by-chunk. It also emits event/data that do not match the frontend contract (`type` and `seq` fields missing).

**OpenAI Streaming Format** (what backend receives from provider):
```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":123,"model":"gpt-4o","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":123,"model":"gpt-4o","choices":[{"index":0,"delta":{"content":" world"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":123,"model":"gpt-4o","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### Backend‑first Resolution (recommended)
- **Normalize provider stream** in `backend/app/agent/services/openai_service.py` to your app’s SSE contract.
- **Emit incremental token events** as `event: token` and include JSON with `type`, `seq`, and `data.delta`.
- **Guard tool call JSON parsing** (wrap `json.loads` for tool `arguments` with validation/try-except).
- **Maintain heartbeats, done, and error semantics** and forward via `backend/app/api/v1/chat/send.py`.

### SSE Contract Specification (Server → Client)
For each frame, send a standard SSE block:
```
event: <name>\n
data: <json>\n
\n
```

Events and payloads:
- **token**
  - JSON: `{ "type": "token", "run_id": "<string>", "seq": <int>, "data": { "delta": "<string>" }, "timestamp": <ms> }`
  - Notes: `seq` is monotonic per run to dedup/order on the client; `run_id` optional but recommended.
- **tool_call**
  - JSON: `{ "type": "tool_call", "run_id", "seq", "data": { "tool_name", "tool_args" }, "timestamp": <ms> }`
- **tool_result**
  - JSON: `{ "type": "tool_result", "run_id", "seq", "data": { "tool_name", "tool_result" }, "timestamp": <ms> }`
- **heartbeat**
  - JSON: `{ "type": "heartbeat", "run_id", "seq": 0, "data": {}, "timestamp": <ms> }`
- **error**
  - JSON: `{ "type": "error", "run_id", "seq": 0, "data": { "error": "...", "error_type": "AUTH_EXPIRED|RATE_LIMITED|NETWORK_ERROR|SERVER_ERROR|FATAL_ERROR" }, "timestamp": <ms> }`
- **done**
  - JSON: `{ "type": "done", "run_id", "seq": <last+1>, "data": { "final_text": "..." }, "timestamp": <ms> }`

Note: Maintain the `event:` header in sync with `type` in JSON for clarity. Frontend currently switches on `eventData.type` and uses `seq` for ordering (`frontend/src/hooks/useFetchStreaming.ts`).

### Expected Fix Pattern

```python
# In openai_service.py - conceptual outline (normalize provider chunks to SSE contract)
import json, time

async def stream_chat_response(self, messages, conversation_id, run_id: str):
    seq = 0
    final_parts: list[str] = []
    try:
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )

        async for chunk in response:
            choice = (chunk.choices or [None])[0]
            if not choice:
                continue

            # Text deltas
            delta = getattr(choice.delta, "content", None)
            if delta:
                final_parts.append(delta)
                payload = {
                    "type": "token",
                    "run_id": run_id,
                    "seq": seq,
                    "data": {"delta": delta},
                    "timestamp": int(time.time() * 1000),
                }
                yield f"event: token\n" + f"data: {json.dumps(payload)}\n\n"
                seq += 1

            # Tool calls (detected via delta.tool_calls; guard JSON)
            if getattr(choice.delta, "tool_calls", None):
                for tc in choice.delta.tool_calls or []:
                    try:
                        args = (getattr(tc, "function", None) or {}).get("arguments") or "{}"
                        tool_args = json.loads(args) if isinstance(args, str) else args
                    except Exception as e:
                        tool_args = {"__parse_error__": str(e), "raw": args}
                    payload = {
                        "type": "tool_call",
                        "run_id": run_id,
                        "seq": seq,
                        "data": {
                            "tool_name": (getattr(tc, "function", None) or {}).get("name"),
                            "tool_args": tool_args
                        },
                        "timestamp": int(time.time() * 1000),
                    }
                    yield f"event: tool_call\n" + f"data: {json.dumps(payload)}\n\n"
                    seq += 1

        final_text = "".join(final_parts)
        done_payload = {
            "type": "done",
            "run_id": run_id,
            "seq": seq,
            "data": {"final_text": final_text},
            "timestamp": int(time.time() * 1000),
        }
        yield f"event: done\n" + f"data: {json.dumps(done_payload)}\n\n"

    except Exception as e:
        err_payload = {
            "type": "error",
            "run_id": run_id,
            "seq": 0,
            "data": {"error": str(e), "error_type": "SERVER_ERROR"},
            "timestamp": int(time.time() * 1000),
        }
        yield f"event: error\n" + f"data: {json.dumps(err_payload)}\n\n"
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

### Unit Tests (backend)
- **Chunk parser**: Simulate provider chunks with deltas, empty deltas, final `finish_reason: stop`, and `[DONE]`. Assert generator yields `event: token` frames with increasing `seq` and a final `event: done` with `final_text`.
- **Tool args guard**: Feed tool call chunks with invalid/partial `arguments` and assert no exception; emitted `tool_call` includes `__parse_error__` in `data.tool_args`.
- **Error classification**: Inject exceptions and assert `event: error` with `error_type: SERVER_ERROR` and proper payload shape.

### Integration Tests (end-to-end)
1. Start backend and frontend:
```bash
# Backend
uv run python backend/run.py

# Frontend (dev)
cd frontend && npm run dev
```
2. Login via UI (or existing session) and open chat page.
3. Send a prompt that produces a normal text response. Expect live tokens and final assistant message.
4. Send a prompt that triggers a tool call (if available). Expect `tool_call` → `tool_result` events (optional, based on tools setup).
5. Monitor browser DevTools network for the SSE request: `Content-Type: text/event-stream` and streaming frames arriving.

### Manual Verification via curl (proxy path)
```bash
# Replace COOKIE with an authenticated cookie if required
curl -N \
  -H 'Accept: text/event-stream' \
  -H "Cookie: $COOKIE" \
  -H 'Content-Type: application/json' \
  -X POST http://localhost:3005/api/proxy/api/v1/chat/send \
  -d '{"text":"Say hello","conversation_id":"<cid>"}'
```
Expect output similar to:
```
event: token
data: {"type":"token","run_id":"run_...","seq":0,"data":{"delta":"Hello"}}

event: token
data: {"type":"token","run_id":"run_...","seq":1,"data":{"delta":" world"}}

event: done
data: {"type":"done","run_id":"run_...","seq":2,"data":{"final_text":"Hello world"}}
```

### Proxy Verification
- Confirm `Accept: text/event-stream` and `Authorization` are forwarded on POST/PUT/DELETE.
- Confirm `Set-Cookie` headers from backend are forwarded in the SSE branch (auth continuity during streaming).

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
- **SSE Client**: `frontend/src/hooks/useFetchStreaming.ts` expects JSON payload with `type` (e.g., `'token'`) and monotonic `seq`. It uses `addToBuffer(runId, delta, seq)` for ordering/dedup.
- **Chat UI**: `frontend/src/components/chat/ChatInterface.tsx` updates message content in real-time based on buffer.
- **Plan**: Do not modify frontend; normalize backend to this contract.

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

- [ ] Analyze current `openai_service.py` implementation
- [ ] Identify specific JSON parsing failure point (tool args)
- [ ] Implement chunk-by-chunk normalization to SSE contract
- [ ] Emit `event: token` with `{ type, run_id, seq, data.delta }`
- [ ] Add `tool_call`/`tool_result` events (guard JSON parsing)
- [ ] Emit `heartbeat`, `error`, and `done` with documented payloads
- [ ] Verify proxy forwards `Accept`, `Authorization`, and `Set-Cookie`
- [ ] Test with frontend integration (live tokens + final text)
- [ ] Ensure no JSON parsing errors in backend logs
- [ ] Run unit + integration tests; document results

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