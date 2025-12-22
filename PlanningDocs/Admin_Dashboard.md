# Admin Dashboard Implementation Plan

**Created**: 2025-12-22
**Updated**: 2025-12-22
**Status**: Phases 1-7 Complete (All Admin Dashboard Features)

## Overview

Create a comprehensive admin dashboard for SigmaSight to:
1. Monitor AI engine operations and **tune AI responses via admin annotations**
2. Track logs and system health
3. Analyze user onboarding

Features separate admin authentication and 30-day rolling data retention.

## User Requirements Summary

| Requirement | Decision |
|-------------|----------|
| Admin Authentication | Separate admin accounts (new table + login endpoint) |
| Onboarding Tracking | Comprehensive (funnel + individual journeys + error analysis) |
| AI Monitoring | Both quality AND performance metrics |
| **AI Tuning** | Admin can comment on AI responses to improve the system |
| Data Retention | 30 days rolling |

---

## Dual Database Architecture

SigmaSight uses **two separate PostgreSQL databases** on Railway:

### Core Database (gondola) - Stock/Portfolio Data
- Users, Portfolios, Positions
- Market data, calculations, snapshots
- Conversations and messages (`agent_conversations`, `agent_messages`)
- Target prices, tags, position tags
- Company profiles
- **Admin tables**: `admin_users`, `admin_sessions`
- **New admin tables**: `user_activity_events`, `batch_run_history`, `daily_metrics`

**Connection**: `DATABASE_URL` / `get_db()` / `get_async_session()`

### AI Database (metro) - AI Learning Data
- `ai_feedback` - User feedback on AI responses (ratings, edits, comments)
- `ai_memories` - Learned user preferences and rules
- `ai_kb_documents` - RAG knowledge base with pgvector embeddings
- **New admin table**: `ai_admin_annotations` - Admin comments for AI tuning

**Connection**: `AI_DATABASE_URL` / `get_ai_db()` / `get_ai_session()`

### Database Session Rules

| Table | Database | FastAPI Dependency | Context Manager |
|-------|----------|-------------------|-----------------|
| `admin_users`, `admin_sessions` | Core | `get_db()` | `get_async_session()` |
| `agent_conversations`, `agent_messages` | Core | `get_db()` | `get_async_session()` |
| `user_activity_events`, `batch_run_history` | Core | `get_db()` | `get_async_session()` |
| `ai_feedback`, `ai_memories` | AI | `get_ai_db()` | `get_ai_session()` |
| `ai_admin_annotations` | AI | `get_ai_db()` | `get_ai_session()` |

---

## Page Structure

```
/admin/login          -> Separate admin login
/admin                -> Dashboard overview (summary cards)
/admin/users          -> User list with onboarding status
/admin/users/[id]     -> Individual user journey timeline
/admin/onboarding     -> Funnel visualization + error breakdown
/admin/ai             -> AI performance metrics
/admin/ai/tuning      -> NEW: Review AI responses + add admin annotations
/admin/batch          -> Batch processing history
```

---

## Implementation Progress

### Phase 1: Admin Authentication Foundation

#### Completed:
- [x] `backend/app/models/admin.py` - AdminUser and AdminSession models
- [x] `backend/migrations_core/versions/o1p2q3r4s5t6_add_admin_user_tables.py` - Migration
- [x] Admin tables created in Railway Core DB
- [x] Two admin accounts seeded:
  - `bbalbale@gmail.com` (super_admin)
  - `elliott.ng@gmail.com` (super_admin)
  - Password: `SigmaSight2026`

#### Backend (Complete):
- [x] `backend/app/core/admin_auth.py` - JWT creation/verification with `type: "admin"` claim
- [x] `backend/app/core/admin_dependencies.py` - `get_current_admin()`, `require_super_admin()`
- [x] `backend/app/api/v1/admin/auth.py` - Login/logout/me/refresh endpoints
- [x] `backend/app/api/v1/admin/router.py` - Admin API router
- [x] Updated `backend/app/api/v1/router.py` - Integrated admin auth router

