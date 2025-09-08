# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SigmaSight Frontend - A Next.js 14 portfolio analytics dashboard with chat assistant integration. The frontend connects to a FastAPI backend that uses OpenAI Responses API, and is currently in active development with V1.1 chat implementation planned.

> 🤖 **CRITICAL**: The backend uses **OpenAI Responses API**, NOT Chat Completions API.

**Current Status**: Portfolio functionality working with real backend data; Chat system with split store architecture (chatStore + streamStore) implemented

## ⚠️ Critical: Authentication Required for Chat Testing

**Chat functionality will fail with 401 errors unless you follow this sequence:**
1. Navigate to `http://localhost:3005/login`
2. Login with demo credentials (e.g., `demo_hnw@sigmasight.com` / `demo12345`)
3. Wait for automatic redirect to portfolio page
4. Only then test chat functionality

**Why:** Chat system requires JWT token in localStorage, which is set during login. The portfolio authentication establishes the initial token that chat services depend on.

## Development Commands

### 🐳 Docker Commands (Preferred)
```bash
# Start frontend server (production)
cd frontend && docker build -t sigmasight-frontend . && docker run -d -p 3005:3005 --name frontend sigmasight-frontend

# Quick start (if image already built)
docker run -d -p 3005:3005 --name frontend sigmasight-frontend

# Stop frontend
docker stop frontend && docker rm frontend

# Check health
curl http://localhost:3005/api/health

# View logs
docker logs -f frontend
```

### Traditional NPM Commands
```bash
# Development server (runs on port 3005)
cd frontend && npm run dev

# Production build
npm run build
npm run start

# Code quality
npm run lint
npm run type-check

# Testing
npm run test         # Run tests once
npm run test:watch   # Run tests in watch mode

# Install dependencies
npm install
```

### Key Configuration
- **Port**: 3005 (configured to avoid conflicts)
- **Docker Image**: sigmasight-frontend (~210MB optimized)
- **Backend API**: Proxies through `/api/proxy/` to `localhost:8000`
- **Authentication**: JWT tokens for portfolio data, HttpOnly cookies planned for chat

## High-Level Architecture

### Dual-Purpose Structure
```
Landing Pages (Marketing)     Application Pages (Authenticated)
├── / (landing)              ├── /portfolio (main dashboard)  
└── SEO-focused content      └── Real-time portfolio data
```

### Core Data Flow
```
Portfolio Selection → URL Param → Service Layer → Next.js Proxy → Backend API → UI
```

### State Management Architecture
- **Zustand stores** for global state
- **Implemented**: Split architecture with `chatStore.ts` (persistent data) and `streamStore.ts` (streaming state)
- **Request management**: Centralized retry logic and deduplication

### Authentication Strategy
- **Implemented**: Mixed authentication strategy
  - JWT tokens for portfolio API calls
  - HttpOnly cookies for chat streaming
  - Centralized auth management via `authManager.ts`
  - Token caching and race condition prevention

## Critical Implementation Context

### Backend Integration Points
- **Working**: Portfolio data via `/api/v1/data/portfolio/{id}/complete`
- **Demo Credentials**: 
  - High Net Worth: `demo_hnw@sigmasight.com` / `demo12345`
  - Individual: `demo_individual@sigmasight.com` / `demo12345`
  - Hedge Fund: `demo_hedgefundstyle@sigmasight.com` / `demo12345`
- **Portfolio IDs**: Dynamically resolved via `portfolioResolver.ts`
- **CORS Solution**: Next.js proxy at `/api/proxy/[...path]`

### Chat System (Implemented)
- **UI**: Sheet overlay pattern (`ChatInterface.tsx`)
- **State**: Split store architecture - `chatStore` (persistent) + `streamStore` (streaming)
- **Architecture**: fetch() POST streaming with manual SSE parsing
- **Authentication**: HttpOnly cookies with credentials:'include'
- **Modes**: 4 conversation modes (green/blue/indigo/violet)
- **Error Handling**: Comprehensive retry policies with exponential backoff

