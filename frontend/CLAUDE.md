# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SigmaSight Frontend - A Next.js 14 portfolio analytics dashboard with chat assistant integration. The frontend connects to a FastAPI backend that uses OpenAI Responses API, and is currently in active development with V1.1 chat implementation planned.

> 🤖 **CRITICAL**: The backend uses **OpenAI Responses API**, NOT Chat Completions API.

**Current Status**: Portfolio functionality working with real backend data; Chat system with mock responses (V1.1 implementation in progress)

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
- **Current**: `chatStore.ts` (mock responses)
- **Planned V1.1**: Split architecture (`chatStore` + `streamStore`)

### Authentication Strategy
- **Current**: JWT tokens via `portfolioService.ts` 
- **V1.1 Plan**: Mixed auth (JWT for portfolio, HttpOnly cookies for chat)

## Critical Implementation Context

### Backend Integration Points
- **Working**: Portfolio data via `/api/v1/data/portfolio/{id}/complete`
- **Demo Credentials**: `demo_hnw@sigmasight.com` / `demo12345`
- **Portfolio IDs**: Mapped in `portfolioService.ts`
- **CORS Solution**: Next.js proxy at `/api/proxy/[...path]`

### Chat System (V1.1 Implementation)
- **UI**: Sheet overlay pattern (`ChatInterface.tsx`)
- **State**: Mock responses currently, real streaming planned
- **Architecture Decision**: fetch() POST streaming (not EventSource)
- **Authentication**: HttpOnly cookies for SSE compatibility
- **Modes**: 4 conversation modes (green/blue/indigo/violet)

### Component Architecture
- **ShadCN UI** components in `/components/ui/`
- **Tailwind CSS** with custom SigmaSight color palette
- **Route Groups**: `(landing)` and `(app)` for separation of concerns

## Key Files and Their Purpose

### Services Layer
- `portfolioService.ts` - Real backend data fetching with authentication
- `apiClient.ts` - Base API client utilities

### State Management
- `chatStore.ts` - Chat state (currently mock, V1.1 will split into chatStore + streamStore)
- Context providers for themes and global state

### Core Components
- `ChatInterface.tsx` - Sheet-based chat overlay with 4 modes
- `PortfolioSelectionDialog.tsx` - Portfolio type selector
- `portfolio/page.tsx` - Main dashboard with real data integration

### Configuration
- `next.config.js` - Security headers, webpack config for frontend-only files
- Tailwind with SigmaSight brand colors and design system
- TypeScript strict configuration

## Development Workflow Considerations

### Backend Dependencies
- Backend must be running on `localhost:8000`
- Use proxy route for CORS during development
- Production will use direct API calls with proper CORS headers

### Data Strategy
- High Net Worth portfolio has real backend data
- Individual and Hedge Fund portfolios use mock data
- Portfolio type determined by URL parameter: `?type=high-net-worth`

### Chat Implementation Status
The chat system is partially implemented with mock responses. V1.1 implementation plan includes:
- Split store architecture for performance
- fetch() POST streaming instead of EventSource
- HttpOnly cookie authentication
- Enhanced error taxonomy and retry logic
- Mobile optimization for iOS Safari

### Testing Approach
- Real portfolio data testing with demo credentials
- Mock responses for chat until V1.1 implementation
- URL parameter-based portfolio type selection

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

The frontend is currently functional for portfolio viewing with real backend integration, and is prepared for V1.1 chat implementation with the architectural foundation in place.