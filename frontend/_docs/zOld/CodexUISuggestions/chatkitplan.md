# OpenAI ChatKit Integration Plan for SigmaSight AI

**Date**: October 9, 2025
**Status**: Planning Phase
**Purpose**: Evaluate OpenAI ChatKit for portfolio discussion agent on `/sigmasight-ai` page

---

## Executive Summary

OpenAI ChatKit is a newly released (October 6, 2025) framework that provides embeddable, AI-powered chat interfaces with deep customization, streaming, and tool integration. **However, SigmaSight already has a production-ready custom chat agent** using OpenAI's Responses API with superior capabilities.

**Recommendation**: **Do not migrate to ChatKit**. Instead, **leverage the existing chat system** on the SigmaSight AI page with enhanced UI/UX optimized for portfolio analysis.

---

## 1. What is OpenAI ChatKit?

### Overview
ChatKit is part of OpenAI's AgentKit suite announced at DevDay 2025. It provides:
- **Drop-in chat interfaces** that can be embedded in apps
- **Framework-agnostic** (React, Vanilla JS, or Web Component)
- **Deep UI customization** to match brand/theme
- **Built-in response streaming** via SSE
- **Tool and workflow integration** (requires Agent Builder)
- **Rich interactive widgets** and attachments

### Key Components
1. **ChatKit (UI Framework)**: Embeddable chat interface
2. **Agent Builder**: Visual workflow designer (drag-and-drop, like Canva)
3. **Session Management**: Server creates short-lived tokens for frontend
4. **Connector Registry**: Secure tool/API integrations

### Architecture Pattern
```
Frontend (React)
    ↓ useChatKit hook
ChatKit Component
    ↓ client_secret (from backend)
Backend API
    ↓ openai.chatkit.sessions.create()
OpenAI Platform
    ↓ Agent Builder Workflow
Tools/Functions
```

### Installation & Setup
```bash
# Install React bindings
npm install @openai/chatkit-react

# Add ChatKit script to HTML
<script src="https://cdn.platform.openai.com/deployments/chatkit/chatkit.js" async></script>
```

**Backend** (Python example):
```python
@app.post("/api/chatkit/session")
def create_chatkit_session():
    session = openai.chatkit.sessions.create({
        "workflow_id": "workflow_xxx",
        # Additional config
    })
    return {"client_secret": session.client_secret}
```

**Frontend** (React):
```javascript
import { ChatKit, useChatKit } from '@openai/chatkit-react';

export function MyChat() {
  const { control } = useChatKit({
    api: {
      async getClientSecret(existing) {
        const res = await fetch('/api/chatkit/session', {
          method: 'POST'
        });
        const { client_secret } = await res.json();
        return client_secret;
      },
    },
  });

  return <ChatKit control={control} className="h-[600px] w-[320px]" />;
}
```

---

## 2. Data You Can Pass to ChatKit

### Session Configuration
When creating a ChatKit session, you can configure:

1. **Workflow ID** (Required)
   - Points to an Agent Builder workflow
   - Defines agent instructions, tools, and behavior

2. **Context/Instructions**
   - System prompts and agent personality
   - Task-specific guidelines
   - Response format instructions

3. **Custom Tools/Functions**
   - Agent Builder supports custom API integrations
   - MCP (Model Context Protocol) servers
   - Pre-built connectors (file search, databases, APIs)

4. **User Context**
   - User metadata (e.g., portfolio_id, user preferences)
   - Session-specific data
   - Historical conversation state

5. **Guardrails**
   - PII detection
   - Jailbreak prevention
   - Hallucination checks
   - Content moderation

### Agent Builder Workflow Nodes

Available node types for building workflows:

