# AI Chat Frontend Migration Plan

**Goal:** Move AI chat agent from backend to frontend to eliminate redundant HTTP calls and use existing frontend services.

**Benefits:**
- 50-80ms faster per tool call (eliminates backend SSE proxy)
- Uses existing frontend services (no duplication)
- Simpler architecture (one data flow path)
- Better error handling (frontend already handles API errors)

---

## Prerequisites

1. OpenAI API key available in environment
2. Existing frontend services in `frontend/services/api/`
3. Current chat UI in `frontend/app/(authenticated)/chat/[id]/`

---

## Phase 1: Setup OpenAI Client on Frontend

### 1.1 Install OpenAI SDK

```bash
cd frontend
npm install openai
```

### 1.2 Create Secure API Route for OpenAI Key

**File:** `frontend/app/api/ai/config/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  // Validate authentication (use existing auth check)
  const authToken = request.cookies.get('auth_token')?.value;

  if (!authToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // Return OpenAI config (not the full key - just validation)
  return NextResponse.json({
    available: !!process.env.OPENAI_API_KEY,
    model: process.env.OPENAI_MODEL || 'gpt-4-turbo-preview'
  });
}
```

### 1.3 Create OpenAI Service

**File:** `frontend/services/ai/openaiService.ts`

```typescript
import OpenAI from 'openai';

class OpenAIService {
  private client: OpenAI | null = null;

  async initialize() {
    // Use Next.js API route to proxy OpenAI calls (keeps key secret)
    // OR use edge function
    // OR use direct client if you're okay with key in frontend env

    this.client = new OpenAI({
      apiKey: process.env.NEXT_PUBLIC_OPENAI_API_KEY,
      dangerouslyAllowBrowser: true // Only if using public key
    });
  }

  getClient() {
    if (!this.client) {
      throw new Error('OpenAI client not initialized');
    }
    return this.client;
  }
}

export const openaiService = new OpenAIService();
```

**Alternative (Secure):** Create proxy API route

**File:** `frontend/app/api/ai/stream/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';

export async function POST(request: NextRequest) {
  // Server-side OpenAI call (key stays secret)
  const client = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY
  });

  const { messages, tools } = await request.json();

  const stream = await client.responses.create({
    model: 'gpt-4-turbo-preview',
    input: messages,
    tools: tools,
    stream: true
  });

  // Convert OpenAI stream to Next.js streaming response
  const encoder = new TextEncoder();
  const readable = new ReadableStream({
    async start(controller) {
      for await (const event of stream) {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify(event)}\n\n`)
        );
      }
      controller.close();
    }
  });

  return new NextResponse(readable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    }
  });
}
```

---

## Phase 2: Create AI Tools Using Existing Services

### 2.1 Identify Existing Frontend Services

**Review these files:**
- `frontend/services/api/portfolioService.ts`
- `frontend/services/api/positionsService.ts`
- `frontend/services/api/pricesService.ts`
- `frontend/services/api/factorsService.ts`

### 2.2 Create Tool Wrapper

**File:** `frontend/services/ai/tools.ts`

```typescript
import { portfolioService } from '@/services/api/portfolioService';
import { positionsService } from '@/services/api/positionsService';
import { pricesService } from '@/services/api/pricesService';

// Tool definitions for OpenAI
export const toolDefinitions = [
  {
    type: 'function',
    name: 'get_portfolio_complete',
    description: 'Get comprehensive portfolio snapshot with positions and values',
    parameters: {
      type: 'object',
      properties: {
        portfolio_id: {
          type: 'string',
          description: 'Portfolio UUID'
        },
        include_holdings: {
          type: 'boolean',
          description: 'Include position details',
          default: true
        },
        include_timeseries: {
          type: 'boolean',
          description: 'Include historical data',
          default: false
        }
      },
      required: ['portfolio_id']
    }
  },
  {
    type: 'function',
    name: 'get_positions_details',
    description: 'Get detailed position information with P&L',
    parameters: {
      type: 'object',
      properties: {
        portfolio_id: {
          type: 'string',
          description: 'Portfolio UUID'
        }
      },
      required: ['portfolio_id']
    }
  },
  {
    type: 'function',
    name: 'get_prices_historical',
    description: 'Get historical price data for portfolio symbols',
    parameters: {
      type: 'object',
      properties: {
        portfolio_id: {
          type: 'string',
          description: 'Portfolio UUID'
        },
        lookback_days: {
          type: 'integer',
          description: 'Days of history (max 180)',
          default: 90
        }
      },
      required: ['portfolio_id']
    }
  },
  {
    type: 'function',
    name: 'get_current_quotes',
    description: 'Get real-time market quotes',
    parameters: {
      type: 'object',
      properties: {
        symbols: {
          type: 'string',
          description: 'Comma-separated symbols (max 5)'
        }
      },
      required: ['symbols']
    }
  },
  {
    type: 'function',
    name: 'get_factor_etf_prices',
    description: 'Get factor ETF prices for analysis',
    parameters: {
      type: 'object',
      properties: {
        lookback_days: {
          type: 'integer',
          description: 'Days of history',
          default: 90
        }
      }
    }
  }
];

