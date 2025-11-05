# Services Reference Guide

**Purpose**: Complete reference for all existing frontend services  
**Audience**: AI coding agents implementing multi-page features  
**Last Updated**: September 29, 2025

---

## Overview

All API interactions **MUST** go through the services layer. Never make direct `fetch()` calls to the backend. Services are located in `/src/services/` and provide:
- Centralized API endpoint management
- Consistent error handling
- Request retry and deduplication
- Authentication token management
- Type-safe responses

---

## Core Infrastructure Services

### 1. apiClient.ts

**Purpose**: Base HTTP client with proxy support, retry logic, and error handling

**Location**: `/src/services/apiClient.ts`

**Key Methods**:
```typescript
apiClient.get<T>(endpoint: string, options?: RequestOptions): Promise<T>
apiClient.post<T>(endpoint: string, data: any, options?: RequestOptions): Promise<T>
apiClient.patch<T>(endpoint: string, data: any, options?: RequestOptions): Promise<T>
apiClient.delete<T>(endpoint: string, options?: RequestOptions): Promise<T>
apiClient.put<T>(endpoint: string, data: any, options?: RequestOptions): Promise<T>
```

**Usage Example**:
```typescript
import { apiClient } from '@/services/apiClient'

// GET request
const positions = await apiClient.get<{ positions: Position[] }>(
  '/api/v1/data/positions/details?portfolio_id=uuid'
)

// POST request
const strategy = await apiClient.post('/api/v1/strategies/', {
  name: 'My Strategy',
  strategy_type: 'LONG'
})

// PATCH request
await apiClient.patch(`/api/v1/strategies/${strategyId}`, {
  name: 'Updated Name'
})

// DELETE request
await apiClient.delete(`/api/v1/strategies/${strategyId}`)
```

**Features**:
- ✅ Automatic proxy routing to `/api/proxy/`
- ✅ Request retry with exponential backoff
- ✅ Request deduplication
- ✅ Authentication token inclusion
- ✅ Error handling and logging

**When to Use**: All API calls should use this as the base client

---

### 2. authManager.ts

**Purpose**: Centralized authentication and JWT token management

**Location**: `/src/services/authManager.ts`

**Key Methods**:
```typescript
authManager.getToken(type: 'individual' | 'organization'): Promise<string | null>
authManager.setToken(token: string, type: 'individual' | 'organization'): void
authManager.clearTokens(type: 'individual' | 'organization'): void
authManager.clearAllTokens(): void
authManager.validateToken(token: string): Promise<boolean>
authManager.refreshToken(): Promise<string | null>
```

**Usage Example**:
```typescript
import { authManager } from '@/services/authManager'

// Get current token
const token = await authManager.getToken('individual')

// Validate token
const isValid = await authManager.validateToken(token)

// Clear on logout
authManager.clearAllTokens()
```

**Features**:
- ✅ localStorage token caching
- ✅ Automatic token validation
- ✅ Token refresh logic
- ✅ Multi-account support (individual/organization)

**When to Use**: Login/logout flows, token validation

---

### 3. requestManager.ts

**Purpose**: Request retry and deduplication logic

**Location**: `/src/services/requestManager.ts`

**Key Methods**:
```typescript
requestManager.request<T>(
  key: string, 
  requestFn: () => Promise<T>,
  options?: RetryOptions
): Promise<T>
```

**Usage Example**:
```typescript
import { requestManager } from '@/services/requestManager'

// Deduplicated request with retry
const data = await requestManager.request(
  'portfolio-positions-uuid',
  () => fetch('/api/proxy/api/v1/data/positions/details'),
  { maxRetries: 3, retryDelay: 1000 }
)
```

**Features**:
- ✅ Automatic request deduplication
- ✅ Configurable retry logic
- ✅ Exponential backoff
- ✅ In-flight request caching

**When to Use**: Automatically used by apiClient, rarely called directly

---

## Data Fetching Services

### 4. portfolioService.ts

**Purpose**: Main portfolio data fetching service

**Location**: `/src/services/portfolioService.ts`

**Key Methods**:
```typescript
portfolioService.fetchPortfolioData(portfolioId?: string): Promise<PortfolioData>
```

**Returns**:
```typescript
{
  overview: AnalyticsOverview        // Portfolio metrics
  positions: Position[]              // All positions
  factors: FactorExposure[]          // Factor betas
}
```

**Usage Example**:
```typescript
import { portfolioService } from '@/services/portfolioService'

const data = await portfolioService.fetchPortfolioData(portfolioId)
console.log(data.overview.total_value)
console.log(data.positions)
console.log(data.factors)
```

**API Endpoints Called**:
- `/analytics/portfolio/{id}/overview`
- `/data/positions/details`
- `/analytics/portfolio/{id}/factor-exposures`

