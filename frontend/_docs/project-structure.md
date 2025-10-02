# Project Structure

## Overview
The SigmaSight frontend follows Next.js best practices with a clean separation between routing (in `/app`) and shared application code (in `/src`). This structure aligns with Next.js's "Option 1" pattern where the `app` directory remains at the project root while other code is organized in shared folders.

## Current Directory Structure (With Multi-Page Implementation)

```
frontend/
├── app/                        # Next.js App Router
│   ├── api/                    # API routes
│   │   └── proxy/              # Backend proxy endpoints
│   ├── dev/                    # Development tools
│   │   └── api-test/           # API testing page
│   │       └── page.tsx
│   ├── landing/                # Marketing landing page
│   │   └── page.tsx            # Public landing page (route: /landing)
│   ├── login/                  # Authentication
│   │   └── page.tsx            # Login page (thin wrapper)
│   ├── portfolio/              # Main dashboard (EXISTING - Modular Pattern)
│   │   └── page.tsx            # Portfolio dashboard - ~230 lines (Keep as-is)
│   ├── public-positions/       # 🔄 PLANNED - Container Pattern
│   │   └── page.tsx            # Will be thin wrapper (~8 lines)
│   ├── private-positions/      # 🔄 PLANNED - Container Pattern
│   │   └── page.tsx            # Will be thin wrapper (~8 lines)
│   ├── organize/               # 🔄 PLANNED - Container Pattern
│   │   └── page.tsx            # Will be thin wrapper (~8 lines)
│   ├── ai-chat/                # 🔄 PLANNED - Container Pattern
│   │   └── page.tsx            # Will be thin wrapper (~8 lines)
│   ├── settings/               # 🔄 PLANNED - Container Pattern
│   │   └── page.tsx            # Will be thin wrapper (~8 lines)
│   ├── providers.tsx           # ✅ IMPLEMENTED - Auth context & global providers
│   ├── error.tsx               # Global error handling
│   ├── layout.tsx              # ✅ UPDATED - Root layout with navigation
│   ├── loading.tsx             # Global loading state
│   └── page.tsx                # Root page (redirects to /landing)
│
├── src/                        # Application Source Code
│   ├── containers/             # 🔄 PLANNED - Container components for pages
│   │   ├── PublicPositionsContainer.tsx   # (To be created)
│   │   ├── PrivatePositionsContainer.tsx  # (To be created)
│   │   ├── OrganizeContainer.tsx          # (To be created)
│   │   ├── AIChatContainer.tsx            # (To be created)
│   │   └── SettingsContainer.tsx          # (To be created)
│   ├── components/             # React components
│   │   ├── common/             # ✅ NEW - Shared reusable components
│   │   │   ├── BasePositionCard.tsx      # Foundation card component
│   │   │   ├── PositionSectionHeader.tsx # Section headers with badges
│   │   │   └── PositionList.tsx          # Generic list container
│   │   ├── positions/          # ✅ NEW - Position card adapters
│   │   │   ├── StockPositionCard.tsx     # Stock/ETF adapter
│   │   │   ├── OptionPositionCard.tsx    # Options adapter
│   │   │   ├── PrivatePositionCard.tsx   # Private investments adapter
│   │   │   └── OrganizePositionCard.tsx  # Organize page adapter (no P&L)
│   │   ├── navigation/         # ✅ IMPLEMENTED - Navigation components
│   │   │   ├── NavigationDropdown.tsx     # Dropdown menu with all 6 pages
│   │   │   └── NavigationHeader.tsx       # Header with branding and dropdown
│   │   ├── app/                # App-specific components
│   │   │   ├── ChatInput.tsx
│   │   │   ├── Header.tsx
│   │   │   └── ThemeToggle.tsx
│   │   ├── auth/               # Authentication components
│   │   │   └── LoginForm.tsx  # Login form with authentication logic
│   │   ├── chat/               # Chat system components
│   │   │   └── ChatInterface.tsx
│   │   ├── portfolio/          # Portfolio components (Modular, Reusable)
│   │   │   ├── FactorExposureCards.tsx    # Factor exposure display
│   │   │   ├── FilterBar.tsx              # Filter & sort controls
│   │   │   ├── OptionsPositions.tsx       # Options contracts display
│   │   │   ├── PortfolioError.tsx         # Error handling & display
│   │   │   ├── PortfolioHeader.tsx        # Portfolio name & chat input
│   │   │   ├── PortfolioMetrics.tsx       # Summary metrics cards
│   │   │   ├── PortfolioPositions.tsx     # 3-column investment class grid (positions)
│   │   │   ├── PortfolioStrategiesView.tsx # ✅ NEW - 3-column grid (strategies)
│   │   │   ├── PrivatePositions.tsx       # Private/alternative investments
│   │   │   ├── PublicPositions.tsx        # Public equity/ETF positions
│   │   │   ├── StrategyList.tsx
│   │   │   └── TagEditor.tsx
│   │   ├── strategies/         # ✅ NEW - Strategy display components
│   │   │   ├── StrategyCard.tsx           # Strategy wrapper component
│   │   │   ├── StrategyPositionList.tsx   # Strategy list container
│   │   │   └── index.ts                   # Module exports
│   │   ├── organize/           # ✅ IMPLEMENTED - Organize page components
│   │   │   ├── SelectablePositionCard.tsx  # Wrapper with checkbox & tags
│   │   │   ├── LongPositionsList.tsx       # Long positions list
│   │   │   ├── ShortPositionsList.tsx      # Short positions list
│   │   │   ├── OptionsPositionsList.tsx    # Options positions list
│   │   │   ├── PrivatePositionsList.tsx    # Private positions list
│   │   │   ├── StrategyCard.tsx            # Strategy display card
│   │   │   └── TagBadge.tsx                # Tag display component
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
│   │   ├── usePortfolioData.ts      # Portfolio data fetching & state management
│   │   ├── useStrategies.ts         # ✅ NEW - Strategy data hook
│   │   ├── useTags.ts               # ✅ NEW - Tag management hook
│   │   └── useStrategyFiltering.ts  # ✅ NEW - Strategy filtering by inv. class
│   ├── lib/                    # Utility libraries
│   │   ├── auth.ts             # Authentication utilities
│   │   ├── dal.ts              # Data access layer
│   │   ├── formatters.ts       # Number & currency formatting utilities
│   │   ├── portfolioType.ts    # Portfolio type definitions
│   │   ├── types.ts            # Shared type definitions
│   │   └── utils.ts            # General utilities
│   ├── pages/                  # Legacy pages (if any)
│   ├── services/               # API services
│   │   ├── apiClient.ts             # Base HTTP client
│   │   ├── authManager.ts           # Authentication service
│   │   ├── chatAuthService.ts       # Chat authentication
│   │   ├── chatService.ts           # Chat messaging
│   │   ├── portfolioResolver.ts     # Portfolio ID resolution
│   │   ├── portfolioService.ts      # Portfolio data
│   │   ├── positionApiService.ts    # Position operations
│   │   ├── strategiesApi.ts         # ✅ NEW - Strategy management API (12/12 methods)
│   │   ├── tagsApi.ts               # ✅ NEW - Tag management API (10/10 methods)
│   │   └── requestManager.ts        # Request retry/deduplication
│   ├── stores/                 # State management (Zustand)
│   │   ├── portfolioStore.ts  # 🆕 NEW - Global portfolio ID state
│   │   ├── chatStore.ts       # Chat persistent data
│   │   └── streamStore.ts     # Chat streaming state
│   ├── styles/                 # Global styles
│   │   └── globals.css
│   ├── types/                  # TypeScript type definitions
│   │   ├── analytics.ts
│   │   └── strategies.ts       # ✅ NEW - Strategy & tag type definitions (25+ exports)
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

### 1. **Hybrid Architecture Pattern**
We use two patterns based on the page:
- **Modular Pattern** (Existing portfolio page): Page file contains logic (~230 lines)
- **Container Pattern** (New pages): Thin pages (8 lines) + container components (150-250 lines)

### 2. **Separation of Concerns**
- **`/app`**: Contains Next.js routing files (thin for new pages)
- **`/src/containers`**: Business logic for new pages
- **`/src`**: Contains all shared application code
- This follows Next.js documentation's "Option 1" pattern

### 3. **Import Path Strategy**
- All imports use absolute paths via the `@/` alias
- `@/` maps to `./src/` in tsconfig.json
- Example: `import { Button } from '@/components/ui/button'`

### 4. **State Management**
- **Portfolio ID**: Stored in Zustand portfolioStore (global, no URL params)
- **User Auth**: React Context in providers.tsx
- **Chat State**: Split between chatStore and streamStore
- **Portfolio Switching**: Logout required (no in-app switching)

### 5. **Component Organization**
- **`ui/`**: Reusable ShadCN UI components
- **`app/`**: Components specific to app pages
- **`auth/`**: Authentication-related components
- **`chat/`**: Chat-related components
- **`portfolio/`**: Portfolio-specific components

### 6. **Service Layer**
All API interactions go through the services layer (no direct fetch calls):
- `portfolioService.ts`: Portfolio data fetching
- `chatService.ts`: Chat messaging
- `authManager.ts`: Authentication management
- `requestManager.ts`: Request retry and deduplication

## Key Routes

### Public Routes
- `/` - Redirects to `/landing`
- `/landing` - Marketing landing page
- `/login` - Authentication page

### Protected Routes (Navigation Dropdown)
- `/portfolio` - Main dashboard (existing modular pattern)
- `/public-positions` - Public equity positions (container pattern)
- `/private-positions` - Private/alternative positions (container pattern)
- `/organize` - Strategy & tag management (container pattern)
- `/ai-chat` - AI assistant chat (container pattern)
- `/settings` - User & portfolio settings (container pattern)

### Development Routes
- `/dev/api-test` - API testing interface

### Navigation
- **Dropdown Menu**: All 6 protected routes accessible via dropdown
- **No Portfolio Switching**: Must logout to change portfolios
- **Portfolio ID**: Stored in Zustand, not in URL

## State Management

### Zustand Stores
- **`portfolioStore`**: 🆕 Global portfolio ID (persists across pages)
- **`chatStore`**: Persistent chat data (conversations, messages)
- **`streamStore`**: Streaming state management (active streams, chunks)

### Context Providers
- **`AuthContext`**: 🆕 User authentication state (in providers.tsx)
- **`ThemeContext`**: Dark/light theme management

## Authentication Flow

1. User logs in at `/login`
2. JWT token stored in localStorage
3. Portfolio ID stored in Zustand portfolioStore
4. Token used for all API calls
5. Portfolio ID persists across page navigations
6. Logout clears both token and portfolio ID
7. No in-app portfolio switching (must logout)

## Development Workflow

### File Placement Guidelines
1. **New page?** → Add thin wrapper to `/app/[route]/page.tsx` (8 lines)
2. **Page logic?** → Add container to `/src/containers/[Page]Container.tsx`
3. **New component?** → Add to `/src/components/[category]/`
4. **New hook?** → Add to `/src/hooks/`
5. **New service?** → Add to `/src/services/`
6. **New utility?** → Add to `/src/lib/` or `/src/utils/`
7. **New type?** → Add to `/src/types/`
8. **Global state?** → Add to `/src/stores/`

### Import Examples
```typescript
// Containers (NEW)
import { PublicPositionsContainer } from '@/containers/PublicPositionsContainer'
import { SettingsContainer } from '@/containers/SettingsContainer'

