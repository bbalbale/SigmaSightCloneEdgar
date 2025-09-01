# API Contracts & TypeScript Interfaces

> **Updated for V1.1 Chat Implementation - Enhanced Events & Auth**

**V1.1 Updates**:
- **Authentication**: Mixed strategy (JWT + HttpOnly cookies)
- **SSE Events**: Enhanced with run_id and sequence numbering
- **Error Taxonomy**: Retryable classification added
- **Message Queue**: Run-time state management
- **Performance Metrics**: TTFB and tokens-per-second tracking

## Authentication Types

```typescript
// Request Types
interface LoginRequest {
  email: string;
  password: string;
}

interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  user: {
    id: string;
    email: string;
    portfolios: Array<{
      id: string;
      name: string;
    }>;
  };
}

interface CurrentUserResponse {
  id: string;
  email: string;
  portfolios: Array<{
    id: string;
    name: string;
    total_value: number;
  }>;
}
```

## Conversation Types

```typescript
type ConversationMode = "green" | "blue" | "indigo" | "violet";

interface CreateConversationRequest {
  mode?: ConversationMode;  // Default: "green"
  name?: string;  // Optional conversation name
}

interface ConversationResponse {
  conversation_id: string;
  user_id: string;
  mode: ConversationMode;
  name?: string;
  created_at: string;  // ISO 8601 with Z
  updated_at: string;
  message_count: number;
}

interface ConversationListResponse {
  conversations: ConversationSummary[];
  total_count: number;
  has_more: boolean;
}

interface ConversationSummary {
  conversation_id: string;
  name?: string;
  mode: ConversationMode;
  message_count: number;
  created_at: string;
  updated_at: string;
  last_message_preview?: string;
}
```

## Message Types

```typescript
interface SendMessageRequest {
  conversation_id: string;
  text: string;
  run_id?: string; // V1.1: Client-generated for deduplication
}

interface Message {
  message_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  tool_calls?: ToolCall[];
}

interface ToolCall {
  name: string;
  duration_ms?: number;
}

interface MessageHistoryResponse {
  messages: Message[];
  total_count: number;
  has_more: boolean;
}
```

## SSE Event Types

```typescript
// V1.1 Enhanced SSE Event with sequencing
interface SSEEvent<T = any> {
  event: string;
  data: T;
  run_id?: string; // V1.1: For event deduplication
  sequence?: number; // V1.1: For event ordering
}

// V1.1 Enhanced Start Event
interface SSEStartData {
  conversation_id: string;
  mode: ConversationMode;
  model: string;  // e.g., "gpt-4o"
  run_id: string; // V1.1: For tracing this request
  timestamp: string; // V1.1: ISO 8601 with Z
}

// Message Event (streaming text)
interface SSEMessageData {
  delta: string;  // Text chunk
  role: "assistant" | "system";
}

// Tool Started Event
interface SSEToolStartedData {
  tool_name: string;
  arguments: Record<string, any>;
}

// Tool Finished Event
interface SSEToolFinishedData {
  tool_name: string;
  result?: any;
  error?: string;
  duration_ms?: number;
}

// Done Event
interface SSEDoneData {
  tool_calls_count: number;
  total_tokens?: number;
  latency_ms?: number;
}

// V1.1 Enhanced Error Event with taxonomy
interface SSEErrorData {
  message: string;
  code?: string;
  retryable: boolean;
  error_type: 'RATE_LIMITED' | 'AUTH_EXPIRED' | 'NETWORK_ERROR' | 'SERVER_ERROR' | 'CLIENT_ERROR'; // V1.1
  retry_delay_ms?: number; // V1.1: Suggested delay
  details?: any;
}

// Heartbeat Event
interface SSEHeartbeatData {
  timestamp: string;
}

// Union type for all SSE events
type SSEEventData = 
  | { event: "start"; data: SSEStartData }
  | { event: "message"; data: SSEMessageData }
  | { event: "tool_started"; data: SSEToolStartedData }
  | { event: "tool_finished"; data: SSEToolFinishedData }
  | { event: "done"; data: SSEDoneData }
  | { event: "error"; data: SSEErrorData }
  | { event: "heartbeat"; data: SSEHeartbeatData };
```