**When to Use**: Dashboard page, portfolio overview

---

### 5. portfolioResolver.ts

**Purpose**: Dynamic portfolio ID resolution for the current user

**Location**: `/src/services/portfolioResolver.ts`

**Key Methods**:
```typescript
portfolioResolver.getUserPortfolioId(): Promise<string>
portfolioResolver.clearCache(): void
```

**Usage Example**:
```typescript
import { portfolioResolver } from '@/services/portfolioResolver'

// Get user's portfolio ID (cached)
const portfolioId = await portfolioResolver.getUserPortfolioId()

// Clear cache on logout
portfolioResolver.clearCache()
```

**Features**:
- ✅ Automatic caching
- ✅ Handles multiple portfolios (returns first)
- ✅ Falls back to user email-based lookup

**API Endpoints Called**:
- `/data/portfolios`
- `/data/portfolio/{id}/complete`

**When to Use**: Whenever you need the current user's portfolio ID

---

### 6. analyticsApi.ts

**Purpose**: Type-safe analytics and calculations endpoints

**Location**: `/src/services/analyticsApi.ts`

**Key Methods**:
```typescript
analyticsApi.getOverview(portfolioId: string): Promise<ApiResponse<AnalyticsOverview>>
analyticsApi.getCorrelationMatrix(portfolioId: string): Promise<ApiResponse<CorrelationMatrix>>
analyticsApi.getFactorExposures(portfolioId: string): Promise<ApiResponse<FactorExposure[]>>
analyticsApi.getPositionFactorExposures(portfolioId: string): Promise<ApiResponse<PositionFactorExposure[]>>
analyticsApi.getStressTest(portfolioId: string): Promise<ApiResponse<StressTestResults>>
analyticsApi.getDiversificationScore(portfolioId: string): Promise<ApiResponse<DiversificationScore>>
```

**Usage Example**:
```typescript
import analyticsApi from '@/services/analyticsApi'

// Get portfolio overview
const { data, error } = await analyticsApi.getOverview(portfolioId)
if (data) {
  console.log(data.total_value)
  console.log(data.total_return)
}

// Get factor exposures
const { data: factors } = await analyticsApi.getFactorExposures(portfolioId)
console.log(factors)
```

**API Endpoints**:
- `/analytics/portfolio/{id}/overview`
- `/analytics/portfolio/{id}/correlation-matrix`
- `/analytics/portfolio/{id}/factor-exposures`
- `/analytics/portfolio/{id}/positions/factor-exposures`
- `/analytics/portfolio/{id}/stress-test`
- `/analytics/portfolio/{id}/diversification-score`

**When to Use**: Analytics dashboard, risk metrics, factor analysis

---

### 7. positionApiService.ts

**Purpose**: Position details and comparison service

**Location**: `/src/services/positionApiService.ts`

**Key Methods**:
```typescript
positionApiService.getPositionDetails(portfolioId?: string): Promise<Position[]>
positionApiService.comparePositions(symbol1: string, symbol2: string): Promise<Comparison>
```

**Usage Example**:
```typescript
import positionApiService from '@/services/positionApiService'

// Get all positions
const positions = await positionApiService.getPositionDetails(portfolioId)

// Compare two positions
const comparison = await positionApiService.comparePositions('AAPL', 'GOOGL')
```

**API Endpoints**:
- `/data/positions/details`
- `/data/positions/compare`

**When to Use**: Position tables, position comparison features

---

## Strategy & Organization Services

### 8. strategiesApi.ts

**Purpose**: Strategy management and CRUD operations

**Location**: `/src/services/strategiesApi.ts`

**Key Methods**:
```typescript
strategiesApi.create(data: CreateStrategyRequest): Promise<Strategy>
strategiesApi.list(): Promise<{ strategies: Strategy[] }>
strategiesApi.listByPortfolio(params: ListByPortfolioParams): Promise<{ strategies: Strategy[] }>
strategiesApi.get(id: string): Promise<Strategy>
strategiesApi.update(id: string, data: UpdateStrategyRequest): Promise<Strategy>
strategiesApi.delete(id: string): Promise<void>
strategiesApi.addPositions(id: string, positionIds: string[]): Promise<void>
strategiesApi.removePositions(id: string, positionIds: string[]): Promise<void>
strategiesApi.assignTags(id: string, tagIds: string[]): Promise<void>
strategiesApi.removeTags(id: string, tagIds: string[]): Promise<void>
strategiesApi.combine(positionIds: string[], ...): Promise<Strategy>
strategiesApi.detect(portfolioId: string): Promise<{ strategies: Strategy[] }>
```

