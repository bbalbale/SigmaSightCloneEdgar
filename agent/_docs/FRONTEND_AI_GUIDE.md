# Frontend AI Agent Guide

> **For AI Coding Agents**: This guide provides everything you need to build a React/Next.js frontend for the SigmaSight Chat API.

## Quick Start

The backend is running at `http://localhost:8000` with a fully functional chat API that streams responses via Server-Sent Events (SSE).

### Test Credentials
```javascript
const TEST_USER = {
  email: "demo_growth@sigmasight.com",
  password: "demo12345"
}
```

### Basic Flow
1. Login to get JWT token
2. Create or select a conversation
3. Send messages and receive SSE streams
4. Parse SSE events to update UI

## Core API Endpoints

### Authentication

#### POST `/api/v1/auth/login`
```javascript
const response = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: "demo_growth@sigmasight.com",
    password: "demo12345"
  })
});

const data = await response.json();
// Returns: { access_token: "jwt...", token_type: "bearer", user: {...} }
```

#### GET `/api/v1/auth/me`
```javascript
const response = await fetch('http://localhost:8000/api/v1/auth/me', {
  headers: { 'Authorization': `Bearer ${token}` }
});
// Returns: { id: "uuid", email: "...", portfolios: [...] }
```

### Conversation Management

#### POST `/api/v1/chat/conversations`
```javascript
const response = await fetch('http://localhost:8000/api/v1/chat/conversations', {
  method: 'POST',
  headers: { 
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    mode: "green"  // or "blue", "indigo", "violet"
  })
});

const data = await response.json();
// Returns: { conversation_id: "uuid", mode: "green", created_at: "..." }
```

#### GET `/api/v1/chat/conversations`
```javascript
const response = await fetch('http://localhost:8000/api/v1/chat/conversations', {
  headers: { 'Authorization': `Bearer ${token}` }
});

const data = await response.json();
// Returns: { conversations: [...], total_count: 5, has_more: false }
```

### Streaming Chat (SSE)

#### POST `/api/v1/chat/send`
```javascript
const response = await fetch('http://localhost:8000/api/v1/chat/send', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream'
  },
  body: JSON.stringify({
    conversation_id: "uuid-here",
    text: "What is my portfolio value?"
  })
});

// Parse SSE stream
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('event:')) {
      const eventType = line.slice(6).trim();
      // Handle event type
    } else if (line.startsWith('data:')) {
      const data = JSON.parse(line.slice(5).trim());
      // Handle event data
    }
  }
}
```

## SSE Event Types

### `start`
```javascript
{
  conversation_id: "uuid",
  mode: "green",
  model: "gpt-4o"
}
```

### `message`
```javascript
{
  delta: "The next ",  // Text chunk
  role: "assistant"
}
```

### `tool_started`
```javascript
{
  tool_name: "get_portfolio_complete",
  arguments: { portfolio_id: "uuid" }
}
```

### `tool_finished`
```javascript
{
  tool_name: "get_portfolio_complete",
  result: { ... },  // Tool response
  duration_ms: 245
}
```

### `done`
```javascript
{
  tool_calls_count: 2,
  latency_ms: 3500
}
```

### `error`
```javascript
{
  message: "Error description",
  retryable: true
}
```

## Conversation Modes

- **green**: Educational, explanatory (default)
- **blue**: Concise, quantitative
- **indigo**: Strategic, narrative
- **violet**: Conservative, risk-focused

Change mode with: `/mode blue` message

## State Management Recommendations

### Zustand Example
```javascript
import { create } from 'zustand';

const useChatStore = create((set) => ({
  conversations: [],
  currentConversation: null,
  messages: [],
  isStreaming: false,
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  
  appendToLastMessage: (delta) => set((state) => {
    const messages = [...state.messages];
    messages[messages.length - 1].content += delta;
    return { messages };
  })
}));
```

## Error Handling

### V1.1 Enhanced Error Taxonomy
```javascript
try {
  const response = await fetch(...);
  if (!response.ok) {
    const error = await response.json();
    
    // V1.1: Error taxonomy with UI behaviors
    switch (response.status) {
      case 429: // RATE_LIMITED
        showError('Rate limited. Retrying in 30s...', { retry: true, delay: 30000 });
        break;
      case 401: // AUTH_EXPIRED  
        showError('Session expired', { retry: false, redirect: '/login' });
        break;
      case 500: // SERVER_ERROR
        showError('Server issue. Retrying...', { retry: true, delay: 10000 });
        break;
      default:
        showError(error.detail || 'Request failed');
    }
  }
} catch (err) {
  // NETWORK_ERROR
  showError('Connection issue. Retrying...', { retry: true, delay: 5000 });
}
```

### SSE Connection Loss
```javascript
const connectSSE = async (retryCount = 0) => {
  try {
    const response = await fetch('/api/v1/chat/send', ...);
    // Process stream
  } catch (err) {
    if (retryCount < 3) {
      await new Promise(r => setTimeout(r, 1000 * Math.pow(2, retryCount)));
      return connectSSE(retryCount + 1);
    }
    // Show error to user
  }
};
```

## UI Components Needed

### Core Components
1. **ChatInterface** - Main chat window with message list
2. **MessageInput** - Text input with send button
3. **ConversationList** - Sidebar with conversations
4. **ModeSelector** - Dropdown/toggle for conversation modes
5. **MessageBubble** - Individual message display
6. **ToolExecution** - Visual indicator for tool calls
7. **StreamingIndicator** - Typing/loading animation

### Layout Structure
```jsx
<AppLayout>
  <Sidebar>
    <ConversationList />
    <ModeSelector />
  </Sidebar>
  <MainContent>
    <ChatInterface>
      <MessageList />
      <StreamingIndicator />
      <MessageInput />
    </ChatInterface>
  </MainContent>
</AppLayout>
```

## Development Tips

### 1. Start Simple
- Implement auth flow first
- Get basic message send/receive working
- Add streaming progressively

### 2. Handle Edge Cases
- Empty conversations
- Network failures
- Token expiration (401 → refresh/relogin)
- SSE reconnection

### 3. Performance
- Virtualize long message lists
- Debounce typing indicators
- Cleanup SSE connections properly

### 4. Accessibility
- Keyboard navigation
- Screen reader support
- Focus management

## Testing Checklist

- [ ] Login flow works
- [ ] Can create conversation
- [ ] Messages send and stream back
- [ ] Mode switching works
- [ ] Tool executions display
- [ ] Error states handled
- [ ] Mobile responsive
- [ ] SSE reconnects on failure
- [ ] Conversation history loads
- [ ] Logout clears state

## Common Pitfalls

1. **CORS Issues**: Backend allows localhost:3000, localhost:5173
2. **SSE Parsing**: Lines are separated by `\n`, events by `\n\n`
3. **Token Format**: Use `Bearer ${token}` not just token
4. **Content-Type**: Always set for POST requests
5. **Streaming**: Response comes in chunks, not all at once

## Example Implementation

See `SSE_STREAMING_GUIDE.md` for complete SSE implementation.
See `API_CONTRACTS.md` for TypeScript interfaces.
See `FRONTEND_FEATURES.md` for detailed feature specifications.