# Frontend Development Setup Guide

> **Updated for V1.1 Chat Implementation - HttpOnly Cookies & Split Stores**  
> **Complete setup instructions for AI coding agents building the SigmaSight frontend**

**V1.1 Updates**:
- **Authentication**: Mixed strategy requiring cookie support for streaming
- **State Management**: Split store architecture for performance
- **API Client**: Enhanced with credential support and error taxonomy
- **Mobile Support**: iOS Safari specific configurations

## Prerequisites

- **Node.js**: 18+ or 20+ (LTS recommended)
- **Package Manager**: npm, yarn, or pnpm
- **Backend Running**: SigmaSight backend at `http://localhost:8000`

## Quick Start

### 1. Create Next.js Project

```bash
# Using create-next-app (recommended)
npx create-next-app@latest sigmasight-frontend --typescript --tailwind --eslint --app --src-dir

# Or with specific template
npx create-next-app@latest sigmasight-frontend \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*"

cd sigmasight-frontend
```

### 2. Install Required Dependencies

```bash
# Core dependencies
npm install \
  @tanstack/react-query \
  zustand \
  react-hook-form \
  @hookform/resolvers \
  zod \
  lucide-react

# UI Components (choose one)
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-toast
# OR
npx shadcn-ui@latest init
npx shadcn-ui@latest add button input textarea dialog dropdown-menu toast

# Development dependencies
npm install -D \
  @types/node \
  @testing-library/react \
  @testing-library/jest-dom \
  jest \
  jest-environment-jsdom
```

### 3. Environment Configuration

Create `.env.local`:

```bash
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# App Configuration
NEXT_PUBLIC_APP_NAME=SigmaSight
NEXT_PUBLIC_APP_VERSION=1.0.0

# Development settings
NEXT_PUBLIC_DEV_MODE=true
NEXT_PUBLIC_LOG_LEVEL=debug
```

### 4. Basic Project Structure

```
src/
├── app/                    # Next.js 13+ App Router
│   ├── globals.css
│   ├── layout.tsx
│   ├── page.tsx           # Landing/dashboard
│   ├── login/
│   │   └── page.tsx       # Login page
│   └── chat/
│       └── page.tsx       # Main chat interface
├── components/             # Reusable UI components
│   ├── ui/                # Base UI components (shadcn/ui)
│   ├── chat/              # Chat-specific components
│   ├── auth/              # Authentication components
│   └── layout/            # Layout components
├── hooks/                  # Custom React hooks
│   ├── useAuth.ts
│   ├── useChat.ts
│   └── useSSE.ts
├── lib/                   # Utilities and configuration
│   ├── api.ts             # API client
│   ├── auth.ts            # Auth utilities
│   ├── types.ts           # TypeScript definitions
│   └── utils.ts           # General utilities
├── stores/                # Zustand stores
│   ├── authStore.ts
│   └── chatStore.ts
└── styles/                # Additional styles
    └── globals.css
```

## API Client Setup

### Basic API Client (`src/lib/api.ts`)

```typescript
class SigmaSightAPI {
  private baseURL = process.env.NEXT_PUBLIC_API_URL!;
  private token: string | null = null;

  constructor() {
    // Load token from localStorage on initialization
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token');
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('auth_token', token);
      } else {
        localStorage.removeItem('auth_token');
      }
    }
  }

  // V1.1: Mixed auth - also sets HttpOnly cookies
  setCredentials(include: boolean = true) {
    return include ? 'include' : 'same-origin';
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({
        detail: `HTTP ${response.status}`,
      }));
      throw new Error(error.detail || 'Request failed');
    }

    return response.json();
  }

  // V1.1 Auth methods with cookie support
  async login(email: string, password: string) {
    const response = await fetch(`${this.baseURL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include', // V1.1: Sets HttpOnly cookies
      body: JSON.stringify({ email, password }),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }
    
    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  }

  async getCurrentUser() {
    return this.request<CurrentUserResponse>('/auth/me');
  }

  async logout() {
    await this.request('/auth/logout', { method: 'POST' });
    this.setToken(null);
  }

  // Chat methods
  async createConversation(mode: ConversationMode = 'green') {
    return this.request<ConversationResponse>('/chat/conversations', {
      method: 'POST',
      body: JSON.stringify({ mode }),
    });
  }

  async getConversations() {
    return this.request<ConversationListResponse>('/chat/conversations');
  }

  async deleteConversation(id: string) {
    return this.request(`/chat/conversations/${id}`, {
      method: 'DELETE',
    });
  }

  // V1.1 SSE streaming with cookies and run_id
  async sendMessage(conversationId: string, text: string, runId?: string): Promise<Response> {
    const url = `${this.baseURL}/chat/send`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        ...(this.token && { 'Authorization': `Bearer ${this.token}` }) // Fallback
      },
      credentials: 'include', // V1.1: HttpOnly cookies
      body: JSON.stringify({
        conversation_id: conversationId,
        text,
        run_id: runId || crypto.randomUUID() // V1.1: Deduplication
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail);
    }

    return response;
  }
}

