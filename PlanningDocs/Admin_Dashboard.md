# Admin Dashboard Implementation Plan

**Created**: 2025-12-22
**Updated**: 2025-12-22
**Status**: Phases 1, 1.5, and 2 Complete (AI Tuning System)

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

### Phase 3: User Activity Tracking

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
    created_at TIMESTAMPTZ DEFAULT NOW()
);
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
chat.message_sent              -> Message sent
chat.feedback_given            -> Feedback submitted
```

---

### Phase 4: AI Performance Metrics

**Database**: Core DB (for request metrics)

```sql
-- Core Database (gondola)
CREATE TABLE ai_request_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    message_id UUID NOT NULL,
    user_id UUID,
    model VARCHAR(100) NOT NULL,
    prompt_tokens INT,
    completion_tokens INT,
    total_tokens INT,
    first_token_ms INT,
    total_latency_ms INT,
    tool_calls_count INT DEFAULT 0,
    tool_calls JSONB,
    error_type VARCHAR(100),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Endpoints:**
```
GET /api/v1/admin/ai/metrics   - Summary stats (total requests, avg latency, error rate)
GET /api/v1/admin/ai/latency   - Latency percentiles (p50, p95, p99)
GET /api/v1/admin/ai/tokens    - Token usage trends
GET /api/v1/admin/ai/errors    - Error breakdown by type
GET /api/v1/admin/ai/tools     - Tool usage frequency
```

---

### Phase 5: Batch History & Onboarding Analytics

**Database**: Core DB

```sql
-- Core Database (gondola)
CREATE TABLE batch_run_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_run_id VARCHAR(255) NOT NULL,
    triggered_by VARCHAR(255) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL,
    total_jobs INT DEFAULT 0,
    completed_jobs INT DEFAULT 0,
    failed_jobs INT DEFAULT 0,
    phase_durations JSONB DEFAULT '{}',
    error_summary JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE daily_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    metric_value NUMERIC(16,4) NOT NULL,
    dimensions JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, metric_type, dimensions)
);
```

---

### Phase 6: Admin Dashboard Frontend

**Pages:**

1. **Dashboard Overview** (`/admin`):
   - User count, conversion rate, AI latency, feedback ratio
   - Quick links to key sections
   - Recent alerts

2. **User Management** (`/admin/users`):
   - Paginated user table with search/filter
   - Onboarding status badges
   - Click to view journey

3. **User Journey** (`/admin/users/[id]`):
   - Timeline of user events
   - Error events highlighted
   - Time between steps

4. **Onboarding Analytics** (`/admin/onboarding`):
   - Funnel visualization
   - Error breakdown by code
   - Daily trends

5. **AI Metrics** (`/admin/ai`):
   - Latency histogram
   - Token usage chart
   - Error rate trend
   - Tool usage breakdown

6. **AI Tuning** (`/admin/ai/tuning`) - NEW:
   - Conversation browser
   - Message review panel
   - Annotation form
   - Annotation queue

7. **Batch Processing** (`/admin/batch`):
   - Historical runs table
   - Phase timing breakdown
   - Success rate trend

---

### Phase 7: Data Aggregation & Cleanup

**Daily job** (Railway cron at 1 AM UTC):
1. Aggregate raw events -> `daily_metrics`
2. Cleanup data older than 30 days:
   - `user_activity_events` (Core DB)
   - `ai_request_metrics` (Core DB)
   - `batch_run_history` (Core DB)
   - `admin_sessions` expired > 7 days (Core DB)

**Permanent data:**
- `daily_metrics` (aggregated)
- `ai_admin_annotations` (training data)

---

## API Endpoints Summary

### Admin Auth (Core DB)
```
POST   /api/v1/admin/auth/login
POST   /api/v1/admin/auth/logout
GET    /api/v1/admin/auth/me
```

### User Management (Core DB)
```
GET    /api/v1/admin/users
GET    /api/v1/admin/users/{id}
GET    /api/v1/admin/users/{id}/journey
```

### Onboarding Analytics (Core DB)
```
GET    /api/v1/admin/onboarding/funnel
GET    /api/v1/admin/onboarding/errors
GET    /api/v1/admin/onboarding/daily
```

### AI Metrics (Core DB)
```
GET    /api/v1/admin/ai/metrics
GET    /api/v1/admin/ai/latency
GET    /api/v1/admin/ai/tokens
GET    /api/v1/admin/ai/errors
GET    /api/v1/admin/ai/tools
```

### AI Tuning (Core DB for reads, AI DB for writes)
```
GET    /api/v1/admin/ai/conversations
GET    /api/v1/admin/ai/conversations/{id}
GET    /api/v1/admin/ai/messages/{id}
POST   /api/v1/admin/ai/annotations
GET    /api/v1/admin/ai/annotations
GET    /api/v1/admin/ai/annotations/{id}
PUT    /api/v1/admin/ai/annotations/{id}
DELETE /api/v1/admin/ai/annotations/{id}
GET    /api/v1/admin/ai/tuning/summary
GET    /api/v1/admin/ai/tuning/export
```

### Batch (Core DB)
```
GET    /api/v1/admin/batch/history
GET    /api/v1/admin/batch/phases
```

### System
```
GET    /api/v1/admin/system/health
POST   /api/v1/admin/system/cleanup
```

---

## Database Schema Summary

### Core Database (gondola)

```sql
-- Already created
CREATE TABLE admin_users (...);      -- Admin authentication
CREATE TABLE admin_sessions (...);   -- Session tracking

-- To be created
CREATE TABLE user_activity_events (...);  -- Onboarding funnel
CREATE TABLE ai_request_metrics (...);    -- AI performance
CREATE TABLE batch_run_history (...);     -- Batch history
CREATE TABLE daily_metrics (...);         -- Aggregated metrics
```

### AI Database (metro)

```sql
-- Already exists
ai_feedback       -- User feedback on AI responses
ai_memories       -- Learned preferences
ai_kb_documents   -- RAG knowledge base

-- To be created
CREATE TABLE ai_admin_annotations (...);  -- Admin tuning comments
```

---

## Implementation Order

1. **Phase 1** ✅ **COMPLETE**: Admin auth foundation (backend + frontend)
2. **Phase 1.5** ✅ **COMPLETE**: AI data access (view KB, memories, feedback)
3. **Phase 2** ✅ **COMPLETE**: AI tuning system (11 backend endpoints)
4. **Phase 3** 🎯 **NEXT**: User activity tracking (onboarding funnel events)
5. **Phase 4**: AI performance metrics (latency, tokens, errors)
6. **Phase 5**: Batch history + onboarding analytics
7. **Phase 6**: Frontend dashboard pages (users, onboarding, AI metrics, AI tuning, batch)
8. **Phase 7**: Daily aggregation job + cleanup (30-day retention)

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