**Usage Example**:
```typescript
import strategiesApi from '@/services/strategiesApi'

// Create strategy
const strategy = await strategiesApi.create({
  name: 'Tech Growth',
  strategy_type: 'LONG',
  portfolio_id: portfolioId
})

// List portfolio strategies
const { strategies } = await strategiesApi.listByPortfolio({
  portfolioId,
  includeTags: true,
  includePositions: true
})

// Update strategy
await strategiesApi.update(strategyId, {
  name: 'Updated Name'
})

// Add positions to strategy
await strategiesApi.addPositions(strategyId, [positionId1, positionId2])

// Assign tags
await strategiesApi.assignTags(strategyId, [tagId1, tagId2])

// Delete strategy
await strategiesApi.delete(strategyId)
```

**API Endpoints**:
- `/strategies/` (POST, GET)
- `/strategies/{id}` (GET, PATCH, DELETE)
- `/strategies/{id}/positions` (POST, DELETE)
- `/strategies/{id}/tags` (POST, DELETE)
- `/strategies/combine` (POST)
- `/strategies/detect/{portfolio_id}` (GET)
- `/data/portfolios/{id}/strategies` (GET)

**When to Use**: Organize page, strategy management features

---

### 9. tagsApi.ts

**Purpose**: Tag management and categorization

**Location**: `/src/services/tagsApi.ts`

**Key Methods**:
```typescript
tagsApi.create(data: CreateTagRequest): Promise<Tag>
tagsApi.list(includeArchived: boolean): Promise<Tag[]>
tagsApi.get(id: string): Promise<Tag>
tagsApi.update(id: string, data: UpdateTagRequest): Promise<Tag>
tagsApi.delete(id: string): Promise<void>
tagsApi.restore(id: string): Promise<Tag>
tagsApi.createDefaults(): Promise<Tag[]>
tagsApi.reorder(tagIds: string[]): Promise<void>
tagsApi.getStrategies(id: string): Promise<{ strategies: Strategy[] }>
tagsApi.batchUpdate(updates: TagUpdate[]): Promise<void>
```

**Usage Example**:
```typescript
import tagsApi from '@/services/tagsApi'

// Create tag
const tag = await tagsApi.create({
  name: 'High Growth',
  color: '#3B82F6',
  description: 'High growth stocks'
})

// List active tags
const tags = await tagsApi.list(false)  // false = exclude archived

// Update tag
await tagsApi.update(tagId, {
  name: 'Updated Name',
  color: '#10B981'
})

// Archive tag
await tagsApi.delete(tagId)

// Restore archived tag
await tagsApi.restore(tagId)

// Create default tags (idempotent)
const defaults = await tagsApi.createDefaults()

// Get strategies using tag
const { strategies } = await tagsApi.getStrategies(tagId)
```

**API Endpoints**:
- `/tags/` (POST, GET)
- `/tags/{id}` (GET, PATCH, DELETE)
- `/tags/{id}/restore` (POST)
- `/tags/defaults` (POST)
- `/tags/reorder` (POST)
- `/tags/{id}/strategies` (GET)
- `/tags/batch-update` (POST)

**When to Use**: Organize page, tag management features

---

## Chat & Streaming Services

### 10. chatService.ts

**Purpose**: Chat conversation management and SSE streaming

**Location**: `/src/services/chatService.ts`

**Key Methods**:
```typescript
chatService.sendMessage(params: {
  conversationId: string
  message: string
  onChunk: (chunk: string) => void
  onComplete: (fullResponse: string) => void
  onError: (error: Error) => void
  signal?: AbortSignal
}): Promise<void>

chatService.createConversation(params: {
  portfolioId: string
  mode?: string
}): Promise<Conversation>

chatService.getConversation(id: string): Promise<Conversation>
chatService.listConversations(): Promise<Conversation[]>
chatService.deleteConversation(id: string): Promise<void>
```

**Usage Example**:
```typescript
import { chatService } from '@/services/chatService'

// Create conversation
const conversation = await chatService.createConversation({
  portfolioId,
  mode: 'portfolio_analysis'
})

// Send message with streaming
await chatService.sendMessage({
  conversationId: conversation.id,
  message: 'What is my portfolio value?',
  onChunk: (chunk) => {
    console.log('Chunk:', chunk)
    // Update UI with streaming chunk
  },
  onComplete: (fullResponse) => {
    console.log('Complete:', fullResponse)
    // Handle complete message
  },
  onError: (error) => {
    console.error('Error:', error)
    // Handle error
  }
})

// List conversations
const conversations = await chatService.listConversations()

// Delete conversation
await chatService.deleteConversation(conversationId)
```

**API Endpoints**:
- `/chat/conversations` (POST, GET)
- `/chat/conversations/{id}` (GET, DELETE)
- `/chat/conversations/{id}/mode` (PUT)
- `/chat/send` (POST, SSE stream)