| Node Type | Purpose | Use Case |
|-----------|---------|----------|
| **Agent Node** | Core LLM processing with instructions and tools | Main reasoning/analysis |
| **MCP (Model Context Protocol)** | Connect external tools/APIs | Custom integrations |
| **File Search** | Query vector store (RAG) | Document retrieval |
| **Guardrails** | Safety checks (PII, jailbreak, hallucination) | Compliance/security |
| **Logic Nodes** | Conditional branching, data transformation | Workflow control |
| **User Approval** | Request human confirmation | Sensitive actions |
| **End Node** | Terminate workflow, return output | Exit points |

### Data Passing Patterns

**Portfolio Context** (example):
```javascript
// Frontend: Pass context when creating session
const session = await fetch('/api/chatkit/session', {
  method: 'POST',
  body: JSON.stringify({
    workflow_id: 'portfolio_agent_workflow',
    context: {
      portfolio_id: portfolioId,
      portfolio_value: 2900000,
      risk_tolerance: 'moderate',
      asset_classes: ['stocks', 'bonds', 'options']
    }
  })
});
```

**Custom Tools** (Agent Builder):
- Define API endpoints for portfolio data
- Map to function calls in Agent Builder
- Agent invokes tools during conversation

---

## 3. ChatKit Limitations & Concerns

### Current Limitations
1. **Beta Status**: Agent Builder is in beta, rolling out to paid users
2. **Workflow Dependency**: Requires Agent Builder to configure tools/behavior
3. **No-Code Focus**: Optimized for visual workflow design, not programmatic control
4. **Limited Customization**: Chat UI is pre-built, some styling constraints
5. **Vendor Lock-in**: Tightly coupled to OpenAI platform
6. **Token Management**: Requires backend session token generation
7. **Debugging**: Limited visibility into workflow execution
8. **Costs**: Standard API pricing, but abstracts away fine-grained control

### Compared to Custom Implementation
| Feature | ChatKit | SigmaSight Custom Agent |
|---------|---------|-------------------------|
| **Control** | Low (visual workflows) | High (direct code) |
| **Flexibility** | Medium (pre-built nodes) | High (custom logic) |
| **Tools** | Predefined connectors | Custom function calling |
| **Context** | Session-based | Full conversation history |
| **Streaming** | Built-in SSE | Custom SSE implementation |
| **Cost** | Standard + overhead | Direct API calls only |
| **Debugging** | Limited (black box) | Full observability |
| **Deployment** | Requires OpenAI infra | Self-hosted backend |

---

## 4. SigmaSight's Existing Chat System (Superior)

### Current Implementation Status
**SigmaSight already has a production-ready chat agent** that is MORE capable than ChatKit:

#### Existing Architecture
```
Frontend (Next.js)
    ↓ React hooks + SSE client
Chat Interface Component
    ↓ JWT + HttpOnly cookies
Next.js Proxy (/api/proxy/api/v1/chat/*)
    ↓ CORS handling
FastAPI Backend (/api/v1/chat/*)
    ↓ Custom SSE streaming
OpenAI Responses API (NOT Chat Completions)
    ↓ Function calling
Custom Portfolio Tools (6 functions)
```

#### Available Endpoints (Fully Implemented)
- `POST /api/v1/chat/conversations` - Create conversation
- `GET /api/v1/chat/conversations` - List conversations
- `GET /api/v1/chat/conversations/{id}` - Get conversation
- `PUT /api/v1/chat/conversations/{id}/mode` - Change mode
- `DELETE /api/v1/chat/conversations/{id}` - Delete conversation
- `POST /api/v1/chat/send` - Send message (SSE streaming)

#### Custom Portfolio Tools (Already Implemented)
The agent has **6 custom functions** for deep portfolio analysis:

1. **`get_portfolio_complete`**
   - Complete portfolio snapshot
   - Positions, values, holdings
   - Optional historical data and attribution
   - Max 200 positions per request

2. **`get_portfolio_data_quality`**
   - Data availability assessment
   - Quality scores (0-1)
   - Feasibility checks for analyses
   - Data gap identification

