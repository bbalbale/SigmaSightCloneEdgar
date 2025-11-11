# AI Chat Page Implementation Guide

**Purpose**: Step-by-step guide to create the AI Chat page  
**Route**: `/ai-chat`  
**Features**: Streaming AI chat with portfolio context  
**Last Updated**: September 29, 2025

---

## Overview

This page provides an AI chat interface with:
- Real-time streaming responses via SSE (Server-Sent Events)
- Portfolio context for queries
- Conversation history
- Agent mode switching
- Existing ChatInterface component (already built!)

---

## Service Dependencies

### Services Used (Already Exist)
```typescript
import { chatService } from '@/services/chatService'           // SSE streaming
import { chatAuthService } from '@/services/chatAuthService'   // Chat auth
import { useAuth } from '@/app/providers'                      // Auth context
```

### Component Dependency (Already Exists!)
```typescript
import { ChatInterface } from '@/components/chat/ChatInterface'  // Fully functional!
```

### API Endpoints Used

```
POST /chat/conversations           # Create conversation
GET  /chat/conversations/{id}      # Get conversation
GET  /chat/conversations           # List conversations
PUT  /chat/conversations/{id}/mode # Change agent mode
POST /chat/send                    # Send message (SSE stream)
DELETE /chat/conversations/{id}    # Delete conversation
```

---

## Implementation Steps

### Step 1: No Custom Hook Needed!

**Why?** The existing `ChatInterface` component already handles:
- ✅ Message sending
- ✅ Streaming responses
- ✅ Conversation management
- ✅ Error handling
- ✅ Loading states

The component uses `chatService` and `chatAuthService` internally.

---

### Step 2: No New Components Needed!

**Why?** The `ChatInterface` component is already complete:
- ✅ Message input
- ✅ Message display
- ✅ Streaming indicator
- ✅ Error handling
- ✅ Conversation controls

**File**: `src/components/chat/ChatInterface.tsx` (already exists)

---

### Step 3: Create Container Component

**File**: `src/containers/AIChatContainer.tsx`

```typescript
// src/containers/AIChatContainer.tsx
'use client'

import { useAuth } from '@/app/providers'
import { ChatInterface } from '@/components/chat/ChatInterface'

export function AIChatContainer() {
  const { portfolioId, user } = useAuth()
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            SigmaSight AI Assistant
          </h1>
          <p className="text-gray-600 mt-1">
            Ask questions about your portfolio
          </p>
        </div>
        
        {portfolioId && (
          <div className="text-sm text-gray-500">
            Portfolio: {portfolioId.slice(0, 8)}...
          </div>
        )}
      </div>
      
      {/* Use existing ChatInterface component */}
      <ChatInterface 
        portfolioId={portfolioId}
        userId={user?.id}
      />
    </div>
  )
}
```

**Key Points**:
- ✅ Minimal container (~25 lines)
- ✅ Just renders existing ChatInterface
- ✅ Passes portfolio context
- ✅ Shows portfolio ID for reference

---

### Step 4: Create Thin Page Route

**File**: `app/ai-chat/page.tsx`

```typescript
// app/ai-chat/page.tsx
'use client'

import { AIChatContainer } from '@/containers/AIChatContainer'

export default function AIChatPage() {
  return <AIChatContainer />
}
```

**Key Points**:
- ✅ Only 8 lines
- ✅ Just imports and renders container
- ✅ No business logic
- ✅ Client component

---

## File Creation Checklist

### Files to Create
- [ ] `src/containers/AIChatContainer.tsx` - Page container
- [ ] `app/ai-chat/page.tsx` - Thin route wrapper

### Dependencies (Already Exist)
- [x] `src/components/chat/ChatInterface.tsx` - Chat UI (complete!)
- [x] `src/services/chatService.ts` - SSE streaming service
- [x] `src/services/chatAuthService.ts` - Chat authentication
- [x] `app/providers.tsx` - Auth context

---

## chatService Reference

### Service Methods (Already Implemented)
```typescript
// src/services/chatService.ts
chatService.sendMessage({
  conversationId: string
  message: string
  onChunk: (chunk: string) => void
  onComplete: (fullResponse: string) => void
  onError: (error: Error) => void
  signal?: AbortSignal
})

chatService.createConversation({
  portfolioId: string
  mode?: string
})

chatService.getConversation(conversationId: string)

chatService.listConversations()

chatService.deleteConversation(conversationId: string)
```

### How ChatInterface Uses chatService

```typescript
// Inside ChatInterface.tsx (reference only - already implemented)
const handleSendMessage = async (message: string) => {
  setStreaming(true)
  
  await chatService.sendMessage({
    conversationId: currentConversation.id,
    message,
    onChunk: (chunk) => {
      // Append streaming chunk to display
      setStreamingMessage(prev => prev + chunk)
    },
    onComplete: (fullResponse) => {
      // Add to message history
      addMessage({ role: 'assistant', content: fullResponse })
      setStreaming(false)
    },
    onError: (error) => {
      setError(error.message)
      setStreaming(false)
    }
  })
}
```

---

## ChatInterface Props

### Component Interface
```typescript
interface ChatInterfaceProps {
  portfolioId?: string | null   // Portfolio context
  userId?: string                // User context
  initialMode?: string           // Agent mode (optional)
}
```