**When to Use**: AI Chat page, streaming chat features

---

### 11. chatAuthService.ts

**Purpose**: Chat-specific authentication with cookie-based auth

**Location**: `/src/services/chatAuthService.ts`

**Key Methods**:
```typescript
chatAuthService.login(email: string, password: string): Promise<AuthResponse>
chatAuthService.logout(): Promise<void>
chatAuthService.getUser(): Promise<User>
chatAuthService.ensureAuthenticated(): Promise<boolean>
```

**Usage Example**:
```typescript
import { chatAuthService } from '@/services/chatAuthService'

// Login for chat (sets HTTP-only cookies)
const { user, access_token } = await chatAuthService.login(email, password)

// Ensure chat auth before sending messages
const isAuthed = await chatAuthService.ensureAuthenticated()

// Logout (clears cookies)
await chatAuthService.logout()
```

**Features**:
- ✅ HTTP-only cookie-based authentication
- ✅ Separate from JWT token auth
- ✅ Required for SSE streaming

**API Endpoints**:
- `/auth/login`
- `/auth/logout`
- `/auth/me`

**When to Use**: Chat interface initialization, chat authentication

---

## Service Usage Patterns

### Pattern 1: Through Custom Hooks (Recommended)

```typescript
// Custom hook uses service internally
// src/hooks/usePositions.ts
export function usePositions(investmentClass) {
  const { portfolioId } = useAuth()
  const [positions, setPositions] = useState([])
  
  useEffect(() => {
    const fetchPositions = async () => {
      // Use apiClient service
      const endpoint = `/api/v1/data/positions/details?portfolio_id=${portfolioId}`
      const response = await apiClient.get(endpoint)
      setPositions(response.positions)
    }
    fetchPositions()
  }, [portfolioId])
  
  return { positions, ... }
}

// Component uses hook (recommended)
function MyComponent() {
  const { positions } = usePositions('PUBLIC')
  return <div>{positions.length} positions</div>
}
```

### Pattern 2: Direct Service Usage in Components

```typescript
// Component uses service directly
import strategiesApi from '@/services/strategiesApi'

function StrategyManager() {
  const handleDelete = async (id: string) => {
    await strategiesApi.delete(id)
    // Refresh data
  }
  
  return <button onClick={() => handleDelete(strategyId)}>Delete</button>
}
```

### Pattern 3: Service Composition

```typescript
// Service uses other services
import { apiClient } from '@/services/apiClient'
import { portfolioResolver } from '@/services/portfolioResolver'

async function fetchMyData() {
  // Use resolver to get portfolio ID
  const portfolioId = await portfolioResolver.getUserPortfolioId()
  
  // Use apiClient to fetch data
  const data = await apiClient.get(`/api/v1/data/portfolio/${portfolioId}/complete`)
  
  return data
}
```

---

## Critical Rules

### ✅ DO

1. **Always use services for API calls**
   ```typescript
   // ✅ CORRECT
   import { apiClient } from '@/services/apiClient'
   const data = await apiClient.get('/api/v1/data/positions')
   ```

2. **Use portfolioResolver for portfolio IDs**
   ```typescript
   // ✅ CORRECT
   import { portfolioResolver } from '@/services/portfolioResolver'
   const portfolioId = await portfolioResolver.getUserPortfolioId()
   ```

3. **Import existing services**
   ```typescript
   // ✅ CORRECT
   import strategiesApi from '@/services/strategiesApi'
   import tagsApi from '@/services/tagsApi'
   ```

### ❌ DON'T

1. **Never make direct fetch() calls**
   ```typescript
   // ❌ WRONG
   const response = await fetch('http://localhost:8000/api/v1/data/positions')
   ```

2. **Never hardcode portfolio IDs**
   ```typescript
   // ❌ WRONG
   const portfolioId = '1d8ddd95-3b45-0ac5-35bf-cf81af94a5fe'
   ```

3. **Never recreate existing services**
   ```typescript
   // ❌ WRONG
   class NewApiClient {
     async request() { ... }
   }
   ```

---

## Service Checklist

Before writing any API code, check:
- [ ] Does a service already exist for this endpoint?
- [ ] Can I use apiClient for this request?
- [ ] Do I need portfolioResolver for the portfolio ID?
- [ ] Am I using the correct service method?
- [ ] Have I handled errors properly?
- [ ] Am I using TypeScript types from the service?

---

## Summary

**Total Services**: 11  
**Categories**: Infrastructure (3), Data (4), Organization (2), Chat (2)  
**Key Principle**: ALL API calls must use services  
**Never**: Direct fetch() calls, hardcoded IDs, recreated services
