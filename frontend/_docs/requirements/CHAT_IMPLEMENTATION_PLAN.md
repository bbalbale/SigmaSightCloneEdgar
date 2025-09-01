# Chat Integration Implementation Plan

**Created:** 2025-01-09  
**Status:** Planning Phase  
**Target:** SigmaSight Portfolio Chat Assistant  
**Architecture:** Sheet Overlay Pattern with SSE Streaming  

## Executive Summary

Implement a chat interface that overlays the current page using shadcn Sheet component, connecting to the existing backend OpenAI integration via Server-Sent Events (SSE). The chat will provide contextual portfolio analysis while preserving the user's current view.

## Current State Analysis

### Backend (95% Complete)
- ✅ **Database**: `agent_conversations`, `agent_messages` tables exist
- ✅ **Authentication**: JWT Bearer + Cookie support for SSE
- ✅ **Chat Endpoints**: 
  - `POST /api/v1/chat/conversations` - Create conversation
  - `GET /api/v1/chat/conversations` - List conversations
  - `DELETE /api/v1/chat/conversations/{id}` - Delete conversation
  - `GET /api/v1/chat/conversations/{id}/messages` - Get history
  - `POST /api/v1/chat/send` - Send message (SSE response)
- ✅ **OpenAI Integration**: GPT-4o with function calling
- ✅ **Portfolio Tools**: 6 analysis tools ready
- ✅ **Conversation Modes**: green/blue/indigo/violet
- ✅ **SSE Infrastructure**: Streaming with heartbeats

### Frontend (5% Complete)
- ✅ **Authentication**: JWT working from portfolio implementation
- ✅ **API Proxy**: `/api/proxy/[...path]` bypasses CORS
- ✅ **ChatInput Component**: Basic input exists
- ❌ **No Sheet UI**: Need to implement overlay
- ❌ **No SSE Client**: Need streaming parser
- ❌ **No Conversation State**: Need state management
- ❌ **No Message Display**: Need chat UI components

## Architecture Decision

### UI Pattern: Sheet Overlay
**Rationale:**
- Preserves user context (stays on current page)
- Progressive disclosure (chat bar → full conversation)
- Mobile-friendly (bottom sheet on mobile, sidebar on desktop)
- Non-intrusive user experience

### Technical Stack
- **UI Library**: shadcn/ui Sheet component
- **State Management**: Zustand (lightweight, TypeScript-friendly)
- **Streaming**: Native EventSource API with fallback to fetch
- **Markdown**: react-markdown with rehype-sanitize
- **Styling**: Tailwind CSS (existing)

## Implementation Phases

### Phase 1: Sheet UI Infrastructure (Day 1)

#### 1.1 Install Dependencies
```bash
npx shadcn-ui@latest add sheet
npm install zustand react-markdown rehype-sanitize
```

#### 1.2 Create Chat Store
```typescript
// frontend/src/stores/chatStore.ts
interface ChatState {
  // Conversation Management
  conversations: Conversation[]
  currentConversationId: string | null
  messages: Message[]
  
  // UI State
  isSheetOpen: boolean
  isStreaming: boolean
  streamingMessage: string
  mode: ConversationMode
  
  // Actions
  setSheetOpen: (open: boolean) => void
  addMessage: (message: Message) => void
  updateStreamingMessage: (content: string) => void
}
```

#### 1.3 Build Sheet Container
```typescript
// frontend/src/components/chat/ChatInterface.tsx
- Integrate with existing ChatInput component
- Sheet trigger on chat bar focus/click
- Responsive sizing (mobile vs desktop)
- Persistent across navigation
```

#### 1.4 Create Message Components
```typescript
// frontend/src/components/chat/MessageList.tsx
- Virtual scrolling for performance
- Auto-scroll to bottom on new messages
- Smooth animations

// frontend/src/components/chat/MessageBubble.tsx
- User vs assistant styling
- Markdown rendering
- Code syntax highlighting
- Timestamp display

// frontend/src/components/chat/ToolExecution.tsx
- Show tool name and status
- Loading spinner during execution
- Collapsible results
```

#### 1.5 Mode Selector
```typescript
// frontend/src/components/chat/ModeSelector.tsx
- Dropdown or button group
- Visual indicators (colors/icons)
- Tooltip explanations
```

