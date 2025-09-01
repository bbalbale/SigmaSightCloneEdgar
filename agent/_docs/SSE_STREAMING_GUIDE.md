# SSE Streaming Implementation Guide

> **Updated for V1.1 Chat Implementation - fetch() POST Streaming**  
> **Complete implementation patterns for Server-Sent Events in React/Next.js**

**V1.1 Updates**:
- Migrated from EventSource to fetch() POST for better control and JSON payloads
- Added HttpOnly cookie authentication support
- Enhanced error handling with retryable taxonomy
- Added run_id for event deduplication

## Overview

The SigmaSight API uses Server-Sent Events (SSE) for streaming chat responses. Unlike WebSockets, SSE is unidirectional (server → client) and handles reconnection automatically.

## Basic SSE Implementation

### React Hook for fetch() POST Streaming (V1.1)

```typescript
import { useRef, useCallback, useEffect } from 'react';

interface UseSSEOptions {
  onMessage?: (event: SSEEventData) => void;
  onError?: (error: Error) => void;
  onOpen?: () => void;
  onClose?: () => void;
  reconnect?: boolean;
  reconnectInterval?: number;
}

export function useSSE(options: UseSSEOptions = {}) {
  const {
    onMessage,
    onError,
    onOpen,
    onClose,
    reconnect = true,
    reconnectInterval = 1000
  } = options;

  const abortControllerRef = useRef<AbortController | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(async (
    url: string,
    payload: Record<string, any>,
    headers: Record<string, string> = {}
  ) => {
    // Cancel any existing connection
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Content-Type': 'application/json',
          ...headers
        },
        credentials: 'include', // V1.1: HttpOnly cookies
        signal: abortControllerRef.current.signal,
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      onOpen?.();
      
      await processSSEStream(response, onMessage, onError);
      
    } catch (error) {
      if (error.name !== 'AbortError') {
        onError?.(error as Error);
        
        // Auto-reconnect if enabled
        if (reconnect && reconnectInterval > 0) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect(url, headers);
          }, reconnectInterval);
        }
      }
    } finally {
      onClose?.();
    }
  }, [onMessage, onError, onOpen, onClose, reconnect, reconnectInterval]);

  const disconnect = useCallback(() => {
    abortControllerRef.current?.abort();
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return { connect, disconnect };
}

// SSE Stream Processor
async function processSSEStream(
  response: Response,
  onMessage?: (event: SSEEventData) => void,
  onError?: (error: Error) => void
) {
  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      
      // Keep incomplete line in buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.trim() === '') {
          // Empty line indicates end of event
          continue;
        }

        if (line.startsWith('event:')) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          const dataStr = line.slice(5).trim();
          if (dataStr && currentEvent) {
            try {
              const data = JSON.parse(dataStr);
              onMessage?.({ event: currentEvent, data });
            } catch (err) {
              onError?.(new Error(`Failed to parse SSE data: ${dataStr}`));
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
```

### Chat Hook Implementation