// Tool execution handlers
export async function executeTool(
  toolName: string,
  args: any
): Promise<any> {
  try {
    switch (toolName) {
      case 'get_portfolio_complete':
        return await portfolioService.getComplete(
          args.portfolio_id,
          {
            include_holdings: args.include_holdings ?? true,
            include_timeseries: args.include_timeseries ?? false
          }
        );

      case 'get_positions_details':
        return await positionsService.getDetails(args.portfolio_id);

      case 'get_prices_historical':
        return await pricesService.getHistorical(
          args.portfolio_id,
          args.lookback_days ?? 90
        );

      case 'get_current_quotes':
        return await pricesService.getCurrentQuotes(args.symbols);

      case 'get_factor_etf_prices':
        return await pricesService.getFactorETFPrices(
          args.lookback_days ?? 90
        );

      default:
        throw new Error(`Unknown tool: ${toolName}`);
    }
  } catch (error) {
    console.error(`Tool execution error [${toolName}]:`, error);
    return {
      error: error instanceof Error ? error.message : 'Unknown error',
      retryable: true
    };
  }
}
```

---

## Phase 3: Create Prompt Templates

### 3.1 Copy Prompt Templates from Backend

**Copy these files:**
- `backend/app/agent/prompts/common_instructions.md` → `frontend/lib/ai/prompts/common_instructions.md`
- `backend/app/agent/prompts/green_v001.md` → `frontend/lib/ai/prompts/green_v001.md`
- `backend/app/agent/prompts/blue_v001.md` → `frontend/lib/ai/prompts/blue_v001.md`
- `backend/app/agent/prompts/indigo_v001.md` → `frontend/lib/ai/prompts/indigo_v001.md`
- `backend/app/agent/prompts/violet_v001.md` → `frontend/lib/ai/prompts/violet_v001.md`

### 3.2 Create Prompt Manager

**File:** `frontend/lib/ai/promptManager.ts`

```typescript
export class PromptManager {
  private prompts: Map<string, string> = new Map();

  async loadPrompt(mode: string): Promise<string> {
    if (this.prompts.has(mode)) {
      return this.prompts.get(mode)!;
    }

    // Load prompt from file
    const promptFile = await import(`./prompts/${mode}_v001.md`);
    const prompt = promptFile.default;

    this.prompts.set(mode, prompt);
    return prompt;
  }

  async getSystemPrompt(
    mode: string,
    context: { portfolio_id?: string }
  ): Promise<string> {
    const commonInstructions = await import('./prompts/common_instructions.md');
    const modePrompt = await this.loadPrompt(mode);

    let fullPrompt = `${commonInstructions.default}\n\n---\n\n${modePrompt}`;

    // Inject variables
    if (context.portfolio_id) {
      fullPrompt = fullPrompt.replace('{portfolio_id}', context.portfolio_id);
    }

    return fullPrompt;
  }
}

export const promptManager = new PromptManager();
```

---

## Phase 4: Create Chat Service with Tool Execution

### 4.1 Create Main Chat Service

**File:** `frontend/services/ai/chatService.ts`

```typescript
import OpenAI from 'openai';
import { toolDefinitions, executeTool } from './tools';
import { promptManager } from '@/lib/ai/promptManager';

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

interface StreamOptions {
  conversationId: string;
  message: string;
  mode: string;
  portfolioId?: string;
  messageHistory: ChatMessage[];
  onToken?: (token: string) => void;
  onToolCall?: (toolName: string, args: any) => void;
  onToolResult?: (result: any) => void;
  onError?: (error: Error) => void;
  onDone?: (finalText: string) => void;
}