3. **`get_positions_details`**
   - Detailed position information
   - P&L, cost basis, unrealized gains
   - Supports filtering by portfolio or position IDs
   - Max 200 positions

4. **`get_prices_historical`**
   - Historical price data for positions
   - Up to 180 days lookback
   - Automatic symbol selection by market value
   - Includes factor ETFs

5. **`get_current_quotes`**
   - Real-time market quotes
   - Up to 5 symbols per request
   - Includes options data

6. **`get_factor_etf_prices`**
   - Factor analysis proxy ETF prices
   - Historical data up to 180 days
   - Factor mappings (Market Beta, Momentum, Value, Growth, Quality, Size, Low Vol)

#### Conversation Modes (4 Personas)
The agent supports **four distinct conversation modes** - something ChatKit doesn't offer:

| Mode | Persona | Style | Token Budget | Use Case |
|------|---------|-------|--------------|----------|
| **Green** | Teaching Financial Analyst | Educational, step-by-step | 2000 | Learning investors |
| **Blue** | Quantitative Analyst | Concise, data-forward | 1500 | Professional traders |
| **Indigo** | Strategic Investment Analyst | Narrative, thematic | 1800 | Strategic insights |
| **Violet** | Conservative Risk Analyst | Risk-focused, cautious | 1700 | Risk-averse users |

Users can switch modes mid-conversation with `/mode blue` command.

#### SSE Event Types
The existing system emits rich SSE events:
- `start` - Response streaming begins
- `tool_started` - Function call initiated (with args)
- `tool_finished` - Function complete (with duration)
- `content_delta` - Text streaming
- `heartbeat` - Keepalive (every 15s)
- `error` - Error with details
- `done` - Completion with metrics

#### Authentication
Dual authentication support:
- JWT Bearer token (programmatic access)
- HttpOnly cookies (browser SSE)

---

## 5. Comparison: ChatKit vs. Current System

### What ChatKit Offers That We DON'T Have
1. **Pre-built UI Component** - Drop-in chat interface
2. **Visual Workflow Designer** - Agent Builder (no-code)
3. **Built-in Guardrails** - PII, jailbreak, hallucination checks
4. **Connector Registry** - Pre-built API integrations
5. **File Upload UI** - Attachment handling

### What We HAVE That ChatKit DOESN'T Offer
1. **Custom Portfolio Tools** - 6 specialized functions (implemented)
2. **Conversation Modes** - 4 distinct personas with mode switching
3. **Full Control** - Direct code, no vendor lock-in
4. **Custom SSE Events** - Rich streaming with tool visibility
5. **Deep Integration** - Direct database access, no abstraction layer
6. **Observability** - Full logging, debugging, monitoring
7. **Context Management** - Sophisticated session/summarization
8. **Historical Data** - Conversation history with pagination
9. **Rate Limiting** - Custom rate limits per endpoint
10. **Error Handling** - Granular error codes and retry logic

### Feature Parity Analysis

| Feature | ChatKit | SigmaSight Current | Winner |
|---------|---------|-------------------|---------|
| **Chat UI** | ✅ Pre-built | ⚠️ Custom needed | ChatKit |
| **Streaming** | ✅ Built-in | ✅ Custom SSE | Tie |
| **Tools** | ⚠️ Visual config | ✅ 6 custom functions | SigmaSight |
| **Context** | ⚠️ Session-based | ✅ Full history | SigmaSight |
| **Modes** | ❌ Not supported | ✅ 4 personas | SigmaSight |
| **Control** | ❌ Low (no-code) | ✅ Full control | SigmaSight |
| **Flexibility** | ⚠️ Limited | ✅ Unlimited | SigmaSight |
| **Cost** | ⚠️ Higher overhead | ✅ Direct API | SigmaSight |
| **Observability** | ❌ Black box | ✅ Full visibility | SigmaSight |
| **Guardrails** | ✅ Built-in | ⚠️ Custom needed | ChatKit |
| **File Upload** | ✅ Built-in | ❌ Not implemented | ChatKit |