#### Frontend (Complete):
- [x] `frontend/src/stores/adminStore.ts` - Zustand store with persistence
- [x] `frontend/src/services/adminAuthService.ts` - Admin auth API service
- [x] `frontend/src/components/admin/AdminLoginForm.tsx` - Login form component
- [x] `frontend/app/admin/login/page.tsx` - Login page
- [x] `frontend/app/admin/layout.tsx` - Auth guard layout
- [x] `frontend/app/admin/page.tsx` - Admin dashboard overview page

---

### Phase 1.5: AI Data Access (Complete)

**Purpose**: Allow admins to view AI database content (knowledge base, memories, feedback).

#### Backend (Complete):
- [x] `backend/app/api/v1/admin/ai_knowledge.py` - New endpoints for AI data access
- [x] Updated `backend/app/api/v1/endpoints/admin_feedback.py` - Now uses proper admin auth
- [x] Updated `backend/app/api/v1/endpoints/admin_batch.py` - Now uses proper admin auth

#### New Endpoints Created:

**AI Knowledge Base** (`/admin/ai/knowledge/`):
| Endpoint | Purpose | Database |
|----------|---------|----------|
| `GET /documents` | List RAG documents (paginated, searchable) | AI DB |
| `GET /documents/{id}` | Get full document content | AI DB |
| `GET /documents/stats` | Document statistics by scope | AI DB |
| `GET /memories` | List all user preferences/rules | AI DB |
| `GET /memories/stats` | Memory statistics | AI DB |
| `GET /feedback` | List all user feedback (with context) | AI DB + Core DB |
| `GET /feedback/stats` | Feedback statistics | AI DB |

**Existing Endpoints Updated** (now require admin auth):
- All `/admin/feedback/*` endpoints (8 total)
- All `/admin/batch/*` endpoints (7 total)

---

### Phase 2: AI Tuning System (COMPLETE)

**Purpose**: Allow admins to review AI responses and add annotations to tune the system.

#### Completed:
- [x] `AIAdminAnnotation` model added to `backend/app/models/ai_models.py`
- [x] Migration: `backend/migrations_ai/versions/0002_add_admin_annotations.py`
- [x] Endpoints: `backend/app/api/v1/admin/ai_tuning.py` (11 endpoints)
- [x] Router updated to include tuning endpoints

#### New Table (AI Database):

```sql
-- AI Database (metro)
CREATE TABLE ai_admin_annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL,              -- References agent_messages in Core DB (logical link)
    admin_user_id UUID NOT NULL,           -- References admin_users in Core DB (logical link)
    annotation_type VARCHAR(50) NOT NULL,  -- 'correction', 'improvement', 'flag', 'approved'
    content TEXT NOT NULL,                 -- Admin's comment/correction
    suggested_response TEXT,               -- Optional: what the AI should have said
    severity VARCHAR(20),                  -- 'minor', 'moderate', 'critical'
    tags JSONB DEFAULT '[]',               -- Categorization tags ['tone', 'accuracy', 'completeness']
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'reviewed', 'applied'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_ai_admin_annotations_message_id ON ai_admin_annotations(message_id);
CREATE INDEX ix_ai_admin_annotations_status ON ai_admin_annotations(status);
CREATE INDEX ix_ai_admin_annotations_type ON ai_admin_annotations(annotation_type);
```

#### Backend Endpoints Created:

**Conversation Browsing (Core DB)**:
| Endpoint | Purpose |
|----------|---------|
| `GET /admin/ai/tuning/conversations` | List all conversations (paginated) |
| `GET /admin/ai/tuning/conversations/{id}` | Get conversation with messages |
| `GET /admin/ai/tuning/messages/{id}` | Get single message with context |

**Admin Annotations (AI DB)**:
| Endpoint | Purpose |
|----------|---------|
| `POST /admin/ai/tuning/annotations` | Create annotation on a message |
| `GET /admin/ai/tuning/annotations` | List annotations (filter by status, type, severity) |
| `GET /admin/ai/tuning/annotations/{id}` | Get annotation |
| `PUT /admin/ai/tuning/annotations/{id}` | Update annotation |
| `DELETE /admin/ai/tuning/annotations/{id}` | Delete annotation |

