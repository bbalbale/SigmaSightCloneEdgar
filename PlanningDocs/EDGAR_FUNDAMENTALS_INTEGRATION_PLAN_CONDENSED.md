# EDGAR Fundamentals Integration Plan

**Project**: Integrate StockFundamentals (SEC EDGAR) into SigmaSight
**Approach**: Microservice Architecture (Same Railway Project)
**Status**: Planning
**Updated**: 2025-12-24

---

## Executive Summary

### Objective
Integrate StockFundamentals microservice to provide **authoritative SEC EDGAR financial data** (10-K, 10-Q filings) alongside existing Yahoo fundamentals.

### Value Proposition
- **Authoritative Data**: Direct from SEC EDGAR vs. third-party providers
- **60+ Financial Metrics**: Comprehensive XBRL-normalized data
- **Historical Depth**: 5+ years of quarterly and annual data
- **Audit Trail**: Direct links to SEC filings

### Key Decisions
1. **Same Railway Project**: Deploy in existing SigmaSight project for private networking
2. **Separate Repos**: StockFundamentals stays in its own repo (`bbalbalbae/StockFundamentals`)
3. **HTTP Communication**: Services communicate via `*.railway.internal`
4. **Redis + Celery Required**: For SEC rate limiting (10 req/sec) and job queue
5. **Estimated Cost**: ~$18-20/mo for 4 new services

### Gradual Rollout
1. **Phase A**: Deploy with `EDGAR_ENABLED=false` - service runs but hidden
2. **Phase B**: Enable for internal testing - verify data quality (2-4 weeks)
3. **Phase C**: Enable UI toggle - users can switch between EDGAR and Yahoo
4. **Phase D**: Make EDGAR default - Yahoo becomes fallback

---

## Architecture

### Target State
```
Railway Project: SigmaSight
├── EXISTING SERVICES (5)
│   ├── Frontend (Next.js)
│   ├── Backend (FastAPI)
│   ├── Core DB (gondola) - portfolios, users, positions
│   └── AI DB (metro) - pgvector, RAG, memories
│
├── NEW SERVICES (4) - StockFundamentals
│   ├── stockfund-api (FastAPI, port 8000)
│   ├── stockfund-worker (Celery)
│   ├── stockfund-db (PostgreSQL)
│   └── stockfund-redis (Redis)
│
└── Communication: HTTP via stockfund-api.railway.internal
```

### Database Separation
- **SigmaSight databases**: NO changes, NO new migrations
- **StockFundamentals**: Own PostgreSQL with own Alembic migrations
- Services communicate via HTTP API only

---

## Railway Deployment Steps

> ⚠️ **CRITICAL**: Do NOT create a new Railway project. Add all services to the **existing SigmaSight project** for private networking to work.

### Step 1: Add PostgreSQL Database
1. Open **SigmaSight** project in Railway dashboard
2. Click "New" → "Database" → "PostgreSQL"
3. Name it `stockfund-db`
4. Wait for provisioning (~30 seconds)

### Step 2: Add Redis (Required for Celery)
1. Click "New" → "Database" → "Redis"
2. Name it `stockfund-redis`
3. Note: Required for SEC rate limiting across workers

### Step 3: Add API Service
1. Click "New" → "GitHub Repo"
2. Select `bbalbalbae/StockFundamentals`
3. Name: `stockfund-api`
4. Root Directory: `backend`
5. Railway auto-detects `Dockerfile` and `railway.toml`

### Step 4: Add Celery Worker
1. Click "New" → "GitHub Repo"
2. Select same repo: `bbalbalbae/StockFundamentals`
3. Name: `stockfund-worker`
4. Root Directory: `backend`
5. Settings → Build → Config File Path: `railway.worker.toml`
6. This uses `Dockerfile.worker` for Celery instead of uvicorn

### Step 5: Configure Environment Variables

**stockfund-api:**
```
DATABASE_URL=${{stockfund-db.DATABASE_URL}}
REDIS_URL=${{stockfund-redis.REDIS_URL}}
CELERY_BROKER_URL=${{stockfund-redis.REDIS_URL}}
EDGAR_USER_AGENT=SigmaSight/1.0 (your-email@domain.com)
API_KEYS=${{shared.STOCKFUND_API_KEY}}
SYNC_MODE=false
```

**stockfund-worker:**
```
DATABASE_URL=${{stockfund-db.DATABASE_URL}}
REDIS_URL=${{stockfund-redis.REDIS_URL}}
CELERY_BROKER_URL=${{stockfund-redis.REDIS_URL}}
EDGAR_USER_AGENT=SigmaSight/1.0 (your-email@domain.com)
API_KEYS=${{shared.STOCKFUND_API_KEY}}
CELERY_WORKER_CONCURRENCY=2
```

**Create Shared Variable:**
- Project Settings → Variables → Add `STOCKFUND_API_KEY` (generate with `openssl rand -hex 32`)

**Add to SigmaSight Backend:**
```
STOCKFUND_API_URL=http://stockfund-api.railway.internal:8000
STOCKFUND_API_KEY=${{shared.STOCKFUND_API_KEY}}
EDGAR_ENABLED=false
```

### Step 6: Configure Deploy Hook (Migrations)
In Railway for `stockfund-api`:
1. Settings → Deploy → Build & Deploy
2. Set "Deploy Command": `uv run alembic upgrade head`

### Step 7: Enable Private Networking
1. Click `stockfund-api` → Settings → Networking
2. Enable "Private Networking"
3. URL: `stockfund-api.railway.internal`

