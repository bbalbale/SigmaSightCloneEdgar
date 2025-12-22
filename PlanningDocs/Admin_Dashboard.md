# Admin Dashboard Implementation Plan

**Created**: 2025-12-22
**Status**: Planning Complete - Ready for Implementation

## Overview

Create a comprehensive admin dashboard for SigmaSight to monitor AI engine operations, track logs, and analyze user onboarding. Features separate admin authentication and 30-day rolling data retention.

## User Requirements Summary

| Requirement | Decision |
|-------------|----------|
| Admin Authentication | Separate admin accounts (new table + login endpoint) |
| Onboarding Tracking | Comprehensive (funnel + individual journeys + error analysis) |
| AI Monitoring | Both quality AND performance metrics |
| Data Retention | 30 days rolling |

---

## Architecture Overview

### Page Structure

```
/admin/login          → Separate admin login
/admin                → Dashboard overview (summary cards)
/admin/users          → User list with onboarding status
/admin/users/[id]     → Individual user journey timeline
/admin/onboarding     → Funnel visualization + error breakdown
/admin/ai             → AI performance + quality metrics
/admin/batch          → Batch processing history
```

### Database Tables (Core DB)

| Table | Purpose | Retention |
|-------|---------|-----------|
| `admin_users` | Admin authentication | Permanent |
| `admin_sessions` | Token invalidation tracking | 7 days |
| `user_activity_events` | Raw funnel events | 30 days → aggregated |
| `ai_request_metrics` | AI performance data | 30 days → aggregated |
| `batch_run_history` | Historical batch runs | 30 days |
| `daily_metrics` | Pre-aggregated metrics | Permanent |

---

## Implementation Phases

### Phase 1: Admin Authentication Foundation

**Backend:**
1. Create `backend/app/models/admin.py` with:
   - `AdminUser` model (id, email, hashed_password, full_name, role, is_active, last_login_at)
   - `AdminSession` model (for token invalidation)

2. Create `backend/app/core/admin_auth.py`:
   - `create_admin_access_token()` - JWT with `type: "admin"` claim
   - `verify_admin_token()` - Validates admin-specific tokens
   - 8-hour token expiry (shorter than user tokens)

3. Create `backend/app/core/admin_dependencies.py`:
   - `get_current_admin()` - Validates admin JWT + active session
   - `require_super_admin()` - Role check for sensitive operations

4. Create `backend/app/api/v1/admin/auth.py`:
   - `POST /api/v1/admin/auth/login`
   - `POST /api/v1/admin/auth/logout`
   - `GET /api/v1/admin/auth/me`

5. Create Alembic migration for admin tables

**Frontend:**
1. Create `frontend/src/stores/adminStore.ts` (Zustand, persisted)
2. Create `frontend/src/services/adminApi.ts`
3. Create `frontend/app/admin/login/page.tsx`
4. Create `frontend/app/admin/layout.tsx` with auth guard

**Files to Create/Modify:**
- `backend/app/models/admin.py` (new)
- `backend/app/core/admin_auth.py` (new)
- `backend/app/core/admin_dependencies.py` (new)
- `backend/app/api/v1/admin/auth.py` (new)
- `backend/app/api/v1/admin/router.py` (new)
- `backend/app/models/__init__.py` (add admin exports)
- `backend/migrations_core/versions/xxx_add_admin_tables.py` (new)
- `frontend/src/stores/adminStore.ts` (new)
- `frontend/src/services/adminApi.ts` (new)
- `frontend/app/admin/login/page.tsx` (new)
- `frontend/app/admin/layout.tsx` (new)

---

### Phase 2: User Activity Tracking

**Backend:**
1. Add to `backend/app/models/admin.py`:
   - `UserActivityEvent` model

2. Create `backend/app/services/activity_tracking_service.py`:
   - `track_event()` - Non-blocking event recording
   - Event types: `onboarding.*`, `chat.*`, `portfolio.*`

3. Integrate tracking into existing endpoints:
   - `backend/app/api/v1/onboarding.py` - Track register/portfolio events
   - `backend/app/api/v1/auth.py` - Track login events
   - `backend/app/api/v1/chat/send.py` - Track chat events