```typescript
import { useState, useCallback, useRef } from 'react';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  streaming?: boolean;
  toolCalls?: Array<{
    name: string;
    duration?: number;
    result?: any;
  }>;
}

export function useChat(conversationId: string, token: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { connect, disconnect } = useSSE({
    onMessage: handleSSEMessage,
    onError: (err) => {
      setError(err.message);
      setIsStreaming(false);
    },
    onOpen: () => {
      setError(null);
      setIsStreaming(true);
    },
    onClose: () => {
      setIsStreaming(false);
    }
  });

  // Track current streaming message
  const currentMessageRef = useRef<string>('');
  const currentToolCallsRef = useRef<ChatMessage['toolCalls']>([]);

  function handleSSEMessage(event: SSEEventData) {
    switch (event.event) {
      case 'start':
        // Reset streaming state
        currentMessageRef.current = '';
        currentToolCallsRef.current = [];
        break;

      case 'message':
        // Append text delta to current message
        currentMessageRef.current += event.data.delta;
        
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          
          if (lastMessage?.streaming) {
            // Update existing streaming message
            lastMessage.content = currentMessageRef.current;
          } else {
            // Create new streaming message
            newMessages.push({
              id: crypto.randomUUID(),
              role: 'assistant',
              content: currentMessageRef.current,
              timestamp: new Date(),
              streaming: true
            });
          }
          
          return newMessages;
        });
        break;

      case 'tool_started':
        // Add tool call to current list
        currentToolCallsRef.current = [
          ...(currentToolCallsRef.current || []),
          {
            name: event.data.tool_name,
            duration: undefined,
            result: undefined
          }
        ];
        break;

      case 'tool_finished':
        // Update tool call with result
        currentToolCallsRef.current = currentToolCallsRef.current?.map(tool =>
          tool.name === event.data.tool_name
            ? {
                ...tool,
                duration: event.data.duration_ms,
                result: event.data.result
              }
            : tool
        ) || [];
        break;

      case 'done':
        // Finalize streaming message
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          
          if (lastMessage?.streaming) {
            lastMessage.streaming = false;
            lastMessage.toolCalls = currentToolCallsRef.current;
          }
          
          return newMessages;
        });
        setIsStreaming(false);
        break;

      case 'error':
        setError(event.data.message);
        setIsStreaming(false);
        break;
    }
  }

  const sendMessage = useCallback(async (text: string) => {
    // Add user message immediately
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setError(null);

    // V1.1: Generate run_id for deduplication
    const runId = crypto.randomUUID();

    // Start SSE connection with fetch() POST
    await connect(
      'http://localhost:8000/api/v1/chat/send',
      {
        conversation_id: conversationId,
        text,
        run_id: runId // V1.1: Client-generated for dedup
      },
      {
        'Authorization': `Bearer ${token}` // Fallback for JWT
      }
    );
  }, [conversationId, token, connect]);

  const stopStreaming = useCallback(() => {
    disconnect();
    setIsStreaming(false);
  }, [disconnect]);

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
    stopStreaming
  };
}
```

## Component Examples

### Chat Interface Component

```tsx
import { useState } from 'react';
import { useChat } from './hooks/useChat';

interface ChatInterfaceProps {
  conversationId: string;
  token: string;
}

export function ChatInterface({ conversationId, token }: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const { messages, isStreaming, error, sendMessage, stopStreaming } = useChat(
    conversationId,
    token
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    
    await sendMessage(input);
    setInput('');
  };

  return (
    <div className="chat-interface">
      {/* Messages */}
      <div className="messages">
        {messages.map(message => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isStreaming && <StreamingIndicator />}
      </div>

      {/* Error Display */}
      {error && (
        <div className="error">
          {error}
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="message-form">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your portfolio..."
          disabled={isStreaming}
        />
        <button type="submit" disabled={!input.trim() || isStreaming}>
          {isStreaming ? 'Stop' : 'Send'}
        </button>
        {isStreaming && (
          <button type="button" onClick={stopStreaming}>
            Stop
          </button>
        )}
      </form>
    </div>
  );
}
```

### Message Bubble Component

```tsx
interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  
  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-content">
        {message.content}
        {message.streaming && <span className="cursor">|</span>}
      </div>
      
      {/* Tool Calls */}
      {message.toolCalls && message.toolCalls.length > 0 && (
        <div className="tool-calls">
          {message.toolCalls.map((tool, index) => (
            <div key={index} className="tool-call">
              <span className="tool-name">{tool.name}</span>
              {tool.duration && (
                <span className="tool-duration">({tool.duration}ms)</span>
              )}
            </div>
          ))}
        </div>
      )}
      
      <div className="message-meta">
        {message.timestamp.toLocaleTimeString()}
      </div>
    </div>
  );
}
```

### Streaming Indicator

```tsx
export function StreamingIndicator() {
  return (
    <div className="streaming-indicator">
      <div className="typing-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <span>SigmaSight is thinking...</span>
    </div>
  );
}
```

