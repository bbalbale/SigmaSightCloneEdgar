# Backend
- Don't see a script to pull company profiles

# Sandbox
- Cron jobs in Railway Sandbox are not occuring - docker instance is crashing

# Target Price
- Target prices need to be aggregated and saved to create a portfolio target return for lons/shorts/optons and the rest of the portfolio. Portfolio Returns are now being calculated only on the frontend

# Chat
- We have two version of chat running now.

## Backend System (/app/agent/ and /app/api/v1/chat/):
- Uses OpenAI Responses API (different from Chat Completions)
- Server-side API key management (secure)
- Conversation persistence in PostgreSQL database
- User authentication & authorization per conversation
- Centralized rate limiting and cost control
- Audit trail and logging of all AI interactions
- Tools have direct database access for complex operations
- Production-ready with retry logic, fallbacks, error handling

## Frontend System (just built):
- Uses OpenAI Chat Completions API (direct from browser)
- API key exposed in browser code (less secure)
- Conversations only in Zustand/localStorage (ephemeral)
- No server-side logging or auditing
- Tools limited to what frontend services can access
- Simpler, faster for demos and prototyping

What Backend APIs Currently Exist:

  ✅ Conversations (already available):
  - POST /api/v1/chat/conversations - Create conversation
  - GET /api/v1/chat/conversations/{id} - Get conversation metadata
  - GET /api/v1/chat/conversations - List conversations
  - PUT /api/v1/chat/conversations/{id}/mode - Change mode
  - DELETE /api/v1/chat/conversations/{id} - Delete conversation

  ✅ Messages (partial):
  - POST /api/v1/chat/send - Send message + stream response (also saves to DB)

  ❌ Missing (needed for your use case):
  - GET /api/v1/chat/conversations/{id}/messages - Retrieve message history
  - POST /api/v1/chat/conversations/{id}/messages/bulk - Save multiple messages at once

  What We Need to Build:

  Backend Side (2 new endpoints needed):

  1. Get Message History Endpoint
  GET /api/v1/chat/conversations/{conversation_id}/messages
    - Returns array of messages for a conversation
    - Ordered chronologically
    - Paginated (limit/offset)
  2. Bulk Save Messages Endpoint
  POST /api/v1/chat/conversations/{conversation_id}/messages/bulk
    - Accepts array of messages
    - Saves all messages in one transaction
    - Returns saved message IDs

  Frontend Side (new service):

  Create frontend/src/services/chatPersistenceService.ts:
  - getConversationHistory(conversationId) - calls GET endpoint
  - saveMessages(conversationId, messages[]) - calls POST bulk endpoint
  - Integrates with existing chatService (frontend/src/services/chatService.ts)

  Proposed Flow:

  1. User opens chat
     ├─> chatPersistenceService.getConversationHistory(id)
     └─> Load from backend DB into Zustand

  2. User sends messages
     ├─> chatService.streamResponse() // Fast OpenAI direct
     └─> Messages stored in Zustand/localStorage

  3. After conversation (on close/timer)
     ├─> chatPersistenceService.saveMessages(id, messages)
     └─> Backend saves to PostgreSQL for audit/multi-device

  Benefits of This Approach:

  ✅ Fast real-time chat (direct OpenAI)
  ✅ Persistence for audit trails
  ✅ Multi-device conversation recovery
  ✅ No API key in browser (eventually can proxy)
  ✅ Minimal backend overhead (bulk operations)