**Analytics**:
| Endpoint | Purpose |
|----------|---------|
| `GET /admin/ai/tuning/summary` | Annotation stats by type/severity/status |
| `GET /admin/ai/tuning/export` | Export annotations for training (super_admin only) |

#### Frontend Page (`/admin/ai/tuning`) - TODO:

**Features:**
1. **Conversation Browser**: List recent conversations, filter by user/date
2. **Message Review Panel**: View full conversation thread
3. **Annotation Form**:
   - Select annotation type (correction, improvement, flag, approved)
   - Add comment explaining the issue
   - Optionally provide suggested response
   - Set severity level
   - Add categorization tags
4. **Annotation Queue**: View pending annotations for review
5. **Export Function**: Export annotations for fine-tuning or RAG updates

#### Files Created:
- [x] `backend/app/models/ai_models.py` - Added AIAdminAnnotation class
- [x] `backend/migrations_ai/versions/0002_add_admin_annotations.py` - Migration
- [x] `backend/app/api/v1/admin/ai_tuning.py` - 11 new endpoints
- [x] `backend/app/api/v1/admin/router.py` - Updated to include tuning router
- [ ] `frontend/app/admin/ai/tuning/page.tsx` (TODO - Phase 6)
- [ ] `frontend/src/containers/AdminAITuningContainer.tsx` (TODO - Phase 6)

---

### Phase 3: User Activity Tracking (COMPLETE)

**Purpose**: Track user onboarding funnel and activity for admin dashboard analytics.

**Database**: Core DB

```sql
-- Core Database (gondola)
CREATE TABLE user_activity_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    session_id VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}',
    error_code VARCHAR(50),
    error_message TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX ix_user_activity_events_user_id ON user_activity_events(user_id);
CREATE INDEX ix_user_activity_events_session_id ON user_activity_events(session_id);
CREATE INDEX ix_user_activity_events_event_type ON user_activity_events(event_type);
CREATE INDEX ix_user_activity_events_event_category ON user_activity_events(event_category);
CREATE INDEX ix_user_activity_events_error_code ON user_activity_events(error_code);
CREATE INDEX ix_user_activity_events_created_at ON user_activity_events(created_at);
```

**Event Types:**
```
onboarding.register_start      -> User started registration
onboarding.register_complete   -> Registration successful
onboarding.register_error      -> Registration failed (with error_code)
onboarding.login_success       -> Login successful
onboarding.login_error         -> Login failed
onboarding.portfolio_start     -> Started portfolio creation
onboarding.portfolio_complete  -> Portfolio created
onboarding.portfolio_error     -> Portfolio creation failed
chat.session_start             -> New conversation created
chat.feedback_given            -> Feedback submitted
auth.logout                    -> User logged out
```

#### Completed:
- [x] `backend/app/models/admin.py` - Added UserActivityEvent model
- [x] `backend/migrations_core/versions/p2q3r4s5t6u7_add_user_activity_events.py` - Migration
- [x] `backend/app/services/activity_tracking_service.py` - Fire-and-forget tracking service
- [x] Integrated tracking into:
  - `backend/app/api/v1/auth.py` - Login success/error, register complete/error, logout
  - `backend/app/api/v1/onboarding.py` - Register start/complete/error, portfolio start/complete/error
  - `backend/app/api/v1/chat/conversations.py` - Chat session start
  - `backend/app/api/v1/chat/feedback.py` - Feedback given
- [x] `backend/app/api/v1/admin/onboarding.py` - Admin analytics endpoints

#### Admin Analytics Endpoints Created:

