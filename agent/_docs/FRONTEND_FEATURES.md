# Frontend Feature Specifications

> **Updated for V1.1 Chat Implementation - Split Stores & Enhanced UX**  
> **Complete feature requirements for SigmaSight Chat Frontend**

**V1.1 Updates**:
- **Authentication**: Mixed strategy (JWT for portfolio, HttpOnly cookies for chat)
- **State Management**: Split store architecture for better performance
- **Message Queue**: One in-flight per conversation with queue cap=1
- **Error Handling**: Enhanced taxonomy with retryable classification
- **Mobile Support**: iOS Safari keyboard fixes and safe area handling
- **Performance**: TTFB metrics and observability hooks

## Core Features

### 1. Authentication System

#### Login Screen
- **Email/password form** with validation
- **Remember me** checkbox (optional)
- **Error handling** for invalid credentials
- **Loading states** during authentication
- **Auto-redirect** to chat after successful login

#### V1.1 Mixed Authentication State
- **JWT tokens**: Stored in localStorage for portfolio API calls
- **HttpOnly cookies**: Set automatically for secure chat streaming
- **Dual auth support**: Bearer tokens as fallback, cookies for streaming
- **Auto token refresh** before expiration
- **Logout functionality** with state cleanup (both tokens and cookies)
- **401 error handling** with auto-relogin prompt

```tsx
interface V1_1_AuthFeatures {
  // Required components
  LoginForm: React.FC;
  LogoutButton: React.FC;
  
  // V1.1 Enhanced auth hook
  useAuth: () => {
    user: User | null;
    token: string | null;
    hasCookieAuth: boolean; // V1.1: Cookie presence check
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
    isLoading: boolean;
    authMethod: 'jwt' | 'cookie' | 'both'; // V1.1: Current method
  };
}
```

### 2. Conversation Management

#### Conversation List (Sidebar)
- **List all conversations** sorted by last updated
- **Show conversation preview** (first 50 chars of last message)
- **Create new conversation** button
- **Delete conversation** with confirmation
- **Search/filter conversations** (nice to have)
- **Infinite scroll** for many conversations

#### Conversation UI
- **Current conversation indicator** (highlighted in sidebar)
- **Conversation metadata** (created date, message count)
- **Empty state** for new conversations
- **Loading states** while fetching history

```tsx
interface ConversationFeatures {
  // Required components
  ConversationList: React.FC<{
    onSelect: (id: string) => void;
    selectedId?: string;
  }>;
  NewConversationButton: React.FC<{
    onCreate: (mode: ConversationMode) => void;
  }>;
  
  // Required hooks  
  useConversations: () => {
    conversations: ConversationSummary[];
    createConversation: (mode?: ConversationMode) => Promise<string>;
    deleteConversation: (id: string) => Promise<void>;
    isLoading: boolean;
  };
}
```

### 3. Mode Selection

#### Mode Switcher
- **Dropdown or toggle buttons** for 4 modes
- **Visual indicators** for each mode (colors/icons)
- **Mode descriptions** on hover/click
- **Persistent mode setting** per conversation

#### Mode Definitions
- **Green (Default)**: 🟢 Educational - "Explains concepts clearly with context"
- **Blue**: 🔵 Quantitative - "Focuses on numbers and precise analysis"  
- **Indigo**: 🟣 Strategic - "Provides big-picture insights and narratives"
- **Violet**: 🟤 Risk-Focused - "Emphasizes conservative analysis and risks"

```tsx
interface ModeFeatures {
  // Required components
  ModeSelector: React.FC<{
    currentMode: ConversationMode;
    onChange: (mode: ConversationMode) => void;
  }>;
  
  // Mode switching via /mode command
  handleModeCommand: (text: string) => ConversationMode | null;
}
```

### 4. Chat Interface

#### Message Display
- **Message bubbles** with user/assistant styling
- **Timestamp display** for each message
- **Message status** (sending, sent, failed)
- **Streaming animation** during response generation
- **Tool execution indicators** (when AI uses tools)
- **Error message display** with retry options

#### Message Input
- **Text area** with auto-resize
- **Send button** with disabled states
- **Enter to send** (Shift+Enter for new line)
- **Character limit** indicator (4000 chars)
- **Voice input** (nice to have)
- **File upload** (future feature)

```tsx
interface V1_1_ChatFeatures {
  // V1.1 Enhanced components
  MessageList: React.FC<{
    conversationId: string; // V1.1: For split store
    isStreaming: boolean;
    queuedCount: number; // V1.1: Show queued messages
  }>;
  
  MessageInput: React.FC<{
    onSend: (text: string) => void;
    disabled: boolean;
    queuedCount: number; // V1.1: Queue indicator
    placeholder?: string;
  }>;
  
  StreamingIndicator: React.FC<{
    runId?: string; // V1.1: For debugging
    tokensPerSecond?: number; // V1.1: Performance metric
  }>;
  
  QueueIndicator: React.FC<{ // V1.1: New component
    queuedCount: number;
    processing: boolean;
  }>;
  
  ToolExecutionBadge: React.FC<{
    toolName: string;
    duration?: number;
    status: 'running' | 'completed' | 'error';
    runId?: string; // V1.1: For tracing
  }>;
}
```

### 5. Real-time Streaming

#### SSE Connection Management  
- **Automatic connection** on message send
- **Reconnection logic** with exponential backoff
- **Connection status indicator** (connected/disconnected/reconnecting)
- **Manual disconnect** (stop button)
- **Graceful degradation** if SSE not supported

#### Streaming UI
- **Typing animation** while receiving text
- **Progressive text rendering** (word by word)
- **Tool execution visualization** 
- **Completion notification** when response done
- **Response time display** (optional)