**Event Types to Track:**
```
onboarding.register_start      → User started registration
onboarding.register_complete   → Registration successful
onboarding.register_error      → Registration failed (with error_code)
onboarding.login_success       → Login successful
onboarding.login_error         → Login failed
onboarding.portfolio_start     → Started portfolio creation
onboarding.portfolio_complete  → Portfolio created
onboarding.portfolio_error     → Portfolio creation failed (with error_code)
chat.session_start            → New conversation created
chat.message_sent             → Message sent
chat.feedback_given           → Feedback submitted
```

**Files to Modify:**
- `backend/app/models/admin.py` (add UserActivityEvent)
- `backend/app/services/activity_tracking_service.py` (new)
- `backend/app/api/v1/onboarding.py` (add tracking calls)
- `backend/app/api/v1/auth.py` (add tracking calls)
- `backend/app/api/v1/chat/send.py` (add tracking calls)

---

### Phase 3: AI Metrics Collection

**Backend:**
1. Add to `backend/app/models/admin.py`:
   - `AIRequestMetrics` model

2. Modify `backend/app/api/v1/chat/send.py`:
   - After SSE completes, record metrics to `ai_request_metrics`
   - Capture: conversation_id, message_id, user_id, model, tokens, latency, tool_calls, errors

3. Create `backend/app/api/v1/admin/ai.py`:
   - `GET /api/v1/admin/ai/metrics` - Summary stats
   - `GET /api/v1/admin/ai/latency` - Latency percentiles (p50, p95, p99)
   - `GET /api/v1/admin/ai/tokens` - Token usage trends
   - `GET /api/v1/admin/ai/errors` - Error breakdown
   - `GET /api/v1/admin/ai/tools` - Tool usage frequency

**Files to Modify:**
- `backend/app/models/admin.py` (add AIRequestMetrics)
- `backend/app/api/v1/chat/send.py` (add metrics recording)
- `backend/app/api/v1/admin/ai.py` (new)
- `backend/app/api/v1/admin/router.py` (add ai routes)

---

### Phase 4: Batch History & Onboarding Analytics

**Backend:**
1. Add to `backend/app/models/admin.py`:
   - `BatchRunHistory` model
   - `DailyMetrics` model (for aggregation)

2. Modify `backend/app/batch/batch_orchestrator.py`:
   - Record each run to `batch_run_history`
   - Track phase durations

3. Create `backend/app/api/v1/admin/onboarding.py`:
   - `GET /api/v1/admin/onboarding/funnel` - Funnel conversion rates
   - `GET /api/v1/admin/onboarding/errors` - Error breakdown by code
   - `GET /api/v1/admin/onboarding/daily` - Daily trends

4. Create `backend/app/api/v1/admin/users.py`:
   - `GET /api/v1/admin/users` - Paginated user list
   - `GET /api/v1/admin/users/{id}` - User details
   - `GET /api/v1/admin/users/{id}/journey` - User's event timeline

5. Extend `backend/app/api/v1/admin/batch.py`:
   - `GET /api/v1/admin/batch/history` - Historical runs
   - `GET /api/v1/admin/batch/phases` - Phase timing breakdown

**Files to Modify:**
- `backend/app/models/admin.py` (add BatchRunHistory, DailyMetrics)
- `backend/app/batch/batch_orchestrator.py` (add history recording)
- `backend/app/api/v1/admin/onboarding.py` (new)
- `backend/app/api/v1/admin/users.py` (new)
- `backend/app/api/v1/endpoints/admin_batch.py` (extend)

---

### Phase 5: Admin Dashboard Frontend

**Pages to Create:**

1. **Dashboard Overview** (`frontend/app/admin/page.tsx`):
   - Summary cards: User count, conversion rate, AI latency, feedback ratio
   - Quick action buttons
   - Recent alerts/issues

2. **User Management** (`frontend/app/admin/users/page.tsx`):
   - Sortable/filterable user table
   - Status badges (onboarding stage)
   - Click to view journey

3. **User Journey** (`frontend/app/admin/users/[id]/page.tsx`):
   - Timeline visualization of user events
   - Error events highlighted
   - Time between steps

4. **Onboarding Analytics** (`frontend/app/admin/onboarding/page.tsx`):
   - Funnel visualization (horizontal bar or sankey)
   - Error breakdown table with counts
   - Daily trend line chart

5. **AI Metrics** (`frontend/app/admin/ai/page.tsx`):
   - Latency histogram
   - Token usage line chart
   - Feedback summary (leverage existing `/admin/feedback/*` endpoints)
   - Error rate trend
   - Tool usage pie chart