| Endpoint | Purpose | Database |
|----------|---------|----------|
| `GET /admin/onboarding/funnel` | Funnel conversion rates (5 steps) | Core DB |
| `GET /admin/onboarding/errors` | Error breakdown by code with samples | Core DB |
| `GET /admin/onboarding/daily` | Daily trends for all event types | Core DB |
| `GET /admin/onboarding/events` | Recent events list (debugging, filterable) | Core DB |

#### Files Created:
- [x] `backend/app/models/admin.py` - UserActivityEvent model
- [x] `backend/migrations_core/versions/p2q3r4s5t6u7_add_user_activity_events.py`
- [x] `backend/app/services/activity_tracking_service.py`
- [x] `backend/app/api/v1/admin/onboarding.py`

#### Files Modified:
- [x] `backend/app/api/v1/auth.py` - Added tracking imports and calls
- [x] `backend/app/api/v1/onboarding.py` - Added tracking imports and calls
- [x] `backend/app/api/v1/chat/conversations.py` - Added session start tracking
- [x] `backend/app/api/v1/chat/feedback.py` - Added feedback tracking
- [x] `backend/app/api/v1/admin/router.py` - Included onboarding router
- [x] `backend/app/models/__init__.py` - Exported admin models

---

### Phase 4: AI Performance Metrics (COMPLETE)

**Purpose**: Track AI request performance (latency, tokens, errors, tool usage)

**Database**: Core DB

#### Completed:
- [x] `backend/app/models/admin.py` - Added AIRequestMetrics model
- [x] `backend/migrations_core/versions/q3r4s5t6u7v8_add_ai_request_metrics.py` - Migration
- [x] `backend/app/services/ai_metrics_service.py` - Fire-and-forget metrics recording
- [x] `backend/app/api/v1/chat/send.py` - Integrated metrics recording after SSE completes
- [x] `backend/app/api/v1/admin/ai_metrics.py` - 6 admin analytics endpoints

#### New Table (Core Database):