// Components
import { NavigationDropdown } from '@/components/navigation/NavigationDropdown'
import { Button } from '@/components/ui/button'
import { LoginForm } from '@/components/auth/LoginForm'
import { PortfolioHeader } from '@/components/portfolio/PortfolioHeader'

// Hooks
import { usePortfolioData } from '@/hooks/usePortfolioData'
import { usePositions } from '@/hooks/usePositions'

// Stores (NEW)
import { usePortfolioStore } from '@/stores/portfolioStore'

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

---

## Reusable Position Card Architecture (Added 2025-10-01)

### Overview
Implemented a layered component architecture for position cards that enables reuse across multiple pages while maintaining UX consistency. This system consists of foundation components, domain adapters, and page-specific wrappers.

### Component Layers

#### 1. Foundation Layer (`/src/components/common/`)
**BasePositionCard.tsx** - Pure presentation component (~65 lines)
- Accepts pre-formatted strings as props
- Handles theme switching and hover states
- Uses design tokens from tailwind.config.js
- NO business logic - just rendering

**PositionSectionHeader.tsx** - Section headers with count badges
**PositionList.tsx** - Generic list container with empty state handling

#### 2. Adapter Layer (`/src/components/positions/`)
Domain-specific adapters that transform data into BasePositionCard props:

