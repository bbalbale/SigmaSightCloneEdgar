# App API Directory Documentation

This document describes all files in `backend/app/api/` and its subdirectories.

---

## Overview

The API is organized into v1 endpoints with multiple categories for different functional areas. Total: 59+ endpoints across 9 categories.

---

## Root-Level Files

### `__init__.py`
Package initialization file for the API module (empty/minimal). Imported implicitly when importing from the `app.api` package.

---

## V1 API Directory (`v1/`)

### `__init__.py`
Package initialization file for v1 API (empty/minimal). Imported implicitly when importing from `app.api.v1` package.

### `router.py`
Main API v1 router that aggregates and combines all endpoint routers into a single unified REST API. Imported in `app/main.py` to register the entire v1 API.

### `auth.py`
Authentication API endpoints for JWT token management, user login/registration, and session control (5 endpoints). Used by frontend authentication flow.

### `data.py`
Raw data API endpoints for portfolio and position data access without calculations (12+ endpoints). Used by frontend portfolio dashboard and chat agent system.

### `portfolios.py`
Portfolio CRUD operations and lifecycle management with multi-portfolio support (7 endpoints). Used by frontend portfolio management.

### `positions.py`
Position CRUD operations and smart features for managing individual holdings (9 endpoints). Used by frontend position management UI.

### `tags.py`
Tag management API for user-scoped organizational tags and reverse lookups (7+ endpoints). Used by frontend tag management UI.

### `position_tags.py`
Position-centric tagging operations for adding, removing, and querying tags on positions (6+ endpoints). Used by frontend position detail page.

### `target_prices.py`
Target price management for portfolio positions with smart price resolution (10 endpoints). Used by frontend target price input UI.

### `insights.py`
AI-powered portfolio insights generation using Claude Sonnet 4 with smart 24-hour caching (5 endpoints). Used by frontend insights dashboard.

### `health.py`
Kubernetes/Railway-compatible health probes for monitoring application status (3 endpoints). Used by deployment platforms.

### `onboarding.py`
User registration and portfolio creation endpoints for beta onboarding flow (3 endpoints). Used by frontend onboarding flow UI.

### `onboarding_status.py`
Real-time batch processing status endpoint for onboarding portfolios (2 endpoints). Used by frontend onboarding progress indicator.

### `fundamentals.py`
Access to fundamental financial data including income statements, balance sheets, and cash flow (4+ endpoints). Used by frontend fundamental analysis pages.

### `equity_search.py`
Search, filtering, and sorting for equities across the symbol universe (1+ endpoints). Used by frontend position creation/search UI.

### `equity_changes.py`
Portfolio capital contributions and withdrawals management (7+ endpoints). Used by frontend portfolio funding management UI.

### `admin_fix.py`
Admin-only endpoints for Railway production data fixes and maintenance operations. Used by admin scripts and maintenance procedures.

### `agent_memories.py`
API endpoints for managing user memories that persist across AI chat conversations (4+ endpoints). Used by frontend memory management UI.

---

## Chat API Subdirectory (`v1/chat/`)

### `__init__.py`
Package initialization file for chat endpoints. Imported when accessing chat endpoints.

### `router.py`
Main chat API router that combines all chat sub-routers (conversations, messages, feedback, memories). Registered in `v1/router.py` with prefix `/chat`.

### `conversations.py`
Conversation lifecycle management endpoints for creating, listing, deleting, and modifying conversations (6 endpoints). Used by frontend chat UI.

### `send.py`
SSE streaming endpoint for real-time AI message responses using OpenAI Responses API (1 endpoint). Used by frontend chat message sending.

### `feedback.py`
Message feedback endpoints for rating AI responses with thumbs up/down and learning integration (2 endpoints). Used by frontend message feedback UI.

### `memories.py`
Memory API for managing user memories that persist across conversations (5 endpoints). Used by frontend memory management.

### `tools.py`
Chat tool definitions and handlers for portfolio data access within AI conversations. Registered with OpenAI Responses API.

---

## Analytics API Subdirectory (`v1/analytics/`)

### `__init__.py`
Package initialization file for analytics endpoints. Implicit import for analytics module.

### `router.py`
Main analytics API router that combines portfolio, spread factors, and aggregate analytics sub-routers. Registered in `v1/router.py` with prefix `/analytics`.