**Winner**: **SigmaSight Current System** (7 wins vs. 3 for ChatKit)

---

## 6. Recommended Approach: Leverage Existing System

### Why NOT Use ChatKit

1. **We Already Have Better**
   - 6 custom portfolio tools vs. generic connectors
   - 4 conversation modes vs. single persona
   - Full control and observability
   - Production-ready and tested

2. **ChatKit Adds Complexity**
   - Requires Agent Builder (beta, no-code tool)
   - Session token management
   - Less flexibility than direct API
   - Vendor lock-in to OpenAI platform

3. **Cost & Maintenance**
   - Additional abstraction layer
   - Harder to debug and optimize
   - Less transparency in costs

4. **Development Time**
   - Would need to rebuild all 6 tools in Agent Builder
   - Migrate conversation modes to workflows
   - Re-implement authentication flow
   - Test and validate new system
   - **Estimated: 2-3 weeks vs. 2-3 days for UI**

### Recommended Implementation: Enhanced Chat UI

Instead of ChatKit, **build a custom portfolio-optimized chat interface** using the existing backend:

#### Frontend Implementation Plan

**Step 1: Create Chat Container** (`SigmaSightAIChatContainer.tsx`)
```typescript
import { useChatConversation } from '@/hooks/useChatConversation';
import { ChatMessages } from '@/components/chat/ChatMessages';
import { ChatInput } from '@/components/chat/ChatInput';
import { ConversationModeSelector } from '@/components/chat/ConversationModeSelector';
import { usePortfolioStore } from '@/stores/portfolioStore';

export function SigmaSightAIChatContainer() {
  const { portfolioId } = usePortfolioStore();

  // Custom hook for SSE streaming
  const {
    messages,
    isStreaming,
    sendMessage,
    mode,
    changeMode,
    createConversation
  } = useChatConversation();

  // Auto-create conversation on mount
  useEffect(() => {
    createConversation('green'); // Default to Green mode
  }, []);

  return (
    <div className="chat-container">
      <ConversationModeSelector
        currentMode={mode}
        onChange={changeMode}
      />

      <ChatMessages
        messages={messages}
        isStreaming={isStreaming}
      />

      <ChatInput
        onSend={sendMessage}
        disabled={isStreaming}
        placeholder="Ask me about your portfolio..."
      />
    </div>
  );
}
```

**Step 2: SSE Streaming Hook** (`hooks/useChatConversation.ts`)
```typescript
export function useChatConversation() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [mode, setMode] = useState<ConversationMode>('green');

  const createConversation = async (initialMode: ConversationMode) => {
    const response = await chatService.createConversation(initialMode);
    setConversationId(response.id);
    setMode(response.mode);
  };

  const sendMessage = async (text: string) => {
    if (!conversationId) return;

    setIsStreaming(true);

    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: text }]);

    // Stream assistant response via SSE
    let assistantMessage = '';
    const eventSource = new EventSource(
      `/api/proxy/api/v1/chat/send`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation_id: conversationId, text })
      }
    );

    eventSource.addEventListener('content_delta', (e) => {
      const data = JSON.parse(e.data);
      assistantMessage += data.delta;
      setMessages(prev => [
        ...prev.slice(0, -1),
        { role: 'assistant', content: assistantMessage }
      ]);
    });

    eventSource.addEventListener('tool_started', (e) => {
      const data = JSON.parse(e.data);
      console.log('Tool called:', data.name, data.args);
      // Show tool indicator in UI
    });

    eventSource.addEventListener('done', () => {
      setIsStreaming(false);
      eventSource.close();
    });
  };

  return {
    messages,
    isStreaming,
    sendMessage,
    mode,
    changeMode: (newMode) => {
      chatService.changeMode(conversationId!, newMode);
      setMode(newMode);
    },
    createConversation
  };
}
```

**Step 3: UI Components**