**StockPositionCard.tsx** - For stocks/ETFs
- Looks up company names
- Formats with `formatNumber()`
- Handles LONG/SHORT display logic
- Shows P&L with color coding

**OptionPositionCard.tsx** - For options contracts
- Maps position types (LC/LP/SC/SP) to labels
- Formats with `formatCurrency()`
- Shows strike prices and expiration
- Shows P&L with color coding

**PrivatePositionCard.tsx** - For private investments
- Uses investment_subtype as secondary text
- Formats with `formatCurrency()`
- Shows P&L with color coding

**OrganizePositionCard.tsx** - For Organize page (70 lines)
- **KEY DIFFERENCE**: NO P&L display
- Only shows market values
- Same visual structure as other adapters
- Reuses BasePositionCard foundation

#### 3. Page-Specific Layer

**Portfolio Page** (`/src/components/portfolio/`)
- Uses Stock/Option/Private adapters WITH P&L
- PositionList provides layout and empty states
- Focus: Performance monitoring and analysis

**Organize Page** (`/src/components/organize/`)
- Uses OrganizePositionCard adapter (NO P&L)
- Adds SelectablePositionCard wrapper for:
  - Checkboxes for selection
  - Tag display badges
  - Drag-drop functionality
- Focus: Position grouping and strategy building