### `portfolio.py`
Single portfolio-level analytics endpoints including overview, risk metrics, exposures, P&L, and performance data (9 endpoints). Used by frontend analytics dashboard.

### `spread_factors.py`
Spread factor analytics for portfolio-level long-short factors using 180-day OLS regression (1+ endpoints). Used by advanced portfolio risk analysis.

### `aggregate.py`
Multi-portfolio aggregate analytics using portfolio-as-asset weighted average approach (1+ endpoints). Used by family office / multi-portfolio view.

---

## Admin API Subdirectory (`v1/admin/`)

### `__init__.py`
Package initialization file for admin endpoints. Implicit import.

### `router.py`
Main admin API router that combines all admin sub-routers. Registered in `v1/router.py`.

### `auth.py`
Admin-only authentication endpoints for admin dashboard login and session management (3 endpoints). Used by admin dashboard authentication.

### `system.py`
System health and maintenance endpoints for admin dashboard including cleanup and aggregation triggers. Used by admin dashboard system monitoring.

### `onboarding.py`
Onboarding funnel analytics for tracking user acquisition and conversion rates. Used by admin dashboard onboarding analytics.

### `ai_metrics.py`
AI request performance analytics including latency, token usage, and error rates. Used by admin dashboard AI monitoring.

### `ai_knowledge.py`
Admin access to AI knowledge base management including RAG documents, memories, and feedback. Used by admin AI system management.

### `ai_tuning.py`
AI model tuning endpoints for managing annotations and training data. Used by admin model improvement workflow.

---

## Endpoints Subdirectory (`v1/endpoints/`)

### `admin_batch.py`
Admin batch processing control endpoints for real-time monitoring and triggering of batch jobs (6 endpoints). Used by admin dashboard batch monitoring.

### `admin_feedback.py`
Admin feedback analysis and learning management endpoints for analyzing AI feedback patterns. Used by admin dashboard feedback analytics.

### `fundamentals.py`
Alternate fundamentals endpoints providing access to financial statement data (4+ endpoints). Alternative endpoint path.

---

## Webhooks Subdirectory (`v1/webhooks/`)

### `__init__.py`
Package initialization for webhooks module. Implicit import.

### `clerk.py`
Clerk webhook handler for user lifecycle and billing events (user creation, deletion, subscription changes). Registered in `v1/router.py`.

---

## Data Subdirectory (`v1/data/`)

### `demo.py`
Demo portfolio bridge endpoint for serving portfolio data from report files (temporary implementation). Registered in `v1/data.py`.

---

## Summary Table

| File | Endpoints | Primary Function | Authentication |
|------|-----------|-----------------|-----------------|
| `auth.py` | 5 | User login, registration, token refresh | Public/JWT |
| `data.py` | 12+ | Portfolio and position raw data | Clerk JWT |
| `portfolios.py` | 7 | Portfolio CRUD and batch control | Clerk JWT |
| `positions.py` | 9 | Position CRUD and smart features | Clerk JWT |
| `tags.py` | 7+ | Tag management and reverse lookups | Clerk JWT |
| `position_tags.py` | 6+ | Position-tag relationship ops | Clerk JWT |
| `target_prices.py` | 10 | Target price management | Clerk JWT |
| `insights.py` | 5 | AI insights generation | Clerk JWT |
| `health.py` | 3 | Health probes | Public |
| `chat/conversations.py` | 6 | Conversation lifecycle | Clerk JWT |
| `chat/send.py` | 1 | SSE message streaming | Clerk JWT |
| `chat/feedback.py` | 2 | Message feedback | Clerk JWT |
| `analytics/portfolio.py` | 9 | Portfolio analytics | Clerk JWT |
| `endpoints/admin_batch.py` | 6 | Batch admin control | Admin JWT |
| `webhooks/clerk.py` | 1 | Clerk webhooks | Signature verified |

---

## Key Architectural Patterns

**Database Session Management**:
- **Core DB** (`get_db`, `get_async_session`): User data, portfolios, positions, messages
- **AI DB** (`get_ai_db`, `get_ai_session`): Memories, feedback, embeddings

**Authentication**:
- **User endpoints:** `get_current_user_clerk` (Clerk JWT)
- **Admin endpoints:** `get_current_admin` (separate admin auth)
- **Webhooks:** Svix signature verification

**Async Patterns**: All endpoints use `async def` with `AsyncSession`.

**Service Layer Pattern**: API endpoints → Service layer → Database operations.