### Component Architecture
- **ShadCN UI** components in `/components/ui/`
- **Tailwind CSS** with custom SigmaSight color palette
- **Route Groups**: `(landing)` and `(app)` for separation of concerns

## Key Files and Their Purpose

### Services Layer
- `portfolioService.ts` - Real backend data fetching with authentication
- `apiClient.ts` - Base API client utilities
- `chatService.ts` - Conversation management with retry logic
- `chatAuthService.ts` - Cookie-based auth for chat streaming
- `portfolioResolver.ts` - Dynamic portfolio ID resolution
- `authManager.ts` - Centralized auth token management
- `requestManager.ts` - Request retry logic and deduplication
- `positionApiService.ts` - Position-specific API operations

### State Management
- `chatStore.ts` - Persistent chat data (conversations, messages, UI state)
- `streamStore.ts` - Streaming state management (active streams, chunks)
- Context providers for themes and global state
- Zustand persist middleware for state persistence

### Core Components
- `ChatInterface.tsx` - Sheet-based chat overlay with 4 modes
- `PortfolioSelectionDialog.tsx` - Portfolio type selector
- `portfolio/page.tsx` - Main dashboard with real data integration

### Configuration
- `next.config.js` - Security headers, webpack config for frontend-only files
- Tailwind with SigmaSight brand colors and design system
- TypeScript strict configuration
- Vitest for testing with React Testing Library
- Node.js >=18.17.0 requirement

## Development Workflow Considerations

### Backend Dependencies
- Backend must be running on `localhost:8000`
- Database (PostgreSQL) must be running for authentication
- Use proxy route for CORS during development
- Production will use direct API calls with proper CORS headers

### Authentication Flow
- **Login Required First**: Must use `/login` page to establish JWT token
- **Token Storage**: JWT stored in localStorage as `access_token`
- **Chat Dependency**: Chat services read token from localStorage
- **Portfolio Auth**: `authManager.ts` handles automatic portfolio authentication
- **Chat Auth**: `chatAuthService.ts` provides cookie-based streaming auth

### Data Strategy
- High Net Worth portfolio has real backend data
- Individual and Hedge Fund portfolios use mock data
- Portfolio type determined by URL parameter: `?type=high-net-worth`

### Chat Implementation Status
The chat system has been fully implemented with:
- ✅ Split store architecture (`chatStore` + `streamStore`)
- ✅ fetch() POST streaming with manual SSE parsing
- ✅ HttpOnly cookie authentication with credentials:'include'
- ✅ Comprehensive error taxonomy and retry policies
- ✅ Request deduplication and cancellation support
- ✅ Dynamic portfolio ID resolution
- ✅ Conversation lifecycle management

### Testing Approach
- **MANDATORY**: Login first at `/login` to establish authentication
- Real portfolio data testing with demo credentials
- URL parameter-based portfolio type selection (`?type=high-net-worth`)
- Check localStorage for `access_token` to verify authentication

### Monitoring & Debugging
- **Chat Monitor**: `backend/simple_monitor.py` captures browser console logs
- **Monitor Report**: `backend/chat_monitoring_report.json` for analysis
- **Manual Mode**: Connect to Chrome DevTools Protocol for full console capture
- **Automated Mode**: Headless browser for basic monitoring

## Architectural Decisions

### Why Next.js Proxy?
CORS restrictions during development; production will use direct API calls

### Why Split Landing/App?
SEO optimization for marketing vs. functional application pages

### Why Zustand?
Lightweight state management suitable for the application size

### Why Sheet UI for Chat?
Non-intrusive overlay that preserves main portfolio view

### Why Mixed Auth Strategy?
JWT works well for portfolio APIs; HttpOnly cookies required for SSE streaming security

The frontend is fully functional with both portfolio viewing and chat capabilities. The split store architecture has been implemented, authentication flows are complete, and the system includes comprehensive error handling and retry logic.

## Important Notes
- **Authentication is mandatory**: Always login first before testing chat features
- **Token verification**: Check DevTools → Application → localStorage for `access_token`
- **Console monitoring available**: Use `simple_monitor.py` for debugging chat issues
- **Recent fixes (2025-09-04)**: Authentication context passing and OpenAI Responses API format issues resolved