export const api = new SigmaSightAPI();
```

## State Management Setup

### Auth Store (`src/stores/authStore.ts`)

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '@/lib/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  initialize: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.login(email, password);
          set({
            user: response.user,
            token: response.access_token,
            isLoading: false,
          });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Login failed',
            isLoading: false,
          });
          throw error;
        }
      },

      logout: () => {
        api.logout().catch(console.error);
        set({ user: null, token: null, error: null });
      },

      clearError: () => set({ error: null }),

      initialize: async () => {
        const token = get().token;
        if (!token) return;

        try {
          const user = await api.getCurrentUser();
          set({ user });
        } catch {
          // Token expired, clear auth state
          set({ user: null, token: null });
        }
      },
    }),
    {
      name: 'sigmasight-auth',
      partialize: (state) => ({ token: state.token }),
    }
  )
);
```

### V1.1 Split Store Architecture

#### Chat Store - Persistent Data (`src/stores/chatStore.ts`)

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ChatState {
  conversations: ConversationSummary[];
  currentConversationId: string | null;
  messages: Record<string, ChatMessage[]>; // V1.1: By conversationId

  setConversations: (conversations: ConversationSummary[]) => void;
  selectConversation: (id: string) => void;
  addMessage: (conversationId: string, message: ChatMessage) => void;
  clearMessages: (conversationId?: string) => void;
}

export const useChatStore = create<ChatState>()(persist(
  (set) => ({
    conversations: [],
    currentConversationId: null,
    messages: {},

    setConversations: (conversations) => set({ conversations }),

    selectConversation: (id) => 
      set({ currentConversationId: id }),

    addMessage: (conversationId, message) =>
      set((state) => ({
        messages: {
          ...state.messages,
          [conversationId]: [...(state.messages[conversationId] || []), message]
        }
      })),

    clearMessages: (conversationId) => 
      set((state) => {
        if (conversationId) {
          const { [conversationId]: _, ...rest } = state.messages;
          return { messages: rest };
        }
        return { messages: {} };
      })
  }),
  { name: 'sigmasight-chat' }
));
```

#### Stream Store - Runtime State (`src/stores/streamStore.ts`)

```typescript
import { create } from 'zustand';

interface StreamState {
  isStreaming: boolean;
  currentRunId: string | null;
  streamBuffer: string;
  abortController: AbortController | null;
  messageQueue: Array<{ conversationId: string; text: string }>;
  processing: boolean;
  error: string | null;

  setStreaming: (streaming: boolean, runId?: string) => void;
  setBuffer: (buffer: string) => void;
  clearBuffer: () => void;
  setAbortController: (controller: AbortController | null) => void;
  addToQueue: (conversationId: string, text: string) => void;
  removeFromQueue: () => void;
  clearQueue: (conversationId?: string) => void;
  setProcessing: (processing: boolean) => void;
  setError: (error: string | null) => void;
}