export class ChatService {
  private client: OpenAI;

  constructor() {
    // Use Next.js API route for security
    this.client = new OpenAI({
      apiKey: process.env.NEXT_PUBLIC_OPENAI_API_KEY,
      dangerouslyAllowBrowser: true
    });
  }

  async streamResponse(options: StreamOptions): Promise<void> {
    const {
      message,
      mode,
      portfolioId,
      messageHistory,
      onToken,
      onToolCall,
      onToolResult,
      onError,
      onDone
    } = options;

    try {
      // Build system prompt
      const systemPrompt = await promptManager.getSystemPrompt(mode, {
        portfolio_id: portfolioId
      });

      // Build messages
      const messages = [
        { role: 'system' as const, content: systemPrompt },
        ...messageHistory,
        { role: 'user' as const, content: message }
      ];

      // Call OpenAI with streaming
      const stream = await this.client.chat.completions.create({
        model: 'gpt-4-turbo-preview',
        messages: messages,
        tools: toolDefinitions,
        stream: true
      });

      let currentContent = '';
      const toolCalls: any[] = [];

      for await (const chunk of stream) {
        const delta = chunk.choices[0]?.delta;

        // Handle text content
        if (delta?.content) {
          currentContent += delta.content;
          onToken?.(delta.content);
        }

        // Handle tool calls
        if (delta?.tool_calls) {
          for (const toolCall of delta.tool_calls) {
            if (toolCall.function) {
              const toolName = toolCall.function.name;
              const toolArgs = JSON.parse(toolCall.function.arguments || '{}');

              onToolCall?.(toolName, toolArgs);

              // Execute tool using existing frontend services
              const result = await executeTool(toolName, toolArgs);

              onToolResult?.(result);

              toolCalls.push({
                id: toolCall.id,
                name: toolName,
                result: result
              });
            }
          }
        }
      }

      // If tools were called, continue conversation with results
      if (toolCalls.length > 0) {
        await this.continueWithToolResults(
          messages,
          toolCalls,
          onToken,
          onDone
        );
      } else {
        onDone?.(currentContent);
      }

    } catch (error) {
      onError?.(error as Error);
    }
  }

  private async continueWithToolResults(
    messages: any[],
    toolCalls: any[],
    onToken?: (token: string) => void,
    onDone?: (text: string) => void
  ) {
    // Build continuation message with tool results
    const toolResultsMessage = {
      role: 'user' as const,
      content: `Based on the tool results below, please analyze and respond:\n\n${
        toolCalls.map(tc =>
          `Tool '${tc.name}' returned:\n${JSON.stringify(tc.result, null, 2)}`
        ).join('\n\n')
      }`
    };

    messages.push(toolResultsMessage);

    // Get final response
    const stream = await this.client.chat.completions.create({
      model: 'gpt-4-turbo-preview',
      messages: messages,
      stream: true
    });

    let finalContent = '';
    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta;
      if (delta?.content) {
        finalContent += delta.content;
        onToken?.(delta.content);
      }
    }

    onDone?.(finalContent);
  }
}

export const chatService = new ChatService();
```

---

## Phase 5: Update Chat UI Component

### 5.1 Update Chat Page to Use Frontend Service

**File:** `frontend/app/(authenticated)/chat/[id]/page.tsx`

**Changes needed:**
1. Remove backend SSE endpoint calls
2. Use `chatService.streamResponse()` instead
3. Keep same UI/UX

**Example:**

```typescript
import { chatService } from '@/services/ai/chatService';

