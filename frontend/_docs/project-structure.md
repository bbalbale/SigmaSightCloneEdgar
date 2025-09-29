# Project Structure

## Overview
The SigmaSight frontend follows Next.js best practices with a clean separation between routing (in `/app`) and shared application code (in `/src`). This structure aligns with Next.js's "Option 1" pattern where the `app` directory remains at the project root while other code is organized in shared folders.

## Current Directory Structure

```
frontend/
├── app/                        # Next.js App Router (Routes Only - Minimal Logic)
│   ├── api/                    # API routes
│   │   └── proxy/              # Backend proxy endpoints
│   ├── dev/                    # Development tools
│   │   └── api-test/           # API testing page
│   │       └── page.tsx
│   ├── landing/                # Marketing landing page
│   │   └── page.tsx            # Public landing page (route: /landing)
│   ├── login/                  # Authentication
│   │   └── page.tsx            # Login page
│   ├── portfolio/              # Main application
│   │   └── page.tsx            # Portfolio dashboard (route: /portfolio) - ~230 lines
│   ├── error.tsx               # Global error handling
│   ├── layout.tsx              # Root layout
│   ├── loading.tsx             # Global loading state
│   └── page.tsx                # Root page (redirects to /landing)
│
├── src/                        # Application Source Code
│   ├── components/             # React components
│   │   ├── app/                # App-specific components
│   │   │   ├── ChatInput.tsx
│   │   │   ├── Header.tsx
│   │   │   └── ThemeToggle.tsx
│   │   ├── auth/               # Authentication components
│   │   │   └── LoginForm.tsx  # Login form with authentication logic
│   │   ├── chat/               # Chat system components
│   │   │   └── ChatInterface.tsx
│   │   ├── portfolio/          # Portfolio components (Modular, Reusable)
│   │   │   ├── FactorExposureCards.tsx  # Factor exposure display
│   │   │   ├── FilterBar.tsx            # Filter & sort controls
│   │   │   ├── OptionsPositions.tsx     # Options contracts display
│   │   │   ├── PortfolioError.tsx       # Error handling & display
│   │   │   ├── PortfolioHeader.tsx      # Portfolio name & chat input
│   │   │   ├── PortfolioMetrics.tsx     # Summary metrics cards
│   │   │   ├── PortfolioPositions.tsx   # 3-column investment class grid
│   │   │   ├── PositionCard.tsx         # Individual position card
│   │   │   ├── PrivatePositions.tsx     # Private/alternative investments
│   │   │   ├── PublicPositions.tsx      # Public equity/ETF positions
│   │   │   ├── StrategyList.tsx
│   │   │   └── TagEditor.tsx
│   │   └── ui/                 # ShadCN UI components
│   │       ├── badge.tsx
│   │       ├── button.tsx
│   │       ├── card.tsx
│   │       ├── dialog.tsx
│   │       ├── input.tsx       # Form input component
│   │       ├── sheet.tsx
│   │       └── ...
│   ├── config/                 # Configuration files
│   ├── contexts/               # React contexts
│   │   └── ThemeContext.tsx
│   ├── hooks/                  # Custom React hooks
│   │   └── usePortfolioData.ts # Portfolio data fetching & state management
│   ├── lib/                    # Utility libraries
│   │   ├── auth.ts             # Authentication utilities
│   │   ├── dal.ts              # Data access layer
│   │   ├── formatters.ts       # Number & currency formatting utilities
│   │   ├── portfolioType.ts    # Portfolio type definitions
│   │   ├── types.ts            # Shared type definitions
│   │   └── utils.ts            # General utilities
│   ├── pages/                  # Legacy pages (if any)
│   ├── services/               # API services
│   │   ├── apiClient.ts
│   │   ├── authManager.ts
│   │   ├── chatAuthService.ts
│   │   ├── chatService.ts
│   │   ├── portfolioResolver.ts
│   │   ├── portfolioService.ts
│   │   ├── positionApiService.ts
│   │   └── requestManager.ts
│   ├── stores/                 # State management (Zustand)
│   │   ├── chatStore.ts
│   │   └── streamStore.ts
│   ├── styles/                 # Global styles
│   │   └── globals.css
│   ├── types/                  # TypeScript type definitions
│   │   └── analytics.ts
│   └── utils/                  # Utility functions
│
├── public/                     # Static assets
├── tests/                      # Test files
├── _docs/                      # Documentation
│   └── project-structure.md   # This file
├── .env                        # Environment variables
├── .env.local                  # Local environment overrides
├── Dockerfile                  # Docker configuration
├── next.config.js              # Next.js configuration
├── package.json                # Dependencies
├── tailwind.config.js          # Tailwind CSS config
└── tsconfig.json               # TypeScript config
```

## Architecture Principles

### 1. **Separation of Concerns**
- **`/app`**: Contains only Next.js routing files (pages, layouts, error handling)
- **`/src`**: Contains all application code (components, services, utilities)
- This follows Next.js documentation's "Option 1" pattern

### 2. **Import Path Strategy**
- All imports use absolute paths via the `@/` alias
- `@/` maps to `./src/` in tsconfig.json
- Example: `import { Button } from '@/components/ui/button'`

### 3. **Component Organization**
- **`ui/`**: Reusable ShadCN UI components
- **`app/`**: Components specific to app pages
- **`auth/`**: Authentication-related components
- **`chat/`**: Chat-related components
- **`portfolio/`**: Portfolio-specific components

### 4. **Service Layer**
All API interactions go through the services layer:
- `portfolioService.ts`: Portfolio data fetching
- `chatService.ts`: Chat messaging
- `authManager.ts`: Authentication management
- `requestManager.ts`: Request retry and deduplication