### Step 8: Deploy and Verify
```bash
# Check health
railway run curl http://stockfund-api.railway.internal:8000/health
```

Expected response:
```json
{"status": "ok", "database": true, "redis": true, "celery_worker": true}
```

### Step 9: Enable EDGAR in SigmaSight
1. Set `EDGAR_ENABLED=true` in SigmaSight backend
2. Redeploy

### Step 10: Configure Weekly Cron
1. Project Settings → Cron
2. Schedule: `0 2 * * 0` (2 AM UTC Sundays)
3. Command: `curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" "https://sigmasight-be-production.up.railway.app/api/v1/admin/edgar/refresh"`

---

## Railway Cost Estimate

| Service | Estimated Cost |
|---------|----------------|
| stockfund-api | ~$5/mo |
| stockfund-worker | ~$5/mo |
| stockfund-db | ~$5/mo |
| stockfund-redis | ~$3-5/mo |
| **Total** | **~$18-20/mo** |

---

## Implementation Phases

### Phase 1: Infrastructure Setup
- [ ] Clone StockFundamentals repo alongside SigmaSight
- [ ] Add env vars to SigmaSight backend `.env`
- [ ] Verify local development works

### Phase 2: StockFundamentals Deployment
- [ ] Deploy 4 services to Railway (db, redis, api, worker)
- [ ] Configure environment variables
- [ ] Run migrations via deploy hook
- [ ] Verify health endpoint

### Phase 3: SigmaSight Integration
- [ ] Create `backend/app/services/edgar_client.py` (HTTP client)
- [ ] Create `backend/app/schemas/edgar_fundamentals.py` (Pydantic models)
- [ ] Create `backend/app/api/v1/edgar_fundamentals.py` (API endpoints)
- [ ] Register router in `router.py`
- [ ] Add config settings

### Phase 4: Batch Integration (FUTURE - After Validation)
- [ ] Create `fundamentals_orchestrator.py` (EDGAR-first, Yahoo fallback)
- [ ] Add admin endpoints for manual refresh
- [ ] Configure Railway cron for weekly refresh

### Phase 5: Frontend Integration
- [ ] Create `edgarApi.ts` service
- [ ] Create `useEdgarFundamentals` hook
- [ ] Add financials table component
- [ ] Add data source badge (EDGAR vs Yahoo)

### Phase 6: Testing & Validation
- [ ] Compare EDGAR vs Yahoo for key metrics
- [ ] Verify coverage for portfolio symbols
- [ ] Monitor for 2-4 weeks

---

## Files to Create

### In StockFundamentals Repo (bbalbalbae/StockFundamentals)

| File | Purpose |
|------|---------|
| `backend/Dockerfile` | API service container (uvicorn) |
| `backend/Dockerfile.worker` | Celery worker container |
| `backend/railway.toml` | Railway config for API service |
| `backend/railway.worker.toml` | Railway config for worker service |

### In SigmaSight Repo

| File | Purpose |
|------|---------|
| `backend/app/services/edgar_client.py` | HTTP client for StockFundamentals |
| `backend/app/schemas/edgar_fundamentals.py` | Pydantic response models |
| `backend/app/api/v1/edgar_fundamentals.py` | Proxy API endpoints |
| `frontend/src/services/edgarApi.ts` | Frontend API service |
| `frontend/src/hooks/useEdgarFundamentals.ts` | React data hook |

---

## API Endpoints (SigmaSight Proxy)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/edgar/health` | GET | Service health check |
| `/api/v1/edgar/financials/{ticker}/periods` | GET | Multi-period financials |
| `/api/v1/edgar/financials/{ticker}` | GET | Latest period |
| `/api/v1/edgar/financials/refresh/{ticker}` | POST | Trigger refresh |
| `/api/v1/admin/edgar/refresh` | POST | Batch refresh all symbols |

---

## Rollback Strategy

### Feature Flag Rollback (Fastest)
```bash
# Disable EDGAR, revert to Yahoo-only
EDGAR_ENABLED=false
# Redeploy SigmaSight backend
```

### Service Rollback
```bash
# In Railway dashboard
# 1. Click stockfund-api → Deployments
# 2. Select previous deployment → Rollback
```

### Complete Removal
1. Set `EDGAR_ENABLED=false` in SigmaSight
2. Remove EDGAR endpoints from router
3. Delete StockFundamentals services from Railway

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| SEC rate limiting (10 req/sec) | Celery + Redis for centralized rate limiting |
| StockFundamentals unavailable | Feature flag + Yahoo fallback |
| Data quality issues | 2-4 week validation before making EDGAR default |
| Cost overrun | Railway usage limits + monitoring |

---

## Local Development

### Environment Variables (SigmaSight backend/.env)
```
STOCKFUND_API_URL=http://localhost:8001
STOCKFUND_API_KEY=dev_key_for_local
EDGAR_ENABLED=true
```

### Start Services
```bash
# Terminal 1: StockFundamentals
cd ../StockFundamentals/backend
uv run uvicorn app.main:app --port 8001

# Terminal 2: SigmaSight Backend
cd backend
uv run python run.py

# Terminal 3: SigmaSight Frontend
cd frontend
npm run dev
```

---

## Reference

For full code samples (Dockerfiles, Python clients, Pydantic schemas, API endpoints), see:
- `EDGAR_FUNDAMENTALS_INTEGRATION_PLAN.md` (original 3,399-line version)

*Condensed version - ~300 lines vs 3,399 lines in original*