6. **Batch Processing** (`frontend/app/admin/batch/page.tsx`):
   - Historical runs table
   - Phase timing breakdown
   - Success rate trend

**Components to Create:**
- `frontend/src/components/admin/AdminSidebar.tsx`
- `frontend/src/components/admin/MetricCard.tsx`
- `frontend/src/components/admin/FunnelChart.tsx`
- `frontend/src/components/admin/LatencyChart.tsx`
- `frontend/src/components/admin/UserJourneyTimeline.tsx`
- `frontend/src/components/admin/DataTable.tsx` (reusable admin table)

**Files to Create:**
- `frontend/app/admin/page.tsx`
- `frontend/app/admin/users/page.tsx`
- `frontend/app/admin/users/[id]/page.tsx`
- `frontend/app/admin/onboarding/page.tsx`
- `frontend/app/admin/ai/page.tsx`
- `frontend/app/admin/batch/page.tsx`
- `frontend/src/components/admin/*.tsx`
- `frontend/src/containers/AdminDashboardContainer.tsx`
- `frontend/src/containers/AdminUsersContainer.tsx`
- `frontend/src/containers/AdminOnboardingContainer.tsx`
- `frontend/src/containers/AdminAIContainer.tsx`
- `frontend/src/containers/AdminBatchContainer.tsx`

---

### Phase 6: Data Aggregation & Cleanup

**Backend:**
1. Create `backend/app/batch/admin_metrics_job.py`:
   - Daily aggregation job (runs 1 AM UTC)
   - Aggregates raw events → `daily_metrics`
   - Cleanup: Delete data older than 30 days

2. Add Railway cron configuration

**Aggregation Strategy:**
- Raw events (user_activity_events, ai_request_metrics) → 30-day retention
- Aggregated metrics (daily_metrics) → Permanent
- Dashboard queries use daily_metrics for efficiency

**Files to Create:**
- `backend/app/batch/admin_metrics_job.py` (new)
- `backend/app/api/v1/admin/system.py` (manual cleanup trigger)

---

## API Endpoints Summary

### Admin Auth
```
POST   /api/v1/admin/auth/login
POST   /api/v1/admin/auth/logout
GET    /api/v1/admin/auth/me
```

### User Management
```
GET    /api/v1/admin/users
GET    /api/v1/admin/users/{id}
GET    /api/v1/admin/users/{id}/journey
```

### Onboarding Analytics
```
GET    /api/v1/admin/onboarding/funnel
GET    /api/v1/admin/onboarding/errors
GET    /api/v1/admin/onboarding/daily
```

### AI Metrics
```
GET    /api/v1/admin/ai/metrics
GET    /api/v1/admin/ai/latency
GET    /api/v1/admin/ai/tokens
GET    /api/v1/admin/ai/errors
GET    /api/v1/admin/ai/tools
```

### Batch (extend existing)
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

## Database Schema

```sql
-- Admin authentication
CREATE TABLE admin_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'admin',  -- admin | super_admin
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Session tracking for token invalidation
CREATE TABLE admin_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_user_id UUID REFERENCES admin_users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

-- User activity events (30-day retention)
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

-- AI request metrics (30-day retention)
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

-- Batch run history (30-day retention)
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

-- Pre-aggregated daily metrics (permanent)
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

## Implementation Order

1. **Phase 1**: Admin auth foundation (backend + frontend login)
2. **Phase 2**: User activity tracking (integrate into existing endpoints)
3. **Phase 3**: AI metrics collection (modify chat/send.py)
4. **Phase 4**: Batch history + admin API endpoints
5. **Phase 5**: Frontend dashboard pages
6. **Phase 6**: Daily aggregation job + cleanup

---

## Key Considerations

### Security
- Admin tokens have shorter expiry (8 hours vs 24 hours for users)
- Session tracking enables token invalidation on logout
- IP/User-Agent logging for audit trail
- `super_admin` role for sensitive operations

### Performance
- Dashboard queries use pre-aggregated `daily_metrics` table
- Raw event tables have indexes on created_at for efficient cleanup
- 30-day rolling window limits data volume

### Existing Infrastructure Leveraged
- Existing `/api/v1/admin/feedback/*` endpoints for AI quality metrics
- Existing error codes from `onboarding_errors.py` (40+ codes)
- Existing batch_run_tracker pattern for real-time status
- Existing JWT auth pattern (adapted for admin-specific claims)