Create portfolio-specific chat components:

1. **`ChatMessages.tsx`**
   - Message bubbles (user/assistant)
   - Tool call indicators (when functions are invoked)
   - Typing indicators during streaming
   - Markdown rendering for formatted responses
   - Syntax highlighting for code/data

2. **`ChatInput.tsx`**
   - Text input with auto-grow
   - Send button (disabled during streaming)
   - "Stop generation" button
   - Suggested prompts (portfolio-specific)

3. **`ConversationModeSelector.tsx`**
   - 4 mode buttons (Green, Blue, Indigo, Violet)
   - Visual indicators for each persona
   - Tooltips explaining each mode
   - Smooth mode switching

4. **`ToolCallBadge.tsx`**
   - Shows when agent calls a function
   - Displays function name and duration
   - Expandable to show args/results

5. **`SuggestedPrompts.tsx`**
   - Portfolio-specific starter questions:
     - "What's my portfolio value?"
     - "Show me my biggest risks"
     - "Analyze my factor exposures"
     - "Which positions are most correlated?"
     - "What's my portfolio diversification score?"

#### UI/UX Optimizations for Portfolio Analysis

1. **Inline Data Visualization**
   - Render charts/tables in assistant messages
   - Factor exposure bars
   - Correlation heatmaps
   - Position breakdown pie charts

2. **Interactive Elements**
   - Clickable position symbols (navigate to details)
   - "Deep dive" buttons on metrics
   - Export conversation as PDF

3. **Context-Aware Prompts**
   - Suggest follow-up questions based on response
   - Auto-complete common queries
   - Remember user preferences

4. **Responsive Design**
   - Mobile-optimized chat
   - Tablet: split view (chat + data)
   - Desktop: side-by-side layout

5. **Conversation Management**
   - List past conversations
   - Resume previous chats
   - Delete/archive conversations
   - Search conversation history

---

## 7. Implementation Phases

### Phase 1: Core Chat UI (2-3 days)
- [ ] Create `SigmaSightAIChatContainer.tsx`
- [ ] Build `useChatConversation.ts` hook with SSE
- [ ] Implement `ChatMessages` component
- [ ] Implement `ChatInput` component
- [ ] Test basic message flow

### Phase 2: Mode Selection & Tools (1-2 days)
- [ ] Create `ConversationModeSelector` component
- [ ] Add mode switching functionality
- [ ] Implement `ToolCallBadge` for function visibility
- [ ] Test all 4 conversation modes

### Phase 3: Portfolio-Specific Features (2-3 days)
- [ ] Create `SuggestedPrompts` component
- [ ] Add inline data visualization
- [ ] Implement clickable elements (symbols, etc.)
- [ ] Portfolio context injection

### Phase 4: Conversation Management (1-2 days)
- [ ] List conversations sidebar
- [ ] Resume conversation functionality
- [ ] Delete/archive conversations
- [ ] Search conversation history

### Phase 5: Polish & Optimization (1-2 days)
- [ ] Responsive design (mobile/tablet/desktop)
- [ ] Error handling and retry logic
- [ ] Loading states and animations
- [ ] Accessibility (ARIA labels, keyboard nav)

**Total Estimated Time: 7-12 days** (vs. 14-21 days for ChatKit migration)

---

## 8. Alternative: Hybrid Approach (Not Recommended)

If you still want to explore ChatKit despite the recommendation:

### Use ChatKit for UI Only, Keep Backend
- Use ChatKit's `<openai-chatkit>` web component for UI
- Proxy ChatKit session creation through your backend
- Configure Agent Builder workflow to call your existing API endpoints
- Keep custom tools and conversation modes

### Pros
- Polished UI out-of-the-box
- Less frontend code to maintain

### Cons
- Still requires Agent Builder setup (no-code workflow)
- Less control over chat behavior
- More complex authentication flow
- Debugging is harder (black box)
- Vendor lock-in