## Error Handling Patterns

### Network Error Recovery

```typescript
function useRobustSSE() {
  const [retryCount, setRetryCount] = useState(0);
  const maxRetries = 3;
  
  const { connect, disconnect } = useSSE({
    onError: (error) => {
      if (retryCount < maxRetries) {
        const delay = Math.pow(2, retryCount) * 1000; // Exponential backoff
        setTimeout(() => {
          setRetryCount(prev => prev + 1);
          // Retry connection
        }, delay);
      } else {
        // Show permanent error state
      }
    },
    onOpen: () => {
      setRetryCount(0); // Reset on successful connection
    }
  });
  
  return { connect, disconnect, isRetrying: retryCount > 0 };
}
```

### Token Refresh

```typescript
async function sendMessageWithAuth(text: string, token: string) {
  try {
    await sendMessage(text);
  } catch (error) {
    if (error.status === 401) {
      // Token expired, try to refresh
      const newToken = await refreshToken();
      if (newToken) {
        // Retry with new token
        await sendMessage(text);
      } else {
        // Redirect to login
        window.location.href = '/login';
      }
    }
  }
}
```

## Performance Optimization

### Virtual Scrolling for Long Conversations

```tsx
import { FixedSizeList as List } from 'react-window';

function MessageList({ messages }: { messages: ChatMessage[] }) {
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style}>
      <MessageBubble message={messages[index]} />
    </div>
  );

  return (
    <List
      height={600}
      itemCount={messages.length}
      itemSize={100}
      itemData={messages}
    >
      {Row}
    </List>
  );
}
```

### Memory Management

```typescript
function useChat() {
  // Limit message history to prevent memory issues
  const MAX_MESSAGES = 1000;
  
  const addMessage = useCallback((message: ChatMessage) => {
    setMessages(prev => {
      const newMessages = [...prev, message];
      if (newMessages.length > MAX_MESSAGES) {
        return newMessages.slice(-MAX_MESSAGES);
      }
      return newMessages;
    });
  }, []);
}
```

## Testing SSE Connections

### Mock SSE for Testing

```typescript
export class MockSSEConnection {
  private callbacks: Record<string, Function[]> = {};
  
  on(event: string, callback: Function) {
    if (!this.callbacks[event]) {
      this.callbacks[event] = [];
    }
    this.callbacks[event].push(callback);
  }
  
  emit(event: string, data: any) {
    this.callbacks[event]?.forEach(callback => callback(data));
  }
  
  simulateChat(messages: string[]) {
    this.emit('start', { conversation_id: 'test', mode: 'green' });
    
    messages.forEach((text, index) => {
      setTimeout(() => {
        const words = text.split(' ');
        words.forEach((word, wordIndex) => {
          setTimeout(() => {
            this.emit('message', { delta: word + ' ', role: 'assistant' });
          }, wordIndex * 50);
        });
        
        if (index === messages.length - 1) {
          setTimeout(() => {
            this.emit('done', { tool_calls_count: 0 });
          }, words.length * 50);
        }
      }, index * 1000);
    });
  }
}
```

## Common Pitfalls & Solutions

1. **Memory Leaks**: Always cleanup SSE connections and cancel timeouts
2. **Buffer Management**: Handle partial JSON in SSE stream properly
3. **Connection Drops**: Implement exponential backoff for reconnection
4. **Token Expiry**: Check auth status before long operations
5. **Browser Limits**: Most browsers limit 6 concurrent SSE connections
6. **Mobile Issues**: SSE may disconnect on mobile when app backgrounds

## Browser Compatibility

SSE is supported in all modern browsers. For older browsers, consider:

```typescript
function isSSESupported(): boolean {
  return typeof EventSource !== 'undefined';
}

// Fallback to polling for unsupported browsers
if (!isSSESupported()) {
  // Implement polling-based chat
}
```

This implementation provides a robust, production-ready SSE streaming solution for the SigmaSight chat interface.