### Usage Examples
```typescript
// Basic usage
<ChatInterface portfolioId={portfolioId} userId={user.id} />

// With initial mode
<ChatInterface 
  portfolioId={portfolioId} 
  userId={user.id}
  initialMode="portfolio_analysis"
/>

// Without portfolio context (general chat)
<ChatInterface userId={user.id} />
```

---

## Agent Modes

### Available Modes
```typescript
// Agent modes supported by backend
const AGENT_MODES = {
  GENERAL: 'general',                    // General conversation
  PORTFOLIO_ANALYSIS: 'portfolio_analysis',  // Portfolio-specific queries
  RESEARCH: 'research',                  // Market research
  RISK_ANALYSIS: 'risk_analysis'         // Risk assessment
}
```

### Mode Switching
```typescript
// ChatInterface handles mode switching internally
// User can switch via UI dropdown
// Backend endpoint: PUT /chat/conversations/{id}/mode
```

---

## Testing Steps

1. **Create container** - Minimal wrapper for ChatInterface
2. **Create page** - Thin route in `/app`
3. **Test navigation** - Go to `/ai-chat`
4. **Test message sending** - Type message and send
5. **Test streaming** - Verify chunks appear in real-time
6. **Test conversation** - Multiple messages work
7. **Test errors** - Handle network failures
8. **Test portfolio context** - Verify portfolioId is passed
9. **Test mode switching** - Change agent mode
10. **Test conversation history** - Load previous conversations

---

## Common Issues & Solutions

### Issue 1: Streaming not working
**Symptom**: Messages don't stream, whole response appears at once  
**Cause**: SSE connection failed or backend not streaming  
**Solution**: 
- Check backend is running
- Verify `/chat/send` endpoint supports SSE
- Check browser console for connection errors

### Issue 2: Portfolio context not working
**Symptom**: Chat doesn't know about portfolio  
**Cause**: portfolioId not passed or null  
**Solution**: 
- Verify useAuth() returns portfolioId
- Check portfolioResolver has loaded
- Console log portfolioId in container

### Issue 3: ChatInterface not found
**Symptom**: Import error for ChatInterface  
**Cause**: Component file missing  
**Solution**: 
- Verify `/src/components/chat/ChatInterface.tsx` exists
- Check it's properly exported

### Issue 4: Authentication errors
**Symptom**: Chat returns 401 Unauthorized  
**Cause**: Chat auth cookie not set  
**Solution**: 
- Use chatAuthService.login() first
- Check HTTP-only cookie is set
- Verify credentials are valid

---

## SSE Streaming Details

### How It Works

```typescript
// 1. Client sends message
POST /chat/send
{
  "conversation_id": "uuid",
  "message": "Tell me about my portfolio"
}

// 2. Backend streams response chunks
// Server-Sent Events (SSE) format
event: message
data: {"chunk": "Your portfolio"}

event: message  
data: {"chunk": " currently has"}

event: message
data: {"chunk": " a total value"}

event: done
data: {"complete": true}

// 3. Client reassembles chunks into full message
```

### chatService SSE Implementation

```typescript
// chatService.ts (reference only - already implemented)
async sendMessage({ conversationId, message, onChunk, onComplete }) {
  const response = await fetch('/api/proxy/chat/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',  // Send HTTP-only cookies
    body: JSON.stringify({ conversation_id: conversationId, message })
  })
  
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  
  let fullResponse = ''
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    
    const chunk = decoder.decode(value)
    fullResponse += chunk
    onChunk(chunk)  // Stream each chunk to UI
  }
  
  onComplete(fullResponse)  // Send complete message
}
```

---

## Future Enhancements

### Optional Features to Add Later

1. **Conversation Management**
   - List previous conversations
   - Resume conversations
   - Delete conversations

2. **Message Actions**
   - Copy message
   - Regenerate response
   - Thumbs up/down feedback

3. **Rich Content**
   - Markdown rendering
   - Code syntax highlighting
   - Tables and charts

4. **Advanced Features**
   - Voice input
   - Export conversation
   - Share conversation

5. **Context Tools**
   - Upload documents
   - Reference specific positions
   - Deep link to portfolio sections

---

## Integration with Portfolio Context

### How Portfolio Context Works

```typescript
// Container passes portfolioId to ChatInterface
<ChatInterface portfolioId={portfolioId} userId={user.id} />

// ChatInterface includes it in API calls
const response = await chatService.sendMessage({
  conversationId,
  message,
  // Portfolio ID is stored in conversation
  // Backend automatically includes portfolio context
})

// Backend retrieves portfolio data for context
// Agent has access to:
// - All positions
// - Current metrics
// - Factor exposures
// - Historical performance
```

### Example Portfolio Queries

```
User: "What's my largest position?"
AI: "Your largest position is AAPL with a market value of $50,000..."

User: "Show me my tech exposure"
AI: "Your technology sector exposure is 35% of total portfolio..."

User: "What's my portfolio risk?"
AI: "Based on your current allocation, your portfolio has..."
```

---

## Next Steps

After implementing AI Chat page:
1. Test chat functionality thoroughly
2. Verify streaming works correctly
3. Test portfolio context queries
4. Check error handling
5. Move on to Settings page

---

## Summary

**Pattern**: Container wraps existing component → Page  
**Services Used**: chatService, chatAuthService (indirect via ChatInterface)  
**New Files**: 2 total (1 container, 1 page)  
**Existing Components**: ChatInterface (fully functional, reused as-is)  
**Key Advantage**: Minimal new code, leverage existing chat implementation