**Verdict**: **Not worth the tradeoffs**. You'd gain a pre-built UI but lose control, observability, and flexibility.

---

## 9. Cost Analysis

### ChatKit Approach
- **Development**: 14-21 days (Agent Builder setup, migration, testing)
- **Ongoing**: Standard API costs + overhead for session management
- **Maintenance**: Medium (less control, harder debugging)
- **Flexibility**: Low (constrained by Agent Builder)

### Custom UI Approach (Recommended)
- **Development**: 7-12 days (UI components, SSE integration)
- **Ongoing**: Direct API costs only (no overhead)
- **Maintenance**: Low (full control, easy debugging)
- **Flexibility**: High (unlimited customization)

**Savings**: 7-9 days of development time + lower ongoing costs

---

## 10. Final Recommendation

### ✅ RECOMMENDED: Build Custom Portfolio Chat UI

**Why:**
1. ✅ **You already have a superior backend** (6 custom tools, 4 modes)
2. ✅ **Faster to implement** (7-12 days vs. 14-21 days)
3. ✅ **Lower cost** (direct API calls, no overhead)
4. ✅ **Full control** (customize everything)
5. ✅ **Better observability** (debugging, logging, monitoring)
6. ✅ **No vendor lock-in** (own your stack)
7. ✅ **Portfolio-optimized** (tailored to financial analysis)

**Implementation:**
- Use existing `/api/v1/chat/*` endpoints
- Build React components for chat UI
- Leverage SSE streaming for real-time responses
- Create portfolio-specific visualizations
- Optimize for financial data presentation

### ❌ NOT RECOMMENDED: Migrate to ChatKit

**Why NOT:**
1. ❌ **Would lose existing capabilities** (modes, custom tools)
2. ❌ **More complex** (Agent Builder, session tokens)
3. ❌ **Less control** (black box workflows)
4. ❌ **Longer development time** (migration overhead)
5. ❌ **Vendor lock-in** (OpenAI platform dependency)
6. ❌ **Debugging challenges** (less visibility)

---

## 11. Next Steps

1. **Review this plan** with the team
2. **Approve custom UI approach** (recommended)
3. **Prioritize Phase 1** (Core Chat UI)
4. **Assign resources** (1-2 frontend developers)
5. **Set timeline** (1-2 weeks for MVP)
6. **Create design mockups** (chat interface, mode selector, etc.)
7. **Start implementation** following the phased approach above

---

## 12. Additional Resources

### OpenAI ChatKit Documentation
- **Official Docs**: https://platform.openai.com/docs/guides/chatkit
- **GitHub Repo**: https://github.com/openai/chatkit-js
- **Starter App**: https://github.com/openai/openai-chatkit-starter-app
- **ChatKit Site**: https://openai.github.io/chatkit-js/

### SigmaSight References
- **Agent API Docs**: `backend/app/agent/docs/API_DOCUMENTATION.md`
- **API Reference**: `backend/_docs/reference/API_REFERENCE_V1.4.6.md`
- **Existing Chat**: `/ai-chat` page (can reference for patterns)

---

## Conclusion

OpenAI ChatKit is an interesting framework for adding AI chat to applications, but **SigmaSight already has a MORE capable system** in production. The existing custom agent with 6 portfolio tools, 4 conversation modes, and SSE streaming provides superior functionality compared to what ChatKit offers.

**The best path forward is to build a custom, portfolio-optimized chat UI** that leverages the existing backend infrastructure. This approach is:
- ✅ Faster (7-12 days vs. 14-21 days)
- ✅ Cheaper (no migration costs, lower ongoing costs)
- ✅ More flexible (full control and customization)
- ✅ More powerful (keep all existing features)
- ✅ Better aligned with SigmaSight's technical strengths

Focus development effort on creating an exceptional **portfolio-specific chat experience** that showcases your unique capabilities, rather than adopting a generic framework that would constrain your system's potential.