export const useStreamStore = create<StreamState>((set, get) => ({
  isStreaming: false,
  currentRunId: null,
  streamBuffer: '',
  abortController: null,
  messageQueue: [],
  processing: false,
  error: null,

  setStreaming: (streaming, runId = null) => 
    set({ isStreaming: streaming, currentRunId: runId }),

  setBuffer: (buffer) => set({ streamBuffer: buffer }),
  clearBuffer: () => set({ streamBuffer: '' }),

  setAbortController: (controller) => set({ abortController: controller }),

  addToQueue: (conversationId, text) => 
    set((state) => {
      // V1.1: Queue cap=1, replace if exists for same conversation
      const filtered = state.messageQueue.filter(m => m.conversationId !== conversationId);
      return { messageQueue: [...filtered, { conversationId, text }] };
    }),

  removeFromQueue: () => 
    set((state) => ({ messageQueue: state.messageQueue.slice(1) })),

  clearQueue: (conversationId) => 
    set((state) => ({
      messageQueue: conversationId 
        ? state.messageQueue.filter(m => m.conversationId !== conversationId)
        : []
    })),

  setProcessing: (processing) => set({ processing }),
  setError: (error) => set({ error })
}));
```

## Testing Setup

### Jest Configuration (`jest.config.js`)

```javascript
const nextJest = require('next/jest');

const createJestConfig = nextJest({
  dir: './',
});

const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapping: {
    '^@/components/(.*)$': '<rootDir>/src/components/$1',
    '^@/lib/(.*)$': '<rootDir>/src/lib/$1',
    '^@/hooks/(.*)$': '<rootDir>/src/hooks/$1',
  },
  testEnvironment: 'jest-environment-jsdom',
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
  ],
};

module.exports = createJestConfig(customJestConfig);
```

### Jest Setup (`jest.setup.js`)

```javascript
import '@testing-library/jest-dom';

// Mock fetch for tests
global.fetch = jest.fn();

// Mock localStorage
Object.defineProperty(window, 'localStorage', {
  value: {
    getItem: jest.fn(() => null),
    setItem: jest.fn(() => null),
    removeItem: jest.fn(() => null),
    clear: jest.fn(() => null),
  },
  writable: true,
});

// Mock EventSource for SSE tests
global.EventSource = jest.fn(() => ({
  addEventListener: jest.fn(),
  removeEventListener: jest.fn(),
  close: jest.fn(),
}));
```

## Development Scripts

Update `package.json`:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage",
    "type-check": "tsc --noEmit"
  }
}
```

## Development Workflow

### 1. Start Development

```bash
# Terminal 1: Start backend (from backend directory)
cd ../backend
uv run python run.py

# Terminal 2: Start frontend
npm run dev
```

### 2. Test with Real Data

Login credentials for testing:
- Email: `demo_growth@sigmasight.com`
- Password: `demo12345`

### 3. Development Checklist

- [ ] Backend API accessible at `http://localhost:8000`
- [ ] Frontend running at `http://localhost:3000`
- [ ] Can login with demo credentials
- [ ] Can create conversation
- [ ] Can send message and receive SSE stream
- [ ] Error states display properly
- [ ] Mobile responsive design
- [ ] TypeScript compilation passes
- [ ] Tests pass

### 4. Common Issues & Solutions

#### CORS Errors
- Ensure backend allows `http://localhost:3000`
- Check CORS headers in network tab

#### Authentication Issues
- Verify token format: `Bearer ${token}`
- Check token expiration
- Ensure localStorage persistence

#### SSE Connection Issues
- Check Accept header: `text/event-stream`
- Verify response content-type
- Test with browser dev tools Network tab

#### Type Errors
- Ensure all API types are defined
- Use strict TypeScript configuration
- Import types from central location

## Production Deployment

### Environment Variables

```bash
# Production .env.local
NEXT_PUBLIC_API_URL=https://api.sigmasight.com/api/v1
NEXT_PUBLIC_DEV_MODE=false
NEXT_PUBLIC_LOG_LEVEL=error
```

### Build Optimization

```bash
# Build with bundle analysis
npm run build
npm run start

# Check bundle size
npx @next/bundle-analyzer
```

### Performance Checklist

- [ ] Code splitting implemented
- [ ] Images optimized (WebP)
- [ ] Unused dependencies removed
- [ ] Bundle size < 500KB gzipped
- [ ] Loading states for all async operations
- [ ] Error boundaries implemented
- [ ] SEO meta tags added

This setup guide provides everything needed to create a production-ready SigmaSight chat frontend with proper development tooling and best practices.