## Error Response Format

```typescript
interface ErrorResponse {
  detail: string;  // Human-readable error message
  // Optional fields for specific errors
  code?: string;
  request_id?: string;
  timestamp?: string;
}

// Rate limit error includes headers
interface RateLimitHeaders {
  "X-RateLimit-Limit": string;
  "X-RateLimit-Remaining": string;
  "X-RateLimit-Reset": string;  // Unix timestamp
}
```

## Tool Function Types

```typescript
// Available tool names
type ToolName = 
  | "get_portfolio_complete"
  | "get_portfolio_data_quality"
  | "get_positions_details"
  | "get_prices_historical"
  | "get_current_quotes"
  | "get_factor_etf_prices";

// Tool response envelope
interface ToolResponse<T = any> {
  meta: {
    requested: Record<string, any>;
    applied: Record<string, any>;
    as_of: string;
    truncated: boolean;
    limits?: Record<string, number>;
    retryable?: boolean;
  };
  data?: T;
  error?: {
    type: string;
    message: string;
    details?: any;
  };
}
```

## V1.1 API Client with Mixed Auth

```typescript
class SigmaSightAPI {
  private token: string | null = null;
  private baseURL = 'http://localhost:8000/api/v1';

  async login(email: string, password: string): Promise<LoginResponse> {
    const response = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include', // V1.1: Sets HttpOnly cookies
      body: JSON.stringify({ email, password })
    });
    
    if (!response.ok) throw await response.json();
    
    const data = await response.json();
    this.token = data.access_token;
    return data;
  }

  async createConversation(mode?: ConversationMode): Promise<ConversationResponse> {
    const response = await fetch(`${this.baseURL}/chat/conversations`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ mode })
    });
    
    if (!response.ok) throw await response.json();
    return response.json();
  }

  async sendMessage(
    conversationId: string, 
    text: string,
    onEvent: (event: SSEEventData) => void,
    runId?: string // V1.1: Optional client-generated ID
  ): Promise<void> {
    const response = await fetch(`${this.baseURL}/chat/send`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        ...(this.token && { 'Authorization': `Bearer ${this.token}` }) // V1.1: Fallback
      },
      credentials: 'include', // V1.1: HttpOnly cookies
      body: JSON.stringify({
        conversation_id: conversationId,
        text,
        run_id: runId || crypto.randomUUID() // V1.1: Deduplication
      })
    });

    if (!response.ok) throw await response.json();
    
    // Parse SSE stream
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      
      // Keep incomplete line in buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('event:')) {
          const eventType = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          const data = JSON.parse(line.slice(5).trim());
          onEvent({ event: eventType, data });
        }
      }
    }
  }

  private getHeaders(): HeadersInit {
    if (!this.token) throw new Error('Not authenticated');
    return {
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json'
    };
  }
}
```

## HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | Success | Process response |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Check request parameters |
| 401 | Unauthorized | Token expired, re-authenticate |
| 403 | Forbidden | User lacks permission |
| 404 | Not Found | Resource doesn't exist |
| 429 | Rate Limited | Retry with backoff |
| 500 | Server Error | Retry with backoff |
| 503 | Service Unavailable | Retry with backoff |

## Rate Limiting

- Default: 100 requests per minute per user
- Streaming endpoints: 10 concurrent connections
- Headers indicate remaining quota
- Use exponential backoff for retries

## CORS Configuration

Allowed origins:
- `http://localhost:3000` (React dev)
- `http://localhost:5173` (Vite dev)
- `https://sigmasight-frontend.vercel.app` (Production)

## Best Practices

1. **Always type API responses** - Don't use `any`
2. **Handle all error cases** - Network, auth, rate limits
3. **Clean up SSE connections** - Use AbortController
4. **Validate responses** - Use zod or similar
5. **Store token securely** - localStorage or secure cookie
6. **Implement token refresh** - Before expiration
7. **Show loading states** - During API calls
8. **Queue messages** - If connection lost