**Potential Failure Points:**
- ⚠️ Sheet z-index conflicts with existing modals
- ⚠️ State persistence during navigation
- ⚠️ Mobile keyboard pushing content up
- ⚠️ Sheet not closing on route change

### Phase 2: API Integration (Day 2)

#### 2.1 Create Chat Service
```typescript
// frontend/src/services/chatService.ts
export class ChatService {
  private baseUrl = '/api/proxy/chat'
  
  async createConversation(mode: ConversationMode): Promise<Conversation>
  async listConversations(): Promise<Conversation[]>
  async deleteConversation(id: string): Promise<void>
  async getMessages(conversationId: string): Promise<Message[]>
}
```

#### 2.2 Authentication Integration
```typescript
// Reuse existing auth from portfolioService.ts
- Get JWT token from localStorage
- Add Bearer token to headers
- Handle 401 errors (redirect to login)
```

#### 2.3 Conversation Lifecycle
```typescript
// On app mount:
1. Check for existing conversations
2. Load most recent or create new
3. Fetch message history
4. Set current conversation in store

// On message send:
1. Ensure conversation exists
2. Add user message to UI optimistically
3. Start SSE connection
4. Handle response streaming
```

**Potential Failure Points:**
- ⚠️ Token expiration during long conversations
- ⚠️ Race condition: multiple conversation creates
- ⚠️ Conversation ID mismatch between frontend/backend
- ⚠️ Message history pagination not implemented

### Phase 3: SSE Streaming Implementation (Day 2-3)

#### 3.1 SSE Client Hook
```typescript
// frontend/src/hooks/useSSEChat.ts
export function useSSEChat() {
  const connectSSE = async (conversationId: string, message: string) => {
    // Option 1: EventSource API (cleaner but less flexible)
    const eventSource = new EventSource(
      `/api/proxy/chat/send?conversation_id=${conversationId}&text=${message}`,
      { withCredentials: true }
    )
    
    // Option 2: Fetch with ReadableStream (more control)
    const response = await fetch('/api/proxy/chat/send', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      },
      body: JSON.stringify({ conversation_id, text })
    })
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    
    // Parse SSE format: "event: type\ndata: json\n\n"
  }
}
```

#### 3.2 SSE Event Handling
```typescript
// Event types from backend
type SSEEventType = 
  | 'start'           // { conversation_id, mode, model }
  | 'message'         // { delta, role }
  | 'tool_started'    // { tool_name, arguments }
  | 'tool_finished'   // { tool_name, result, duration_ms }
  | 'done'           // { tool_calls_count, latency_ms }
  | 'error'          // { message, retryable }
  | 'heartbeat'      // { timestamp }

// Parser implementation
function parseSSEMessage(data: string): SSEEvent {
  const lines = data.split('\n')
  let event = ''
  let jsonData = ''
  
  for (const line of lines) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      jsonData = line.slice(5).trim()
    }
  }
  
  return { event, data: JSON.parse(jsonData) }
}
```

#### 3.3 Stream Processing
```typescript
// Handle streaming text
const handleStreamingMessage = (delta: string) => {
  // Append to current message
  setStreamingMessage(prev => prev + delta)
  
  // Update UI immediately
  // Handle markdown parsing
  // Auto-scroll to bottom
}

// Handle tool execution
const handleToolExecution = (tool: ToolEvent) => {
  // Show tool indicator
  // Display loading state
  // Show results when complete
}
```

#### 3.4 Error Recovery
```typescript
// Reconnection with exponential backoff
const reconnectWithBackoff = async (
  attempt: number = 0,
  maxAttempts: number = 3
) => {
  const delay = Math.min(1000 * Math.pow(2, attempt), 10000)
  await new Promise(resolve => setTimeout(resolve, delay))
  
  try {
    await connectSSE()
  } catch (error) {
    if (attempt < maxAttempts) {
      return reconnectWithBackoff(attempt + 1, maxAttempts)
    }
    throw error
  }
}
```

**Potential Failure Points:**
- ⚠️ CORS blocking EventSource (need proxy config)
- ⚠️ SSE buffering (nginx/proxy buffering)
- ⚠️ Connection timeout (default 2 min limit)
- ⚠️ Message parsing errors (malformed JSON)
- ⚠️ Browser EventSource limitations (no headers)
- ⚠️ Network interruptions losing messages
- ⚠️ Memory leaks from unclosed connections