### Organize Page Differences

#### Component Structure
```
SelectablePositionCard (wrapper)
  ├── Checkbox input
  ├── OrganizePositionCard (adapter - no P&L)
  │   └── BasePositionCard (foundation)
  └── Tag badges display
```

#### Key Features
1. **No P&L Display** - Organize page focuses on grouping, not performance
2. **Checkbox Selection** - Users can select multiple positions to combine into strategies
3. **Tag Display** - Shows tags associated with each position
4. **Drag-Drop Support** - Drag tags onto positions to categorize them
5. **No Card Backgrounds** - Position lists use simple divs with h3 headings (matching Portfolio page)

#### Implementation Files
- `OrganizePositionCard.tsx` - Universal adapter for all investment types (no P&L)
- `SelectablePositionCard.tsx` - Wrapper adding checkboxes, tags, drag-drop
- `LongPositionsList.tsx` - Long positions with section header
- `ShortPositionsList.tsx` - Short positions with section header
- `OptionsPositionsList.tsx` - Options with Long/Short subsections
- `PrivatePositionsList.tsx` - Private investments with section header

### Design Tokens (tailwind.config.js)

All position cards use centralized design tokens:
```javascript
colors: {
  'card-bg': '#ffffff',           // Light theme background
  'card-bg-dark': '#1e293b',      // Dark theme background
  'card-text': '#111827',         // Primary text light
  'card-text-dark': '#ffffff',    // Primary text dark
  'card-positive': '#34d399',     // Positive P&L (emerald-400)
  'card-negative': '#f87171',     // Negative P&L (red-400)
  // ... more tokens
}
```

**Benefits:**
- Change one value, affects entire app
- Semantic naming (card-positive vs emerald-400)
- Type-safe autocomplete in IDE
- Easy theme customization

### Benefits of This Architecture

1. **Code Reuse**
   - BasePositionCard used by all position types
   - Same visual consistency automatically
   - 40+ lines of duplicate JSX eliminated

2. **Maintainability**
   - Styling changes in one place (BasePositionCard)
   - Theme changes propagate automatically
   - Clear separation of concerns

3. **Flexibility**
   - Portfolio page: Shows P&L for analysis
   - Organize page: Hides P&L, adds checkboxes/tags
   - Same foundation, different features

4. **Scalability**
   - New position type: Create adapter (~20 lines)
   - New page feature: Create wrapper component
   - Foundation remains unchanged

### Usage Examples

**Portfolio Page** (with P&L):
```typescript
import { StockPositionCard } from '@/components/positions/StockPositionCard'

<StockPositionCard position={position} />
// Shows: Symbol, Company, $350K, +$45K (green)
```

**Organize Page** (no P&L, with checkbox):
```typescript
import { SelectablePositionCard } from '@/components/organize/SelectablePositionCard'
import { OrganizePositionCard } from '@/components/positions/OrganizePositionCard'

<SelectablePositionCard
  isSelected={isSelected(position.id)}
  onToggleSelection={() => onToggle(position.id)}
  tags={position.tags}
  onDropTag={(tagId) => onDrop(position.id, tagId)}
>
  <OrganizePositionCard position={position} />
</SelectablePositionCard>
// Shows: Checkbox, Symbol, Company, $350K, Tags (no P&L)
```

### Migration Pattern

When adding the Organize page, we followed this pattern:
1. Created OrganizePositionCard adapter (reuses BasePositionCard, removes P&L logic)
2. Created SelectablePositionCard wrapper (adds checkboxes, tags, drag-drop)
3. Updated all position list components to use new architecture
4. Removed Card background wrappers to match Portfolio page styling
5. Preserved all functionality (selection, tags, drag-drop)

This same pattern can be applied to future pages with different requirements.