```tsx
interface V1_1_StreamingFeatures {
  // V1.1 Enhanced streaming hooks with split stores
  useStreaming: () => {
    isConnected: boolean;
    isStreaming: boolean;
    processing: boolean; // V1.1: Queue processing state
    connectionStatus: 'connected' | 'disconnected' | 'reconnecting';
    currentRunId: string | null; // V1.1: For deduplication
    tokensPerSecond: number; // V1.1: Performance metric
    startStream: (conversationId: string, text: string) => void;
    stopStream: () => void;
    clearQueue: (conversationId?: string) => void; // V1.1: Queue management
  };
  
  useMessageQueue: () => { // V1.1: New queue hook
    queuedCount: number;
    isProcessing: boolean;
    addToQueue: (conversationId: string, text: string) => void;
    removeFromQueue: () => void;
  };
  
  // V1.1 Enhanced components with observability
  ConnectionStatus: React.FC<{
    status: 'connected' | 'disconnected' | 'reconnecting';
    runId?: string;
    performance?: PerformanceMetrics;
  }>;
}
```

## UI/UX Requirements

### Layout Structure
```
┌─────────────────────────────────────┐
│ Header: Logo + User Menu            │
├──────────┬──────────────────────────┤
│ Sidebar  │ Main Chat Area           │
│          │                          │
│ - Convs  │ ┌──────────────────────┐ │
│ - New    │ │ Message List         │ │  
│ - Mode   │ │                      │ │
│          │ │ [User bubble]        │ │
│          │ │ [AI bubble]          │ │
│          │ │ [Streaming...]       │ │
│          │ └──────────────────────┘ │
│          │ ┌──────────────────────┐ │
│          │ │ Message Input        │ │
│          │ │ [Send]               │ │
│          │ └──────────────────────┘ │
└──────────┴──────────────────────────┘
```

### Responsive Design
- **Mobile-first** approach
- **Collapsible sidebar** on mobile
- **Touch-friendly** buttons and inputs
- **Readable text sizes** on all devices
- **Optimized for portrait** orientation

### Accessibility
- **Keyboard navigation** throughout app
- **Screen reader support** with proper ARIA labels  
- **Focus management** for modal dialogs
- **Color contrast** meeting WCAG AA standards
- **Text scaling** support

### Loading States
- **Skeleton screens** while loading conversations
- **Shimmer effects** for message list loading
- **Button spinners** during API calls
- **Progressive loading** for long message lists
- **Empty states** with helpful messaging

### Error Handling
- **Network error banners** with retry options
- **Form validation** with inline error messages
- **API error displays** with user-friendly text
- **Fallback UI** for JavaScript errors
- **Offline mode** indicators

## Advanced Features (Phase 2)

### Message Management
- **Message search** within conversations
- **Export conversation** (PDF/text)
- **Copy message** to clipboard  
- **Pin important messages**
- **Message reactions** (like/dislike)

### Collaboration
- **Share conversation** via link
- **Public/private conversations**
- **Comment on specific messages**
- **@mention users** (multi-user setup)

### Customization
- **Theme switching** (light/dark)
- **Font size adjustment**
- **Custom conversation colors**
- **Notification preferences**

### Analytics Integration
- **Usage tracking** (with user consent)
- **Performance monitoring**
- **Error reporting**
- **User feedback collection**

## Technical Requirements

### Performance
- **Initial load**: < 3 seconds
- **Message send**: < 1 second to start streaming
- **Smooth scrolling** in long conversations
- **Efficient re-renders** (React.memo, useMemo)
- **Code splitting** by route

### Browser Support
- **Chrome/Edge**: Last 2 versions
- **Firefox**: Last 2 versions  
- **Safari**: Last 2 versions
- **Mobile browsers**: iOS Safari, Chrome Mobile

### Bundle Size
- **Initial bundle**: < 500KB gzipped
- **Lazy loading** for non-critical features
- **Tree shaking** for unused code
- **Image optimization** (WebP with fallbacks)

### Security
- **XSS protection** for user-generated content
- **CSRF tokens** for state-changing operations
- **Secure token storage** (httpOnly cookies preferred)
- **Input sanitization** for all user inputs

## Testing Requirements

### Unit Tests
- **Component rendering** tests
- **Hook behavior** tests  
- **Utility function** tests
- **API client** tests (with mocks)
- **Coverage target**: > 80%

### Integration Tests
- **User flows** (login → chat → logout)
- **SSE streaming** simulation
- **Error handling** scenarios
- **Responsive behavior** tests

### E2E Tests
- **Complete user journeys**
- **Cross-browser testing**
- **Mobile device testing**
- **Performance benchmarks**

## Design System

### Color Palette
```css
:root {
  /* Mode colors */
  --mode-green: #22c55e;
  --mode-blue: #3b82f6;
  --mode-indigo: #6366f1;
  --mode-violet: #8b5cf6;
  
  /* UI colors */
  --bg-primary: #ffffff;
  --bg-secondary: #f8fafc;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --border: #e2e8f0;
  --error: #ef4444;
  --success: #22c55e;
}
```

### Typography
- **Primary font**: Inter or system fonts
- **Monospace**: For code/data display
- **Font sizes**: 12px, 14px, 16px, 18px, 24px
- **Line heights**: 1.4-1.6 for readability

### Spacing
- **Base unit**: 4px
- **Common sizes**: 4, 8, 12, 16, 24, 32, 48px
- **Consistent margins/padding** throughout

### Components
- **Reusable UI library** (shadcn/ui recommended)
- **Consistent button styles** and states  
- **Standardized form inputs**
- **Loading and error components**

This specification provides a complete roadmap for building a production-ready SigmaSight chat frontend that delivers an exceptional user experience.