### Phase 4: Context Integration (Day 3)

#### 4.1 Portfolio Context
```typescript
// Inject current page context
const getPageContext = () => {
  const pathname = window.location.pathname
  const params = new URLSearchParams(window.location.search)
  
  if (pathname.includes('/portfolio')) {
    const portfolioType = params.get('type')
    return {
      page: 'portfolio',
      portfolioType,
      context: `User is viewing ${portfolioType} portfolio`
    }
  }
  // ... other pages
}

// Auto-inject context in first message
const enhancedMessage = `${userMessage}\n\n[Context: ${context}]`
```

#### 4.2 Smart Suggestions
```typescript
// Based on current page, suggest relevant queries
const getSuggestions = (page: string): string[] => {
  switch(page) {
    case 'portfolio':
      return [
        "What's my largest position?",
        "Show me my factor exposures",
        "Calculate my portfolio beta"
      ]
    case 'holdings':
      return [
        "Which stocks are down today?",
        "Show me sector allocation",
        "What's my cash balance?"
      ]
    // ...
  }
}
```

**Potential Failure Points:**
- ⚠️ Context injection revealing sensitive data
- ⚠️ Suggestions not updating on navigation
- ⚠️ Portfolio ID not available in context

### Phase 5: Mobile Optimization (Day 3-4)

#### 5.1 Responsive Behavior
```typescript
// Mobile: Full screen bottom sheet
// Tablet: Half screen side panel
// Desktop: 400px sidebar

const sheetSize = useMediaQuery({
  mobile: 'full',
  tablet: 'half',
  desktop: 'fixed'
})
```

#### 5.2 Touch Gestures
```typescript
// Swipe down to minimize
// Pull to refresh conversation
// Tap outside to close
```

#### 5.3 Keyboard Management
```typescript
// Adjust viewport when keyboard opens
// Scroll to input field
// Prevent content push
```

**Potential Failure Points:**
- ⚠️ iOS Safari viewport bugs
- ⚠️ Android keyboard overlapping input
- ⚠️ Sheet gesture conflicts with scroll
- ⚠️ Safe area insets (iPhone notch)

## Critical Failure Points & Mitigations

### 1. Authentication Failures
**Issue:** JWT token expires during conversation  
**Mitigation:** 
- Implement token refresh before SSE connection
- Store refresh token securely
- Auto-retry with new token on 401

### 2. SSE Connection Issues
**Issue:** Proxy/CORS blocking SSE  
**Mitigation:**
```typescript
// Next.js proxy configuration
// app/api/proxy/[...path]/route.ts modifications:
export async function POST(request: Request) {
  // Special handling for SSE
  if (request.headers.get('accept') === 'text/event-stream') {
    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no' // Disable nginx buffering
      }
    })
  }
}
```

### 3. State Synchronization
**Issue:** Message history out of sync  
**Mitigation:**
- Optimistic updates with rollback
- Message IDs for deduplication
- Periodic sync with backend

### 4. Network Interruptions
**Issue:** Lost messages during streaming  
**Mitigation:**
- Message sequence numbers
- Automatic reconnection
- Resume from last received message

### 5. Memory Leaks
**Issue:** Unclosed SSE connections  
**Mitigation:**
```typescript
// Cleanup on unmount
useEffect(() => {
  return () => {
    eventSource?.close()
    abortController?.abort()
  }
}, [])
```

### 6. Rate Limiting
**Issue:** OpenAI rate limits  
**Mitigation:**
- Show clear error messages
- Implement client-side throttling
- Queue messages when rate limited

### 7. Large Responses
**Issue:** Tool results too large for UI  
**Mitigation:**
- Implement pagination
- Collapsible sections
- Virtual scrolling
- Truncate with "Show more"

## Testing Strategy

### Unit Tests
- Message parsing functions
- SSE event handling
- State management actions
- Context extraction

### Integration Tests
- Authentication flow
- Conversation creation
- Message sending
- SSE streaming
- Tool execution

### E2E Tests
- Complete chat flow
- Mode switching
- Mobile interactions
- Error recovery

### Manual Testing Checklist
- [ ] Chat bar opens Sheet
- [ ] Messages send and display
- [ ] Streaming text appears smoothly
- [ ] Tools show execution status
- [ ] Mode switching works
- [ ] Conversation persists on refresh
- [ ] Mobile gestures work
- [ ] Errors show user-friendly messages
- [ ] Network interruption recovery
- [ ] Long conversations scroll properly