## Key Routes

### Public Routes
- `/` - Redirects to `/landing`
- `/landing` - Marketing landing page
- `/login` - Authentication page

### Protected Routes
- `/portfolio` - Main portfolio dashboard
- `/portfolio?type={high-net-worth|individual|hedge-fund}` - Portfolio by type

### Development Routes
- `/dev/api-test` - API testing interface

## State Management

### Zustand Stores
- **`chatStore`**: Persistent chat data (conversations, messages)
- **`streamStore`**: Streaming state management (active streams, chunks)

### Context Providers
- **`ThemeContext`**: Dark/light theme management

## Authentication Flow

1. User logs in at `/login`
2. JWT token stored in localStorage
3. Token used for portfolio API calls
4. HttpOnly cookies used for chat streaming

## Development Workflow

### File Placement Guidelines
1. **New page?** → Add to `/app/[route]/page.tsx`
2. **New component?** → Add to `/src/components/[category]/`
3. **New service?** → Add to `/src/services/`
4. **New utility?** → Add to `/src/lib/` or `/src/utils/`
5. **New type?** → Add to `/src/types/`

### Import Examples
```typescript
// Components
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { LoginForm } from '@/components/auth/LoginForm'
import { ChatInput } from '@/components/app/ChatInput'
import { PortfolioHeader } from '@/components/portfolio/PortfolioHeader'

// Hooks
import { usePortfolioData } from '@/hooks/usePortfolioData'

// Services
import { portfolioService } from '@/services/portfolioService'
import { chatAuthService } from '@/services/chatAuthService'

// Utilities
import { cn } from '@/lib/utils'
import { formatNumber, formatCurrency } from '@/lib/formatters'

// Types
import type { FactorExposure } from '@/types/analytics'
```

## Benefits of This Structure

### 1. **Clear Boundaries**
- Routing logic separate from business logic
- Easy to understand where code belongs
- Follows Next.js best practices

### 2. **Maintainability**
- Consistent import paths
- No duplicate directories
- Clean separation of concerns

### 3. **Scalability**
- Easy to add new routes in `/app`
- Easy to add new features in `/src`
- Components organized by function

### 4. **Developer Experience**
- TypeScript path aliases for clean imports
- Logical grouping of related code
- Standard Next.js patterns

## Component Architecture Pattern (Modular Refactoring)

### Pattern: Option 2 - Modular Components with Shared Hooks
We've implemented a modular architecture pattern where:
- **Page files** (`/app/[route]/page.tsx`) are thin wrappers (~230 lines max)
- **Business logic** lives in custom hooks (`/src/hooks/`)
- **UI components** are small, focused, and reusable (`/src/components/portfolio/`)
- **Utilities** are centralized (`/src/lib/formatters.ts`)

### Example: Page Refactoring
#### Portfolio Page
The portfolio page was refactored from a 540-line monolithic component to:
- **1 custom hook** (`usePortfolioData`) - All data fetching & state management with investment class grouping
- **11 focused components** - Including specialized components for each investment class
- **1 utility file** - Shared formatting functions
- **Result**: Clean, maintainable, ready for multi-page expansion

#### Investment Class Components (Added 2025-09-29)
The portfolio positions display now uses a 3-column layout with specialized components:
- **PublicPositions.tsx** - Displays public equities/ETFs with Long/Short grouping
- **OptionsPositions.tsx** - Shows options contracts with strike prices and expiration dates
- **PrivatePositions.tsx** - Displays private/alternative investments with custom formatting
- **PortfolioPositions.tsx** - Orchestrates the 3-column layout and maintains backward compatibility

#### Login Page
The login page was refactored from a 190-line page file to:
- **1 component** (`LoginForm`) - All authentication logic and UI
- **1 thin wrapper** (`/app/login/page.tsx`) - 5 lines, just renders LoginForm
- **ShadCN UI components** - Button, Input, Card for consistent design
- **Result**: Follows architecture pattern, reusable authentication component

### Component Prop Naming Convention
**Important**: Always check component prop interfaces. Example issue found:
- `FactorExposureCards` expects prop `factors` not `exposures`
- Always verify prop names match component expectations

#

## Deployment Considerations

### Docker Build
- Uses multi-stage build for optimization
- Standalone output mode in next.config.js
- ~210MB optimized image size

### Environment Variables
- Development: `.env.local`
- Production: Environment-specific `.env`
- API proxy configured for CORS handling

## Maintenance Guidelines

1. **Keep `/app` minimal** - Only routing files, thin wrappers (~200-300 lines max)
2. **Extract business logic to hooks** - Use custom hooks for data fetching and state
3. **Create focused components** - Single responsibility, reusable across pages
4. **Organize `/src` by feature** - Group related code
5. **Use absolute imports** - Always use `@/` paths
6. **Verify prop interfaces** - Ensure prop names match component expectations
7. **Centralize utilities** - Keep formatting and helpers in `/src/lib/`
8. **Document new patterns** - Update this file when adding new structures
9. **Test after restructuring** - Ensure all imports resolve correctly

## Best Practices Learned

### Refactoring Large Pages
When refactoring large page components (>300 lines):
1. **Extract data logic** → Create custom hook in `/src/hooks/`
2. **Identify UI sections** → Create component for each major section
3. **Find repeated code** → Extract to utilities in `/src/lib/`
4. **Keep page thin** → Page file should just compose components
5. **Test incrementally** → Verify each extraction works

### Multi-Page Ready Architecture
For applications that will expand to multiple pages:
- Use modular components with shared hooks
- Ensures data consistency across pages
- Components can be mixed and matched
- Hooks provide single source of truth for data