// Inside component
const handleSendMessage = async (text: string) => {
  setIsLoading(true);

  await chatService.streamResponse({
    conversationId: conversationId,
    message: text,
    mode: currentMode,
    portfolioId: selectedPortfolioId,
    messageHistory: messages,
    onToken: (token) => {
      // Update UI with streaming token
      setCurrentMessage(prev => prev + token);
    },
    onToolCall: (toolName, args) => {
      // Show tool execution in UI
      console.log(`Calling tool: ${toolName}`, args);
    },
    onToolResult: (result) => {
      // Show tool result in UI
      console.log('Tool result:', result);
    },
    onError: (error) => {
      toast.error(`Error: ${error.message}`);
    },
    onDone: (finalText) => {
      // Save message to backend (for history)
      saveMessage(finalText);
      setIsLoading(false);
    }
  });
};
```

---

## Phase 6: Backend Cleanup

### 6.1 Mark Backend Agent as Deprecated

**Add to:** `backend/app/api/v1/chat/send.py`

```python
# DEPRECATED: This endpoint is being replaced by frontend-native AI chat
# See frontend/app/ai-chat/MIGRATION_PLAN.md for details
# TODO: Remove after frontend migration is complete and tested
```

### 6.2 Keep Backend Endpoints (Data APIs)

**Do NOT remove:**
- `/api/v1/data/*` endpoints - Still used by frontend services
- Authentication endpoints
- All other non-chat APIs

### 6.3 Optional: Remove After Full Migration

**Can be removed after frontend migration is stable:**
- `backend/app/agent/` directory
- `backend/app/api/v1/chat/` directory
- Related dependencies in `pyproject.toml`

---

## Phase 7: Testing

### 7.1 Manual Testing Checklist

- [ ] Create new conversation
- [ ] Send message "Show me my portfolio"
- [ ] Verify AI calls `get_portfolio_complete` tool
- [ ] Verify portfolio data loads correctly
- [ ] Test each tool:
  - [ ] `get_portfolio_complete`
  - [ ] `get_positions_details`
  - [ ] `get_prices_historical`
  - [ ] `get_current_quotes`
  - [ ] `get_factor_etf_prices`
- [ ] Test mode switching (`/mode green`, `/mode blue`, etc.)
- [ ] Test with different portfolios
- [ ] Test error handling (invalid portfolio ID)
- [ ] Test streaming performance (should be faster)

### 7.2 Performance Testing

**Measure latency:**
- Time from message send to first token
- Time from tool call to tool result
- Total response time

**Expected improvements:**
- 50-80ms faster per tool call
- Lower latency for streaming

### 7.3 Comparison Test

**Before (Backend Proxy):**
```
Frontend → Backend SSE → OpenAI → Backend Tools → localhost:8000
```

**After (Frontend Direct):**
```
Frontend → OpenAI → Frontend Tools → Backend API
```

**Measure and compare both flows.**

---

## Phase 8: Deployment

### 8.1 Environment Variables

**Add to `.env.local`:**
```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...
NEXT_PUBLIC_OPENAI_API_KEY=sk-...  # Only if using client-side
OPENAI_MODEL=gpt-4-turbo-preview
```

**Security Note:**
- Use Next.js API routes to keep key server-side
- OR use `NEXT_PUBLIC_` only for development
- OR use Vercel environment variables (encrypted)

### 8.2 Build and Deploy

```bash
cd frontend
npm run build
npm run start
```

### 8.3 Monitor Errors

- Check browser console for errors
- Monitor OpenAI API usage
- Track tool execution success rate

---

## Rollback Plan

If migration fails:

1. **Revert frontend changes:**
   ```bash
   git revert <commit-hash>
   ```

2. **Re-enable backend agent:**
   - Remove deprecation notice
   - Ensure backend SSE endpoint working

3. **Switch frontend back to backend endpoint:**
   - Change chat component to use `/api/v1/chat/send`

---

## Success Criteria

✅ Chat interface works identically to before
✅ All tools execute correctly using frontend services
✅ 50-80ms latency improvement per tool call
✅ No backend proxy for OpenAI calls
✅ Same or better error handling
✅ All existing features work (mode switching, history, etc.)

---

## Questions for AI Agent Executor

Before starting, verify:

1. **Do frontend services already exist?**
   - Check `frontend/services/api/` directory
   - Confirm services match tool requirements

2. **Is OpenAI API key available?**
   - Check environment variables
   - Decide: client-side or API route?

3. **Should we use Responses API or Chat Completions API?**
   - Current backend uses Responses API
   - Frontend can use either (Chat Completions is more common)

4. **Should we keep message history in backend?**
   - For persistence across sessions
   - Or move to frontend state only?

---

## Next Steps

1. Review this plan with team
2. Decide on OpenAI key strategy (API route vs client-side)
3. Begin Phase 1 implementation
4. Test thoroughly before deprecating backend

---

## References

- Backend agent: `backend/app/agent/`
- Frontend services: `frontend/services/api/`
- Current chat UI: `frontend/app/(authenticated)/chat/[id]/`
- OpenAI SDK: https://github.com/openai/openai-node
- Next.js streaming: https://nextjs.org/docs/app/building-your-application/routing/route-handlers#streaming