## Performance Considerations

### Optimization Targets
- First message < 3s response
- Smooth streaming (60 fps)
- Sheet open < 200ms
- Memory usage < 50MB

### Optimization Techniques
- Virtual scrolling for long conversations
- Debounce streaming updates
- Lazy load conversation history
- Memoize expensive renders
- Use React.memo for message components

## Security Considerations

### Data Protection
- Sanitize markdown output
- No raw HTML rendering
- XSS prevention in user input
- Validate conversation ownership

### Token Management
- Secure token storage
- Auto-refresh before expiry
- Clear tokens on logout
- No tokens in URLs

## Rollout Strategy

### Phase 1: Internal Testing
- Deploy to staging
- Test with team members
- Gather feedback
- Fix critical bugs

### Phase 2: Beta Users
- Enable for subset of users
- Monitor error rates
- Track performance metrics
- Iterate on UX

### Phase 3: General Availability
- Full rollout
- Monitor closely
- Have rollback plan
- Document known issues

## Success Metrics

### Technical Metrics
- < 3s to first token
- < 10s full response
- < 1% error rate
- 99% uptime

### User Metrics
- > 50% engagement rate
- > 3 messages per session
- < 10% abandonment rate
- > 4.0 satisfaction score

## Timeline

### Week 1
- Day 1: Sheet UI implementation
- Day 2: API integration
- Day 3: SSE streaming
- Day 4: Testing & bug fixes
- Day 5: Mobile optimization

### Week 2
- Refinement and polish
- Performance optimization
- Extended testing
- Documentation
- Deployment preparation

## Appendix: Code References

### Existing Files to Modify
- `/frontend/src/app/components/ChatInput.tsx` - Enhance to trigger Sheet
- `/frontend/src/app/layout.tsx` - Add ChatInterface wrapper
- `/frontend/src/services/portfolioService.ts` - Reuse auth pattern

### New Files to Create
- `/frontend/src/components/chat/ChatInterface.tsx` - Main container
- `/frontend/src/components/chat/ChatSheet.tsx` - Sheet wrapper
- `/frontend/src/components/chat/MessageList.tsx` - Message display
- `/frontend/src/components/chat/MessageBubble.tsx` - Individual messages
- `/frontend/src/components/chat/ToolExecution.tsx` - Tool status
- `/frontend/src/components/chat/ModeSelector.tsx` - Mode switcher
- `/frontend/src/hooks/useSSEChat.ts` - SSE streaming hook
- `/frontend/src/services/chatService.ts` - API communication
- `/frontend/src/stores/chatStore.ts` - Zustand store
- `/frontend/src/types/chat.ts` - TypeScript interfaces

### Backend Endpoints (Already Implemented)
- `POST /api/v1/chat/conversations` - Create conversation
- `GET /api/v1/chat/conversations` - List conversations
- `DELETE /api/v1/chat/conversations/{id}` - Delete conversation
- `GET /api/v1/chat/conversations/{id}/messages` - Get message history
- `POST /api/v1/chat/send` - Send message (SSE response)

### Test Credentials
```typescript
const TEST_USER = {
  email: "demo_growth@sigmasight.com",
  password: "demo12345"
}
```

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| SSE CORS issues | High | High | Use proxy, test early |
| Token expiration | Medium | Medium | Implement refresh flow |
| Mobile keyboard issues | High | Low | Test on real devices |
| Rate limiting | Low | High | Client-side throttling |
| Memory leaks | Medium | Medium | Proper cleanup hooks |
| Network interruptions | High | Low | Auto-reconnection |
| Large responses | Medium | Medium | Pagination/truncation |

## Conclusion

This implementation plan provides a comprehensive roadmap for integrating the chat interface with the existing backend. The Sheet overlay pattern preserves user context while providing a rich chat experience. Key success factors include proper SSE handling, robust error recovery, and careful attention to mobile UX.

The phased approach allows for iterative development with early validation of critical components. By identifying potential failure points upfront, we can build mitigations into the implementation rather than discovering issues in production.

Next steps:
1. Install shadcn Sheet component
2. Create basic Sheet UI structure  
3. Test with mock data
4. Integrate real API
5. Handle edge cases
6. Polish and optimize