```sql
-- Core Database (gondola)
CREATE TABLE ai_request_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    message_id UUID NOT NULL,
    user_id UUID,
    model VARCHAR(100) NOT NULL,
    input_tokens INT,              -- Prompt/input tokens
    output_tokens INT,             -- Completion/output tokens
    total_tokens INT,
    first_token_ms INT,            -- Time to first token
    total_latency_ms INT,          -- Total response time
    tool_calls_count INT DEFAULT 0,
    tool_calls JSONB,              -- Tool names and details
    error_type VARCHAR(100),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Admin Endpoints Created:

| Endpoint | Purpose | Database |
|----------|---------|----------|
| `GET /admin/ai/metrics` | Summary stats (requests, latency, tokens, error rate) | Core DB |
| `GET /admin/ai/latency` | Latency percentiles (p50, p75, p90, p95, p99) | Core DB |
| `GET /admin/ai/tokens` | Daily token usage trends | Core DB |
| `GET /admin/ai/errors` | Error breakdown by type with samples | Core DB |
| `GET /admin/ai/tools` | Tool usage frequency | Core DB |
| `GET /admin/ai/models` | Model usage breakdown | Core DB |

#### Files Created:
- [x] `backend/app/models/admin.py` - AIRequestMetrics model
- [x] `backend/migrations_core/versions/q3r4s5t6u7v8_add_ai_request_metrics.py`
- [x] `backend/app/services/ai_metrics_service.py`
- [x] `backend/app/api/v1/admin/ai_metrics.py`

#### Files Modified:
- [x] `backend/app/api/v1/chat/send.py` - Added metrics recording
- [x] `backend/app/api/v1/admin/router.py` - Included ai_metrics router
- [x] `backend/app/models/__init__.py` - Exported AIRequestMetrics

---

### Phase 5: Batch History & Daily Metrics (COMPLETE)

**Purpose**: Track batch processing history and provide pre-aggregated daily metrics for dashboard.

**Database**: Core DB

#### Completed:
- [x] `backend/app/models/admin.py` - Added BatchRunHistory and DailyMetrics models
- [x] `backend/migrations_core/versions/r4s5t6u7v8w9_add_batch_history_daily_metrics.py` - Migration
- [x] `backend/app/services/batch_history_service.py` - Fire-and-forget batch history recording
- [x] `backend/app/batch/batch_orchestrator.py` - Integrated history recording at batch start/end
- [x] `backend/app/api/v1/endpoints/admin_batch.py` - 3 new history endpoints

#### New Tables (Core Database):

```sql
-- Core Database (gondola)
CREATE TABLE batch_run_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_run_id VARCHAR(255) NOT NULL,
    triggered_by VARCHAR(255) NOT NULL,  -- "cron", "manual", "admin:email"
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL,         -- "running", "completed", "failed", "partial"
    total_jobs INT DEFAULT 0,
    completed_jobs INT DEFAULT 0,
    failed_jobs INT DEFAULT 0,
    phase_durations JSONB DEFAULT '{}',  -- {"phase_1_5_symbol_factors": 12.5, ...}
    error_summary JSONB,                 -- {"count": 3, "types": [...], "details": [...]}
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    metric_type VARCHAR(100) NOT NULL,   -- "user_registrations", "ai_requests", etc.
    metric_value NUMERIC(16,4) NOT NULL,
    dimensions JSONB DEFAULT '{}',       -- {"model": "gpt-4o"}, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, metric_type, dimensions)
);
```

#### Admin Endpoints Created:

| Endpoint | Purpose | Database |
|----------|---------|----------|
| `GET /admin/batch/history` | List batch runs (filter by days, status) | Core DB |
| `GET /admin/batch/history/{batch_run_id}` | Get batch run details with errors | Core DB |
| `GET /admin/batch/history/summary` | Aggregate stats (success rate, avg duration) | Core DB |

#### Files Created:
- [x] `backend/app/models/admin.py` - BatchRunHistory, DailyMetrics models
- [x] `backend/migrations_core/versions/r4s5t6u7v8w9_add_batch_history_daily_metrics.py`
- [x] `backend/app/services/batch_history_service.py`

#### Files Modified:
- [x] `backend/app/batch/batch_orchestrator.py` - Added history recording
- [x] `backend/app/api/v1/endpoints/admin_batch.py` - Added history endpoints
- [x] `backend/app/models/__init__.py` - Exported new models

---

### Phase 6: Admin Dashboard Frontend (COMPLETE)

**Purpose**: Build React frontend pages for admin dashboard analytics.

#### Completed:

**Admin API Service** (`frontend/src/services/adminApiService.ts`):
- [x] Types for all admin API responses
- [x] Methods for onboarding, AI metrics, and batch history endpoints
- [x] Dashboard overview aggregation helper

**Dashboard Overview** (`/admin`) - Updated:
- [x] Real-time AI request count, avg latency, error rate
- [x] Last batch run status
- [x] Navigation cards to sub-pages (3 enabled, 2 coming soon)
- [x] Implementation status badges

**Onboarding Analytics** (`/admin/onboarding`):
- [x] Funnel visualization with step-by-step conversion
- [x] Drop-off rate indicators per step
- [x] Error breakdown by error code with samples
- [x] Daily activity table (registrations, logins, portfolios, chats)
- [x] Period selector (7-90 days)

**AI Metrics** (`/admin/ai`):
- [x] Summary cards (total requests, avg latency, error rate, tool usage)
- [x] Latency percentiles (P50-P99) with first token times
- [x] Token usage with daily breakdown
- [x] Tool usage breakdown with percentage bars
- [x] Model usage breakdown with avg latency
- [x] Error breakdown with error types and samples
- [x] Period selector (1-30 days)

**Batch History** (`/admin/batch`):
- [x] Summary cards (total runs, success rate, avg duration, last status)
- [x] Status breakdown (completed, failed, partial, running)
- [x] Run history list with status icons and job counts
- [x] Run details panel (triggered by, jobs, phase durations, errors)
- [x] Status and period filters

**Pending (User Management & AI Tuning)**:
- [ ] User Management (`/admin/users`) - Coming Soon
- [ ] User Journey (`/admin/users/[id]`) - Coming Soon
- [ ] AI Tuning (`/admin/ai/tuning`) - Backend complete, frontend pending

#### Files Created:
- [x] `frontend/src/services/adminApiService.ts`
- [x] `frontend/app/admin/onboarding/page.tsx`
- [x] `frontend/app/admin/ai/page.tsx`
- [x] `frontend/app/admin/batch/page.tsx`

#### Files Modified:
- [x] `frontend/app/admin/page.tsx` - Updated with real data and navigation

---

### Phase 7: Data Aggregation & Cleanup (COMPLETE)

**Daily job** (Railway scheduler at 8:30 PM ET):
1. Aggregate raw events -> `daily_metrics`
2. Cleanup data older than 30 days:
   - `user_activity_events` (Core DB)
   - `ai_request_metrics` (Core DB)
   - `batch_run_history` (Core DB)
   - `admin_sessions` expired > 7 days (Core DB)

**Permanent data:**
- `daily_metrics` (aggregated)
- `ai_admin_annotations` (training data)

#### Completed:
- [x] `backend/app/batch/admin_metrics_job.py` - Aggregation and cleanup job
- [x] `backend/app/api/v1/admin/system.py` - 7 new system endpoints
- [x] `backend/app/batch/scheduler_config.py` - Added scheduled job at 8:30 PM ET
- [x] `backend/app/api/v1/admin/router.py` - Added system router

#### New Admin System Endpoints:
| Endpoint | Purpose |
|----------|---------|
| `GET /admin/system/health` | System health status |
| `GET /admin/system/aggregation/status` | Aggregation coverage |
| `GET /admin/system/retention/status` | Retention compliance |
| `POST /admin/system/cleanup` | Manual cleanup trigger (super_admin) |
| `POST /admin/system/aggregate` | Manual aggregation trigger (super_admin) |
| `POST /admin/system/run-batch` | Full batch job trigger (super_admin) |
| `GET /admin/system/daily-metrics` | Query aggregated metrics |

#### Aggregation Metrics Captured:
**User Activity:**
- user_registrations, user_logins, portfolios_created
- chat_sessions, feedback_given
- registration_errors, login_errors
- total_activity_events, unique_users

**AI Requests:**
- ai_requests, ai_requests_with_errors
- avg_latency_ms, avg_first_token_ms
- total_input_tokens, total_output_tokens
- latency_p50, p75, p90, p95, p99
- model_breakdown

**Batch Processing:**
- batch_runs, batch_completed, batch_failed, batch_partial
- avg_duration_minutes
- total_jobs, total_completed_jobs, total_failed_jobs

---

## API Endpoints Summary

### Admin Auth (Core DB) ✅ Complete
```
POST   /api/v1/admin/auth/login
POST   /api/v1/admin/auth/logout
POST   /api/v1/admin/auth/refresh
GET    /api/v1/admin/auth/me
```

### User Management (Core DB)
```
GET    /api/v1/admin/users
GET    /api/v1/admin/users/{id}
GET    /api/v1/admin/users/{id}/journey
```

### Onboarding Analytics (Core DB) ✅ Complete
```
GET    /api/v1/admin/onboarding/funnel
GET    /api/v1/admin/onboarding/errors
GET    /api/v1/admin/onboarding/daily
GET    /api/v1/admin/onboarding/events
```

### AI Metrics (Core DB) ✅ Complete
```
GET    /api/v1/admin/ai/metrics
GET    /api/v1/admin/ai/latency
GET    /api/v1/admin/ai/tokens
GET    /api/v1/admin/ai/errors
GET    /api/v1/admin/ai/tools
GET    /api/v1/admin/ai/models
```

### AI Tuning (Core DB for reads, AI DB for writes) ✅ Complete
```
GET    /api/v1/admin/ai/tuning/conversations
GET    /api/v1/admin/ai/tuning/conversations/{id}
GET    /api/v1/admin/ai/tuning/messages/{id}
POST   /api/v1/admin/ai/tuning/annotations
GET    /api/v1/admin/ai/tuning/annotations
GET    /api/v1/admin/ai/tuning/annotations/{id}
PUT    /api/v1/admin/ai/tuning/annotations/{id}
DELETE /api/v1/admin/ai/tuning/annotations/{id}
GET    /api/v1/admin/ai/tuning/summary
GET    /api/v1/admin/ai/tuning/export
```

### Batch (Core DB) ✅ Complete
```
GET    /api/v1/admin/batch/history
GET    /api/v1/admin/batch/history/{batch_run_id}
GET    /api/v1/admin/batch/history/summary
```

### System (Core DB) ✅ Complete
```
GET    /api/v1/admin/system/health
GET    /api/v1/admin/system/aggregation/status
GET    /api/v1/admin/system/retention/status
POST   /api/v1/admin/system/cleanup
POST   /api/v1/admin/system/aggregate
POST   /api/v1/admin/system/run-batch
GET    /api/v1/admin/system/daily-metrics
```

---

## Database Schema Summary

### Core Database (gondola)

```sql
-- All tables created
CREATE TABLE admin_users (...);           -- Admin authentication (Phase 1)
CREATE TABLE admin_sessions (...);        -- Session tracking (Phase 1)
CREATE TABLE user_activity_events (...);  -- Onboarding funnel (Phase 3)
CREATE TABLE ai_request_metrics (...);    -- AI performance (Phase 4)
CREATE TABLE batch_run_history (...);     -- Batch history (Phase 5)
CREATE TABLE daily_metrics (...);         -- Aggregated metrics (Phase 5)
```

### AI Database (metro)

```sql
-- Already exists
ai_feedback            -- User feedback on AI responses
ai_memories            -- Learned preferences
ai_kb_documents        -- RAG knowledge base
ai_admin_annotations   -- Admin tuning comments (Phase 2)
```

---

## Implementation Order

1. **Phase 1** ✅ **COMPLETE**: Admin auth foundation (backend + frontend)
2. **Phase 1.5** ✅ **COMPLETE**: AI data access (view KB, memories, feedback)
3. **Phase 2** ✅ **COMPLETE**: AI tuning system (11 backend endpoints)
4. **Phase 3** ✅ **COMPLETE**: User activity tracking (onboarding funnel events + 4 admin endpoints)
5. **Phase 4** ✅ **COMPLETE**: AI performance metrics (6 admin endpoints + metrics recording)
6. **Phase 5** ✅ **COMPLETE**: Batch history & daily metrics (3 history endpoints + batch_orchestrator integration)
7. **Phase 6** ✅ **COMPLETE**: Frontend dashboard pages (onboarding, AI metrics, batch history)
8. **Phase 7** ✅ **COMPLETE**: Daily aggregation job + cleanup (7 system endpoints + scheduled job)

---

## Key Considerations

### Dual Database Access Pattern

For endpoints that need both databases (e.g., AI tuning):

```python
from app.database import get_db, get_ai_db

@router.post("/annotations")
async def create_annotation(
    annotation: AnnotationCreate,
    core_db: AsyncSession = Depends(get_db),    # Read messages
    ai_db: AsyncSession = Depends(get_ai_db),   # Write annotations
    admin: AdminUser = Depends(get_current_admin),
):
    # Verify message exists in Core DB
    message = await core_db.execute(
        select(ConversationMessage).where(...)
    )

    # Write annotation to AI DB
    new_annotation = AIAdminAnnotation(...)
    ai_db.add(new_annotation)
    await ai_db.commit()
```

### Security
- Admin tokens: 8-hour expiry (shorter than user tokens)
- Session tracking enables logout/invalidation
- `super_admin` role for sensitive operations
- IP/User-Agent logging for audit

### AI Tuning Workflow
1. Admin browses recent conversations
2. Identifies problematic AI response
3. Creates annotation with correction/suggestion
4. Annotations can be exported for:
   - Fine-tuning datasets
   - RAG knowledge base updates
   - Prompt engineering improvements
